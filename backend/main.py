"""
FastAPI main application
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import PyPDF2
import io
from dotenv import load_dotenv
from pathlib import Path

from interview_controller import InterviewController
from local_utils import validate_skills_local

load_dotenv()

app = FastAPI(title="  BEE — beeeee freee!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

controller = InterviewController()

# Resolve frontend directory
STATIC_DIR = Path(__file__).parent.parent / "frontend"
if not STATIC_DIR.exists():
    STATIC_DIR = Path(__file__).parent.parent / "front"
if not STATIC_DIR.exists():
    STATIC_DIR = Path(__file__).parent / "frontend"
if not STATIC_DIR.exists():
    STATIC_DIR = Path(__file__).parent / "front"
if not STATIC_DIR.exists():
    STATIC_DIR = Path(__file__).parent

print(f"🗁 Serving static files from: {STATIC_DIR}")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Models ──

class SkillsInput(BaseModel):
    skills: List[str]

class AnswerSubmission(BaseModel):
    session_id: str
    answer: str

class ManualIntakeInput(BaseModel):
    skills: List[str]
    experience_level: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    target_role: Optional[str] = None


# ── Frontend routes ──

@app.get("/")
async def serve_index():
    p = STATIC_DIR / "index.html"
    return FileResponse(p) if p.exists() else {"message": "BEE API"}

@app.get("/style.css")
async def serve_css():
    return FileResponse(STATIC_DIR / "style.css")

@app.get("/landing.js")
async def serve_landing_js():
    return FileResponse(STATIC_DIR / "landing.js")

@app.get("/interview.html")
async def serve_interview():
    p = STATIC_DIR / "interview.html"
    if p.exists(): return FileResponse(p)
    raise HTTPException(404, "Interview page not found")

@app.get("/interview")
async def serve_interview_alt():
    return await serve_interview()

@app.get("/interview.js")
async def serve_interview_js():
    return FileResponse(STATIC_DIR / "interview.js")

@app.get("/results.html")
async def serve_results():
    p = STATIC_DIR / "results.html"
    if p.exists(): return FileResponse(p)
    raise HTTPException(404, "Results page not found")

@app.get("/results")
async def serve_results_alt():
    return await serve_results()

@app.get("/results.js")
async def serve_results_js():
    return FileResponse(STATIC_DIR / "results.js")


# ── API ──

@app.get("/api")
async def api_root():
    return {"message": "BEE API", "status": "running"}


@app.post("/api/start-with-skills")
async def start_with_skills(data: SkillsInput):
    if not data.skills:
        raise HTTPException(400, "At least one skill required")

    valid_skills, invalid_skills = validate_skills_local(data.skills)
    if not valid_skills:
        raise HTTPException(400, {
            "message": "No valid AI/ML/tech skills found.",
            "invalid_skills": invalid_skills,
        })

    try:
        session_id = await controller.create_session(valid_skills)
        first_question = controller.get_current_question(session_id)
        return {
            "session_id": session_id,
            "skills": valid_skills,
            "invalid_skills": invalid_skills,
            "question": first_question,
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to start interview: {e}")


@app.post("/api/start-manual")
async def start_manual(data: ManualIntakeInput):
    raw_skills = data.skills or data.tech_stack
    if not raw_skills:
        raise HTTPException(400, "Skills or tech stack required")

    valid_skills, invalid_skills = validate_skills_local(raw_skills)
    if not valid_skills:
        raise HTTPException(400, {
            "message": "No valid AI/ML/tech skills found.",
            "invalid_skills": invalid_skills,
        })

    try:
        session_id = await controller.create_session(
            valid_skills, experience=data.experience_level, role=data.target_role,
        )
        first_question = controller.get_current_question(session_id)
        return {
            "session_id": session_id,
            "skills": valid_skills,
            "invalid_skills": invalid_skills,
            "experience": data.experience_level,
            "role": data.target_role,
            "question": first_question,
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to start interview: {e}")


@app.post("/api/start-with-resume")
async def start_with_resume(file: UploadFile = File(...)):
    if not file.filename.endswith((".pdf", ".txt")):
        raise HTTPException(400, "Only PDF and TXT files supported")

    try:
        content = await file.read()
        if file.filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = "".join(page.extract_text() or "" for page in pdf_reader.pages)
        else:
            text = content.decode("utf-8")

        if len(text.strip()) < 200:
            raise HTTPException(400, "Resume content too short or invalid")

        # Reuse shared controller client — no extra instance
        skills = await controller.mistral_client.extract_skills(text)

        if not skills:
            raise HTTPException(400, "Could not extract AI/ML skills from resume")

        # Validate extracted skills the same way manual entry does
        valid_skills, invalid_skills = validate_skills_local(skills)
        if not valid_skills:
            raise HTTPException(400, "No valid AI/ML/tech skills found in resume")

        session_id = await controller.create_session(valid_skills)
        first_question = controller.get_current_question(session_id)
        return {"session_id": session_id, "skills": valid_skills, "question": first_question}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to process resume: {e}")


@app.post("/api/submit-answer")
async def submit_answer(data: AnswerSubmission):
    if not data.answer or len(data.answer.strip()) < 5:
        raise HTTPException(400, "Answer too short")
    try:
        result = await controller.submit_answer(data.session_id, data.answer)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to submit answer: {e}")


@app.post("/api/rephrase/{session_id}")
async def rephrase_question(session_id: str):
    try:
        result = await controller.rephrase_current_question(session_id)
        if "error" in result:
            raise HTTPException(400, result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to rephrase: {e}")


@app.get("/api/current-question/{session_id}")
async def get_current_question(session_id: str):
    q = controller.get_current_question(session_id)
    if not q:
        raise HTTPException(404, "Session not found or completed")
    return q


@app.post("/api/restart/{session_id}")
async def restart_interview(session_id: str):
    session = controller.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    try:
        new_id = await controller.create_session(
            session.skills, experience=session.experience, role=session.role,
        )
        # Only delete old session after new one is confirmed ready
        first_question = controller.get_current_question(new_id)
        if not first_question:
            raise Exception("New session failed to initialise questions")
        controller.delete_session(session_id)
        return {
            "session_id": new_id,
            "skills": session.skills,
            "question": first_question,
            "message": "Interview restarted",
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to restart: {e}")


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    controller.delete_session(session_id)
    return {"message": "Session deleted"}


@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    session = controller.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "session_id": session.session_id,
        "skills": session.skills,
        "status": session.status,
        "progress": {
            "current": session.current_question_index + 1,
            "total": len(session.questions),
        },
        "created_at": session.created_at.isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  BEE — beeeee freee!")
    print("=" * 60)
    print(f"  Frontend:  http://localhost:8000")
    print(f"  Interview: http://localhost:8000/interview.html")
    print(f"  API Docs:  http://localhost:8000/docs")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=120)
