# 🎬 Kuku Promo Finder

A Streamlit tool for microdrama editors to automatically find, validate, and rank the best **20–60 second promos** across an entire short-drama series from timestamped screenplay files.

---

## ✨ Features

- **One-click demo**: "Try a sample" runs instantly on three original scenes — no account, no API key required.
- **Upload scripts**: Drop one or more `.txt` screenplay files or a single `.zip` archive.
- **Duration & cut validation**: Python enforces 20–60 s total length and rejects any cut that splits a spoken line.
- **Compare endings**: Inspect the chosen cut point side-by-side with the very next spoken line in the script to verify spoiler safety.
- **Offline & AI modes**:
  - **Offline (default)**: Deterministic keyword-and-question rules baseline, runs locally with zero network calls.
  - **AI model**: Connects to any OpenAI-compatible chat-completions endpoint (OpenAI, Gemini, Groq, Ollama, etc.).
- **Downloads**: One-click download of `ranked_promos.csv`, `episode_coverage.csv`, and `promo_run.json`.
- **Privacy-first**: No screenplays, transcripts, or API keys are ever stored or logged.

---

## 🚀 Quick start (local)

```bash
# 1. Clone the repository
git clone https://github.com/your-username/kuku-promo-finder.git
cd kuku-promo-finder

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`.

---

## ☁️ Deploy to Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Sign in to [share.streamlit.io](https://share.streamlit.io/).
3. Click **New app**, select your repo, branch `main`, and main file `app.py`.
4. *(Optional — to enable server-side AI)* In **App settings → Secrets**, paste:

```toml
PROMO_API_URL = "https://api.openai.com/v1/chat/completions"
PROMO_MODEL   = "gpt-4o-mini"
PROMO_API_KEY = "sk-..."
```

If secrets are not provided, the app runs happily in **offline mode** with zero configuration.

---

## 📄 Screenplay format

Each `.txt` file must include an episode header and cue blocks:

```
EPISODE NUMBER: Episode 1

**SPEAKER:**
Start: (00:00.00) | End: (00:05.50)
Spoken dialogue or voiceover text here.

**CAMERA:**
Start: (00:05.50) | End: (00:10.00)
Action description. Non-speech cues are allowed and given IDs.
```

Non-speech cue labels (`CAMERA`, `ACTION`, `SOUND FX`, `SFX`, `MUSIC`, `TRANSITION`, `VFX`) are recognized so cuts won't accidentally split mid-sentence speech.

---

## 🧪 Testing locally

A built-in test suite verifies the parser, rules engine, and CSV/JSON export:

```bash
python3 test_app.py
```

