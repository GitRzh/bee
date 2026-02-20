"""
Scoring and results calculation
"""

from typing import Dict, List
from resources import get_resources_for_topics


class ScoringEngine:
    def __init__(self):
        self.max_score_per_question = 15  # 5 + 5 + 5
        self.total_questions = 15
        self.max_total_score = 100  # FINAL SCORE OUT OF 100

    def calculate_question_score(self, evaluation: Dict) -> float:
        """
        Calculate score for a question (0-15 points scale).
        If answer is incorrect, score is 0.
        """
        if evaluation["correctness"] == 0:
            return 0.0

        raw_score = (
            evaluation["correctness"]
            + evaluation["depth"]
            + evaluation["clarity"]
        )  # max = 15

        return min(raw_score, 15.0)

    def calculate_final_results(
        self, questions: List[Dict], evaluations: List[Dict]
    ) -> Dict:
        """
        Calculate comprehensive final results
        """

        # Section-wise scoring
        section_scores = {
            "theory": {"obtained": 0.0, "total": 0.0, "count": 0},
            "aptitude": {"obtained": 0.0, "total": 0.0, "count": 0},
            "coding": {"obtained": 0.0, "total": 0.0, "count": 0},
            "hr": {"obtained": 0.0, "total": 0.0, "count": 0},
        }

        total_score = 0.0
        evaluated_questions = 0
        weak_topics = {}
        max_possible_score = 0.0

        for question, evaluation in zip(questions, evaluations):
            if evaluation is None:
                continue

            q_type = question["type"]
            score = self.calculate_question_score(evaluation)

            total_score += score
            max_possible_score += 15.0
            evaluated_questions += 1

            # Convert to percentage for section scoring
            score_percentage = (score / 15.0) * 100

            section_scores[q_type]["obtained"] += score_percentage
            section_scores[q_type]["total"] += 100
            section_scores[q_type]["count"] += 1

            # Track weak topics (score < 50/100)
            if score_percentage < 50:
                topic = question.get("topic", "Unknown")
                if topic not in weak_topics:
                    weak_topics[topic] = {"count": 0, "total_score": 0.0}
                weak_topics[topic]["count"] += 1
                weak_topics[topic]["total_score"] += score_percentage

        # Calculate section percentages
        for section in section_scores.values():
            if section["total"] > 0:
                section["percentage"] = round(
                    (section["obtained"] / section["total"]) * 100, 1
                )
            else:
                section["percentage"] = 0.0

        # Identify weakest areas
        weak_areas = []
        for topic, data in weak_topics.items():
            avg_score = data["total_score"] / data["count"]
            weak_areas.append(
                {
                    "topic": topic,
                    "avg_score": round(avg_score, 1),
                    "questions_failed": data["count"],
                }
            )

        weak_areas.sort(key=lambda x: x["avg_score"])

        # Overall percentage (FINAL SCORE OUT OF 100)
        if max_possible_score > 0:
            overall_percentage = round((total_score / max_possible_score) * 100, 1)
        else:
            overall_percentage = 0.0
        
        # Cap at 100%
        overall_percentage = min(overall_percentage, 100.0)

        # Performance verdict
        if overall_percentage >= 80:
            verdict = "EXCELLENT"
        elif overall_percentage >= 60:
            verdict = "GOOD"
        elif overall_percentage >= 40:
            verdict = "AVERAGE"
        else:
            verdict = "POOR"

        # Get learning resources for weak topics only if there are any
        weak_topic_names = [w["topic"] for w in weak_areas[:5]] if weak_areas else []
        resources = get_resources_for_topics(weak_topic_names) if weak_topic_names else []

        return {
            "total_score": overall_percentage,
            "max_score": self.max_total_score,
            "percentage": overall_percentage,
            "verdict": verdict,
            "section_scores": section_scores,
            "weak_areas": weak_areas[:5],
            "improvement_suggestions": self._generate_suggestions(
                section_scores, weak_areas
            ),
            "learning_resources": resources,
        }

    def _generate_suggestions(
        self, section_scores: Dict, weak_areas: List
    ) -> List[str]:
        """
        Generate improvement suggestions based on performance
        """
        suggestions = []

        # Section-based suggestions
        for section, scores in section_scores.items():
            if scores["percentage"] < 50 and scores["count"] > 0:
                section_map = {
                    "theory": "Focus on theoretical foundations and core concepts",
                    "aptitude": "Practice more problem-solving and analytical thinking exercises",
                    "coding": "Improve coding skills through regular practice on platforms like LeetCode",
                    "hr": "Prepare better behavioral answers using the STAR method",
                }
                suggestions.append(
                    section_map.get(section, f"Improve {section} skills")
                )

        # Topic-based suggestion
        if weak_areas:
            top_weak = weak_areas[0]["topic"]
            suggestions.append(
                f"Deep dive into {top_weak} — this is your weakest area"
            )

        # General fallback
        if not suggestions:
            suggestions.append(
                "Maintain your strong performance through continuous practice"
            )

        return suggestions[:5]