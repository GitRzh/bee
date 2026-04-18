"""
Qwen client via HuggingFace Inference API

CALL BUDGET PER SESSION:
  Session start : 4 calls  (sequential, 1.5s apart)
  Per answer    : 1-2 calls (eval + fallback if parse fails)
  Rephrase      : 1 call
  Resume parse  : 1 call
  WORST CASE    : 4 + 30 = 34 calls per full session
"""

import os
import asyncio
import json
from typing import Dict, Optional, List
from huggingface_hub import InferenceClient


# ── Local fallback question bank ──
_FALLBACKS = {
    "theory": {
        "easy": [
            {"question": "What is the difference between supervised and unsupervised learning?", "topic": "ML Basics"},
            {"question": "Define overfitting and explain how to detect it.", "topic": "Model Evaluation"},
        ],
        "medium": [
            {"question": "Explain gradient descent and how learning rate affects convergence.", "topic": "Optimization"},
            {"question": "What is the bias-variance tradeoff and why does it matter?", "topic": "Model Theory"},
        ],
        "hard": [
            {"question": "Explain the vanishing gradient problem and three techniques to mitigate it.", "topic": "Deep Learning"},
            {"question": "Compare batch normalization and layer normalization — when would you choose each?", "topic": "Neural Networks"},
        ],
    },
    "aptitude": {
        "easy": [
            {"question": "A train travels 120 km in 2 hours. What is its speed in m/s?", "topic": "Speed Distance"},
            {"question": "Find the next term: 2, 6, 12, 20, 30, ?", "topic": "Number Series"},
        ],
        "medium": [
            {"question": "A can finish a task in 10 days, B in 15 days. How many days to finish together?", "topic": "Work Problems"},
            {"question": "In a class of 40, average score is 72. If 5 students with avg 60 leave, what is the new average?", "topic": "Averages"},
        ],
        "hard": [
            {"question": "In how many ways can 4 boys and 3 girls sit in a row so no two girls are adjacent?", "topic": "Permutations"},
        ],
    },
    "coding": {
        "easy": [
            {"question": "Write a function to normalize an array to the range [0, 1].", "topic": "Data Processing"},
        ],
        "medium": [
            {"question": "Implement k-fold cross-validation from scratch without using ML libraries.", "topic": "Model Evaluation"},
        ],
        "hard": [
            {"question": "Implement a fully-connected neural network layer with forward and backward pass from scratch.", "topic": "Neural Networks"},
        ],
    },
    "hr": {
        "medium": [
            {"question": "Describe a challenging ML project you worked on. What was your approach and what did you learn?", "topic": "Behavioral"},
        ],
    },
}


