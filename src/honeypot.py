"""
honeypot.py
-----------
Detects honeypot / trap candidates and returns a graduated penalty.

From the README: the dataset contains ~80 honeypots with subtly impossible
profiles. Submissions with honeypot rate > 10% in top 100 are disqualified.

Honeypot types documented:
    1. Keyword stuffers       — skills listed but zero career evidence
    2. Plain-language Tier 5s — clearly wrong domain, no AI background
    3. Behavioral twins       — copy of a real candidate with tweaked signals
    4. Impossible profiles    — e.g. 8 yrs experience at a 3yr old company

Penalty scale (graduated, not binary):
    NONE     → 1.00  (clean profile)
    MILD     → 0.70  (some inconsistency)
    SERIOUS  → 0.30  (multiple red flags)
    FATAL    → 0.00  (impossible profile — definite honeypot)
"""

from datetime import date, datetime

TODAY = date(2026, 6, 18)
TODAY_YEAR = TODAY.year


# ─────────────────────────────────────────────────────────────────────────────
# INDIVIDUAL CHECKS
# ─────────────────────────────────────────────────────────────────────────────

def _check_experience_vs_career(candidate: dict) -> tuple[bool, str]:
    """
    Check 1: Does claimed years_of_experience match actual career history?

    Honeypot pattern: profile says 8 yrs experience but career history
    only adds up to 2 years total.
    """
    claimed_yoe = candidate["profile"].get("years_of_experience", 0) or 0
    career = candidate.get("career_history", [])

    if not career:
        if claimed_yoe > 1:
            return True, f"claims {claimed_yoe}yrs experience but has no career history"
        return False, ""

    # Sum up all career months
    total_months = sum(job.get("duration_months", 0) or 0 for job in career)
    total_years = total_months / 12.0

    # Allow 2 year gap (career gaps, freelance, education overlap)
    gap = claimed_yoe - total_years
    if gap > 3:
        return True, f"claims {claimed_yoe}yrs but career history only shows {total_years:.1f}yrs"

    return False, ""


def _check_company_age_vs_tenure(candidate: dict) -> tuple[bool, str]:
    """
    Check 2: Did the candidate work at a company before it existed?

    Classic honeypot: joined a startup in 2018 but startup was founded in 2021.
    We detect this by checking if start_date is unreasonably early for
    very small companies (proxy: company_size = 1-10 or 11-50).
    """
    for job in candidate.get("career_history", []):
        try:
            start = date.fromisoformat(job.get("start_date", "2000-01-01"))
        except Exception:
            continue

        size = job.get("company_size", "")
        duration = job.get("duration_months", 0) or 0

        # If a tiny company has someone with implausibly long tenure
        # (e.g. 10+ years at a 1-10 person company = suspicious)
        if size == "1-10" and duration > 120:
            return True, f"implausible: {duration} months at a 1-10 person company ({job.get('company', '')})"

        # End date before start date
        end_str = job.get("end_date")
        if end_str:
            try:
                end = date.fromisoformat(end_str)
                if end < start:
                    return True, f"end_date {end} is before start_date {start} at {job.get('company', '')}"
            except Exception:
                pass

    return False, ""


def _check_future_dates(candidate: dict) -> tuple[bool, str]:
    """
    Check 3: Are any dates set in the future (beyond today)?

    Honeypot pattern: start_date or education end_year in the future.
    """
    for job in candidate.get("career_history", []):
        try:
            start = date.fromisoformat(job.get("start_date", "2000-01-01"))
            if start > TODAY:
                return True, f"future start_date {start} at {job.get('company', '')}"
        except Exception:
            pass

    for edu in candidate.get("education", []):
        end_year = edu.get("end_year", 0)
        if end_year > TODAY_YEAR + 1:
            return True, f"future education end_year {end_year} at {edu.get('institution', '')}"

    return False, ""


def _check_skill_keyword_stuffing(candidate: dict) -> tuple[bool, str]:
    """
    Check 4: Does the candidate have many AI skills listed but zero
    career evidence for any of them?

    Classic keyword stuffer pattern:
        - 10+ AI/ML skills in skills section
        - Career history has NO mention of ML/AI work
        - All skills have 0 endorsements

    This is the most common trap type.
    """
    from src.jd_parser import get_evidence_keywords
    evidence_keywords = get_evidence_keywords()

    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])

    # Build career text
    career_text = " ".join(
        (job.get("description", "") + " " + job.get("title", "")).lower()
        for job in career
    )

    # Count AI/ML skills listed
    ai_skill_names = [
        "python", "pytorch", "tensorflow", "rag", "embedding", "faiss",
        "pinecone", "qdrant", "milvus", "llm", "fine-tuning", "lora",
        "transformers", "hugging face", "nlp", "vector", "langchain",
        "mlflow", "kubeflow", "xgboost", "deep learning", "neural"
    ]

    ai_skills_listed = sum(
        1 for s in skills
        if any(a in s["name"].lower() for a in ai_skill_names)
    )

    # Check career evidence
    career_evidence_hits = sum(
        1 for kw in evidence_keywords if kw in career_text
    )

    # Check endorsements on AI skills
    zero_endorsement_ai = sum(
        1 for s in skills
        if any(a in s["name"].lower() for a in ai_skill_names)
        and s.get("endorsements", 0) == 0
    )

    # Flag: many AI skills, zero career evidence, mostly zero endorsements
    if ai_skills_listed >= 6 and career_evidence_hits == 0 and zero_endorsement_ai >= 4:
        return True, (
            f"keyword stuffer: {ai_skills_listed} AI skills listed, "
            f"0 career evidence hits, {zero_endorsement_ai} skills with 0 endorsements"
        )

    return False, ""


