"""
explainer.py
------------
Generates honest 1-2 sentence reasoning for each ranked candidate.
This goes into the 'reasoning' column of the submission CSV.

Design principle: reasoning must reflect the ACTUAL scores, not be generic.
Bad: "Strong candidate with relevant skills and experience."
Good: "Ranked #3 for RAG pipeline and Pinecone production experience at Swiggy (6yr);
       penalized slightly for 45-day notice period."
"""

from src.jd_parser import get_jd_profile

JD = get_jd_profile()

# Skills we specifically call out if found in career text
HIGHLIGHT_SKILLS = [
    "rag", "retrieval", "embedding", "embeddings", "vector",
    "faiss", "pinecone", "qdrant", "milvus", "weaviate",
    "opensearch", "elasticsearch", "fine-tun", "fine tuning",
    "lora", "qlora", "peft", "llm", "language model",
    "ranking", "reranking", "semantic search", "dense retrieval",
    "ndcg", "mrr", "a/b test", "pytorch", "transformers",
    "hugging face", "sentence-transformer", "langchain",
    "production", "deployed", "shipped", "scaled",
    "kubeflow", "mlflow", "airflow",
]

# Proficiency labels for readability
PROFICIENCY_LABEL = {
    "expert": "expert-level",
    "advanced": "strong",
    "intermediate": "working knowledge of",
    "beginner": "basic",
}


def _find_highlighted_skills(features: dict) -> list[str]:
    """
    Finds JD-relevant skills that the candidate actually has,
    preferring ones backed by career evidence.
    Returns up to 3 most relevant skill names.
    """
    career_text = features.get("career_text_snippet", "").lower()
    skill_names = []

    # Pull from career text first (evidence-backed)
    for kw in HIGHLIGHT_SKILLS:
        if kw in career_text and kw not in skill_names:
            skill_names.append(kw)
        if len(skill_names) >= 3:
            break

    return skill_names


def _format_experience(features: dict) -> str:
    """Returns a readable experience string like '6.5yr at product companies'."""
    yoe = features.get("years_of_experience", 0)
    product_ratio = features.get("product_ratio", 0)
    company = features.get("current_company", "")

    yoe_str = f"{yoe:.0f}yr" if yoe == int(yoe) else f"{yoe:.1f}yr"

    if product_ratio >= 0.8:
        return f"{yoe_str} mostly at product companies"
    elif product_ratio >= 0.5:
        return f"{yoe_str} mixed product/consulting background"
    elif product_ratio < 0.3 and features.get("is_consulting_current", False):
        return f"{yoe_str} primarily at consulting firms"
    else:
        return f"{yoe_str} experience"


def _build_strength_clause(features: dict, score_result: dict) -> str:
    """
    Builds the positive part of the reasoning.
    Focuses on what actually drove the score up.
    """
    components = score_result.get("component_scores", {})
    skills_score = components.get("skills", 0)
    title_score = components.get("title", 0)
    career_evidence = features.get("career_evidence", 0)

    highlighted = _find_highlighted_skills(features)
    exp_str = _format_experience(features)
    title = features.get("current_title", "")
    company = features.get("current_company", "")

    parts = []

    # Lead with title if it's a strong match
    if title_score >= 0.5:
        parts.append(f"{title} at {company}")
    elif title_score >= 0.3:
        parts.append(f"{title} background")

    # Lead with career evidence if strong
    if highlighted and career_evidence >= 0.3:
        skill_str = ", ".join(highlighted[:2])
        parts.append(f"career evidence of {skill_str}")
    elif highlighted:
        skill_str = ", ".join(highlighted[:2])
        parts.append(f"skills include {skill_str}")

    # Experience
    parts.append(exp_str)

    if not parts:
        return f"{title} with {exp_str}"

    return "; ".join(parts)


def _build_weakness_clause(features: dict, score_result: dict,
                            multiplier: float, honeypot_penalty: float) -> str:
    """
    Builds the penalty/concern part of the reasoning.
    Only included if there are real concerns.
    """
    concerns = []
    penalties = score_result.get("penalties", {})

    # Title penalty
    if penalties.get("disqualifying_title", False):
        concerns.append("non-technical current role")

    # Consulting penalty
    if penalties.get("consulting_current", False):
        concerns.append("currently at consulting firm")
    elif penalties.get("consulting_history", False):
        concerns.append("some consulting background")

    # Location
    loc_score = score_result.get("component_scores", {}).get("location", 0)
    if loc_score <= 0.1:
        country = features.get("country", "")
        if country.lower() not in ("india", ""):
            concerns.append(f"based outside India ({country})")
        concerns.append("not willing to relocate")
    elif loc_score <= 0.4:
        concerns.append("relocation required")

    # Notice period
    notice = features.get("notice_days", 30)
    if notice > 90:
        concerns.append(f"{notice}-day notice period")
    elif notice > 60:
        concerns.append(f"long notice period ({notice} days)")

    # Behavioral multiplier
    if multiplier < 0.92:
        concerns.append("low platform activity")
    elif multiplier < 0.96:
        concerns.append("moderate platform engagement")

    # Honeypot
    if honeypot_penalty <= 0.3:
        concerns.append("profile inconsistencies detected")

    if not concerns:
        return ""

    return "Concerns: " + ", ".join(concerns[:3])  # cap at 3 concerns


def generate_reasoning(
    features: dict,
    score_result: dict,
    rank: int,
    final_score: float,
    multiplier: float,
    honeypot_penalty: float,
) -> str:
    """
    Generates a 1-2 sentence reasoning string for the CSV.

    Args:
        features:        output of feature_extractor.extract_features()
        score_result:    output of scorer.score_candidate()
        rank:            final rank (1-100)
        final_score:     final score after all multipliers
        multiplier:      behavioral multiplier used
        honeypot_penalty: honeypot penalty used

    Returns:
        str: 1-2 sentence reasoning for the reasoning column
    """
    strength = _build_strength_clause(features, score_result)
    weakness = _build_weakness_clause(features, score_result, multiplier, honeypot_penalty)

    # Build sentence 1 — what's good about them
    sentence1 = f"Ranked #{rank} ({final_score:.3f}): {strength}."

    # Build sentence 2 — concerns if any
    if weakness:
        sentence2 = weakness + "."
        return f"{sentence1} {sentence2}"

    return sentence1


def generate_bulk_reasoning(ranked_results: list[dict]) -> dict[str, str]:
    """
    Generates reasoning for all ranked candidates at once.

    Args:
        ranked_results: list of dicts, each containing:
            - features, score_result, rank, final_score,
              multiplier, honeypot_penalty

    Returns:
        dict: {candidate_id: reasoning_string}
    """
    reasoning_map = {}

    for item in ranked_results:
        cid = item["features"]["candidate_id"]
        reasoning = generate_reasoning(
            features=item["features"],
            score_result=item["score_result"],
            rank=item["rank"],
            final_score=item["final_score"],
            multiplier=item["multiplier"],
            honeypot_penalty=item["honeypot_penalty"],
        )
        reasoning_map[cid] = reasoning

    return reasoning_map