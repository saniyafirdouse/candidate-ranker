from src.loader import load_sample
from src.honeypot import compute_honeypot_penalty

sample = load_sample('data/candidates.jsonl', n=50)

flagged = []
clean = 0

for c in sample:
    penalty, reason = compute_honeypot_penalty(c)
    if penalty < 1.0:
        flagged.append((c['candidate_id'], c['profile']['current_title'], penalty, reason))
    else:
        clean += 1

print(f"Clean: {clean} | Flagged: {len(flagged)}\n")
print("Flagged candidates:")
for cid, title, penalty, reason in flagged:
    print(f"  {cid} | {title[:30]:<30} | penalty={penalty:.2f} | {reason[:80]}")
