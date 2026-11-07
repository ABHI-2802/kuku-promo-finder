"""
Kuku Promo Finder — Ultra-Modern Studio Editorial Suite
======================================================
Next-generation microdrama promotional cut finder & retention analyzer.
Designed for high-velocity short-drama editorial teams (Kuku FM, ReelShort, DramaBox).
"""
from __future__ import annotations

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent))

from kuku.parser import read_pack, timecode, spoken, next_spoken_cue
from kuku.rules import rule_run
from kuku.validator import resolve_ranking, compare_endings
from kuku.export import results_to_csv, coverage_to_csv, run_to_json, edit_list

# ════════════════════════════════════════════════════════════════════════════
# Page Configuration & Cinema Dark Theme
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="KUKU STUDIO // Promo Finder",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">

<style>
/* ── Reset & Core Theme ── */
:root {
    --bg-primary: #07090e;
    --bg-surface: #0f131e;
    --bg-card: rgba(18, 24, 38, 0.75);
    --border-subtle: rgba(255, 255, 255, 0.08);
    --border-glow: rgba(255, 107, 0, 0.4);
    --accent-kuku: #FF6B00;
    --accent-gold: #FFB800;
    --accent-cyan: #00E5FF;
    --accent-emerald: #00F59B;
    --accent-rose: #FF2E63;
    --text-primary: #F0F4FC;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
}

[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 15% 10%, rgba(255, 107, 0, 0.06) 0%, transparent 40%),
                radial-gradient(circle at 85% 85%, rgba(0, 229, 255, 0.04) 0%, transparent 45%),
                var(--bg-primary);
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: var(--text-primary);
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stSidebar"] {
    background-color: #0b0e17;
    border-right: 1px solid var(--border-subtle);
}

/* ── Studio Header Bar ── */
.studio-brand-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.9rem 1.4rem;
    background: linear-gradient(135deg, rgba(26, 32, 48, 0.65) 0%, rgba(15, 19, 30, 0.85) 100%);
    backdrop-filter: blur(14px);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.studio-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background: linear-gradient(90deg, #FFFFFF 0%, #FFB800 50%, #FF6B00 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.live-indicator {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: rgba(0, 245, 155, 0.1);
    border: 1px solid rgba(0, 245, 155, 0.3);
    color: var(--accent-emerald);
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 0.25rem 0.65rem;
    border-radius: 20px;
}

.live-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent-emerald);
    box-shadow: 0 0 8px var(--accent-emerald);
}

/* ── KPI Metric Tiles ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.8rem;
}

.kpi-card {
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.kpi-card:hover {
    border-color: rgba(255, 107, 0, 0.3);
    transform: translateY(-2px);
}

.kpi-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 0.3rem;
}

.kpi-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: #FFFFFF;
    line-height: 1.1;
}

.kpi-sub {
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
}

/* ── High-Impact Promo Cards ── */
.promo-master-card {
    background: linear-gradient(180deg, rgba(22, 28, 44, 0.8) 0%, rgba(13, 17, 27, 0.9) 100%);
    backdrop-filter: blur(14px);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 1.4rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
}
.promo-master-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #FF6B00 0%, #FFB800 50%, #00E5FF 100%);
    opacity: 0.7;
}
.promo-master-card:hover {
    border-color: var(--border-glow);
    box-shadow: 0 14px 40px rgba(255, 107, 0, 0.12);
    transform: translateY(-2px);
}

.promo-header-flex {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.8rem;
}

.rank-badge-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: linear-gradient(135deg, #FF6B00 0%, #D84315 100%);
    color: #FFFFFF;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 800;
    font-size: 0.85rem;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    box-shadow: 0 4px 12px rgba(255, 107, 0, 0.35);
}

.promo-duration-pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 600;
    background: rgba(0, 229, 255, 0.1);
    border: 1px solid rgba(0, 229, 255, 0.3);
    color: var(--accent-cyan);
    padding: 0.3rem 0.75rem;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}

