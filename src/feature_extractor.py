"""
feature_extractor.py
--------------------
Converts a raw candidate dict into a flat feature dict.
scorer.py only sees this output — never the raw candidate.

Core principle: Evidence > Keywords
A skill mentioned in career history beats a skill just listed in the skills section.
"""

from datetime import date
from src.jd_parser import get_jd_profile

# Load JD once at module level — not on every candidate
JD = get_jd_profile()

# Reference date for recency calculations
TODAY = date(2026, 6, 18)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase + strip for consistent matching."""
    return text.lower().strip()


def _get_all_career_text(candidate: dict) -> str:
    """
    Concatenates all career description text into one lowercase string.
    This is what we search for evidence of skills actually being used.
    """
    parts = []
    for job in candidate.get("career_history", []):
        parts.append(job.get("description", ""))
        parts.append(job.get("title", ""))
    # Also include profile summary — candidates describe their real work there
    parts.append(candidate.get("profile", {}).get("summary", ""))
    parts.append(candidate.get("profile", {}).get("headline", ""))
    return " ".join(parts).lower()


def _get_career_titles(candidate: dict) -> list[str]:
    """Returns list of all job titles the candidate has held, lowercased."""
    titles = []
    for job in candidate.get("career_history", []):
        titles.append(_normalize(job.get("title", "")))
    titles.append(_normalize(candidate.get("profile", {}).get("current_title", "")))
    return titles


def _get_skill_names(candidate: dict) -> list[str]:
    """Returns lowercased skill names from the skills section."""
    return [_normalize(s["name"]) for s in candidate.get("skills", [])]


def _get_skill_map(candidate: dict) -> dict:
    """Returns {skill_name_lower: skill_dict} for quick lookup."""
    return {
        _normalize(s["name"]): s
        for s in candidate.get("skills", [])
    }


def _days_since(date_str: str) -> int:
    """Returns number of days between a date string and TODAY."""
    try:
        d = date.fromisoformat(date_str)
        return (TODAY - d).days
    except Exception:
        return 9999  # treat missing as very old


def _months_at_product_companies(candidate: dict) -> float:
    """
    Returns fraction of total career months spent at product companies.
    Product = NOT a consulting firm AND industry is not pure IT Services outsourcing.
    """
    consulting_firms = JD["consulting_firms"]
    total_months = 0
    product_months = 0

    for job in candidate.get("career_history", []):
        duration = job.get("duration_months", 0) or 0
        total_months += duration
        company = _normalize(job.get("company", ""))
        industry = _normalize(job.get("industry", ""))
        is_consulting = any(f in company for f in consulting_firms)
        is_outsourcing = industry in ("it services", "bpo", "outsourcing")
        if not is_consulting and not is_outsourcing:
            product_months += duration

    if total_months == 0:
        return 0.0
    return product_months / total_months


# ─────────────────────────────────────────────────────────────────────────────
# EVIDENCE SCORING
# ─────────────────────────────────────────────────────────────────────────────

def _career_evidence_score(career_text: str) -> float:
    """
    Searches career text for JD evidence keywords.
    Returns 0.0 – 1.0 based on how many evidence keywords appear.

    This is the core of 'evidence over keywords'.
    """
    keywords = JD["evidence_keywords"]
    hits = sum(1 for kw in keywords if kw in career_text)
    # Cap at 10 hits for full score — more than 10 is still 1.0
    return min(hits / 10.0, 1.0)


def _skill_evidence_multiplier(skill_name: str, career_text: str) -> float:
    """
    For a given skill, checks if it actually appears in career text.

    Returns:
        1.0  — strong evidence (skill name or synonym found in career text)
        0.7  — moderate (related keyword found)
        0.4  — weak (skill listed but career text has vague/adjacent mention)
        0.1  — no evidence (pure keyword stuffer)
    """
    name = _normalize(skill_name)

    # Strong: exact skill name in career text
    if name in career_text:
        return 1.0

    # Check synonyms / short forms
    synonyms = {
        "faiss": ["faiss", "facebook ai similarity"],
        "qdrant": ["qdrant"],
        "pinecone": ["pinecone"],
        "milvus": ["milvus"],
        "weaviate": ["weaviate"],
        "opensearch": ["opensearch", "open search"],
        "elasticsearch": ["elasticsearch", "elastic search"],
        "rag": ["rag", "retrieval augmented", "retrieval-augmented"],
        "embeddings": ["embedding", "embeddings", "embed"],
        "fine-tuning llms": ["fine-tun", "finetuning", "fine tuning", "lora", "qlora", "peft"],
        "sentence transformers": ["sentence-transformer", "sentence transformer", "sbert"],
        "hugging face": ["hugging face", "huggingface", "hf transformers"],
        "lora": ["lora", "qlora", "low-rank"],
        "peft": ["peft", "parameter efficient"],
        "ndcg": ["ndcg", "normalized discounted"],
        "mrr": ["mrr", "mean reciprocal"],
        "vector database": ["vector db", "vector database", "vectordb"],
        "learning to rank": ["learning to rank", "ltr", "listwise", "pairwise rank"],
    }

    if name in synonyms:
        for syn in synonyms[name]:
            if syn in career_text:
                return 1.0

    # Moderate: related broader keyword found
    related = {
        "faiss": ["similarity search", "ann", "approximate nearest"],
        "qdrant": ["vector search", "vector store"],
        "pinecone": ["vector search", "vector store"],
        "rag": ["retrieval", "knowledge base", "document search"],
        "embeddings": ["semantic", "representation", "dense"],
        "fine-tuning llms": ["llm", "language model", "foundation model"],
        "ndcg": ["evaluation", "metric", "ranking quality"],
        "learning to rank": ["ranking", "reranking", "relevance"],
    }

    if name in related:
        for rel in related[name]:
            if rel in career_text:
                return 0.7

    # Weak: at least something vaguely AI/ML in career
    ai_adjacent = ["machine learning", "ml ", "deep learning", "neural", "model", "ai "]
    if any(a in career_text for a in ai_adjacent):
        return 0.4

    # No evidence
    return 0.1


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENT EXTRACTORS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_title_score(candidate: dict) -> float:
    """
    Scores how well the candidate's career titles match JD target titles.
    Current title counts most; historical titles also matter.

    Returns 0.0 – 1.0
    """
    all_titles = _get_career_titles(candidate)
    target_titles = JD["target_titles"]
    disqualifying = JD["disqualifying_titles"]

    # Current title gets 2x weight
    current = _normalize(candidate["profile"].get("current_title", ""))

    score = 0.0

    # Check current title
    if any(t in current for t in target_titles):
        score += 0.6
    elif any(d in current for d in disqualifying):
        score -= 0.3   # penalty but not zero — they might have career pivoted

    # Check historical titles
    historical = all_titles[:-1]  # exclude current (already scored)
    for title in historical:
        if any(t in title for t in target_titles):
            score += 0.15
            break  # one good historical title is enough

    # Clamp
    return max(0.0, min(1.0, score))


def _extract_skills_score(candidate: dict, career_text: str) -> float:
    """
    Scores skill match against JD required + preferred skills.
    Each skill is weighted by its evidence multiplier (career-backed vs listed only).

    Returns 0.0 – 1.0
    """
    skill_names = _get_skill_names(candidate)
    skill_map = _get_skill_map(candidate)
    required = JD["required_skills"]
    preferred = JD["preferred_skills"]

    required_score = 0.0
    preferred_score = 0.0

    # Score required skills (weight: 0.7 of total)
    for req in required:
        # Check if candidate has this skill (by name or partial match)
        matched_skill = None
        for sname in skill_names:
            if req in sname or sname in req:
                matched_skill = sname
                break

        if matched_skill:
            evidence = _skill_evidence_multiplier(matched_skill, career_text)
            proficiency = skill_map.get(matched_skill, {})
            prof_bonus = {
                "expert": 1.0, "advanced": 0.85,
                "intermediate": 0.7, "beginner": 0.5
            }.get(proficiency.get("proficiency", "beginner"), 0.5)
            required_score += evidence * prof_bonus
        else:
            # Skill not listed — but check if it appears in career text anyway
            if req in career_text:
                required_score += 0.5  # career evidence without explicit skill listing

    # Normalize required score
    required_score = min(required_score / len(required), 1.0)

    # Score preferred skills (weight: 0.3 of total)
    for pref in preferred:
        matched_skill = None
        for sname in skill_names:
            if pref in sname or sname in pref:
                matched_skill = sname
                break
        if matched_skill:
            evidence = _skill_evidence_multiplier(matched_skill, career_text)
            preferred_score += evidence
        elif pref in career_text:
            preferred_score += 0.4

    preferred_score = min(preferred_score / len(preferred), 1.0)

    return (required_score * 0.7) + (preferred_score * 0.3)


def _extract_experience_score(candidate: dict) -> float:
    """
    Scores years of experience against JD range.
    Sweet spot (6-8 yrs) gets full score. Outside range gets penalized.

    Returns 0.0 – 1.0
    """
    yoe = candidate["profile"].get("years_of_experience", 0) or 0
    exp_min = JD["experience_min"]
    exp_max = JD["experience_max"]
    sweet_min = JD["experience_sweet_spot_min"]
    sweet_max = JD["experience_sweet_spot_max"]

    if sweet_min <= yoe <= sweet_max:
        return 1.0
    elif exp_min <= yoe < sweet_min:
        # Slightly under sweet spot — still good
        return 0.8
    elif sweet_max < yoe <= exp_max:
        # Slightly over sweet spot — still acceptable
        return 0.8
    elif yoe > exp_max:
        # Overqualified — penalty scales with how far over
        over = yoe - exp_max
        return max(0.4, 0.8 - (over * 0.05))
    elif yoe < exp_min:
        # Underqualified
        under = exp_min - yoe
        return max(0.1, 0.6 - (under * 0.1))
    return 0.5


def _extract_location_score(candidate: dict) -> float:
    """
    Scores location fit.
    Preferred Indian cities > India generally > willing to relocate > outside India.

    Returns 0.0 – 1.0
    """
    profile = candidate["profile"]
    location = _normalize(profile.get("location", ""))
    country = _normalize(profile.get("country", ""))
    willing = candidate.get("redrob_signals", {}).get("willing_to_relocate", False)
    preferred_locs = JD["preferred_locations"]

    # Exact preferred city match
    if any(city in location for city in preferred_locs):
        return 1.0

    # India but not preferred city — still decent
    if country == "india":
        if willing:
            return 0.85
        return 0.7

    # Outside India but willing to relocate
    if willing:
        return 0.4

    # Outside India and not willing
    return 0.1


def _extract_education_score(candidate: dict) -> float:
    """
    Scores education quality. Low weight (2%) per the JD's emphasis.
    Tier 1 > Tier 2 > Tier 3 > Tier 4.
    CS/related field gets a small bonus.

    Returns 0.0 – 1.0
    """
    education = candidate.get("education", [])
    if not education:
        return 0.3

    tier_scores = {
        "tier_1": 1.0,
        "tier_2": 0.8,
        "tier_3": 0.55,
        "tier_4": 0.3,
        "unknown": 0.4,
    }

    relevant_fields = [
        "computer science", "cs", "information technology",
        "ai", "machine learning", "data science",
        "mathematics", "statistics", "electronics"
    ]

    best_score = 0.0
    for edu in education:
        tier = edu.get("tier", "unknown")
        field = _normalize(edu.get("field_of_study", ""))
        base = tier_scores.get(tier, 0.4)
        field_bonus = 0.1 if any(f in field for f in relevant_fields) else 0.0
        best_score = max(best_score, min(1.0, base + field_bonus))

    return best_score


def _extract_product_company_ratio(candidate: dict) -> float:
    """
    Returns 0.0 – 1.0 representing fraction of career at product companies.
    """
    return _months_at_product_companies(candidate)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

def extract_features(candidate: dict) -> dict:
    """
    Main function. Takes a raw candidate dict, returns a clean feature dict.

    Args:
        candidate: raw candidate dict from loader

    Returns:
        dict with all features scorer.py needs
    """
    profile = candidate["profile"]
    signals = candidate.get("redrob_signals", {})
    career_text = _get_all_career_text(candidate)

    # ── Core scores ──────────────────────────────────────────────────────────
    title_score = _extract_title_score(candidate)
    skills_score = _extract_skills_score(candidate, career_text)
    experience_score = _extract_experience_score(candidate)
    location_score = _extract_location_score(candidate)
    education_score = _extract_education_score(candidate)
    product_ratio = _extract_product_company_ratio(candidate)

    # ── Career evidence ──────────────────────────────────────────────────────
    career_evidence = _career_evidence_score(career_text)

    # ── Behavioral signals (raw — signals.py will convert to multiplier) ─────
    days_inactive = _days_since(signals.get("last_active_date", "2000-01-01"))
    open_to_work = signals.get("open_to_work_flag", False)
    notice_days = signals.get("notice_period_days", 90)
    github_score = signals.get("github_activity_score", -1)
    profile_completeness = signals.get("profile_completeness_score", 0)
    recruiter_response_rate = signals.get("recruiter_response_rate", 0)
    interview_completion = signals.get("interview_completion_rate", 0)
    offer_acceptance = signals.get("offer_acceptance_rate", -1)
    verified = (
        signals.get("verified_email", False) and
        signals.get("verified_phone", False)
    )

    # Skill assessment scores from the platform (if any)
    assessment_scores = signals.get("skill_assessment_scores", {})
    avg_assessment = (
        sum(assessment_scores.values()) / len(assessment_scores)
        if assessment_scores else -1
    )

    # ── Flags ────────────────────────────────────────────────────────────────
    current_title = _normalize(profile.get("current_title", ""))
    current_company = _normalize(profile.get("current_company", ""))

    is_disqualifying_title = any(
        d in current_title for d in JD["disqualifying_titles"]
    )
    is_consulting_current = any(
        f in current_company for f in JD["consulting_firms"]
    )
    has_consulting_history = any(
        any(f in _normalize(job.get("company", "")) for f in JD["consulting_firms"])
        for job in candidate.get("career_history", [])
    )

    return {
        # Identity
        "candidate_id": candidate["candidate_id"],

        # Component scores (0.0 – 1.0 each)
        "title_score": round(title_score, 4),
        "skills_score": round(skills_score, 4),
        "experience_score": round(experience_score, 4),
        "location_score": round(location_score, 4),
        "education_score": round(education_score, 4),
        "product_ratio": round(product_ratio, 4),
        "career_evidence": round(career_evidence, 4),

        # Raw behavioral signals
        "days_inactive": days_inactive,
        "open_to_work": open_to_work,
        "notice_days": notice_days,
        "github_score": github_score,
        "profile_completeness": profile_completeness,
        "recruiter_response_rate": recruiter_response_rate,
        "interview_completion": interview_completion,
        "offer_acceptance": offer_acceptance,
        "avg_assessment_score": avg_assessment,
        "verified": verified,

        # Flags
        "is_disqualifying_title": is_disqualifying_title,
        "is_consulting_current": is_consulting_current,
        "has_consulting_history": has_consulting_history,
        "years_of_experience": profile.get("years_of_experience", 0),
        "current_title": profile.get("current_title", ""),
        "current_company": profile.get("current_company", ""),
        "location": profile.get("location", ""),
        "country": profile.get("country", ""),

        # For explainer.py
        "career_text_snippet": career_text[:300],
    }