def _check_impossible_signals(candidate: dict) -> tuple[bool, str]:
    """
    Check 5: Are the redrob_signals internally inconsistent?

    Honeypot signal patterns:
        - profile_completeness = 100 but many fields missing
        - endorsements_received = 0 but connection_count = 500+
        - offer_acceptance_rate = 1.0 but interview_completion_rate = 0.0
        - github_activity_score > 0 but no technical skills whatsoever
    """
    signals = candidate.get("redrob_signals", {})
    skills = candidate.get("skills", [])

    # Perfect completeness but very few skills
    completeness = signals.get("profile_completeness_score", 0)
    if completeness >= 98 and len(skills) < 3:
        return True, f"profile_completeness={completeness} but only {len(skills)} skills listed"

    # High connections but zero endorsements (fake network)
    connections = signals.get("connection_count", 0)
    endorsements = signals.get("endorsements_received", 0)
    if connections >= 400 and endorsements == 0:
        return True, f"suspicious: {connections} connections but 0 endorsements received"

    # Accepted all offers but never completed an interview
    offer_rate = signals.get("offer_acceptance_rate", -1)
    interview_rate = signals.get("interview_completion_rate", 0)
    if offer_rate == 1.0 and interview_rate == 0.0:
        return True, "impossible: offer_acceptance=1.0 but interview_completion=0.0"

    return False, ""


def _check_title_skill_mismatch(candidate: dict) -> tuple[bool, str]:
    """
    Check 6: Does the candidate's entire career contradict their skills?

    Tier 5 plain-language trap:
        - Entire career in HR/Marketing/Civil Engineering
        - But skills section lists Python, RAG, Embeddings, LLMs
        - No career description mentions anything technical

    This catches the 'wrong domain' trap candidates.
    """
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])

    non_tech_titles = [
        "hr manager", "marketing manager", "accountant", "civil engineer",
        "mechanical engineer", "customer support", "content writer",
        "operations manager", "brand manager", "sales manager",
        "graphic designer", "project manager", "business development"
    ]

    tech_skills = [
        "python", "pytorch", "tensorflow", "rag", "faiss", "pinecone",
        "llm", "embeddings", "vector", "nlp", "machine learning",
        "deep learning", "transformers", "hugging face"
    ]

    # Check if ALL career titles are non-technical
    if not career:
        return False, ""

    all_non_tech = all(
        any(nt in job.get("title", "").lower() for nt in non_tech_titles)
        for job in career
    )

    # Count tech skills listed
    tech_skills_count = sum(
        1 for s in skills
        if any(t in s["name"].lower() for t in tech_skills)
    )

    if all_non_tech and tech_skills_count >= 4:
        titles = [job.get("title", "") for job in career]
        return True, (
            f"domain mismatch: entire career in {titles} "
            f"but lists {tech_skills_count} technical AI skills"
        )

    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN HONEYPOT DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

def compute_honeypot_penalty(candidate: dict) -> tuple[float, str]:
    """
    Runs all honeypot checks and returns a graduated penalty + reason.

    Penalty scale:
        0 flags  → 1.00  NONE
        1 flag   → 0.70  MILD
        2 flags  → 0.30  SERIOUS
        3+ flags → 0.00  FATAL

    Args:
        candidate: raw candidate dict from loader

    Returns:
        tuple: (penalty_multiplier, reason_string)
    """
    checks = [
        _check_experience_vs_career,
        _check_company_age_vs_tenure,
        _check_future_dates,
        _check_skill_keyword_stuffing,
        _check_impossible_signals,
        _check_title_skill_mismatch,
    ]

    flags = []
    for check in checks:
        flagged, reason = check(candidate)
        if flagged:
            flags.append(reason)

    flag_count = len(flags)

    if flag_count == 0:
        return 1.00, "clean"
    elif flag_count == 1:
        return 0.70, f"MILD: {flags[0]}"
    elif flag_count == 2:
        return 0.30, f"SERIOUS: {'; '.join(flags)}"
    else:
        return 0.00, f"FATAL: {'; '.join(flags)}"


def apply_honeypot_penalty(score: float, candidate: dict) -> tuple[float, float, str]:
    """
    Applies honeypot penalty to a score.

    Args:
        score:     current score (after behavioral multiplier)
        candidate: raw candidate dict

    Returns:
        tuple: (final_score, penalty_multiplier, reason)
    """
    penalty, reason = compute_honeypot_penalty(candidate)
    final = round(score * penalty, 6)
    return final, penalty, reason