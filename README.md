# BEE — Behavioral Evaluation Engine

> A mock interview tool that generates questions using a quantized LLM (Qwen2.5-7B via HuggingFace), grades your answers, and gives you a breakdown.

---

## What it does

You drop in your skills (or upload a resume), and BEE puts together a 15-question interview split across four sections — theory, aptitude, coding, and HR. Each answer gets evaluated for correctness, depth, and clarity. At the end you get a score, section-wise breakdown, weak areas, and learning resources.

**What it can do:**
- Extract skills from a PDF or TXT resume automatically
- Generate tailored questions based on your skill set
- Evaluate free-text and code answers
- Rephrase a question if you don't understand it (2 tries per question)
- Show a full review of every question + answer + feedback after the session
- Restart the interview with the same skills in one click

---

## Tech Stack

| Layer | What |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| LLM | Qwen2.5-7B-Instruct via HuggingFace Inference API |
| Resume parsing | PyPDF2 |
| Frontend | Vanilla HTML / CSS / JS |
| Code editor | CodeMirror 5 (Dracula theme) |
| Env management | python-dotenv |

---

## File Structure

```
bee/
│
├── backend/
│   ├── main.py                  # FastAPI app, all routes
│   ├── interview_controller.py  # Session logic, question flow
│   ├── qwen_client.py           # HuggingFace API calls (generate, eval, rephrase)
│   ├── scoring.py               # Score calculation and verdict logic
│   ├── local_utils.py           # Skill validation, gibberish checks (no API)
│   ├── resources.py             # Static learning resource map
│   └── requirements.txt
│
└── frontend/
    ├── index.html               # Landing page
    ├── interview.html           # Interview page
    ├── results.html             # Results page
    ├── style.css                # All styles (single file)
    ├── landing.js               # Landing page logic
    ├── interview.js             # Interview page logic, CodeMirror setup
    └── results.js               # Results rendering and score animation
```

> `main.py` auto-detects the frontend folder — it looks for `frontend/` or `front/` relative to itself.

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/GitRzh/bee.git
cd bee
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r backend/requirements.txt
```

**4. Create a `.env` file in the `backend/` folder**
```
HF_API_KEY=your_huggingface_api_key_here
```
Get a free key at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). A free account works, but the free tier has rate limits.

**5. Run the server**
```bash
cd backend
python main.py
```

Open `http://localhost:8000` in your browser. That's it. :P

---

## Caution :O

A few things to know before you go in:

- **HuggingFace free tier runs out.** If your monthly credits are gone, question generation and evaluation will fail silently — the app falls back to a local question bank, but grading will stop working. Keep an eye on your HF usage.

- **Cold start lag.** The first request of the day can take 30–60 seconds because the model has to load on HF's servers. There's a 90-second timeout built in, but if it hits that, just try again.

- **The model can hallucinate scores.** Qwen grades answers by parsing JSON from an LLM output. If the model returns something malformed, it falls back to a heuristic scorer (based on word count). The heuristic is rough — don't trust a suspiciously high or low score on a long answer.

- **Aptitude grading is strict.** Math-style answers with symbols and working steps can confuse the model. It's been prompted to handle this, but edge cases exist.

- **Sessions are in-memory only.** Restarting the server wipes all active sessions. No persistence anywhere.

- **Resume parsing is basic.** PyPDF2 doesn't handle heavily formatted or scanned PDFs well. If skill extraction looks wrong, use the manual skill entry instead.

---

*A project, don't use this as a substitute for actual interview prep.*
