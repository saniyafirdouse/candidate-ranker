"""
evaluation.py
-------------
Sanity checks on your top-100 output before submission.

Answers these questions:
    - Did any honeypots survive into top 100?
    - Are all 100 from one company? (diversity check)
    - Are too many consultants getting through?
    - Is the score distribution healthy?
    - Are there duplicate candidate IDs?
"""

from collections import Counter


def check_honeypot_leakage(ranked_results: list[dict]) -> dict:
    """
    Checks how many honeypots made it into the top 100.
    Disqualification threshold: > 10% (more than 10 out of 100).

    Args:
        ranked_results: list of result dicts containing honeypot_penalty

    Returns:
        dict with leakage stats
    """
    top100 = ranked_results[:100]
    honeypots = [r for r in top100 if r.get("honeypot_penalty", 1.0) < 1.0]
    fatal = [r for r in top100 if r.get("honeypot_penalty", 1.0) == 0.0]
    serious = [r for r in top100 if r.get("honeypot_penalty", 1.0) == 0.3]
    mild = [r for r in top100 if r.get("honeypot_penalty", 1.0) == 0.7]

    leakage_rate = len(honeypots) / len(top100) if top100 else 0
    safe = leakage_rate <= 0.10

    return {
        "total_flagged": len(honeypots),
        "fatal_count": len(fatal),
        "serious_count": len(serious),
        "mild_count": len(mild),
        "leakage_rate": round(leakage_rate, 3),
        "safe": safe,
        "status": "✅ SAFE" if safe else "❌ DISQUALIFICATION RISK",
    }


def check_company_diversity(ranked_results: list[dict]) -> dict:
    """
    Checks if the top 100 is too concentrated in one company.
    A good ranking should have diverse company representation.

    Args:
        ranked_results: list of result dicts

    Returns:
        dict with diversity stats
    """
    top100 = ranked_results[:100]
    companies = [
        r.get("features", {}).get("current_company", "Unknown")
        for r in top100
    ]
    company_counts = Counter(companies)
    most_common = company_counts.most_common(5)
    top_company, top_count = most_common[0] if most_common else ("None", 0)

    return {
        "unique_companies": len(company_counts),
        "top_company": top_company,
        "top_company_count": top_count,
        "top_5_companies": most_common,
        "status": (
            "✅ DIVERSE" if top_count <= 20
            else "⚠️ WARNING: too concentrated" if top_count <= 35
            else "❌ PROBLEM: over-concentrated"
        ),
    }


def check_consulting_ratio(ranked_results: list[dict]) -> dict:
    """
    Checks what fraction of top 100 are at consulting firms.
    JD explicitly penalises consulting backgrounds.

    Args:
        ranked_results: list of result dicts

    Returns:
        dict with consulting stats
    """
    top100 = ranked_results[:100]
    consulting_current = sum(
        1 for r in top100
        if r.get("features", {}).get("is_consulting_current", False)
    )
    consulting_history = sum(
        1 for r in top100
        if r.get("features", {}).get("has_consulting_history", False)
    )

    ratio = consulting_current / len(top100) if top100 else 0

    return {
        "consulting_current_count": consulting_current,
        "consulting_history_count": consulting_history,
        "consulting_current_ratio": round(ratio, 3),
        "status": (
            "✅ GOOD" if ratio <= 0.15
            else "⚠️ WARNING: high consulting ratio" if ratio <= 0.30
            else "❌ PROBLEM: too many consultants"
        ),
    }


def check_score_distribution(ranked_results: list[dict]) -> dict:
    """
    Checks if the score distribution looks healthy.
    Red flags: all scores are the same, or top score is very low.

    Args:
        ranked_results: list of result dicts

    Returns:
        dict with score distribution stats
    """
    top100 = ranked_results[:100]
    if not top100:
        return {"status": "❌ NO RESULTS"}

    scores = [r.get("final_score", 0) for r in top100]
    top_score = scores[0] if scores else 0
    bottom_score = scores[-1] if scores else 0
    avg_score = sum(scores) / len(scores) if scores else 0

    # Check scores are non-increasing
    is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

    return {
        "top_score": round(top_score, 4),
        "bottom_score": round(bottom_score, 4),
        "avg_score": round(avg_score, 4),
        "score_range": round(top_score - bottom_score, 4),
        "is_non_increasing": is_sorted,
        "status": (
            "✅ HEALTHY" if top_score >= 0.3 and is_sorted and (top_score - bottom_score) > 0.05
            else "⚠️ WARNING: narrow score range" if (top_score - bottom_score) <= 0.05
            else "❌ PROBLEM: scores not sorted or top score too low"
        ),
    }