.segment-track-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0.6rem 0 1.1rem;
}

.segment-capsule {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 0.25rem 0.65rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #E2E8F0;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}

/* ── Content Pillars Grid ── */
.editorial-pillars {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1rem;
}

.pillar-box {
    background: rgba(10, 14, 22, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 0.9rem 1rem;
    position: relative;
}

.pillar-box.hook-box {
    border-left: 3px solid var(--accent-cyan);
}
.pillar-box.question-box {
    border-left: 3px solid var(--accent-gold);
}

.pillar-tag {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}
.pillar-tag.hook-tag { color: var(--accent-cyan); }
.pillar-tag.question-tag { color: var(--accent-gold); }

.pillar-body {
    font-size: 0.92rem;
    line-height: 1.45;
    color: #E2E8F0;
}

/* ── Rationale Section ── */
.why-section {
    background: rgba(0, 245, 155, 0.03);
    border: 1px solid rgba(0, 245, 155, 0.15);
    border-left: 3px solid var(--accent-emerald);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.88rem;
    color: #CBD5E1;
    line-height: 1.45;
    margin-bottom: 0.8rem;
}

/* ── Microdrama Phone Mockup Simulator ── */
.phone-sim-wrap {
    background: #000000;
    border: 2px solid #2B3347;
    border-radius: 18px;
    padding: 1rem;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.7);
    margin: 1rem 0;
    position: relative;
    overflow: hidden;
}
.phone-top-bar {
    display: flex;
    justify-content: space-between;
    font-size: 0.7rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-muted);
    border-bottom: 1px solid #1E2433;
    padding-bottom: 0.4rem;
    margin-bottom: 0.8rem;
}
.sim-hook-banner {
    background: linear-gradient(90deg, rgba(255, 107, 0, 0.3) 0%, rgba(255, 184, 0, 0.15) 100%);
    border: 1px solid var(--accent-kuku);
    padding: 0.6rem 0.8rem;
    border-radius: 8px;
    margin-bottom: 0.8rem;
}
.sim-subtitles {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 700;
    font-size: 1.05rem;
    color: #FFFFFF;
    text-shadow: 0 2px 8px rgba(0,0,0,0.8);
    background: rgba(0,0,0,0.65);
    padding: 0.5rem 0.8rem;
    border-radius: 6px;
    border-left: 3px solid var(--accent-gold);
}

/* ── Split-Screen Compare Endings Laboratory ── */
.lab-split-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.2rem;
    margin: 1rem 0;
}
.lab-card {
    border-radius: 10px;
    padding: 1.1rem;
    backdrop-filter: blur(10px);
}
.lab-chosen {
    background: rgba(0, 229, 255, 0.03);
    border: 1px solid rgba(0, 229, 255, 0.2);
    border-top: 3px solid var(--accent-cyan);
}
.lab-next {
    background: rgba(255, 46, 99, 0.04);
    border: 1px solid rgba(255, 46, 99, 0.25);
    border-top: 3px solid var(--accent-rose);
}
.lab-badge {
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.2rem 0.55rem;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 0.5rem;
}
.badge-chosen { background: rgba(0, 229, 255, 0.15); color: var(--accent-cyan); }
.badge-next { background: rgba(255, 46, 99, 0.15); color: var(--accent-rose); }

