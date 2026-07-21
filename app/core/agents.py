from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentBrief:
    intent: str
    instructions: str


class InterviewPlanner:
    def run(self, user_message: str) -> AgentBrief:
        message = user_message.lower()
        if any(word in message for word in ("báo cáo", "tong ket", "tổng kết", "report")):
            return AgentBrief("final_report", "Tổng hợp điểm mạnh, khoảng trống, mức sẵn sàng và 3 ưu tiên cải thiện.")
        if any(word in message for word in ("trả lời", "câu trả lời", "answer", "toi da", "tôi đã")):
            return AgentBrief("evaluate_answer", "Đánh giá theo STAR: cụ thể, liên quan CV, tác động, độ rõ ràng; đưa góp ý có thể hành động.")
        if any(word in message for word in ("câu hỏi", "phỏng vấn", "interview", "hỏi")):
            return AgentBrief("generate_questions", "Lập vòng phỏng vấn phù hợp vị trí và kinh nghiệm CV; ưu tiên câu hỏi có căn cứ từ CV.")
        return AgentBrief("review_cv", "Xác định nhu cầu người dùng, nhận xét CV dựa trên bằng chứng và hỏi một câu làm rõ nếu thiếu mục tiêu.")


class QuestionGenerator:
    def instruction(self, intent: str, user_message: str) -> str:
        if intent == "generate_questions":
            if "20" in user_message:
                return (
                    "Tạo đúng 20 câu hỏi phỏng vấn, nhóm theo chủ đề và bám sát kinh nghiệm trong CV. "
                    "Không hỏi thêm câu làm rõ."
                )
            return "Đặt đúng 1 câu hỏi phỏng vấn mở đầu, có thể kèm lý do ngắn. Chờ câu trả lời trước khi hỏi tiếp."
        return "Khi cần thông tin, chỉ hỏi 1 câu hỏi tiếp theo rõ ràng và có mục đích."


class AnswerEvaluator:
    def instruction(self, intent: str) -> str:
        if intent == "evaluate_answer":
            return "Nêu điểm tốt, điểm thiếu và một phiên bản trả lời tốt hơn ngắn gọn. Không bịa dữ kiện ngoài CV/lời người dùng."
        return "Không chấm điểm nếu người dùng chưa cung cấp câu trả lời phỏng vấn."


class NextActionDecider:
    def instruction(self, intent: str) -> str:
        if intent == "final_report":
            return "Kết thúc bằng các việc tiếp theo theo thứ tự ưu tiên, không đặt câu hỏi mới."
        return "Kết thúc bằng một next step rõ ràng: sửa CV, trả lời câu hỏi, hoặc làm rõ vị trí mục tiêu."


class FinalReportGenerator:
    def instruction(self, intent: str) -> str:
        if intent == "final_report":
            return "Dùng các mục: Tóm tắt, Điểm mạnh, Khoảng trống, Kế hoạch hành động. Giữ báo cáo ngắn gọn."
        return "Chỉ tạo báo cáo cuối khi người dùng yêu cầu rõ ràng."


class AgentOrchestrator:
    """A deterministic orchestration layer, ready to be replaced by a LangGraph flow."""

    def __init__(self) -> None:
        self.planner = InterviewPlanner()
        self.question_generator = QuestionGenerator()
        self.answer_evaluator = AnswerEvaluator()
        self.next_action_decider = NextActionDecider()
        self.final_report_generator = FinalReportGenerator()

    def build_brief(self, user_message: str) -> AgentBrief:
        plan = self.planner.run(user_message)
        parts = [
            f"Intent hiện tại: {plan.intent}.",
            f"1. Interview Planner: {plan.instructions}",
            f"2. Question Generator: {self.question_generator.instruction(plan.intent, user_message)}",
            f"3. Answer Evaluator: {self.answer_evaluator.instruction(plan.intent)}",
            f"4. Next-action Decider: {self.next_action_decider.instruction(plan.intent)}",
            f"5. Final Report Generator: {self.final_report_generator.instruction(plan.intent)}",
        ]
        return AgentBrief(intent=plan.intent, instructions="\n".join(parts))
