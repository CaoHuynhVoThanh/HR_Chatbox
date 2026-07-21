import unittest

from app.core.agents import AgentOrchestrator


class AgentOrchestratorTests(unittest.TestCase):
    def test_interview_request_produces_question_intent(self) -> None:
        brief = AgentOrchestrator().build_brief("Hãy bắt đầu phỏng vấn tôi")
        self.assertIn("generate_questions", brief.instructions)
        self.assertIn("Question Generator", brief.instructions)

    def test_report_request_produces_report_intent(self) -> None:
        brief = AgentOrchestrator().build_brief("Tạo báo cáo tổng kết CV")
        self.assertIn("final_report", brief.instructions)

    def test_twenty_question_request_generates_a_question_set_instruction(self) -> None:
        brief = AgentOrchestrator().build_brief("Hãy tạo đúng 20 câu hỏi phỏng vấn cho tôi")
        self.assertIn("đúng 20 câu hỏi", brief.instructions)
