"""
app.py - Intelligent Candidate Ranking Engine
Run: streamlit run app.py --server.maxUploadSize 500
"""

import json, io, time
import streamlit as st
import pandas as pd

from src.feature_extractor import extract_features
from src.scorer import score_candidate
from src.signals import apply_behavioral_multiplier
from src.honeypot import apply_honeypot_penalty
from src.explainer import generate_reasoning
from src.jd_parser import get_jd_profile

st.set_page_config(
    page_title="Candidate Ranking Engine",
    page_icon="🔍",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.hero {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-left: 4px solid #059669;
    border-radius: 12px;
    padding: 32px 40px;
    margin-bottom: 24px;
}
.hero .badge {
    display: inline-block;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    color: #166534;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
    text-transform: uppercase;
}
.hero h1 { font-size: 1.9rem; font-weight: 700; margin: 0 0 6px 0; color: #111827; }
.hero p  { font-size: 0.9rem; color: #6b7280; margin: 0; }
.pill {
    display: inline-block;
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-radius: 5px;
    padding: 1px 9px;
    margin: 0 3px;
    font-size: 0.8rem;
    color: #374151;
}

.sec-head {
    font-size: 0.95rem; font-weight: 700; color: #111827;
    padding-bottom: 8px;
    border-bottom: 1px solid #f3f4f6;
    margin: 24px 0 14px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.step-row { display: flex; gap: 10px; margin-bottom: 20px; }
.step-card {
    flex: 1; background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px; padding: 16px;
}
.step-num {
    width: 24px; height: 24px;
    background: #f0fdf4; color: #166534;
    border: 1px solid #bbf7d0;
    border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.75rem;
    margin-bottom: 8px;
}
.step-card h4 { margin: 0 0 4px 0; font-size: 0.85rem; font-weight: 600; color: #111827; display: inline; margin-left: 6px; }
.step-card p  { margin: 6px 0 0 0; font-size: 0.78rem; color: #6b7280; line-height: 1.5; }

.upload-zone {
    border: 1px dashed #d1d5db; border-radius: 10px;
    padding: 28px 20px; text-align: center;
    background: #fafafa; margin-bottom: 12px;
}
.upload-zone .uz-icon  { font-size: 2rem; margin-bottom: 8px; }
.upload-zone .uz-title { font-size: 0.9rem; font-weight: 600; color: #111827; margin-bottom: 3px; }
.upload-zone .uz-sub   { font-size: 0.77rem; color: #9ca3af; }
.upload-zone .uz-tip   {
    display: inline-block; margin-top: 8px;
    background: #f0fdf4; border: 1px solid #bbf7d0;
    color: #166534; border-radius: 5px;
    padding: 2px 10px; font-size: 0.74rem; font-weight: 500;
}

.box-warn {
    background: #fffbeb; border: 1px solid #fde68a;
    border-radius: 7px; padding: 12px 16px;
    color: #92400e; font-size: 0.85rem;
    margin: 8px 0;
}
.box-ok {
    background: #f0fdf4; border: 1px solid #bbf7d0;
    border-radius: 7px; padding: 12px 16px;
    color: #166534; font-size: 0.85rem;
    margin: 8px 0;
}

.m-row { display: flex; gap: 10px; margin: 16px 0; flex-wrap: wrap; }
.m-card {
    flex: 1; min-width: 100px;
    background: #ffffff; border: 1px solid #e5e7eb;
    border-radius: 8px; padding: 14px 12px; text-align: center;
}
.m-card .mv { font-size: 1.6rem; font-weight: 700; line-height: 1; color: #111827; }
.m-card .ml { font-size: 0.68rem; color: #9ca3af; margin-top: 4px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.3px; }
.m-card .ms { font-size: 0.68rem; margin-top: 3px; color: #9ca3af; }
.c-green { color: #059669 !important; }
.c-red   { color: #dc2626 !important; }
.c-amber { color: #d97706 !important; }

.empty-wrap {
    border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 48px 32px; text-align: center;
    background: #fafafa; margin-top: 8px;
}
.empty-wrap .ei { font-size: 2.8rem; margin-bottom: 10px; }
.empty-wrap h3  { font-size: 1rem; font-weight: 600; color: #111827; margin: 0 0 6px 0; }
.empty-wrap p   { font-size: 0.82rem; color: #6b7280; margin: 0; line-height: 1.7; }
.es-cmd {
    display: inline-block; margin-top: 14px;
    background: #1f2937; color: #d1d5db;
    border-radius: 6px; padding: 7px 16px;
    font-family: monospace; font-size: 0.8rem;
}
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="badge">🏆 Hack2Skill × Redrob — Track 1 · AI & Datathon Arena</div>
    <h1>🔍 Intelligent Candidate Ranking Engine</h1>
    <p>
        <span class="pill">Evidence &gt; Keywords</span>
        <span class="pill">Career trajectory &gt; Skills list</span>
        <span class="pill">100K candidates · Sub-60s · CPU only · No API calls</span>
    </p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Job Description")
    jd = get_jd_profile()
    st.markdown("**Role:** Senior AI Engineer (Founding Team)")
    st.markdown(
        f"**Experience:** {jd['experience_min']}–{jd['experience_max']} yrs &nbsp;|&nbsp; "
        f"Sweet spot: {jd['experience_sweet_spot_min']}–{jd['experience_sweet_spot_max']} yrs"
    )
    st.markdown("**Required Skills**")
    req_tags = "".join([
        f'<span style="background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;'
        f'border-radius:4px;padding:2px 6px;font-size:0.7rem;margin:2px;display:inline-block">{s}</span>'
        for s in jd["required_skills"]
    ])
    st.markdown(req_tags, unsafe_allow_html=True)

    st.markdown("**Preferred Skills**")
    pref_tags = "".join([
        f'<span style="background:#f9fafb;color:#374151;border:1px solid #e5e7eb;'
        f'border-radius:4px;padding:2px 6px;font-size:0.7rem;margin:2px;display:inline-block">{s}</span>'
        for s in jd["preferred_skills"]
    ])
    st.markdown(pref_tags, unsafe_allow_html=True)

    st.markdown("**Preferred Locations**")
    st.caption(", ".join(jd["preferred_locations"]))

    st.markdown(
        f"**Notice:** Ideal ≤{jd['notice_ideal_days']}d · "
        f"OK up to {jd['notice_acceptable_days']}d"
    )
    st.markdown(f"**Salary:** ₹{jd['salary_min_lpa']}–{jd['salary_max_lpa']} LPA")
    st.markdown("**Prefer product companies** over consulting firms")

    st.markdown("---")
    st.markdown("**Scoring Weights**")
    for name, pct, color in [
        ("Skill Evidence", 30, "#059669"),
        ("Title & Career", 25, "#10b981"),
        ("Experience",     20, "#34d399"),
        ("Product Co.",    10, "#6ee7b7"),
        ("Location",        8, "#a7f3d0"),
        ("Misc",            5, "#d1fae5"),
        ("Education",       2, "#ecfdf5"),
    ]:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
            f'<div style="width:{pct*3}px;height:5px;background:{color};'
            f'border-radius:3px;flex-shrink:0"></div>'
            f'<span style="font-size:0.76rem;color:#374151">{name} <b>{pct}%</b></span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("**Disqualifying Signals**")
    st.caption(
        "Honeypot profiles · Zero career evidence · "
        "Domain mismatch · Consulting-only background"
    )
    st.markdown("---")
    st.caption("Full 100K CLI run:\n`python rank.py --out submission.csv`")

# ── How it works ──────────────────────────────────────────────────────────────
st.markdown('<div class="sec-head">⚡ How it works</div>', unsafe_allow_html=True)
st.markdown("""
<div class="step-row">
  <div class="step-card">
    <div class="step-num">1</div><h4>📂 Upload</h4>
    <p>Upload <code>sample_candidates.json</code> from the hackathon bundle. Accepts .json or .jsonl. For the full 100K run use the CLI.</p>
  </div>
  <div class="step-card">
    <div class="step-num">2</div><h4>⚙️ Rank</h4>
    <p>Click <strong>Run Ranking</strong>. Each candidate is scored across 6 evidence-backed dimensions with honeypot detection.</p>
  </div>
  <div class="step-card">
    <div class="step-num">3</div><h4>📊 Inspect</h4>
    <p>Browse the ranked table with per-candidate reasoning. Toggle score breakdowns and behavioral signals for deeper insight.</p>
  </div>
  <div class="step-card">
    <div class="step-num">4</div><h4>⬇️ Export</h4>
    <p>Download a submission-ready CSV (top 100, ranked 1–100 with reasoning) that passes the official validator.</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Pipeline (fast st.columns, no heavy HTML) ─────────────────────────────────
st.markdown('<div class="sec-head">🔬 Scoring Pipeline</div>', unsafe_allow_html=True)

steps = [
    ("📥", "Loader",            "Stream JSONL",            False),
    ("🔬", "Feature Extractor", "Evidence features",       True),
    ("⚖️", "Scorer",            "6-component weights",     True),
    ("📡", "Signals",           "×0.85–1.10 multiplier",   False),
    ("🛡️", "Honeypot",          "Graduated penalty",       False),
    ("💬", "Explainer",         "Honest reasoning",        True),
    ("📄", "CSV Output",        "Top 100 ranked",          False),
]

cols = st.columns([3,1,3,1,3,1,3,1,3,1,3,1,3])
for i, (icon, name, desc, hl) in enumerate(steps):
    bg = "#f0fdf4" if hl else "#f9fafb"
    bd = "#bbf7d0" if hl else "#e5e7eb"
    tc = "#166534" if hl else "#374151"
    with cols[i * 2]:
        st.markdown(
            f'<div style="background:{bg};border:1px solid {bd};border-radius:8px;'
            f'padding:12px 8px;text-align:center">'
            f'<div style="font-size:1.3rem">{icon}</div>'
            f'<div style="font-size:0.7rem;font-weight:700;color:{tc};margin-top:5px">{name}</div>'
            f'<div style="font-size:0.6rem;color:#9ca3af;margin-top:2px">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    if i < len(steps) - 1:
        with cols[i * 2 + 1]:
            st.markdown(
                '<div style="text-align:center;color:#d1d5db;font-size:1.1rem;padding-top:18px">→</div>',
                unsafe_allow_html=True
            )

st.markdown("---")

# ── Upload ────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-head">📂 Upload Candidate File</div>', unsafe_allow_html=True)

st.markdown("""
<div class="upload-zone">
  <div class="uz-icon">📁</div>
  <div class="uz-title">Upload <code>sample_candidates.json</code> from the hackathon bundle</div>
  <div class="uz-sub">Accepts .json or .jsonl &nbsp;·&nbsp; Use sample file for sandbox · Full 100K via CLI</div>
  <div class="uz-tip">💡 sample_candidates.json (50 candidates, ~500KB) is ideal for this sandbox</div>
</div>
""", unsafe_allow_html=True)

col_up, col_opts = st.columns([2, 1])
with col_up:
    uploaded_file = st.file_uploader(
        "Choose file", type=["jsonl", "json"], label_visibility="collapsed"
    )
with col_opts:
    top_n           = st.slider("Top N to display", 5, 100, 10, 5)
    show_components = st.checkbox("Show score breakdown", value=False)
    show_signals    = st.checkbox("Show behavioral signals", value=False)

# ── File loaded ───────────────────────────────────────────────────────────────
if uploaded_file is not None:

    st.markdown(
        '<div class="box-warn">⏳ &nbsp; Reading file — parsing candidates, please wait...</div>',
        unsafe_allow_html=True
    )

    raw = uploaded_file.read().decode("utf-8")
    candidates = []
    try:
        for line in raw.strip().split("\n"):
            line = line.strip()
            if line:
                candidates.append(json.loads(line))
    except json.JSONDecodeError:
        candidates = json.loads(raw)

    st.markdown(
        f'<div class="box-ok">✅ &nbsp; File loaded — <strong>{len(candidates):,} candidates</strong> ready. '
        f'Click <strong>Run Ranking</strong> to start scoring.</div>',
        unsafe_allow_html=True
    )

    if st.button("🚀 Run Ranking", type="primary", use_container_width=True):

        start   = time.time()
        results = []

        # ── Single clean progress bar — no extra rerenders ─────────────────
        progress = st.progress(0, text="Scoring candidates...")

        for i, candidate in enumerate(candidates):
            try:
                features     = extract_features(candidate)
                score_result = score_candidate(features)
                signals      = candidate.get("redrob_signals", {})
                after, mult  = apply_behavioral_multiplier(
                    score_result["penalized_score"], signals
                )
                final, hp, hpr = apply_honeypot_penalty(after, candidate)
                results.append({
                    "candidate_id":     candidate["candidate_id"],
                    "final_score":      final,
                    "features":         features,
                    "score_result":     score_result,
                    "multiplier":       mult,
                    "honeypot_penalty": hp,
                    "honeypot_reason":  hpr,
                })
            except Exception as e:
                st.warning(f"Skipped {candidate.get('candidate_id','?')}: {e}")

            progress.progress(
                (i + 1) / len(candidates),
                text=f"Scoring candidates... {i+1}/{len(candidates)}"
            )

        results.sort(key=lambda x: (-x["final_score"], x["candidate_id"]))
        elapsed = time.time() - start
        progress.empty()

        top100 = results[:100]

        st.success(f"✅ Ranked {len(results):,} candidates in {elapsed:.1f}s")
        st.markdown("---")

        # ── Metric cards ──────────────────────────────────────────────────────
        open_c  = sum(1 for r in top100 if r["features"]["open_to_work"])
        consult = sum(1 for r in top100 if r["features"]["is_consulting_current"])
        hps     = sum(1 for r in top100 if r["honeypot_penalty"] < 1.0)
        avg_sc  = sum(r["final_score"] for r in top100) / len(top100)
        u_cos   = len(set(r["features"]["current_company"] for r in top100))
        india_c = sum(
            1 for r in top100
            if r["features"]["country"].lower() == "india"
        )

        hp_col = "c-green" if hps <= 10 else "c-red"
        hp_lbl = "✅ SAFE" if hps <= 10 else "❌ AT RISK"
        ow_col = "c-green" if open_c >= 50 else "c-amber"
        cn_col = "c-green" if consult == 0 else "c-amber"

        st.markdown(
            '<div class="sec-head">📊 Top-100 at a Glance</div>',
            unsafe_allow_html=True
        )
        st.markdown(f"""
        <div class="m-row">
          <div class="m-card">
            <div class="mv">{len(results):,}</div>
            <div class="ml">Scored</div>
            <div class="ms">candidates</div>
          </div>
          <div class="m-card">
            <div class="mv {ow_col}">{open_c}/100</div>
            <div class="ml">Open to Work</div>
            <div class="ms">will respond</div>
          </div>
          <div class="m-card">
            <div class="mv {cn_col}">{consult}/100</div>
            <div class="ml">Consulting</div>
            <div class="ms">currently at</div>
          </div>
          <div class="m-card">
            <div class="mv {hp_col}">{hps}/100</div>
            <div class="ml">Honeypots</div>
            <div class="ms {hp_col}">{hp_lbl}</div>
          </div>
          <div class="m-card">
            <div class="mv">{u_cos}</div>
            <div class="ml">Companies</div>
            <div class="ms">unique in top 100</div>
          </div>
          <div class="m-card">
            <div class="mv">{india_c}/100</div>
            <div class="ml">India-based</div>
            <div class="ms">preferred country</div>
          </div>
          <div class="m-card">
            <div class="mv">{avg_sc:.3f}</div>
            <div class="ml">Avg Score</div>
            <div class="ms">top 100</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Results table ─────────────────────────────────────────────────────
        st.markdown(
            f'<div class="sec-head">🏆 Top {min(top_n, len(results))} Ranked Candidates</div>',
            unsafe_allow_html=True
        )

        rows = []
        for rank, r in enumerate(results[:top_n], start=1):
            f    = r["features"]
            comp = r["score_result"]["component_scores"]
            reasoning = generate_reasoning(
                features=f, score_result=r["score_result"],
                rank=rank, final_score=r["final_score"],
                multiplier=r["multiplier"],
                honeypot_penalty=r["honeypot_penalty"],
            )
            row = {
                "Rank":     rank,
                "ID":       r["candidate_id"],
                "Score":    round(r["final_score"], 4),
                "Title":    f["current_title"],
                "Company":  f["current_company"],
                "YoE":      f["years_of_experience"],
                "Location": f["location"],
                "Reasoning": reasoning,
            }
            if show_components:
                row.update({
                    "Skills": round(comp["skills"], 3),
                    "Title S": round(comp["title"], 3),
                    "Exp":    round(comp["experience"], 3),
                    "Prod":   round(comp["product"], 3),
                })
            if show_signals:
                row.update({
                    "×Mult":  round(r["multiplier"], 3),
                    "HP":     round(r["honeypot_penalty"], 3),
                    "Open?":  "✅" if f["open_to_work"] else "❌",
                    "Notice": f"{f['notice_days']}d",
                })
            rows.append(row)

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score", min_value=0, max_value=1, format="%.4f"
                ),
                "Rank":      st.column_config.NumberColumn("Rank", width="small"),
                "Reasoning": st.column_config.TextColumn("Reasoning", width="large"),
                "YoE":       st.column_config.NumberColumn("YoE", format="%.1f yrs"),
            }
        )

        # ── Download ──────────────────────────────────────────────────────────
        st.markdown(
            '<div class="sec-head">⬇️ Download Submission CSV</div>',
            unsafe_allow_html=True
        )
        csv_rows = []
        for rank, r in enumerate(results[:100], start=1):
            f = r["features"]
            reasoning = generate_reasoning(
                features=f, score_result=r["score_result"],
                rank=rank, final_score=r["final_score"],
                multiplier=r["multiplier"],
                honeypot_penalty=r["honeypot_penalty"],
            )
            csv_rows.append({
                "candidate_id": r["candidate_id"],
                "rank":         rank,
                "score":        round(r["final_score"], 6),
                "reasoning":    reasoning,
            })

        buf = io.StringIO()
        pd.DataFrame(csv_rows).to_csv(buf, index=False)

        c1, c2 = st.columns([1, 2])
        with c1:
            st.download_button(
                "⬇️ Download submission.csv (top 100)",
                data=buf.getvalue(),
                file_name="submission.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c2:
            st.info(
                "CSV passes `validate_submission.py` · "
                "100 rows · scores non-increasing · tie-break by candidate_id"
            )

else:
    st.markdown("""
    <div class="empty-wrap">
      <div class="ei">🗂️</div>
      <h3>No file uploaded yet</h3>
      <p>
        Upload <code>sample_candidates.json</code> from the hackathon bundle using the uploader above.<br>
        This sandbox is designed for the 50-candidate sample file.<br>
        To rank all 100,000 candidates use the command line:
      </p>
      <div class="es-cmd">python rank.py --out submission.csv</div>
    </div>
    """, unsafe_allow_html=True)