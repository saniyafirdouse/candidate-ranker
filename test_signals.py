from src.loader import load_sample
from src.feature_extractor import extract_features
from src.scorer import score_candidate
from src.signals import apply_behavioral_multiplier, compute_behavioral_multiplier

sample = load_sample('data/candidates.jsonl', n=5)

for c in sample:
    features = extract_features(c)
    result = score_candidate(features)
    signals = c['redrob_signals']

    multiplier = compute_behavioral_multiplier(signals)
    final_score, _ = apply_behavioral_multiplier(result['penalized_score'], signals)

    print(
        result['candidate_id'], '|',
        c['profile']['current_title'][:20].ljust(20), '|',
        f"penalized={result['penalized_score']:.4f}",
        f"× multiplier={multiplier:.4f}",
        f"= final={final_score:.4f}",
        f"| active={signals['last_active_date']}",
        f"open={signals['open_to_work_flag']}"
    )