def check_duplicates(ranked_results: list[dict]) -> dict:
    """
    Checks for duplicate candidate IDs in top 100.

    Args:
        ranked_results: list of result dicts

    Returns:
        dict with duplicate stats
    """
    top100 = ranked_results[:100]
    ids = [r.get("candidate_id", "") for r in top100]
    unique_ids = set(ids)
    duplicates = [cid for cid, count in Counter(ids).items() if count > 1]

    return {
        "total": len(ids),
        "unique": len(unique_ids),
        "duplicates": duplicates,
        "status": "✅ CLEAN" if not duplicates else f"❌ DUPLICATES: {duplicates}",
    }


def check_open_to_work_ratio(ranked_results: list[dict]) -> dict:
    """
    What fraction of top 100 are actively open to work?
    Higher is better — these candidates will actually respond.
    """
    top100 = ranked_results[:100]
    open_count = sum(
        1 for r in top100
        if r.get("features", {}).get("open_to_work", False)
    )
    ratio = open_count / len(top100) if top100 else 0

    return {
        "open_to_work_count": open_count,
        "ratio": round(ratio, 3),
        "status": (
            "✅ GREAT" if ratio >= 0.5
            else "⚠️ OK" if ratio >= 0.3
            else "⚠️ LOW: few candidates open to work"
        ),
    }


def run_full_evaluation(ranked_results: list[dict]) -> None:
    """
    Runs all checks and prints a full evaluation report.

    Args:
        ranked_results: sorted list of result dicts (best first)
    """
    print("=" * 60)
    print("  SUBMISSION EVALUATION REPORT")
    print(f"  Total candidates ranked: {len(ranked_results)}")
    print("=" * 60)

    # 1. Honeypot leakage
    hp = check_honeypot_leakage(ranked_results)
    print(f"\n📍 Honeypot Leakage: {hp['status']}")
    print(f"   Flagged in top 100: {hp['total_flagged']} "
          f"(fatal={hp['fatal_count']}, serious={hp['serious_count']}, mild={hp['mild_count']})")
    print(f"   Leakage rate: {hp['leakage_rate']:.1%} (limit: 10%)")

    # 2. Duplicates
    dup = check_duplicates(ranked_results)
    print(f"\n📍 Duplicate IDs: {dup['status']}")
    print(f"   Unique candidates: {dup['unique']} / {dup['total']}")

    # 3. Score distribution
    sd = check_score_distribution(ranked_results)
    print(f"\n📍 Score Distribution: {sd['status']}")
    print(f"   Top={sd['top_score']}  Bottom={sd['bottom_score']}  "
          f"Avg={sd['avg_score']}  Range={sd['score_range']}")
    print(f"   Scores non-increasing: {sd['is_non_increasing']}")

    # 4. Company diversity
    cd = check_company_diversity(ranked_results)
    print(f"\n📍 Company Diversity: {cd['status']}")
    print(f"   Unique companies: {cd['unique_companies']}")
    print(f"   Top 5 companies: {cd['top_5_companies']}")

    # 5. Consulting ratio
    cr = check_consulting_ratio(ranked_results)
    print(f"\n📍 Consulting Ratio: {cr['status']}")
    print(f"   Currently at consulting: {cr['consulting_current_count']}/100 "
          f"({cr['consulting_current_ratio']:.1%})")

    # 6. Open to work
    ow = check_open_to_work_ratio(ranked_results)
    print(f"\n📍 Open to Work: {ow['status']}")
    print(f"   Open to work: {ow['open_to_work_count']}/100 ({ow['ratio']:.1%})")

    print("\n" + "=" * 60)

    # Final verdict
    all_safe = (
        hp["safe"] and
        not dup["duplicates"] and
        sd["is_non_increasing"] and
        sd["top_score"] >= 0.2
    )
    if all_safe:
        print("  ✅ OVERALL: READY TO SUBMIT")
    else:
        print("  ❌ OVERALL: ISSUES FOUND — fix before submitting")
    print("=" * 60)