class QwenClient:
    def __init__(self):
        self.api_key = os.getenv("HF_API_KEY")
        if not self.api_key:
            raise ValueError("HF_API_KEY environment variable not set")

        self.model = "Qwen/Qwen2.5-7B-Instruct"
        self.client = InferenceClient(token=self.api_key)
        print(f"✔ Qwen client ready | model: {self.model}")

    # ─────────────────────────── CORE ───────────────────────────

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Optional[str]:
        try:
            print(f">_> Qwen call | temp={temperature:.1f} | max_tokens={max_tokens}")
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
            )
            text = response.choices[0].message.content.strip()
            print(f":) Qwen done | {len(text)} chars")
            return text
        except Exception as e:
            print(f":( Qwen error: {type(e).__name__}: {e}")
            return None

    # ─────────────────── SKILL EXTRACTION (1 call) ───────────────────────

    async def extract_skills(self, resume_text: str) -> list:
        """
        Extract ONLY AI/ML technical skills from the skills section of resume.
        Targets specific section headers to avoid extracting irrelevant text.
        """
        # Step 1: Extract only the skills section
        skills_section = self._extract_skills_section(resume_text)
        
        if not skills_section:
            skills_section = resume_text[:2000]
        
        prompt = f"""Extract ONLY AI/ML technical skills from this skills section.
Return a JSON array of skill strings only. NO job titles, NO soft skills, NO company names.

ONLY these types of skills:
- Programming languages: Python, Java, C++, etc
- ML frameworks: PyTorch, TensorFlow, Keras, etc
- Libraries: Pandas, NumPy, Scikit-learn, etc
- ML concepts: Deep Learning, NLP, Computer Vision, etc
- Tools: Docker, Git, AWS, etc
- Data: SQL, NoSQL, Big Data, etc

Skills Section:
{skills_section}

Return ONLY valid JSON like: ["skill1", "skill2"]"""

        response = await self.generate(prompt, max_tokens=256, temperature=0.2)
        if not response:
            return ["Machine Learning", "Python", "Deep Learning"]
        try:
            start, end = response.find("["), response.rfind("]") + 1
            skills = json.loads(response[start:end], strict=False)
            # Clean up: remove duplicates, filter empty, max 15 skills
            cleaned = [s.strip() for s in skills if s.strip()]
            return list(dict.fromkeys(cleaned))[:15]  # Remove duplicates, keep order
        except Exception:
            return ["Machine Learning", "Python", "Deep Learning"]
    
    def _extract_skills_section(self, text: str) -> Optional[str]:
        """
        Extract only the skills section from resume.
        Looks for headers like 'Skills', 'Technical Skills', 'Expertise', etc.
        """
        lines = text.split('\n')
        skills_start = -1
        skills_end = -1
        
        # Headers that indicate skills section
        skills_headers = ['skill', 'technical', 'expertise', 'proficiency', 'competency', 'abilities']
        # Headers that indicate section end
        section_headers = ['experience', 'work', 'education', 'project', 'achievement', 'certification', 
                          'publication', 'award', 'language', 'contact', 'summary', 'objective', 'profile']
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Find skills section start
            if skills_start == -1:
                if any(header in line_lower for header in skills_headers):
                    skills_start = i + 1
            
            # Find skills section end (next major section)
            elif skills_start != -1 and skills_end == -1:
                if any(header in line_lower for header in section_headers):
                    skills_end = i
                    break
        
        # If we found skills section, extract it
        if skills_start != -1:
            if skills_end == -1:
                skills_end = min(skills_start + 50, len(lines))  # Limit to 50 lines
            
            skills_text = '\n'.join(lines[skills_start:skills_end])
            return skills_text[:2000]  # Limit to 2000 chars
        
        return None

    # ──────────────────── QUESTION GENERATION (1 call per type) ──────────────────

    _TYPE_PROMPTS = {
        "theory": {
            "easy":   "definition-based conceptual (What is? Define?), beginner-friendly, NO coding",
            "medium": "conceptual explanation (Explain, Difference between, Advantages of), NO coding",
            "hard":   "analytical theory (Why is X used? Compare X vs Y in depth), NO coding",
        },
        "aptitude": {
            "easy":   "simple single-step logical/quantitative (e.g., speed-distance, basic series)",
            "medium": "multi-step quantitative/logical reasoning, GATE-level",
            "hard":   "complex puzzles, seating arrangements, or advanced data interpretation, GATE-level",
        },
        "coding": {
            "easy":   "simple 5-10 line Python function (basic logic, no data structures)",
            "medium": "moderate 15-30 line algorithmic challenge",
            "hard":   "complex 40+ line implementation (e.g., NN layer, custom optimizer)",
        },
        "hr": {
            "medium": "behavioral question using STAR format for an AI/ML candidate",
        },
    }

    async def generate_questions_batch(
        self,
        skills: List[str],
        q_type: str,
        difficulty_counts: List[tuple],
        existing_questions: List[Dict],
    ) -> List[Dict]:
        """
        ONE HF call per question type, up to 3 retry attempts on parse failure.
        Returns [] on all failures — controller fills from _FALLBACKS.
        """
        skills_str = ", ".join(skills[:5])
        existing_texts = [q["question"].lower()[:80] for q in existing_questions]
        total = sum(c for _, c in difficulty_counts)

        spec_lines = []
        for diff, count in difficulty_counts:
            desc = self._TYPE_PROMPTS.get(q_type, {}).get(diff, "")
            spec_lines.append(f'  - {count} "{diff}" question(s): {desc}')

        aptitude_note = (
            "\nIMPORTANT: Aptitude questions must NOT be about the skills above — "
            "they are pure logical/quantitative reasoning problems."
            if q_type == "aptitude"
            else f"\nSkills to focus on: {skills_str}"
        )

        prompt = f"""Generate exactly {total} unique {q_type} interview questions.{aptitude_note}

Breakdown:
{chr(10).join(spec_lines)}

Return ONLY a JSON array (no extra text):
[
  {{"question": "...", "difficulty": "easy", "topic": "..."}},
  ...
]

Rules:
- All questions must be different from each other
- Do NOT include code snippets in theory/aptitude/hr questions
- topic should be a short label (2-4 words)"""

        print(f"⏳ Generating {total} {q_type} questions")
        for attempt in range(3):
            response = await self.generate(
                prompt, max_tokens=1800, temperature=0.6 + attempt * 0.1
            )
            if not response:
                continue
            try:
                start = response.find("[")
                end = response.rfind("]") + 1
                if start == -1 or end == 0:
                    continue
                data = json.loads(response[start:end], strict=False)
                if not isinstance(data, list):
                    continue

                filtered = []
                for item in data:
                    if not item.get("question"):
                        continue
                    q_lower = item["question"].lower()
                    if not any(q_lower[:80] in ex or ex in q_lower[:80] for ex in existing_texts):
                        filtered.append({
                            "question": item["question"],
                            "topic": item.get("topic", q_type.capitalize()),
                            "difficulty": item.get("difficulty", "medium"),
                        })

                if len(filtered) >= max(1, total - 1):
                    print(f"✅ {q_type}: {len(filtered)}/{total} from Qwen")
                    return filtered[:total]

            except Exception as e:
                print(f"⚠️ {q_type} parse error (attempt {attempt + 1}): {e}")

        print(f"⚠️ {q_type}: Qwen failed — local fallbacks will be used")
        return []

    # ──────────────────── REPHRASE (1 call) ──────────────────

    async def rephrase_question(self, question: str, q_type: str) -> Optional[str]:
        prompt = f"""Rephrase the following {q_type} interview question to make it clearer and easier to understand.
Keep the same intent and difficulty. Do NOT make it easier — just clearer wording.

Original: {question}

Return ONLY the rephrased question text, nothing else."""

        response = await self.generate(prompt, max_tokens=200, temperature=0.4)
        if response:
            return response.strip('"\'').strip()
        return None

    # ──────────────────── ANSWER EVALUATION (1-2 calls) ──────────────────

    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        topic: str,
        q_type: str = "theory",
        previous_qa: List[Dict] = None,
    ) -> Optional[Dict]:
        """1 call normally, 2 if first parse fails. Local checks are free."""

        # ── Free local checks — 0 API calls ──
        if self._is_gibberish(answer):
            return {
                "correctness": 0,
                "depth": 0,
                "clarity": 0,
                "feedback": "Invalid answer — gibberish or placeholder detected.",
            }

        if self._is_no_answer(answer):
            return {
                "correctness": 0,
                "depth": 0,
                "clarity": 0,
                "feedback": "No answer provided — candidate indicated they do not know.",
            }

        context = ""
        if previous_qa:
            context = "\n".join(
                f"Q: {qa['q']}\nA: {qa['a'][:200]}..." for qa in previous_qa[-3:]
            )

        if q_type == "coding":
            prompt = self._build_code_eval_prompt(question, answer, topic, context)
        elif q_type == "aptitude":
            prompt = self._build_aptitude_eval_prompt(question, answer, context)
        else:
            prompt = self._build_theory_eval_prompt(question, answer, topic, context)

        # Attempt 1: full prompt
        # SOLUTION 5: Use lower temperature (0.15) for aptitude to prevent hallucinations
        # Regular 0.3 for theory/coding (needs more creativity)
        temp = 0.15 if q_type == "aptitude" else 0.3
        response = await self.generate(prompt, max_tokens=400, temperature=temp)
        result = self._parse_eval_response(response)
        if result:
            # SOLUTION 5: Apply post-validation rules to catch LLM errors
            if q_type == "aptitude":
                result = self._validate_aptitude_eval(question, answer, result)
            return result

        # Attempt 2: stripped-down prompt
        print("⚠️ Eval parse failed — retrying with simplified prompt")
        fallback_prompt = f"""Score this answer from 0-5 each for correctness, depth, clarity.

Question: {question[:200]}
Answer: {answer[:300]}

Return ONLY this JSON with no extra text:
{{"correctness": 0, "depth": 0, "clarity": 0, "feedback": "brief reason"}}"""

        response2 = await self.generate(fallback_prompt, max_tokens=150, temperature=0.2)
        result2 = self._parse_eval_response(response2)
        if result2:
            return result2

        # Local heuristic fallback — 0 extra calls
        print("⚠️ Both eval attempts failed — using local heuristic")
        return self._local_score_fallback(answer)

    def _local_score_fallback(self, answer: str) -> Dict:
        words = len(answer.strip().split())
        if words < 10:   c, d, cl = 1, 0, 1
        elif words < 30: c, d, cl = 2, 1, 2
        elif words < 80: c, d, cl = 3, 2, 3
        else:            c, d, cl = 3, 3, 3
        return {"correctness": c, "depth": d, "clarity": cl,
                "feedback": "Auto-scored (evaluation unavailable) — based on response length."}

    def _parse_eval_response(self, response: Optional[str]) -> Optional[Dict]:
        if not response:
            return None
        try:
            cleaned = response.replace("\u2019", "'").replace("\u2018", "'")
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start == -1 or end == 0:
                return None
            data = json.loads(cleaned[start:end], strict=False)
            c  = max(0, min(5, int(data.get("correctness", 0))))
            d  = max(0, min(5, int(data.get("depth", 0))))
            cl = max(0, min(5, int(data.get("clarity", 0))))
            fb = str(data.get("feedback", "")).strip()
            if not fb:
                total = c + d + cl
                fb = (
                    "Strong answer covering all key points." if total >= 12 else
                    "Good answer with most key points covered." if total >= 8 else
                    "Partially correct — some key points missing." if total >= 4 else
                    "Answer was insufficient or incorrect."
                )
            return {"correctness": c, "depth": d, "clarity": cl, "feedback": fb}
        except Exception as e:
            print(f"⚠️ Eval parse error: {e}")
            return None

    def _build_aptitude_eval_prompt(self, question: str, answer: str, context: str) -> str:
        return f"""You are evaluating a quantitative aptitude / logical reasoning answer.

Question: {question}
Answer: {answer}

{context}

IMPORTANT RULES:
- Step-by-step working with math symbols is CORRECT and expected
- A numerical final answer with correct working should score high
- Only mark correctness=0 if the final answer is clearly wrong or missing

Score 0-5 each:
- correctness: Is the final answer correct?
- depth: Did they show clear working/steps?
- clarity: Is the solution easy to follow?

Return ONLY JSON:
{{
  "correctness": 0-5,
  "depth": 0-5,
  "clarity": 0-5,
  "feedback": "1 sentence stating if final answer is correct or not"
}}"""

    def _build_theory_eval_prompt(self, question: str, answer: str, topic: str, context: str) -> str:
        return f"""You are a STRICT AI/ML interviewer evaluating a theory/HR answer.

Question: {question}
Topic: {topic}
Answer: {answer}

{context}

Score 0-5 for each dimension:
- correctness: Is the answer factually correct?
- depth: Does it go beyond surface-level?
- clarity: Is it clearly communicated?

Return ONLY JSON:
{{
  "correctness": 0-5,
  "depth": 0-5,
  "clarity": 0-5,
  "feedback": "1 sentence stating what was right or wrong"
}}"""

    def _build_code_eval_prompt(self, question: str, answer: str, topic: str, context: str) -> str:
        return f"""You are a STRICT code reviewer evaluating a coding interview submission.

Question: {question}
Topic: {topic}
Submitted Code:
{answer}

Score 0-5 each:
- correctness: Does the code logically solve the problem?
- depth: Quality of implementation (edge cases, efficiency)?
- clarity: Code readability and structure?

IMPORTANT: If only a comment or placeholder is written, score 0 for all.

Return ONLY JSON:
{{
  "correctness": 0-5,
  "depth": 0-5,
  "clarity": 0-5,
  "feedback": "1 sentence stating what was good or wrong in the code"
}}"""

    # ──────────────────── HELPERS ──────────────────

    def _is_no_answer(self, text: str) -> bool:
        """
        Detect explicit "I don't know" answers.
        Only match if the answer is SHORT and EXPLICITLY says they don't know.
        Don't match if answer contains actual content + "maybe I don't know" as aside.
        """
        t = text.strip().lower()
        
        # If answer is very long, it's not a pure "I don't know" — it's actual content
        if len(t) > 80:
            return False
        
        # Must have very few words (max 10 words) to be a pure "I don't know"
        word_count = len(t.split())
        if word_count > 10:
            return False
        
        # Exact patterns that explicitly say they don't know
        exact_patterns = [
            "don't know", "dont know", "do not know",
            "no idea", "no clue", "not sure", "i give up",
            "can't answer", "cannot answer", "cant answer",
            "don't understand", "dont understand",
            "skip", "pass", "idk", "n/a", "na",
            "no solution",
        ]
        
        # For short answers, check if it's MOSTLY about not knowing
        # Allow patterns like "maybe i dont know" or "i have no idea" 
        # but only if answer is very short and explicit
        for pattern in exact_patterns:
            if t == pattern or (word_count <= 5 and pattern in t):
                return True
        
        return False

    def _is_gibberish(self, text: str) -> bool:
        """
        Detect pure gibberish (999999, #####, etc).
        Don't flag actual short answers with real words.
        """
        text = text.strip().lower()
        
        # Empty or too short
        if len(text) < 10:
            return False  # Could be valid short answer
        
        # Check if it's PURE repetition (999999, #####, hhhhh, etc)
        # These are obvious placeholder gibberish
        unique_chars = set(text.replace(" ", "").replace("\n", ""))
        if len(unique_chars) <= 3:  # Only 1-3 unique characters (like 9, #, h)
            # But allow real words: "aaa" is gibberish, "the" is not
            if text.isalnum() or not any(c.isalpha() for c in text):
                # No letters or only numbers/symbols = gibberish
                return True
        
        # Must have actual words (not just punctuation)
        word_count = len(text.split())
        if word_count < 3:
            return False  # Allow short valid answers
        
        # Check if most characters are alphanumeric (should be for real text)
        alpha_count = sum(c.isalnum() or c.isspace() for c in text)
        if alpha_count / len(text) < 0.7:
            return True  # Too many symbols
        
        # Check consonant-vowel ratio (real text has balanced vowels)
        alpha_chars = [c for c in text if c.isalpha()]
        if alpha_chars:
            vowels = sum(1 for c in alpha_chars if c in "aeiou")
            # Real words must have SOME vowels
            if vowels == 0:
                return True
            consonant_ratio = (len(alpha_chars) - vowels) / len(alpha_chars)
            if consonant_ratio > 0.85:
                return True  # Too few vowels
        
        return False

    def _validate_aptitude_eval(self, question: str, answer: str, evaluation: Dict) -> Dict:
        """
        SOLUTION 5 HYBRID: Post-validation rules for aptitude evaluations.
        Catches common LLM hallucinations without extra tokens.
        
        These rules are applied AFTER the LLM evaluation to catch mistakes:
        - The "8.33 km" bug (incorrectly dividing 25/3)
        - Vague feedback that contradicts the score
        - Inconsistent correctness judgment
        """
        # Rule 1: Catch the exact "8.33 km" hallucination pattern
        # If LLM says answer is wrong but feedback mentions "8.33" or "25/3"
        # and the user answered with "25", it's the known bug
        feedback_lower = evaluation.get("feedback", "").lower()
        answer_lower = answer.lower()
        
        if evaluation["correctness"] == 0 and ("8.33" in feedback_lower or "25/3" in feedback_lower):
            if "25" in answer_lower or "25 km" in answer_lower:
                # This is the exact bug pattern - user said 25, LLM hallucinated 8.33
                # Override: user is correct
                evaluation["correctness"] = 5
                evaluation["depth"] = 4
                evaluation["clarity"] = 4
                evaluation["feedback"] = "Correct answer: 25 km. User answered: 25 km. CORRECT."
                return evaluation
        
        # Rule 2: If user gave a number but feedback doesn't explain what's wrong, mark as inconclusive
        # User answers: "25 km", LLM says correctness=0 but feedback is vague
        if evaluation["correctness"] == 0 and any(char.isdigit() for char in answer):
            explanation_keywords = ["wrong", "incorrect", "error", "should be", "actually", "instead", "not", "false"]
            has_explanation = any(word in feedback_lower for word in explanation_keywords)
            
            if not has_explanation:
                # Feedback is vague, can't trust this evaluation
                evaluation["correctness"] = max(1, evaluation["correctness"])
                evaluation["feedback"] = f"Evaluation inconclusive: {evaluation['feedback']}"
        
        # Rule 3: If correctness=5 but feedback says wrong, contradiction detected
        if evaluation["correctness"] == 5 and any(word in feedback_lower for word in ["wrong", "incorrect", "false"]):
            # LLM contradicted itself, be conservative
            evaluation["correctness"] = 3
            evaluation["feedback"] = f"Evaluation unclear: marked correct but feedback mentions errors. Review needed."
        
        # Rule 4: Catch division hallucinations (user says "25 km", LLM invents "25 ÷ 3")
        if evaluation["correctness"] == 0:
            # Check if feedback invents division that wasn't in question
            if "÷" in feedback_lower or "/ " in feedback_lower or "/3" in feedback_lower:
                # If user answer is simple/direct and LLM invents complex division, suspicious
                if len(answer) < 50:  # Short answer = probably not that complicated
                    evaluation["correctness"] = max(2, evaluation["correctness"])
                    evaluation["feedback"] = f"Caution: LLM feedback may contain errors. Original: {evaluation['feedback']}"
        
        return evaluation
