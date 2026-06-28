from src.loader import load_sample
from src.feature_extractor import extract_features
from src.scorer import score_candidate
from src.signals import apply_behavioral_multiplier
from src.honeypot import apply_honeypot_penalty
from src.explainer import generate_reasoning

sample = load_sample('data/candidates.jsonl', n=50)
results = []

for c in sample:
    features = extract_features(c)
    score_result = score_candidate(features)
    signals = c['redrob_signals']

    scored, multiplier = apply_behavioral_multiplier(
        score_result['penalized_score'], signals
    )
    final_score, honeypot_penalty, _ = apply_honeypot_penalty(scored, c)

    results.append({
        "candidate_id": c['candidate_id'],
        "final_score": final_score,
        "features": features,
        "score_result": score_result,
        "multiplier": multiplier,
        "honeypot_penalty": honeypot_penalty,
    })

# Sort and rank
results.sort(key=lambda x: x['final_score'], reverse=True)

print("Top 10 candidates with reasoning:\n")
for rank, r in enumerate(results[:10], start=1):
    reasoning = generate_reasoning(
        features=r['features'],
        score_result=r['score_result'],
        rank=rank,
        final_score=r['final_score'],
        multiplier=r['multiplier'],
        honeypot_penalty=r['honeypot_penalty'],
    )
    print(f"  {r['candidate_id']} | score={r['final_score']:.4f}")
    print(f"  {reasoning}")
    print()