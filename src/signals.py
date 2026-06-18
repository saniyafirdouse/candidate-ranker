"""
signals.py
----------
Converts raw redrob_signals into a behavioral multiplier (0.85 – 1.10).

Design principle: signals NUDGE rankings, they don't redefine them.
A great candidate who is slightly inactive stays great.
A weak candidate who is very active stays weak.

Multiplier range: 0.85 (bad signals) → 1.0 (neutral) → 1.10 (great signals)
"""

from datetime import date

TODAY = date(2026, 6, 18)


def _days_since(date_str: str) -> int:
    """Days between a date string and TODAY."""
    try:
        d = date.fromisoformat(date_str)
        return (TODAY - d).days
    except Exception:
        return 9999


def _activity_score(signals: dict) -> float:
    """
    How recently and actively is the candidate engaging on the platform?

    Signals used:
        - last_active_date     → recency
        - open_to_work_flag    → explicitly looking
        - applications_submitted_30d → actively applying
        - search_appearance_30d → being found by recruiters
        - saved_by_recruiters_30d → recruiters are interested

    Returns -1.0 to +1.0
    """
    score = 0.0

    # Recency of last activity
    days = _days_since(signals.get("last_active_date", "2000-01-01"))
    if days <= 7:
        score += 0.4       # active this week
    elif days <= 30:
        score += 0.3       # active this month
    elif days <= 90:
        score += 0.1       # active this quarter
    elif days <= 180:
        score -= 0.1       # going cold
    else:
        score -= 0.4       # very inactive

    # Open to work flag
    if signals.get("open_to_work_flag", False):
        score += 0.2

    # Actively applying (1–5 applications = healthy, >10 = desperate signal)
    apps = signals.get("applications_submitted_30d", 0)
    if 1 <= apps <= 5:
        score += 0.1
    elif apps > 10:
        score -= 0.05      # slight concern — mass applying

    # Being found + saved by recruiters
    saved = signals.get("saved_by_recruiters_30d", 0)
    if saved >= 5:
        score += 0.15
    elif saved >= 2:
        score += 0.05

    return max(-1.0, min(1.0, score))


def _reliability_score(signals: dict) -> float:
    """
    How reliable and professional is this candidate in the hiring process?

    Signals used:
        - recruiter_response_rate  → do they respond to recruiters?
        - avg_response_time_hours  → how fast?
        - interview_completion_rate → do they show up?
        - offer_acceptance_rate    → do they ghost after offer?
        - verified_email + phone   → basic trust

    Returns -1.0 to +1.0
    """
    score = 0.0

    # Recruiter response rate (0 – 1)
    response_rate = signals.get("recruiter_response_rate", 0)
    if response_rate >= 0.7:
        score += 0.2
    elif response_rate >= 0.4:
        score += 0.1
    elif response_rate < 0.2:
        score -= 0.15

    # Response time
    response_time = signals.get("avg_response_time_hours", 999)
    if response_time <= 4:
        score += 0.15
    elif response_time <= 24:
        score += 0.1
    elif response_time > 72:
        score -= 0.1

    # Interview completion
    interview_rate = signals.get("interview_completion_rate", 0)
    if interview_rate >= 0.8:
        score += 0.2
    elif interview_rate >= 0.6:
        score += 0.1
    elif interview_rate < 0.4:
        score -= 0.2

    # Offer acceptance (-1 means no history — neutral)
    offer_rate = signals.get("offer_acceptance_rate", -1)
    if offer_rate >= 0.7:
        score += 0.1
    elif 0 <= offer_rate < 0.3:
        score -= 0.1       # accepts then backs out often

    # Verified contact
    if signals.get("verified_email", False) and signals.get("verified_phone", False):
        score += 0.1
    elif not signals.get("verified_email", False):
        score -= 0.05

    return max(-1.0, min(1.0, score))


def _technical_signal_score(signals: dict) -> float:
    """
    Technical credibility signals from the platform.

    Signals used:
        - github_activity_score    → real code activity
        - skill_assessment_scores  → platform-verified skills
        - profile_completeness     → effort put into profile

    Returns -1.0 to +1.0
    """
    score = 0.0

    # GitHub activity (-1 = no GitHub linked)
    github = signals.get("github_activity_score", -1)
    if github >= 70:
        score += 0.4
    elif github >= 40:
        score += 0.2
    elif github >= 10:
        score += 0.05
    elif github == -1:
        score -= 0.05      # no GitHub is a mild negative for an AI engineer role
    else:
        score -= 0.1       # linked but barely active

    # Skill assessments
    assessments = signals.get("skill_assessment_scores", {})
    if assessments:
        avg = sum(assessments.values()) / len(assessments)
        if avg >= 75:
            score += 0.3
        elif avg >= 55:
            score += 0.15
        elif avg >= 40:
            score += 0.05
        else:
            score -= 0.05  # took assessments but scored poorly

    # Profile completeness
    completeness = signals.get("profile_completeness_score", 0)
    if completeness >= 90:
        score += 0.1
    elif completeness >= 70:
        score += 0.05
    elif completeness < 40:
        score -= 0.1

    return max(-1.0, min(1.0, score))


def _notice_period_score(signals: dict) -> float:
    """
    Notice period fit against JD expectations.
    Sub-30 days = great. 30-60 = acceptable. 60-90 = ok. 90+ = concern.

    Returns -1.0 to +1.0
    """
    notice = signals.get("notice_period_days", 90)
    if notice <= 15:
        return 0.4
    elif notice <= 30:
        return 0.3
    elif notice <= 60:
        return 0.1
    elif notice <= 90:
        return -0.1
    else:
        return -0.3


def compute_behavioral_multiplier(signals: dict) -> float:
    """
    Combines all signal scores into a single multiplier (0.85 – 1.10).

    The multiplier is built from 4 sub-scores, each weighted:
        activity      35%   — are they active and findable?
        reliability   35%   — will they show up and not ghost?
        technical     20%   — GitHub + assessments
        notice        10%   — can they join quickly?

    Raw combined score maps linearly to 0.85 – 1.10 range.

    Args:
        signals: candidate['redrob_signals']

    Returns:
        float: multiplier in range [0.85, 1.10]
    """
    activity    = _activity_score(signals)
    reliability = _reliability_score(signals)
    technical   = _technical_signal_score(signals)
    notice      = _notice_period_score(signals)

    # Weighted combination → range is roughly -1.0 to +1.0
    combined = (
        activity    * 0.35
        + reliability * 0.35
        + technical   * 0.20
        + notice      * 0.10
    )

    # Map [-1.0, +1.0] → [0.85, 1.10]
    # midpoint (0.0) → 1.0 (neutral, no effect)
    # +1.0 → 1.10 (best signals add 10%)
    # -1.0 → 0.85 (worst signals subtract 15%)
    multiplier = 1.0 + (combined * 0.125)

    # Asymmetric clamp: bad signals hurt slightly more than good signals help
    return round(max(0.85, min(1.10, multiplier)), 4)


def apply_behavioral_multiplier(penalized_score: float, signals: dict) -> tuple[float, float]:
    """
    Applies behavioral multiplier to a penalized score.

    Args:
        penalized_score: output of scorer.apply_penalties()
        signals:         candidate['redrob_signals']

    Returns:
        tuple: (final_score, multiplier_used)
    """
    multiplier = compute_behavioral_multiplier(signals)
    final = round(max(0.0, min(1.0, penalized_score * multiplier)), 6)
    return final, multiplier