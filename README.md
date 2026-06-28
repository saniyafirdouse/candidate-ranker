# 🔍 Intelligent Candidate Discovery & Ranking Engine

> **Hack2Skill × Redrob — Track 1: AI & Datathon Arena**  
> Evidence-based candidate ranking for a Senior AI Engineer role across 100,000 candidates.

---

## 🏆 Results at a Glance

| Metric | Result |
|---|---|
| Candidates processed | 100,000 |
| Runtime (CPU only) | **49.1 seconds** |
| Honeypot leakage rate | **0.0%** (limit: 10%) |
| Consulting firms in top 100 | **0 / 100** |
| Open to work (top 100) | **76 / 100** |
| Unique companies (top 100) | **40** |
| Scores non-increasing | ✅ Yes |
| Passes `validate_submission.py` | ✅ Yes |

---

## 🧠 Core Philosophy

> **Evidence > Keywords. Career trajectory > Skills list.**

Traditional ATS systems rank candidates by keyword frequency.
This engine ranks by **career evidence** — whether a skill appears in actual
job descriptions, responsibilities, and achievements, not just a skills checklist.

A candidate who lists *"RAG, Pinecone, LLMs"* in their skills section but has
zero career evidence scores far lower than someone whose job description reads:
*"Built production RAG pipeline using Pinecone and LangChain, serving 10M users."*

---

## 📁 Project Structure
candidate-ranker/

│

├── data/

│   ├── candidates.jsonl          # 100K candidate pool (not committed — 465MB)

│   ├── job_description.docx      # Target JD

│   └── sample_candidates.json   # First 50 candidates for testing

│

├── src/

│   ├── init.py

│   ├── loader.py                 # Stream candidates from JSONL without RAM spike

│   ├── jd_parser.py              # Structured JD profile: skills, titles, exclusions

│   ├── feature_extractor.py     # Evidence-backed feature extraction per candidate

│   ├── scorer.py                 # Weighted multi-component scoring with penalties

│   ├── signals.py                # Behavioral multiplier from 23 Redrob signals

│   ├── honeypot.py               # Graduated fraud/trap detection

│   ├── explainer.py              # Honest per-candidate reasoning generation

│   └── evaluation.py            # Pre-submission sanity checks

│

├── rank.py                       # CLI entry point → produces submission.csv

├── app.py                        # Streamlit sandbox UI

├── validate_submission.py        # Official hackathon format validator

├── requirements.txt

├── submission_metadata.yaml

└── README.md

---

## ⚙️ Scoring Pipeline
candidates.jsonl

│

▼

┌─────────────┐

│   loader    │  Streams JSONL line by line — no full file in RAM

└──────┬──────┘

│

▼

┌──────────────────┐

│ feature_extractor│  Extracts 20+ features per candidate:

│                  │  title_score, skills_score (with evidence multiplier),

│                  │  experience_score, location_score, education_score,

│                  │  product_ratio, career_evidence, behavioral signals

└──────┬───────────┘

│

▼

┌─────────────┐

│   scorer    │  Weighted combination → base score

│             │  + consulting/title penalties → penalized score

│             │

│  Weights:   │

│  skills 30% │  (career-backed, not just listed)

│  title  25% │

│  exp    20% │

│  product 10%│

│  location 8%│

│  education 2%│

│  misc    5% │

└──────┬──────┘

│

▼

┌─────────────┐

│  signals    │  23 Redrob behavioral signals →

│             │  multiplier × 0.85 – 1.10

│             │  (activity, reliability, GitHub, notice period)

└──────┬──────┘

│

▼

┌─────────────┐

│  honeypot   │  6 fraud checks → graduated penalty:

│             │  clean × 1.00 | mild × 0.70

│             │  serious × 0.30 | fatal × 0.00

└──────┬──────┘

│

▼

┌─────────────┐

│  explainer  │  Honest 1–2 sentence reasoning per candidate

│             │  reflects actual scores, names penalties explicitly

└──────┬──────┘

│

▼

submission.csv

(top 100, ranked, validated)

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Add the dataset
data/candidates.jsonl        ← from hackathon bundle

data/job_description.docx    ← from hackathon bundle

data/sample_candidates.json  ← from hackathon bundle
### 3. Run on full dataset

```bash
python rank.py --out submission.csv
```

Expected output:
INTELLIGENT CANDIDATE RANKING ENGINE

Input:  data/candidates.jsonl

Output: submission.csv

Mode:   FULL DATASET
[1/4] Processing candidates...

Scoring: 100%|████████████| 100000/100000

Processed 100,000 candidates
[2/4] Ranking top 100...

Top score: 0.8514

#100 score: 0.7696
[3/4] Writing submission.csv...

Written: submission.csv
[4/4] Running evaluation checks...

✅ OVERALL: READY TO SUBMIT
Total time: 49.1s

### 4. Validate before submitting

```bash
python validate_submission.py submission.csv
# Submission is valid.
```

