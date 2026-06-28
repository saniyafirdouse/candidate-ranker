from src.loader import load_sample
from src.feature_extractor import extract_features
from src.scorer import score_candidate

sample = load_sample('data/candidates.jsonl', n=50)
results = []

for c in sample:
    f = extract_features(c)
    r = score_candidate(f)
    results.append(r)

results.sort(key=lambda x: x['penalized_score'], reverse=True)

print('Top 5 from first 50 candidates:')
for r in results[:5]:
    f = r['features']
    print(f"  {r['candidate_id']} | {f['current_title'][:28]:<28} | {f['current_company']:<20} | score={r['penalized_score']:.4f}")