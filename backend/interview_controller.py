"""
Interview flow controller — uses MistralClient
"""

import uuid
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from qwen_client import QwenClient, _FALLBACKS
from scoring import ScoringEngine
from local_utils import classify_response_local


class InterviewSession:
    def __init__(self, session_id: str, skills: List[str], experience: str = None, role: str = None):
        self.session_id = session_id
        self.skills = skills
        self.experience = experience
        self.role = role
        self.questions = []
        self.current_question_index = 0
        self.answers = []
        self.evaluations = []
        self.off_topic_warnings = 0
        self.status = "initializing"
        self.created_at = datetime.now()
        self.rephrase_counts: Dict[int, int] = {}


class InterviewController:
    def __init__(self):
        self.mistral_client = QwenClient()
        self.scoring_engine = ScoringEngine()
        self.sessions: Dict[str, InterviewSession] = {}

        self.question_distribution = [
            ("theory",   [("easy", 2), ("medium", 2), ("hard", 2)]),
            ("aptitude", [("easy", 2), ("medium", 2), ("hard", 1)]),
            ("coding",   [("easy", 1), ("medium", 1), ("hard", 1)]),
            ("hr",       [("medium", 1)]),
        ]
        self.max_rephrases_per_question = 2

    def _cleanup_old_sessions(self):
        cutoff = datetime.now() - timedelta(hours=2)
        expired = [sid for sid, s in self.sessions.items() if s.created_at < cutoff]
        for sid in expired:
            del self.sessions[sid]

    async def create_session(self, skills: List[str], experience: str = None, role: str = None) -> str:
        self._cleanup_old_sessions()
        session_id = str(uuid.uuid4())
        session = InterviewSession(session_id, skills, experience, role)
        self.sessions[session_id] = session
        await self._generate_questions(session)
        session.status = "in_progress"
        return session_id

    async def _generate_questions(self, session: InterviewSession):
        """
        4 sequential calls with 1.5s delay between each to avoid rate limits.
        Gaps filled from local fallbacks.
        """
        async def generate_for_type(q_type, difficulty_counts):
            generated = await self.mistral_client.generate_questions_batch(
                session.skills, q_type, difficulty_counts, [],
            )

            diff_order = []
            for diff, count in difficulty_counts:
                diff_order.extend([diff] * count)

            api_by_diff: Dict[str, list] = {}
            for q in generated:
                d = q.get("difficulty", "medium")
                api_by_diff.setdefault(d, []).append(q)

            results = []
            for diff in diff_order:
                if api_by_diff.get(diff):
                    q_data = api_by_diff[diff].pop(0)
                else:
                    q_data = next(
                        (v.pop(0) for v in api_by_diff.values() if v), None
                    ) or self._get_fallback_question(q_type, diff)

                results.append({
                    "type": q_type,
                    "difficulty": diff,
                    "question": q_data["question"],
                    "topic": q_data.get("topic", q_type.capitalize()),
                })
            return results

        # Sequential with delay to stay under rate limits
        for i, (q_type, difficulty_counts) in enumerate(self.question_distribution):
            if i > 0:
                await asyncio.sleep(1.5)
            type_questions = await generate_for_type(q_type, difficulty_counts)
            for q in type_questions:
                session.questions.append({"id": len(session.questions), **q})

    def _get_fallback_question(self, q_type: str, difficulty: str) -> Dict:
        bank = _FALLBACKS.get(q_type, {}).get(difficulty, [])
        if bank:
            return bank[0]
        return {
            "question": f"Explain your experience with {q_type} concepts.",
            "topic": q_type.capitalize(),
            "difficulty": difficulty,
        }

    async def submit_answer(self, session_id: str, answer: str) -> Dict:
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        if session.current_question_index >= len(session.questions):
            return {"error": "No more questions"}

        current_question = session.questions[session.current_question_index]
        classification = classify_response_local(current_question["question"], answer)

        if classification in ["OFF_TOPIC", "META"]:
            session.off_topic_warnings += 1
            if session.off_topic_warnings == 1:
                return {
                    "warning": "WARNING: Stay on topic. Answer the question asked or you will fail this question.",
                    "continue": True,
                }
            else:
                session.answers.append(answer)
                session.evaluations.append({
                    "correctness": 0, "depth": 0, "clarity": 0,
                    "feedback": "FAILED: Refused to answer the question properly.",
                })
                session.off_topic_warnings = 0
                session.current_question_index += 1
                return await self._get_next_question_response(session)

        session.off_topic_warnings = 0

        previous_qa = [
            {"q": session.questions[i]["question"], "a": session.answers[i]}
            for i in range(len(session.answers))
        ]

        evaluation = await self.mistral_client.evaluate_answer(
            current_question["question"],
            answer,
            current_question["topic"],
            q_type=current_question["type"],
            previous_qa=previous_qa,
        )

        if not evaluation:
            evaluation = {"correctness": 1, "depth": 1, "clarity": 1,
                          "feedback": "Unable to evaluate. Default low score assigned."}

        session.answers.append(answer)
        session.evaluations.append(evaluation)
        session.current_question_index += 1
        return await self._get_next_question_response(session)

    async def rephrase_current_question(self, session_id: str) -> Dict:
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        idx = session.current_question_index
        if idx >= len(session.questions):
            return {"error": "No current question"}
        used = session.rephrase_counts.get(idx, 0)
        if used >= self.max_rephrases_per_question:
            return {"error": "No rephrase attempts remaining"}

        current_q = session.questions[idx]
        rephrased = await self.mistral_client.rephrase_question(
            current_q["question"], current_q["type"],
        )
        if not rephrased:
            return {"error": "Could not rephrase question"}

        session.rephrase_counts[idx] = used + 1
        remaining = self.max_rephrases_per_question - session.rephrase_counts[idx]
        return {
            "rephrased_question": rephrased,
            "original_question": current_q["question"],
            "rephrases_remaining": remaining,
        }

    async def _get_next_question_response(self, session: InterviewSession) -> Dict:
        # Always reset warning counter when moving to a new question
        session.off_topic_warnings = 0

        if session.current_question_index >= len(session.questions):
            session.status = "completed"
            results = self.scoring_engine.calculate_final_results(
                session.questions, session.evaluations,
            )
            review = []
            for i, (q, e, a) in enumerate(zip(session.questions, session.evaluations, session.answers)):
                if e is None:
                    continue
                score_pct = round(((e["correctness"] + e["depth"] + e["clarity"]) / 15.0) * 100, 1)
                review.append({
                    "index": i + 1,
                    "type": q["type"],
                    "difficulty": q["difficulty"],
                    "question": q["question"],
                    "answer": a,
                    "feedback": e.get("feedback", ""),
                    "score": score_pct,
                })
            results["review"] = review
            return {"completed": True, "results": results}

        next_question = session.questions[session.current_question_index]
        idx = session.current_question_index
        return {
            "completed": False,
            "question": next_question,
            "progress": {"current": idx + 1, "total": len(session.questions)},
            "rephrases_remaining": self.max_rephrases_per_question - session.rephrase_counts.get(idx, 0),
        }

    def get_current_question(self, session_id: str) -> Optional[Dict]:
        session = self.sessions.get(session_id)
        if not session or session.current_question_index >= len(session.questions):
            return None
        idx = session.current_question_index
        return {
            "question": session.questions[idx],
            "progress": {"current": idx + 1, "total": len(session.questions)},
            "rephrases_remaining": self.max_rephrases_per_question - session.rephrase_counts.get(idx, 0),
        }

    def get_session(self, session_id: str) -> Optional[InterviewSession]:
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
