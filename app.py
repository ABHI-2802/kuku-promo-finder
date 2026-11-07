"""
Kuku Promo Finder — Streamlit app
==================================
Rank the best 20–60 s promos across a short-drama series.

Local run:
    pip install -r requirements.txt
    streamlit run app.py

Streamlit Community Cloud:
    Set PROMO_API_URL, PROMO_MODEL, PROMO_API_KEY in the app's Secrets panel.
"""
from __future__ import annotations

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

# Load .env if present (local dev only)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Make the kuku package importable ─────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from kuku.parser   import read_pack, timecode, spoken, next_spoken_cue
from kuku.rules    import rule_run
from kuku.validator import resolve_ranking, compare_endings
from kuku.export   import results_to_csv, coverage_to_csv, run_to_json, edit_list


# ════════════════════════════════════════════════════════════════════════════
# Page & style
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Kuku Promo Finder",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
/* ── Global ── */
[data-testid="stAppViewContainer"] { background: #0f1117; }
h1 { letter-spacing: -0.5px; }

/* ── Promo card ── */
.promo-card {
    background: #1a1d27;
    border-left: 4px solid #f0a500;
    border-radius: 6px;
    padding: 1.1rem 1.4rem 0.9rem;
    margin-bottom: 1.2rem;
}
.promo-card-lower { border-left-color: #c47f00; }
.promo-card-low   { border-left-color: #8a5a00; }

/* ── Rank badge ── */
.rank-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 2rem; height: 2rem; border-radius: 50%;
    background: #f0a500; color: #0f1117;
    font-weight: 800; font-size: 0.85rem;
    margin-right: 0.5rem;
}
.rank-badge-lower { background: #c47f00; }
.rank-badge-low   { background: #8a5a00; }

/* ── Segment pill ── */
.seg-pill {
    display: inline-block;
    background: #252836; border: 1px solid #3a3f55;
    border-radius: 20px; padding: 0.15rem 0.65rem;
    font-family: monospace; font-size: 0.82rem; color: #cdd5e0;
    margin: 0.15rem 0.3rem 0.15rem 0;
}

/* ── Field labels ── */
.field-hook     { color: #5b9bd5; font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; }
.field-question { color: #f0a500; font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; }
.field-why      { color: #6cba7d; font-weight: 600; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; }

/* ── Duration badge ── */
.dur-badge {
    float: right; background: #252836; border: 1px solid #3a3f55;
    border-radius: 4px; padding: 0.1rem 0.5rem;
    font-size: 0.8rem; color: #9aa5b4; font-family: monospace;
}

/* ── Compare endings ── */
.compare-box {
    background: #12141d; border: 1px solid #2a2d3e;
    border-radius: 5px; padding: 0.75rem 1rem; margin-top: 0.4rem;
}
.compare-chosen  { border-left: 3px solid #5b9bd5; }
.compare-next    { border-left: 3px solid #e06c75; }
.compare-safe    { border-left: 3px solid #6cba7d; }

/* ── Offline badge ── */
.offline-badge {
    background: #2d2200; border: 1px solid #614700;
    border-radius: 4px; padding: 0.1rem 0.5rem;
    font-size: 0.75rem; color: #f0a500;
}

/* ── Pass row ── */
.pass-row {
    background: #141620; border-left: 3px solid #3a3f55;
    border-radius: 4px; padding: 0.4rem 0.75rem;
    margin-bottom: 0.4rem; font-size: 0.85rem; color: #6b7585;
}

/* Streamlit tweak: remove padding around download buttons */
[data-testid="stDownloadButton"] > button {
    width: 100%;
}
</style>
""",
    unsafe_allow_html=True,
)


# ════════════════════════════════════════════════════════════════════════════
# Session-state defaults
# ════════════════════════════════════════════════════════════════════════════
_DEFAULTS: dict = {
    "pack":     None,   # Dict[int, List[dict]]
    "reviews":  None,   # List[dict]
    "ranking":  None,   # dict
    "results":  None,   # List[dict]  — resolved ranked promos
    "origin":   "",
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ════════════════════════════════════════════════════════════════════════════
# Config helpers
# ════════════════════════════════════════════════════════════════════════════
def _secret(key: str, fallback: str = "") -> str:
    """Priority: st.secrets → env var → fallback."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError, AttributeError):
        pass
    return os.getenv(key, fallback)


def _ai_configured(url: str, model: str, key: str) -> bool:
    return bool(url and model and key)


# ════════════════════════════════════════════════════════════════════════════
# UI helpers
# ════════════════════════════════════════════════════════════════════════════
def _rank_class(rank: int) -> str:
    if rank <= 3:
        return ""
    if rank <= 8:
        return "promo-card-lower"
    return "promo-card-low"


def _badge_class(rank: int) -> str:
    if rank <= 3:
        return ""
    if rank <= 8:
        return "rank-badge-lower"
    return "rank-badge-low"


def _promo_card_html(r: dict) -> str:
    rc = _rank_class(r["rank"])
    bc = _badge_class(r["rank"])
    segs_html = "".join(
        f'<span class="seg-pill">E{s["episode"]} '
        f'{s["start"]}–{s["end"]} · {s["duration_s"]:.1f}s</span>'
        for s in r["segments"]
    )
    return f"""
<div class="promo-card {rc}">
  <div>
    <span class="dur-badge">⏱ {r['duration_s']:.1f} s</span>
    <span class="rank-badge {bc}">{r['rank']}</span>
    <strong style="font-size:1.05rem">{r['id']} — {r['title']}</strong>
  </div>
  <div style="margin:0.55rem 0 0.2rem">{segs_html}</div>
  <div style="margin-top:0.65rem">
    <span class="field-hook">🎣 Hook</span><br>
    <span style="color:#dde3ee">{r['hook']}</span>
  </div>
  <div style="margin-top:0.55rem">
    <span class="field-question">❓ Unanswered question</span><br>
    <span style="color:#dde3ee">{r['question']}</span>
  </div>
  <div style="margin-top:0.55rem">
    <span class="field-why">💡 Why it works</span><br>
    <span style="color:#9aa5b4">{r['why']}</span>
  </div>
</div>
"""


def _render_compare(pack, promo: dict) -> None:
    comparisons = compare_endings(pack, promo)
    for comp in comparisons:
        ep     = comp["episode"]
        final  = comp["final_cue"]
        nxt    = comp["next_spoken"]
        label  = final.get("label", "")

        st.markdown(
            f"**Episode {ep} · Cue {final['id']}** "
            f"({label}) — chosen endpoint `{comp['seg_start']}–{comp['seg_end']}`",
        )
        st.markdown(
            f'<div class="compare-box compare-chosen">'
            f'<small style="color:#5b9bd5">CHOSEN FINAL LINE</small><br>'
            f'<span style="color:#dde3ee">{final["text"]}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

        if nxt:
            spoiler_risk = "?" in promo["question"] and any(
                w.lower() in nxt["text"].lower()
                for w in promo["question"].lower().split()
                if len(w) > 4
            )
            box_cls  = "compare-next" if spoiler_risk else "compare-safe"
            icon     = "⚠️" if spoiler_risk else "✅"
            caption  = (
                "May answer or narrow the cliffhanger question — cutting here could reduce suspense."
                if spoiler_risk
                else "Does not appear to answer the cliffhanger question — extending looks safe."
            )
            st.markdown(
                f'<div class="compare-box {box_cls}" style="margin-top:0.5rem">'
                f'<small style="color:#e06c75">NEXT SPOKEN LINE IN SCRIPT '
                f"(Cue {nxt['id']} · {nxt['label']})</small><br>"
                f'<span style="color:#dde3ee">{nxt["text"]}</span><br>'
                f'<small style="color:#9aa5b4;margin-top:4px;display:block">'
                f"{icon} {caption}</small>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="compare-box compare-safe" style="margin-top:0.5rem">'
                '<small style="color:#6cba7d">✅ No further spoken lines in this episode — '
                "cliffhanger fully preserved.</small>"
                "</div>",
                unsafe_allow_html=True,
            )


def _render_results(pack, reviews, results, origin) -> None:
    n_pass = sum(1 for r in reviews if r.get("pick") is None)
    n_nom  = len(results)

    # ── Summary bar ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ranked promos", n_nom)
    c2.metric("Episodes processed", len(pack))
    c3.metric("Passed over", n_pass)
    c4.metric("Total cues", sum(len(v) for v in pack.values()))

    if not results:
        st.info(
            "The baseline found no eligible windows in any episode. "
            "Try uploading episodes with more spoken conflict and question cues."
        )
        return

    st.markdown("---")

    # ── Ranked promos ─────────────────────────────────────────────────────────
    st.subheader("Ranked promos")
    for r in results:
        st.markdown(_promo_card_html(r), unsafe_allow_html=True)

        with st.expander(f"🔍 Compare endings — {r['id']} {r['title']}"):
            _render_compare(pack, r)

    # ── Passed episodes ───────────────────────────────────────────────────────
    passes = [rv for rv in reviews if rv.get("pick") is None]
    if passes:
        st.markdown("---")
        with st.expander(f"📋 {len(passes)} episode(s) passed over"):
            for rv in passes:
                note = rv.get("note", "No note.")
                st.markdown(
                    f'<div class="pass-row">'
                    f"<strong>E{rv['episode']}</strong> — {note}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("⬇ Downloads")
    dcol1, dcol2, dcol3 = st.columns(3)

    with dcol1:
        st.download_button(
            label="📄 Ranked promos CSV",
            data=results_to_csv(results),
            file_name="ranked_promos.csv",
            mime="text/csv",
        )
    with dcol2:
        st.download_button(
            label="📋 Episode coverage CSV",
            data=coverage_to_csv(pack, reviews),
            file_name="episode_coverage.csv",
            mime="text/csv",
        )
    with dcol3:
        st.download_button(
            label="🗂 Raw run JSON",
            data=run_to_json(
                pack, reviews,
                st.session_state.ranking,
                origin,
            ),
            file_name="promo_run.json",
            mime="application/json",
        )
    st.caption(f"Origin: {origin}")


# ════════════════════════════════════════════════════════════════════════════
# Run logic
# ════════════════════════════════════════════════════════════════════════════
def _run_rules(pack) -> tuple:
    reviews, ranking = rule_run(pack)
    if ranking["order"]:
        results = resolve_ranking(pack, reviews, ranking)
    else:
        results = []
    origin = "Deterministic keyword/question rules baseline — no model."
    return reviews, ranking, results, origin


def _run_ai(pack, url: str, model: str, api_key: str) -> tuple:
    from kuku.ai_client import run_api

    cache_dir = Path(tempfile.gettempdir()) / "kuku_promo_cache"
    prog      = st.progress(0.0, text="Starting AI analysis …")

    def _progress(msg: str, frac: float) -> None:
        prog.progress(min(frac, 0.99), text=msg)

    reviews, ranking = run_api(
        pack, url, model, api_key, cache_dir, progress_cb=_progress
    )
    prog.progress(1.0, text="Done.")
    prog.empty()

    if ranking.get("order"):
        results = resolve_ranking(pack, reviews, ranking)
    else:
        results = []
    origin = f"AI model: {model} at {url}"
    return reviews, ranking, results, origin


def _store_and_display(pack, reviews, ranking, results, origin) -> None:
    st.session_state.pack     = pack
    st.session_state.reviews  = reviews
    st.session_state.ranking  = ranking
    st.session_state.results  = results
    st.session_state.origin   = origin


# ════════════════════════════════════════════════════════════════════════════
# Sidebar
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🎬 Kuku Promo Finder")
    st.caption("Short-drama promo editor")
    st.markdown("---")

    # Pull server-side secrets first
    _srv_url   = _secret("PROMO_API_URL")
    _srv_model = _secret("PROMO_MODEL")
    _srv_key   = _secret("PROMO_API_KEY")
    _srv_ai    = _ai_configured(_srv_url, _srv_model, _srv_key)

    st.subheader("⚙ AI settings")
    if _srv_ai:
        st.success("✅ AI model configured via server secrets.")
        ai_url   = _srv_url
        ai_model = _srv_model
        ai_key   = _srv_key
        with st.expander("Show endpoint details"):
            st.code(f"URL:   {ai_url}\nModel: {ai_model}", language="")
    else:
        st.info(
            "No server-side key found. Enter your own for AI mode, "
            "or use the **offline** rules baseline (no key required)."
        )
        ai_url   = st.text_input(
            "Chat-completions endpoint URL",
            placeholder="https://api.openai.com/v1/chat/completions",
            help="Any OpenAI-compatible endpoint.",
        )
        ai_model = st.text_input(
            "Model name",
            placeholder="gpt-4o-mini",
        )
        ai_key   = st.text_input(
            "API key",
            type="password",
            help="Stored only in your browser session.",
        )

    user_ai = _ai_configured(ai_url, ai_model, ai_key)

    st.markdown("---")
    st.markdown(
        """
**How it works**
1. Each cue gets a stable ID and timestamp.
2. The baseline (or AI model) nominates one clip per episode.
3. Python validates duration and rejects cuts mid-speech.
4. Promos are ranked and exported as CSV + JSON.

**Format** — each `.txt` file needs:
```
EPISODE NUMBER: Episode N

**SPEAKER:**
Start: (MM:SS.cc) | End: (MM:SS.cc)
Cue text.
```
"""
    )
    st.markdown("---")
    st.caption("Private screenplays and API keys are never stored or logged.")


# ════════════════════════════════════════════════════════════════════════════
# Main header
# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    "## 🎬 Kuku Promo Finder"
    '<span style="margin-left:0.6rem;font-size:0.75rem;'
    "background:#1a2a1a;border:1px solid #2d4a2d;border-radius:4px;"
    'padding:0.1rem 0.4rem;color:#6cba7d">v1.0</span>',
    unsafe_allow_html=True,
)
st.caption(
    "Upload timestamped screenplay files and get the best 20–60 s promos "
    "ranked across your show."
)

# ════════════════════════════════════════════════════════════════════════════
# Tabs
# ════════════════════════════════════════════════════════════════════════════
tab_sample, tab_upload = st.tabs(["✨ Try a sample", "📂 Analyse your scripts"])

# ── Tab 1 : sample ───────────────────────────────────────────────────────────
with tab_sample:
    st.markdown(
        """
**Three original scenes — no sign-in, no API key.**

The offline rules baseline finds conflict cues and spoken questions, then ranks
the best 20–60 s windows. This always runs without an AI model.
"""
    )

    _demo_dir = Path(__file__).parent / "demo"
    _demo_ok  = _demo_dir.exists() and any(_demo_dir.glob("*.txt"))

    if not _demo_ok:
        st.error("Demo scripts not found. Check that the `demo/` folder is present.")
    else:
        col_a, col_b = st.columns([1, 3])
        with col_a:
            demo_mode = st.radio(
                "Analysis mode",
                ["Offline (rules)", "AI model"] if user_ai else ["Offline (rules)"],
                index=0,
                help="AI mode uses your configured endpoint.",
            )
        with col_b:
            if st.button("▶ Run sample analysis", type="primary", use_container_width=True):
                try:
                    pack = read_pack([_demo_dir])
                    if demo_mode == "AI model" and user_ai:
                        with st.spinner("Running AI analysis on demo scripts …"):
                            reviews, ranking, results, origin = _run_ai(
                                pack, ai_url, ai_model, ai_key
                            )
                    else:
                        with st.spinner("Running offline rules baseline …"):
                            reviews, ranking, results, origin = _run_rules(pack)
                    _store_and_display(pack, reviews, ranking, results, origin)
                    st.success(
                        f"Found **{len(results)} promo(s)** across "
                        f"**{len(pack)} demo episodes**."
                    )
                except Exception as exc:
                    st.error(f"Error: {exc}")

# ── Tab 2 : upload ───────────────────────────────────────────────────────────
with tab_upload:
    st.markdown(
        """
Upload your own timestamped screenplay files. Each `.txt` must start with
`EPISODE NUMBER: Episode N`. You can upload individual files or a single ZIP.
"""
    )

    uploaded = st.file_uploader(
        "Drop screenplay files here",
        type=["txt", "zip"],
        accept_multiple_files=True,
        help="One or more .txt files, or a single .zip containing them.",
    )

    # Mode selector
    if user_ai:
        col_m, _ = st.columns([1, 2])
        with col_m:
            upload_mode = st.radio(
                "Analysis mode",
                ["Offline (rules)", "AI model"],
                index=0,
                horizontal=True,
            )
    else:
        upload_mode = "Offline (rules)"
        st.markdown(
            '<span class="offline-badge">📡 Offline mode</span> '
            "Configure an AI endpoint in the sidebar for AI analysis.",
            unsafe_allow_html=True,
        )

    if st.button(
        "🔍 Find promos",
        type="primary",
        disabled=not uploaded,
        use_container_width=False,
    ):
        try:
            # Write uploaded bytes to a temp directory
            with tempfile.TemporaryDirectory() as tmp:
                tmp_paths = []
                for uf in uploaded:
                    dest = Path(tmp) / uf.name
                    dest.write_bytes(uf.getvalue())
                    tmp_paths.append(dest)

                with st.spinner("Parsing screenplays …"):
                    pack = read_pack(tmp_paths)

                st.info(
                    f"Loaded **{len(pack)} episode(s)** · "
                    f"**{sum(len(v) for v in pack.values())} cues** total."
                )

                if upload_mode == "AI model" and user_ai:
                    reviews, ranking, results, origin = _run_ai(
                        pack, ai_url, ai_model, ai_key
                    )
                else:
                    with st.spinner("Running offline rules baseline …"):
                        reviews, ranking, results, origin = _run_rules(pack)

                _store_and_display(pack, reviews, ranking, results, origin)
                st.success(
                    f"Found **{len(results)} promo(s)** across "
                    f"**{len(pack)} episode(s)**."
                )
        except Exception as exc:
            st.error(f"Error: {exc}")


# ════════════════════════════════════════════════════════════════════════════
# Results — shown below both tabs whenever a run has completed
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.results is not None:
    st.markdown("---")
    _render_results(
        st.session_state.pack,
        st.session_state.reviews,
        st.session_state.results,
        st.session_state.origin,
    )