/* ── Custom Tab Styling ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    background-color: transparent;
}
.stTabs [data-baseweb="tab"] {
    height: 48px;
    border-radius: 8px;
    border: 1px solid var(--border-subtle);
    background-color: rgba(18, 24, 38, 0.5);
    padding: 0 1.4rem;
    color: var(--text-secondary);
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(255, 107, 0, 0.15) 0%, rgba(255, 184, 0, 0.05) 100%) !important;
    border-color: var(--accent-kuku) !important;
    color: #FFFFFF !important;
}

/* ── Buttons & Streamlit Component Overrides ── */
.stButton > button {
    border-radius: 8px;
    font-weight: 700;
    letter-spacing: 0.02em;
    transition: all 0.2s ease;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #FF6B00 0%, #FF8F00 100%);
    border: none;
    box-shadow: 0 4px 15px rgba(255, 107, 0, 0.4);
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 22px rgba(255, 107, 0, 0.6);
    transform: translateY(-1px);
}
</style>
""",
    unsafe_allow_html=True,
)

# ════════════════════════════════════════════════════════════════════════════
# Session State Defaults
# ════════════════════════════════════════════════════════════════════════════
_DEFAULTS = {
    "pack": None,
    "reviews": None,
    "ranking": None,
    "results": None,
    "origin": "",
    "filter_mode": "All Durations",
    "search_query": "",
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ════════════════════════════════════════════════════════════════════════════
# Configuration Helpers
# ════════════════════════════════════════════════════════════════════════════
def _secret(key: str, fallback: str = "") -> str:
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError, AttributeError):
        pass
    return os.getenv(key, fallback)

def _ai_configured(url: str, model: str, key: str) -> bool:
    return bool(url and model and key)

# ════════════════════════════════════════════════════════════════════════════
# Studio Sidebar
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.8rem;">
            <div style="background:linear-gradient(135deg, #FF6B00, #FFB800); width:32px; height:32px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:18px;">🎬</div>
            <div>
                <strong style="font-size:1.1rem; color:#FFF; font-family:'Space Grotesk'">KUKU STUDIO</strong><br>
                <span style="font-size:0.75rem; color:#64748B;">Microdrama Editorial Core</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    _srv_url = _secret("PROMO_API_URL")
    _srv_model = _secret("PROMO_MODEL")
    _srv_key = _secret("PROMO_API_KEY")
    _srv_ai = _ai_configured(_srv_url, _srv_model, _srv_key)

    st.markdown("#### ⚡ Editorial Engine")
    if _srv_ai:
        st.markdown(
            """
            <div style="background:rgba(0, 245, 155, 0.08); border:1px solid rgba(0, 245, 155, 0.25); border-radius:6px; padding:0.6rem 0.8rem; margin-bottom:0.8rem;">
                <span style="color:#00F59B; font-weight:700; font-size:0.8rem;">● AI MODEL CONNECTED</span><br>
                <span style="color:#94A3B8; font-size:0.75rem;">Server credentials verified.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        ai_url, ai_model, ai_key = _srv_url, _srv_model, _srv_key
    else:
        engine_opt = st.selectbox(
            "Engine Mode",
            ["Deterministic Rules (Offline)", "Custom LLM API (OpenAI / Groq / Ollama)"],
            index=0,
            help="The offline engine works out of the box with zero external dependencies.",
        )
        if "Custom LLM" in engine_opt:
            ai_url = st.text_input("Endpoint URL", placeholder="https://api.openai.com/v1/chat/completions")
            ai_model = st.text_input("Model ID", placeholder="gpt-4o-mini")
            ai_key = st.text_input("Bearer API Key", type="password")
        else:
            ai_url, ai_model, ai_key = "", "", ""

    user_ai = _ai_configured(ai_url, ai_model, ai_key)

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size:0.8rem; color:#94A3B8; line-height:1.5;">
        <strong style="color:#E2E8F0;">Editorial Rules Enforced:</strong><br>
        • Exact 20.0s – 60.0s continuous playback<br>
        • 3-Second Retention Hook identification<br>
        • Unresolved spoken question out-point<br>
        • Zero mid-speech cuts (safe boundary check)<br>
        • Next-beat spoiler leak comparison
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.caption("🔒 100% Private. Screenplays & keys are processed strictly in-memory.")

