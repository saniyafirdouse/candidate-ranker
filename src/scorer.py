"""
scorer.py
---------
Combines feature dict into a single final score (0.0 - 1.0).

Weights (sum to 1.0):
    skill_evidence    30%   — career-backed skill match (most important)
    title_career      25%   — title + career trajectory
    experience        20%   — years + product company quality
    product_history   10%   — fraction of career at product companies
    location          8%    — location fit
    education         2%    — institution tier + field
    misc              5%    — profile completeness + assessments

Then multiplied by:
    behavioral_multiplier   (0.85 – 1.10)  from signals.py
    honeypot_penalty        (0.0  – 1.0)   from honeypot.py
"""

from src.jd_parser import get_jd_profile

JD = get_jd_profile()

# ── Weights ───────────────────────────────────────────────────────────────────
WEIGHTS = {
    "skills":      0.30,
    "title":       0.25,
    "experience":  0.20,
    "product":     0.10,
    "location":    0.08,
    "education":   0.02,
    "misc":        0.05,
}


def _misc_score(features: dict) -> float:
    """
    Small catch-all score for signals that don't fit elsewhere.
    Profile completeness + platform assessment scores.

    Returns 0.0 – 1.0
    """
    score = 0.0
    count = 0

    # Profile completeness (0 – 100 → 0.0 – 1.0)
    completeness = features.get("profile_completeness", 0)
    score += completeness / 100.0
    count += 1

    # Platform assessment scores if available
    avg_assessment = features.get("avg_assessment_score", -1)
    if avg_assessment >= 0:
        score += avg_assessment / 100.0
        count += 1

    # Verified contact details — small trust signal
    if features.get("verified", False):
        score += 0.8
        count += 1

    return score / count if count > 0 else 0.3


def _combine_experience(features: dict) -> float:
    """
    Blends raw experience score with product company ratio.
    Product company experience is worth more than consulting years.

    Returns 0.0 – 1.0
    """
    exp_score = features.get("experience_score", 0.0)
    product_ratio = features.get("product_ratio", 0.0)

    # 70% raw experience fit, 30% quality of that experience
    return (exp_score * 0.70) + (product_ratio * 0.30)


def _combine_skills(features: dict) -> float:
    """
    Blends skills score with career evidence score.
    Career evidence is a strong signal that skills are real.

    Returns 0.0 – 1.0
    """
    skills_score = features.get("skills_score", 0.0)
    career_evidence = features.get("career_evidence", 0.0)

    # 60% skill match, 40% career text evidence
    return (skills_score * 0.60) + (career_evidence * 0.40)


def compute_base_score(features: dict) -> float:
    """
    Computes the weighted base score from feature components.
    Does NOT apply behavioral multiplier or honeypot penalty yet.

    Args:
        features: output of feature_extractor.extract_features()

    Returns:
        float: base score 0.0 – 1.0
    """
    skills_combined = _combine_skills(features)
    experience_combined = _combine_experience(features)
    misc = _misc_score(features)

    base = (
        skills_combined                         * WEIGHTS["skills"]
        + features.get("title_score", 0.0)     * WEIGHTS["title"]
        + experience_combined                   * WEIGHTS["experience"]
        + features.get("product_ratio", 0.0)   * WEIGHTS["product"]
        + features.get("location_score", 0.0)  * WEIGHTS["location"]
        + features.get("education_score", 0.0) * WEIGHTS["education"]
        + misc                                  * WEIGHTS["misc"]
    )

    return round(max(0.0, min(1.0, base)), 6)


def apply_penalties(base_score: float, features: dict) -> float:
    """
    Applies hard rule penalties on top of the base score.
    These are deterministic rules, not ML — fully explainable.

    Penalties applied:
        - Disqualifying current title:   × 0.5
        - Currently at consulting firm:  × 0.75
        - Consulting career history:     × 0.88
        - Outside India, won't relocate: (already handled in location_score)

    Args:
        base_score: output of compute_base_score()
        features:   feature dict

    Returns:
        float: penalized score 0.0 – 1.0
    """
    score = base_score

    # Disqualifying title — e.g. Marketing Manager, HR Manager
    # Still not zero because they may have pivoted in career history
    if features.get("is_disqualifying_title", False):
        score *= 0.5

    # Currently at a consulting / outsourcing firm
    if features.get("is_consulting_current", False):
        score *= 0.75

    # Has consulting history but not current
    elif features.get("has_consulting_history", False):
        score *= 0.88

    return round(max(0.0, min(1.0, score)), 6)


def score_candidate(features: dict) -> dict:
    """
    Full scoring pipeline for one candidate.
    Returns a score dict with base, penalized, and component breakdown.

    Note: behavioral_multiplier and honeypot_penalty are applied later
    in rank.py after signals.py and honeypot.py run.

    Args:
        features: output of feature_extractor.extract_features()

    Returns:
        dict with score breakdown
    """
    base = compute_base_score(features)
    penalized = apply_penalties(base, features)

    return {
        "candidate_id": features["candidate_id"],
        "base_score": base,
        "penalized_score": penalized,

        # Component breakdown for explainer.py
        "component_scores": {
            "skills":     round(_combine_skills(features), 4),
            "title":      round(features.get("title_score", 0.0), 4),
            "experience": round(_combine_experience(features), 4),
            "product":    round(features.get("product_ratio", 0.0), 4),
            "location":   round(features.get("location_score", 0.0), 4),
            "education":  round(features.get("education_score", 0.0), 4),
            "misc":       round(_misc_score(features), 4),
        },

        # Penalty flags for explainer.py
        "penalties": {
            "disqualifying_title": features.get("is_disqualifying_title", False),
            "consulting_current":  features.get("is_consulting_current", False),
            "consulting_history":  features.get("has_consulting_history", False),
        },

        # Pass-through for later steps
        "features": features,
    }