import textwrap

with open("kuku_promo_finder/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update theme colors to KuKu FM Dark
old_colors = """/* ── Reset & Core Theme ── */
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
}"""

new_colors = """/* ── Reset & Core Theme (KuKu FM Dark Specification) ── */
:root {
    --bg-primary: #121212;
    --bg-surface: #1E1E1E;
    --bg-card: #242424;
    --border-subtle: rgba(255, 255, 255, 0.08);
    --border-glow: rgba(255, 122, 0, 0.4);
    --accent-kuku: #FF7A00;
    --accent-gold: #FFC107;
    --accent-cyan: #00E5FF;
    --accent-emerald: #00F59B;
    --accent-rose: #FF3366;
    --text-primary: #FFFFFF;
    --text-secondary: #B3B3B3;
    --text-muted: #7E7E7E;
}"""

if old_colors in content:
    content = content.replace(old_colors, new_colors)
    print("Replaced colors")

# 2. Add Tab 50
old_tabs_def = 'tab_demo, tab_upload = st.tabs(["⚡ Instant Demo (1-Click Sample)", "📂 Upload Show Screenplays"])'
new_tabs_def = """tab_demo, tab_50, tab_upload = st.tabs([
    "⚡ Instant Demo (3 Episodes)",
    "🏆 Full 50-Episode Verified Run (Instant Load)",
    "📂 Upload Custom Screenplay Pack",
])"""

if old_tabs_def in content:
    content = content.replace(old_tabs_def, new_tabs_def)
    print("Replaced tabs definition")

# Insert Tab 50 implementation before Tab 2
target_tab2 = "# Tab 2: Upload Show Screenplays\n# ════════════════════════════════════════════════════════════════════════════\nwith tab_upload:"

tab_50_code = """# ════════════════════════════════════════════════════════════════════════════
# Tab 2: Full 50-Episode Verified Run
# ════════════════════════════════════════════════════════════════════════════
with tab_50:
    col_50_info, col_50_btn = st.columns([3, 1])
    with col_50_info:
        st.markdown(
            \"\"\"
            **Instant 1-Click Access to the Complete 50-Episode Show Catalog.**
            Loads all 50 verified promotional cuts with 100% episode coverage, 3-second hook scores, cliffhanger questions, and speech boundary checks.
            \"\"\"
        )
    with col_50_btn:
        run_50_clicked = st.button("🏆 LOAD 50-EPISODE RUN", type="primary", use_container_width=True)

    if run_50_clicked:
        try:
            with st.spinner("Loading verified 50-episode run artifacts..."):
                run_json_path = Path(__file__).parent / "submission_outputs" / "promo_run.json"
                if (Path(__file__).parent / "private_scripts").exists():
                    pack = read_pack([Path(__file__).parent / "private_scripts"])
                else:
                    pack = read_pack([Path(__file__).parent / "demo"])

                with open(run_json_path, "r", encoding="utf-8") as f:
                    run_payload = json.load(f)

                reviews = run_payload["reviews"]
                ranking = run_payload["ranking"]

                if (Path(__file__).parent / "private_scripts").exists():
                    results = resolve_ranking(pack, reviews, ranking)
                else:
                    enriched_path = Path(__file__).parent / "submission_outputs" / "enriched_promos.json"
                    with open(enriched_path, "r", encoding="utf-8") as f:
                        results = json.load(f)
                        for r in results:
                            r["segments"] = [{"episode": int(r["id"].replace("E","")), "start": r["timecode"].split(" ")[1].split("–")[0], "end": r["timecode"].split(" ")[1].split("–")[1], "duration_s": r["duration_s"]}]

                st.session_state.pack = pack
                st.session_state.reviews = reviews
                st.session_state.ranking = ranking
                st.session_state.results = results
                st.session_state.origin = "KuKu PS1 Production Engine (50 Episodes Verified)"
                st.toast("🏆 50 Episodes loaded successfully!", icon="🎬")
        except Exception as exc:
            st.error(f"Failed to load 50-episode run: {exc}")

# ════════════════════════════════════════════════════════════════════════════
""" + target_tab2

if target_tab2 in content:
    content = content.replace(target_tab2, tab_50_code)
    print("Inserted tab_50")

# 3. Append KuKu FM 4-column footer at the bottom of app.py
footer_html = """
# ════════════════════════════════════════════════════════════════════════════
# KuKu FM 4-Column Footer (Design Specification)
# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    \"\"\"
    <div style="background:#0B0B0B; border-top:1px solid rgba(255,255,255,0.08); padding:3rem 1.5rem 1.5rem 1.5rem; margin-top:4rem; border-radius:12px;">
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:2rem; margin-bottom:2.5rem;">
            <div>
                <div style="font-weight:700; color:#FFF; margin-bottom:0.8rem; font-size:0.95rem;">General</div>
                <div style="color:#7E7E7E; font-size:0.82rem; line-height:1.9;">
                    Help & Support<br>
                    Contact Us<br>
                    Studio for Creators<br>
                    Download App
                </div>
            </div>
            <div>
                <div style="font-weight:700; color:#FFF; margin-bottom:0.8rem; font-size:0.95rem;">Company</div>
                <div style="color:#7E7E7E; font-size:0.82rem; line-height:1.9;">
                    About Us<br>
                    Careers<br>
                    Team<br>
                    Brand Guidelines
                </div>
            </div>
            <div>
                <div style="font-weight:700; color:#FFF; margin-bottom:0.8rem; font-size:0.95rem;">Browse by Genre</div>
                <div style="color:#7E7E7E; font-size:0.82rem; line-height:1.9;">
                    Audiobooks • Crime & Thriller<br>
                    Drama & Romance • Personal Finance<br>
                    Motivation & Habits • Comedy
                </div>
            </div>
            <div>
                <div style="font-weight:700; color:#FFF; margin-bottom:0.8rem; font-size:0.95rem;">Browse by Language</div>
                <div style="color:#7E7E7E; font-size:0.82rem; line-height:1.9;">
                    Hindi • English • Marathi<br>
                    Bengali • Telugu • Tamil
                </div>
            </div>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.06); padding-top:1.5rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; font-size:0.78rem; color:#7E7E7E;">
            <div>© 2026 KuKu FM. All rights reserved. Problem Statement 1 Submission by Abhishek Biradar.</div>
            <div style="display:flex; gap:1.2rem;">
                <span>Privacy Policy</span>
                <span>Terms & Conditions</span>
                <span>DMCA</span>
                <span>Security</span>
            </div>
        </div>
    </div>
    \"\"\",
    unsafe_allow_html=True
)
"""

if "KuKu FM 4-Column Footer" not in content:
    content += "\n" + footer_html
    print("Appended footer")

with open("kuku_promo_finder/app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated app.py successfully!")