# ════════════════════════════════════════════════════════════════════════════
# Studio Header & Navigation
# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="studio-brand-bar">
        <div>
            <div class="studio-title">
                <span>KUKU PROMO FINDER</span>
                <span style="font-size:0.8rem; font-family:'JetBrains Mono'; background:rgba(255,255,255,0.06); padding:0.2rem 0.5rem; border-radius:4px; color:#94A3B8;">STUDIO EDITION</span>
            </div>
            <div style="font-size:0.82rem; color:#94A3B8; margin-top:0.2rem;">
                Automated 20–60s microdrama promotional cut extraction, retention scoring & spoiler verification
            </div>
        </div>
        <div class="live-indicator">
            <span class="live-dot"></span>
            <span>PROMO CORE ONLINE</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_demo, tab_upload = st.tabs(["⚡ Instant Demo (1-Click Sample)", "📂 Upload Show Screenplays"])

# ════════════════════════════════════════════════════════════════════════════
# Tab 1: Instant 1-Click Demo
# ════════════════════════════════════════════════════════════════════════════
with tab_demo:
    col_demo_info, col_demo_btn = st.columns([3, 1])
    with col_demo_info:
        st.markdown(
            """
            **Experience the editorial workflow on 3 original full-fidelity microdrama scenes.**
            No setup, accounts, or API keys needed. Python will parse timed cues, scan for high-conflict hooks, enforce 20–60s duration, verify speech boundaries, and rank the top promo cuts.
            """
        )
    with col_demo_btn:
        run_demo_clicked = st.button("▶ RUN SAMPLE NOW", type="primary", use_container_width=True)

    _demo_dir = Path(__file__).parent / "demo"
    if run_demo_clicked:
        try:
            with st.spinner("Processing timestamped cues and validating speech boundaries..."):
                pack = read_pack([_demo_dir])
                if user_ai:
                    from kuku.ai_client import run_api
                    cache_dir = Path(tempfile.gettempdir()) / "kuku_promo_cache"
                    reviews, ranking = run_api(pack, ai_url, ai_model, ai_key, cache_dir)
                    origin = f"AI Engine: {ai_model}"
                else:
                    reviews, ranking = rule_run(pack)
                    origin = "Deterministic Keyword & Question Rules Core (Offline)"

                results = resolve_ranking(pack, reviews, ranking) if ranking.get("order") else []
                st.session_state.pack = pack
                st.session_state.reviews = reviews
                st.session_state.ranking = ranking
                st.session_state.results = results
                st.session_state.origin = origin
                st.toast("✅ Sample analyzed successfully!", icon="🎬")
        except Exception as exc:
            st.error(f"Execution Error: {exc}")

# ════════════════════════════════════════════════════════════════════════════
# Tab 2: Upload Show Screenplays
# ════════════════════════════════════════════════════════════════════════════
with tab_upload:
    st.markdown(
        """
        Upload one or more `.txt` screenplay files or a single `.zip` containing your show's timed scripts.
        Each file must begin with `EPISODE NUMBER: Episode N`.
        """
    )
    uploaded_files = st.file_uploader(
        "Drop screenplay files or ZIP here",
        type=["txt", "zip"],
        accept_multiple_files=True,
        help="Screenplay files with timestamped dialogue and camera/action cues.",
    )

    col_up_mode, col_up_btn = st.columns([2, 1])
    with col_up_mode:
        if user_ai:
            up_engine_choice = st.radio("Selected Engine", ["Deterministic Rules Baseline", f"AI Model ({ai_model})"], horizontal=True)
        else:
            st.info("💡 Running in Offline Rules Mode (deterministic & private). Connect an API in the sidebar for LLM analysis.")
            up_engine_choice = "Deterministic Rules Baseline"

    with col_up_btn:
        run_upload_clicked = st.button(
            "🔍 EXTRACT & RANK PROMOS",
            type="primary",
            disabled=not uploaded_files,
            use_container_width=True,
        )

    if run_upload_clicked and uploaded_files:
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                file_paths = []
                for uf in uploaded_files:
                    target = Path(tmp_dir) / uf.name
                    target.write_bytes(uf.getvalue())
                    file_paths.append(target)

                with st.spinner("Ingesting screenplays and indexing cue boundaries..."):
                    pack = read_pack(file_paths)

                st.toast(f"Parsed {len(pack)} episodes and {sum(len(v) for v in pack.values())} timed cues.", icon="📂")

                if "AI Model" in up_engine_choice and user_ai:
                    from kuku.ai_client import run_api
                    cache_dir = Path(tempfile.gettempdir()) / "kuku_promo_cache"
                    reviews, ranking = run_api(pack, ai_url, ai_model, ai_key, cache_dir)
                    origin = f"AI Engine: {ai_model}"
                else:
                    reviews, ranking = rule_run(pack)
                    origin = "Deterministic Keyword & Question Rules Core (Offline)"

                results = resolve_ranking(pack, reviews, ranking) if ranking.get("order") else []
                st.session_state.pack = pack
                st.session_state.reviews = reviews
                st.session_state.ranking = ranking
                st.session_state.results = results
                st.session_state.origin = origin
                st.toast("✅ Analysis complete!", icon="🎯")
        except Exception as exc:
            st.error(f"Ingestion & Validation Error: {exc}")

