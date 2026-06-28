from src.loader import load_sample
from src.feature_extractor import extract_features
from src.scorer import score_candidate

sample = load_sample('data/candidates.jsonl', n=5)

for c in sample:
    features = extract_features(c)
    result = score_candidate(features)
    print(
        result['candidate_id'], '|',
        result['features']['current_title'][:22].ljust(22), '|',
        'base=', f"{result['base_score']:.4f}",
        'penalized=', f"{result['penalized_score']:.4f}",
        '| components:', {k: v for k, v in result['component_scores'].items()}
    )