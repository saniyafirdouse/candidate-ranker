"""
rank.py
-------
Main entry point for the candidate ranking engine.

Usage:
    python rank.py
    python rank.py --candidates data/candidates.jsonl --out submission.csv
    python rank.py --sample 500   # quick test on first N candidates

Produces submission.csv with columns:
    candidate_id, rank, score, reasoning

Runs in < 5 minutes on CPU with 16GB RAM. No network calls.
"""

import argparse
import csv
import time
from pathlib import Path
from tqdm import tqdm

from src.loader import stream_candidates
from src.feature_extractor import extract_features
from src.scorer import score_candidate
from src.signals import apply_behavioral_multiplier
from src.honeypot import apply_honeypot_penalty
from src.explainer import generate_reasoning
from src.evaluation import run_full_evaluation


# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_CANDIDATES = "data/candidates.jsonl"
DEFAULT_OUTPUT     = "submission.csv"
TOP_N              = 100


def parse_args():
    parser = argparse.ArgumentParser(
        description="Intelligent Candidate Ranking Engine"
    )
    parser.add_argument(
        "--candidates",
        default=DEFAULT_CANDIDATES,
        help=f"Path to candidates JSONL file (default: {DEFAULT_CANDIDATES})"
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Only process first N candidates (for quick testing)"
    )
    parser.add_argument(
        "--no-eval",
        action="store_true",
        help="Skip evaluation report (faster)"
    )
    return parser.parse_args()


def process_candidate(candidate: dict) -> dict:
    """
    Full pipeline for one candidate:
    extract → score → signals → honeypot → return result dict.
    """
    features     = extract_features(candidate)
    score_result = score_candidate(features)
    signals      = candidate.get("redrob_signals", {})

    # Apply behavioral multiplier (0.85 – 1.10)
    after_signals, multiplier = apply_behavioral_multiplier(
        score_result["penalized_score"], signals
    )

    # Apply honeypot penalty (graduated 0.0 – 1.0)
    final_score, honeypot_penalty, honeypot_reason = apply_honeypot_penalty(
        after_signals, candidate
    )

    return {
        "candidate_id":    candidate["candidate_id"],
        "final_score":     final_score,
        "features":        features,
        "score_result":    score_result,
        "multiplier":      multiplier,
        "honeypot_penalty": honeypot_penalty,
        "honeypot_reason": honeypot_reason,
    }


def write_csv(ranked_results: list[dict], output_path: str) -> None:
    """
    Writes the top 100 results to a CSV file.
    Format: candidate_id, rank, score, reasoning
    Scores are non-increasing (required by validator).
    Tie-break: candidate_id ascending (required by validator).
    """
    top100 = ranked_results[:TOP_N]

    # Sort by score desc, then candidate_id asc for tie-breaking
    top100 = sorted(
        top100,
        key=lambda x: (-x["final_score"], x["candidate_id"])
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank, result in enumerate(top100, start=1):
            reasoning = generate_reasoning(
                features        = result["features"],
                score_result    = result["score_result"],
                rank            = rank,
                final_score     = result["final_score"],
                multiplier      = result["multiplier"],
                honeypot_penalty= result["honeypot_penalty"],
            )
            writer.writerow([
                result["candidate_id"],
                rank,
                round(result["final_score"], 6),
                reasoning,
            ])


def main():
    args = parse_args()
    start_time = time.time()

    print("=" * 60)
    print("  INTELLIGENT CANDIDATE RANKING ENGINE")
    print("=" * 60)
    print(f"  Input:  {args.candidates}")
    print(f"  Output: {args.out}")
    if args.sample:
        print(f"  Mode:   SAMPLE (first {args.sample} candidates)")
    else:
        print(f"  Mode:   FULL DATASET")
    print("=" * 60)

    # ── Stream and process all candidates ────────────────────────────────────
    print("\n[1/4] Processing candidates...")

    all_results = []
    count = 0

    for candidate in tqdm(
        stream_candidates(args.candidates),
        desc="Scoring",
        unit="candidates",
        total=args.sample,
    ):
        result = process_candidate(candidate)
        all_results.append(result)
        count += 1

        if args.sample and count >= args.sample:
            break

    print(f"      Processed {count:,} candidates")

    # ── Sort by final score ───────────────────────────────────────────────────
    print("\n[2/4] Ranking top 100...")
    all_results.sort(key=lambda x: (-x["final_score"], x["candidate_id"]))
    top100 = all_results[:TOP_N]
    print(f"      Top score: {top100[0]['final_score']:.4f}")
    print(f"      #100 score: {top100[-1]['final_score']:.4f}")

    # ── Write CSV ─────────────────────────────────────────────────────────────
    print(f"\n[3/4] Writing {args.out}...")
    write_csv(all_results, args.out)
    print(f"      Written: {args.out}")

    # ── Evaluation report ─────────────────────────────────────────────────────
    if not args.no_eval:
        print("\n[4/4] Running evaluation checks...")
        run_full_evaluation(all_results)

    # ── Done ──────────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print(f"\n  Total time: {elapsed:.1f}s")
    print(f"  Output:     {args.out}")
    print("  Done!\n")


if __name__ == "__main__":
    main()