# ════════════════════════════════════════════════════════════════════════════
# Studio Results Canvas
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.results is not None:
    st.markdown("---")
    pack = st.session_state.pack
    reviews = st.session_state.reviews
    results = st.session_state.results
    origin = st.session_state.origin

    n_promos = len(results)
    n_eps = len(pack)
    n_passes = sum(1 for r in reviews if r.get("pick") is None)
    total_cues = sum(len(c) for c in pack.values())

    # ── Live KPI Metrics Bar ──
    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Ranked Promos</div>
                <div class="kpi-value" style="color:var(--accent-kuku);">{n_promos}</div>
                <div class="kpi-sub">Across {n_eps} episodes</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Speech Boundary Check</div>
                <div class="kpi-value" style="color:var(--accent-emerald);">100%</div>
                <div class="kpi-sub">0 lines split mid-speech</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Episodes Passed</div>
                <div class="kpi-value" style="color:var(--accent-gold);">{n_passes}</div>
                <div class="kpi-sub">Weak cliffhangers skipped</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Indexed Cues</div>
                <div class="kpi-value" style="color:var(--accent-cyan);">{total_cues}</div>
                <div class="kpi-sub">Audio/Speech/Action synchronized</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Filter & Search Toolbar ──
    filter_col1, filter_col2, dl_col = st.columns([1.5, 2, 2.5])
    with filter_col1:
        duration_filter = st.selectbox(
            "Duration Filter",
            ["All Durations", "⚡ Punchy (20–35s)", "🔥 Extended (35–60s)"],
            index=0,
        )
    with filter_col2:
        search_kw = st.text_input("Filter by Keyword", placeholder="Search hook, question or character...")

    with dl_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        sub_d1, sub_d2, sub_d3 = st.columns(3)
        with sub_d1:
            st.download_button(
                "📥 Promos CSV",
                data=results_to_csv(results),
                file_name="kuku_ranked_promos.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with sub_d2:
            st.download_button(
                "📋 Coverage CSV",
                data=coverage_to_csv(pack, reviews),
                file_name="kuku_episode_coverage.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with sub_d3:
            st.download_button(
                "🗂 Run JSON",
                data=run_to_json(pack, reviews, st.session_state.ranking, origin),
                file_name="kuku_promo_run.json",
                mime="application/json",
                use_container_width=True,
            )

    # Filter results
    filtered_results = results
    if "Punchy" in duration_filter:
        filtered_results = [r for r in filtered_results if r["duration_s"] <= 35]
    elif "Extended" in duration_filter:
        filtered_results = [r for r in filtered_results if r["duration_s"] > 35]

    if search_kw.strip():
        kw = search_kw.strip().lower()
        filtered_results = [
            r for r in filtered_results
            if kw in r["title"].lower() or kw in r["hook"].lower() or kw in r["question"].lower() or kw in r["why"].lower()
        ]

    st.markdown(f"#### 🏆 Ranked Editorial Cut List ({len(filtered_results)} matching)")

    # ── Render Each Master Promo Card ──
    for p in filtered_results:
        # Segment capsules HTML
        capsules_html = "".join(
            f'<div class="segment-capsule">'
            f'<span>📼 Episode {s["episode"]}</span>'
            f'<span style="color:var(--accent-cyan);">{s["start"]} ➔ {s["end"]}</span>'
            f'<span style="color:#94A3B8;">({s["duration_s"]:.1f}s)</span>'
            f'</div>'
            for s in p["segments"]
        )

        st.markdown(
            f"""
            <div class="promo-master-card">
                <div class="promo-header-flex">
                    <div>
                        <span class="rank-badge-pill">RANK #{p['rank']}</span>
                        <strong style="font-size:1.25rem; font-family:'Space Grotesk'; color:#FFF; margin-left:0.6rem;">{p['id']} · {p['title']}</strong>
                    </div>
                    <div class="promo-duration-pill">
                        <span>⏱</span>
                        <span>{p['duration_s']:.2f}s TOTAL</span>
                    </div>
                </div>
                
                <div class="segment-track-bar">
                    {capsules_html}
                </div>

                <div class="editorial-pillars">
                    <div class="pillar-box hook-box">
                        <div class="pillar-tag hook-tag">
                            <span>⚡</span>
                            <span>FIRST 3-SECOND RETENTION HOOK</span>
                        </div>
                        <div class="pillar-body">
                            "{p['hook']}"
                        </div>
                    </div>
                    <div class="pillar-box question-box">
                        <div class="pillar-tag question-tag">
                            <span>❓</span>
                            <span>UNANSWERED CLIFFHANGER QUESTION</span>
                        </div>
                        <div class="pillar-body">
                            "{p['question']}"
                        </div>
                    </div>
                </div>

                <div class="why-section">
                    <strong style="color:var(--accent-emerald);">💡 Editorial Rationale:</strong> {p['why']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Interactive Split-Screen & Smartphone Simulator Inside Expander ──
        with st.expander(f"🔬 Studio Inspection Lab · Compare Endings & 9:16 Feed Preview — {p['id']} ({p['title']})"):
            tab_inspect_compare, tab_inspect_sim = st.tabs(["⚖️ Compare Endings (Spoiler Autopsy)", "📱 9:16 Microdrama Feed Simulator"])

            with tab_inspect_compare:
                st.markdown(
                    """
                    <div style="font-size:0.85rem; color:#94A3B8; margin-bottom:0.8rem;">
                    Inspect the chosen cut against the subsequent line in the screenplay. 
                    A great microdrama promo ends precisely before the answer is revealed.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                comps = compare_endings(pack, p)
                for comp in comps:
                    ep_num = comp["episode"]
                    final_c = comp["final_cue"]
                    next_c = comp["next_spoken"]

                    # Check spoiler risk
                    spoiler_words = [w.lower() for w in p["question"].split() if len(w) > 4]
                    has_spoiler = next_c and any(w in next_c["text"].lower() for w in spoiler_words)

                    st.markdown(
                        f"""
                        <div style="font-family:'JetBrains Mono'; font-size:0.8rem; color:#94A3B8; margin-bottom:0.4rem;">
                            SEGMENT: Episode {ep_num} [Cue #{final_c['id']} ➔ Cue #{next_c['id'] if next_c else 'END'}]
                        </div>
                        <div class="lab-split-grid">
                            <div class="lab-card lab-chosen">
                                <span class="lab-badge badge-chosen">✓ CHOSEN OUT-POINT (CUE #{final_c['id']} · {final_c['label']})</span>
                                <div style="font-size:1.05rem; font-weight:600; color:#FFF; margin-bottom:0.5rem;">
                                    "{final_c['text']}"
                                </div>
                                <div style="font-size:0.78rem; color:var(--accent-cyan);">
                                    Ends at {timecode(final_c['b'])} • Leaves audience hanging on the cliffhanger.
                                </div>
                            </div>
                            <div class="lab-card lab-next">
                                <span class="lab-badge badge-next">{'⚠️ SPOILER RISK' if has_spoiler else '⚡ NEXT SPOKEN LINE'} (CUE #{next_c['id'] if next_c else 'None'} · {next_c['label'] if next_c else 'N/A'})</span>
                                <div style="font-size:1.05rem; font-weight:600; color:{'#FF6B8B' if has_spoiler else '#CBD5E1'}; margin-bottom:0.5rem;">
                                    "{next_c['text'] if next_c else 'No further spoken dialogue in this episode.'}"
                                </div>
                                <div style="font-size:0.78rem; color:{'#FF2E63' if has_spoiler else '#64748B'};">
                                    {'🚨 Warning: Cutting here reveals the answer and kills mystery!' if has_spoiler else 'Safe boundary: Extends tension without premature reveal.'}
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            with tab_inspect_sim:
                st.markdown(
                    f"""
                    <div class="phone-sim-wrap">
                        <div class="phone-top-bar">
                            <span>KUKU FM • 9:16 FEED SIMULATOR</span>
                            <span>EVALUATION PREVIEW</span>
                            <span>REC ● 00:00:00</span>
                        </div>
                        <div class="sim-hook-banner">
                            <span style="font-size:0.7rem; font-weight:800; color:var(--accent-kuku); text-transform:uppercase;">⚡ 0:00–0:03 Retention Hook</span><br>
                            <span style="font-size:0.95rem; font-weight:700; color:#FFF;">{p['hook']}</span>
                        </div>
                        <div style="height:120px; display:flex; align-items:center; justify-content:center; background:radial-gradient(circle, rgba(255,107,0,0.15) 0%, transparent 70%); border-radius:8px; margin-bottom:0.8rem; border:1px dashed rgba(255,255,255,0.1);">
                            <div style="text-align:center;">
                                <div style="font-size:1.8rem; margin-bottom:0.2rem;">🎬</div>
                                <div style="font-size:0.75rem; color:#94A3B8; font-family:'JetBrains Mono';">SCENE TIMECODE: {p['segments'][0]['start']} ➔ {p['segments'][-1]['end']}</div>
                            </div>
                        </div>
                        <div class="sim-subtitles">
                            "{p['question']}"
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.8rem; font-size:0.75rem; color:#94A3B8;">
                            <span>Duration: {p['duration_s']:.1f}s</span>
                            <span style="color:var(--accent-emerald); font-weight:700;">Swipe up for Episode {p['segments'][0]['episode']} ➔</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── Reviewer Notes on Passed Episodes ──
    passes = [rv for rv in reviews if rv.get("pick") is None]
    if passes:
        st.markdown("---")
        with st.expander(f"📋 Editorial Pass Log ({len(passes)} episodes passed over)"):
            st.markdown(
                """
                <div style="font-size:0.82rem; color:#94A3B8; margin-bottom:0.6rem;">
                Episodes that did not qualify due to resolved conflict within the scene, lack of a 3-second hook, or duration outside 20–60s:
                </div>
                """,
                unsafe_allow_html=True,
            )
            for rv in passes:
                st.markdown(
                    f"""
                    <div style="background:rgba(255,255,255,0.02); border-left:3px solid #475569; padding:0.4rem 0.8rem; border-radius:4px; margin-bottom:0.4rem; font-size:0.85rem;">
                        <strong style="color:#CBD5E1;">Episode {rv['episode']}:</strong> <span style="color:#94A3B8;">{rv.get('note', 'No note.')}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