### 5. Run sandbox UI

```bash
streamlit run app.py --server.maxUploadSize 500
```

Upload `data/sample_candidates.json` in the browser.

---

## 🔬 Feature Extraction — Evidence Over Keywords

The most important design decision in this system is the **evidence multiplier** on skills.

Every skill listed in a candidate's profile is checked against their career descriptions:

| Evidence level | How detected | Multiplier |
|---|---|---|
| **Strong** | Skill name / synonym found in job description text | × 1.00 |
| **Moderate** | Related keyword found in career text | × 0.70 |
| **Weak** | Vague AI/ML mention in career | × 0.40 |
| **None** | Skill listed but zero career evidence | × 0.10 |

Example:
- Candidate A: lists *"Pinecone"* in skills → score contribution × 0.10
- Candidate B: career description contains *"built vector search pipeline on Pinecone"* → × 1.00

This single mechanism eliminates most keyword stuffers from the top 100.

---

## 🛡️ Honeypot Detection

The dataset contains ~80 honeypot profiles with subtly impossible characteristics.
Submissions with >10% honeypots in top 100 are disqualified.

Six checks run on every candidate:

| Check | Pattern detected |
|---|---|
| Experience vs career gap | Claims 15 yrs, career history shows 0.5 yrs |
| Future dates | `start_date` or education `end_year` in the future |
| Company age vs tenure | 10-year tenure at a 3-year-old startup |
| Keyword stuffing | 8+ AI skills listed, 0 career evidence hits, 0 endorsements |
| Impossible signals | 500 connections, 0 endorsements received |
| Domain mismatch | Entire career in HR/Marketing + 7 AI skills listed |

Penalty scale:
- **0 flags** → × 1.00 (clean)
- **1 flag** → × 0.70 (mild)
- **2 flags** → × 0.30 (serious)
- **3+ flags** → × 0.00 (fatal — zeroed out)

Result: **0 honeypots in our top 100**.

---

## 📡 Behavioral Signals

23 Redrob platform signals are combined into a fine-tuning multiplier (× 0.85 – 1.10).

Signals are grouped into four categories:

| Category | Weight | Key signals |
|---|---|---|
| Activity | 35% | Last active date, open to work flag, applications submitted, saved by recruiters |
| Reliability | 35% | Recruiter response rate, response time, interview completion, offer acceptance |
| Technical | 20% | GitHub activity score, platform assessment scores, profile completeness |
| Notice period | 10% | Days to join vs JD expectation (ideal ≤ 30 days) |

Design principle: **signals nudge rankings, they don't flip them.**
Range is intentionally narrow (0.85–1.10) so a great candidate who is slightly
inactive stays great, and a weak candidate who is very active stays weak.

---

## 💬 Explainability

Every candidate in the output CSV has a 1–2 sentence reasoning
that reflects their **actual scores** — not generic text.

Examples:
Ranked #1 (0.851): Senior ML Engineer at Zomato; career evidence of rag,

retrieval; 7.2yr mostly at product companies.
Ranked #3 (0.438): 6.7yr mostly at product companies.

Concerns: long notice period (90 days).
Ranked #7 (0.355): 9.7yr mostly at product companies.

Concerns: some consulting background, 120-day notice period.

Rules:
- Reasoning only references what was actually scored
- Penalties are named explicitly (consulting background, notice period, location)
- No hallucination — reasoning is generated from the feature dict, not from an LLM

---

## 🔧 CLI Reference

```bash
# Full run
python rank.py

# Custom input/output
python rank.py --candidates data/candidates.jsonl --out submission.csv

# Quick test on first 500 candidates
python rank.py --sample 500 --out submission_test.csv

# Skip evaluation report
python rank.py --no-eval --out submission.csv

# Validate output
python validate_submission.py submission.csv

# Streamlit sandbox
streamlit run app.py --server.maxUploadSize 500
```

---

## 📦 Dependencies
pandas>=2.0.0          # Data manipulation and CSV output

numpy>=1.24.0          # Numerical operations

scikit-learn>=1.3.0    # Utility functions

python-docx>=1.1.0     # JD parsing

streamlit>=1.35.0      # Sandbox UI

python-dateutil>=2.8.0 # Date parsing for honeypot checks

tqdm>=4.66.0           # Progress bar
No GPU required. No external API calls at inference time.
Runs on any machine with Python 3.11+ and 4GB+ RAM.

---

## 🤖 AI Tools Declaration

- **Claude (Anthropic)** — architecture discussion, code review, README drafting
- **GitHub Copilot** — autocomplete during development

No candidate data was fed to any LLM.
All scoring logic, weights, and heuristics are original engineering decisions.

---

## 📄 Reproduce Command

```bash
python rank.py --candidates ./data/candidates.jsonl --out ./submission.csv
```

Runtime: ~50 seconds on CPU. No network. No GPU.

---

*Built for Hack2Skill × Redrob Track 1 — Intelligent Candidate Discovery & Ranking Challenge*