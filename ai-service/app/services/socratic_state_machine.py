"""Máy trạng thái Socratic 5 giai đoạn định hướng tư duy (TK-14 / Phân hệ 4).

Hiện thực hóa:
- Cỗ máy trạng thái (SocraticStateMachine) quản lý 5 bước:
  1. Khám phá (DISCOVER)
  2. Thử thách (CHALLENGE)
  3. Gợi ý (HINT)
  4. Củng cố suy luận / Đúc kết (SYNTHESIZE)
  5. Đánh giá / Tổng kết (EVALUATE)
- Tuân thủ quy tắc nghiệp vụ BR-02:
  * Không tiết lộ lời giải/đáp án ở các bước 1-4.
  * Tự động tổng kết ở bước 5 hoặc khi người học đã tự tìm ra đáp án đúng.
- Xử lý luồng ngoại lệ 4a (SRS):
  * Khi sinh viên sai hoặc trả lời không biết 2 lần liên tiếp (wrong_streak >= 2),
    hệ thống lập tức tăng cường gợi ý cụ thể kèm ví dụ trực quan.
- Bộ phân tích cú pháp trạng thái (JSON State Parser) trích xuất dữ liệu từ response của LLM.
"""
from dataclasses import dataclass
import json
import re
from typing import Any, Dict, Optional, Tuple

from app.schemas.socratic_schema import (
    STAGE_NAMES,
    STEP_TO_STAGE,
    SocraticFeedback,
    SocraticStage,
    StudentEvaluation,
)

# Giới hạn tối đa 5 bước sư phạm theo BR-02
MAX_SOCRATIC_STEPS = 5

# Biểu thức chính quy phát hiện nguy cơ lộ đáp án ở các bước 1-4 (BR-02 Guardian)
SPOILER_PATTERNS = [
    re.compile(r"(đáp án là|kết quả là|lời giải là|kết quả cuối cùng là)\s*[:：]?", re.IGNORECASE),
    re.compile(r"(chính xác đáp án là|đáp án chính xác là)\s*[:：]?", re.IGNORECASE),
]

# Các từ khóa nhận diện sinh viên lúng túng hoặc không biết câu trả lời
DONT_KNOW_PATTERNS = [
    re.compile(r"(không biết|em không biết|chưa biết|chịu|không rõ|bí rồi|không hiểu|chưa hiểu|ko biết|k biết|chua hieu|kho hieu|khó hiểu)", re.IGNORECASE),
    re.compile(r"(không biết làm sao|giải hộ|nói đáp án đi|cho đáp án đi|cho em lời giải)", re.IGNORECASE),
]


@dataclass
class StateTransitionResult:
    """Kết quả tính toán bước chuyển tiếp của máy trạng thái."""
    next_step: int
    stage: SocraticStage
    stage_name: str
    is_concluded: bool
    wrong_streak: int
    action: str  # "PROMPT_NEXT_QUESTION" | "CONCLUDE_AND_SUMMARIZE" | "PROVIDE_INTENSIVE_HINT"


class SocraticStateMachine:
    """Cỗ máy trạng thái hữu hạn (FSM) quản lý tiến trình dẫn dắt sư phạm 5 giai đoạn."""

    @classmethod
    def evaluate_student_input(cls, message: str) -> Optional[StudentEvaluation]:
        """Phân tích nhanh thông điệp của sinh viên để phát hiện trạng thái bối rối/không biết."""
        clean_msg = message.strip()
        for pattern in DONT_KNOW_PATTERNS:
            if pattern.search(clean_msg):
                return StudentEvaluation.DONT_KNOW
        return None

    @classmethod
    def compute_transition(
        cls,
        current_step: int,
        evaluation: Optional[StudentEvaluation],
        current_wrong_streak: int = 0,
    ) -> StateTransitionResult:
        """
        Tính toán bước chuyển tiếp tiếp theo dựa trên đánh giá câu trả lời của sinh viên.

        Quy tắc nghiệp vụ:
        1. Nếu sinh viên trả lời đúng hoàn toàn (CORRECT) -> Nhảy thẳng tới bước 5 (Tổng kết).
        2. Nếu sinh viên đã chạm bước 5 -> Kết thúc phiên Socratic (is_concluded = True).
        3. Ngoại lệ 4a (SRS): Nếu sai hoặc không biết 2 lần liên tiếp (wrong_streak >= 2) ->
           Cung cấp gợi ý cụ thể hơn (HINT), reset wrong_streak về 0.
        4. Bình thường: Tăng step lên 1 nấc (tối đa là 5).
        """
        eval_str = evaluation.value if isinstance(evaluation, StudentEvaluation) else (evaluation or "")
        eval_upper = str(eval_str).upper()

        wrong_streak = current_wrong_streak

        # 1. Trường hợp trả lời đúng hoàn toàn -> Kết thúc sớm thành công
        if eval_upper == StudentEvaluation.CORRECT.value:
            return StateTransitionResult(
                next_step=MAX_SOCRATIC_STEPS,
                stage=SocraticStage.EVALUATE,
                stage_name=STAGE_NAMES[SocraticStage.EVALUATE],
                is_concluded=True,
                wrong_streak=0,
                action="CONCLUDE_AND_SUMMARIZE",
            )

        # 2. Xử lý chuỗi trả lời sai / không biết (SRS Exception 4a)
        if eval_upper in (StudentEvaluation.WRONG.value, StudentEvaluation.DONT_KNOW.value):
            wrong_streak += 1
        else:
            # Sinh viên đúng một phần hoặc phản hồi tích cực
            wrong_streak = 0

        # Nếu đã đạt tới bước 5 hoặc vượt quá
        if current_step >= MAX_SOCRATIC_STEPS:
            return StateTransitionResult(
                next_step=MAX_SOCRATIC_STEPS,
                stage=SocraticStage.EVALUATE,
                stage_name=STAGE_NAMES[SocraticStage.EVALUATE],
                is_concluded=True,
                wrong_streak=wrong_streak,
                action="CONCLUDE_AND_SUMMARIZE",
            )

        # Ngoại lệ 4a: Bị kẹt 2 lần liên tiếp -> ưu tiên cung cấp gợi ý cụ thể (HINT)
        if wrong_streak >= 2:
            next_step = min(MAX_SOCRATIC_STEPS, max(current_step, 3))  # Nhảy đến ít nhất bước 3 (HINT)
            return StateTransitionResult(
                next_step=next_step,
                stage=STEP_TO_STAGE.get(next_step, SocraticStage.HINT),
                stage_name=STAGE_NAMES[STEP_TO_STAGE.get(next_step, SocraticStage.HINT)],
                is_concluded=(next_step >= MAX_SOCRATIC_STEPS),
                wrong_streak=0,  # Reset sau khi đã kích hoạt gợi ý tăng cường
                action="PROVIDE_INTENSIVE_HINT",
            )

        # Chuyển tiếp lũy tiến sang bước tiếp theo
        next_step = min(MAX_SOCRATIC_STEPS, current_step + 1)
        next_stage = STEP_TO_STAGE.get(next_step, SocraticStage.DISCOVER)
        is_concluded = (next_step >= MAX_SOCRATIC_STEPS)

        return StateTransitionResult(
            next_step=next_step,
            stage=next_stage,
            stage_name=STAGE_NAMES[next_stage],
            is_concluded=is_concluded,
            wrong_streak=wrong_streak,
            action="CONCLUDE_AND_SUMMARIZE" if is_concluded else "PROMPT_NEXT_QUESTION",
        )

    @classmethod
    def sanitize_spoilers(cls, text: str, step: int) -> str:
        """
        Bộ lọc bảo vệ BR-02 (Anti-Spoiler):
        Nếu ở các bước 1-4 mà văn bản chứa các cụm từ khẳng định đáp án trực tiếp,
        tự động điều chỉnh để không làm hỏng trải nghiệm tự tư duy của sinh viên.
        """
        if step >= MAX_SOCRATIC_STEPS:
            return text  # Bước 5 được phép đưa ra đáp án

        sanitized = text
        for pattern in SPOILER_PATTERNS:
            if pattern.search(sanitized):
                # Thay thế phát hiện lộ đáp án bằng chỉ dẫn gợi mở
                sanitized = pattern.sub("hãy cùng suy luận để tìm ra điều này: ", sanitized)
        return sanitized

    @classmethod
    def parse_socratic_response(
        cls,
        raw_text: str,
        current_step: int,
        current_wrong_streak: int = 0,
        detected_eval: Optional[StudentEvaluation] = None,
    ) -> SocraticFeedback:
        """
        Trích xuất và chuẩn hóa phản hồi từ mô hình AI sang đối tượng SocraticFeedback.

        Hỗ trợ 2 định dạng:
        1. JSON thuần túy hoặc khối ```json ... ``` do AI sinh ra.
        2. Văn bản Markdown theo cấu trúc chuẩn của socratic_system.md:
           **Bước X/5 – [Tên bước]**
           [Nhận xét/Gợi ý]
           **Câu hỏi:** [Câu hỏi]
        """
        clean_text = raw_text.strip()

        # 1. Thử bóc tách JSON nếu có
        parsed_json = cls._extract_json_payload(clean_text)
        if parsed_json:
            return cls._build_from_json(parsed_json, current_step, current_wrong_streak)

        # 2. Bóc tách từ định dạng Markdown có cấu trúc
        return cls._build_from_markdown(clean_text, current_step, current_wrong_streak, detected_eval)

    @classmethod
    def _extract_json_payload(cls, text: str) -> Optional[Dict[str, Any]]:
        """Tìm và trích xuất đối tượng JSON từ chuỗi văn bản."""
        # Trường hợp bọc trong ```json ... ```
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Trường hợp chuỗi thuần là JSON
        if text.startswith("{") and text.endswith("}"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        return None

    @classmethod
    def _build_from_json(
        cls, data: Dict[str, Any], current_step: int, current_wrong_streak: int
    ) -> SocraticFeedback:
        """Chuyển đổi từ dữ liệu JSON sang SocraticFeedback, đảm bảo an toàn quy tắc BR-02."""
        raw_step = data.get("step") or current_step
        step = max(1, min(MAX_SOCRATIC_STEPS, int(raw_step)))
        stage_val = str(data.get("stage") or STEP_TO_STAGE[step].value).upper()

        try:
            stage = SocraticStage(stage_val)
        except ValueError:
            stage = STEP_TO_STAGE[step]

        stage_name = STAGE_NAMES.get(stage, "Gợi mở")
        eval_raw = data.get("evaluation")
        evaluation = None
        if eval_raw:
            try:
                evaluation = StudentEvaluation(str(eval_raw).upper())
            except ValueError:
                evaluation = None

        feedback_text = str(data.get("feedback") or "Hãy tiếp tục suy nghĩ theo hướng này nhé.")
        guidance_q = data.get("guidance_question")
        explanation = data.get("explanation")
        is_concluded = bool(data.get("is_concluded")) or (step >= MAX_SOCRATIC_STEPS)

        # Ràng buộc BR-02: Bước 1-4 TUYỆT ĐỐI không có explanation và is_concluded=False
        if step < MAX_SOCRATIC_STEPS:
            explanation = None
            is_concluded = False
            feedback_text = cls.sanitize_spoilers(feedback_text, step)
            if guidance_q:
                guidance_q = cls.sanitize_spoilers(str(guidance_q), step)
            else:
                guidance_q = "Bạn nghĩ bước tiếp theo chúng ta cần chú ý điều gì?"
        else:
            is_concluded = True
            if not explanation:
                explanation = feedback_text

        wrong_streak = int(data.get("wrong_streak", current_wrong_streak))

        return SocraticFeedback(
            step=step,
            stage=stage,
            stage_name=stage_name,
            evaluation=evaluation,
            feedback=feedback_text,
            guidance_question=guidance_q,
            explanation=explanation,
            is_concluded=is_concluded,
            wrong_streak=wrong_streak,
        )

    @classmethod
    def _build_from_markdown(
        cls,
        text: str,
        current_step: int,
        current_wrong_streak: int,
        detected_eval: Optional[StudentEvaluation] = None,
    ) -> SocraticFeedback:
        """Phân tích cấu trúc Markdown từ socratic_system.md để lập mô hình trạng thái."""
        # Tìm tiêu đề bước: **Bước X/5 – [Tên bước]**
        step_match = re.search(r"\*\*Bước\s*(\d)/5\s*[–-—]\s*([^*]+)\*\*", text, re.IGNORECASE)
        if step_match:
            step = int(step_match.group(1))
            raw_stage_name = step_match.group(2).strip()
        else:
            step = current_step
            raw_stage_name = STAGE_NAMES.get(STEP_TO_STAGE[step], "Gợi mở")

        step = max(1, min(MAX_SOCRATIC_STEPS, step))
        stage = STEP_TO_STAGE[step]
        stage_name = STAGE_NAMES[stage]

        # Trích xuất phần câu hỏi nếu có: **Câu hỏi:** ...
        guidance_question = None
        question_match = re.search(r"\*\*Câu hỏi:\*\*\s*(.*)", text, re.IGNORECASE | re.DOTALL)
        if question_match:
            guidance_question = question_match.group(1).strip()

        # Phần nhận xét / phản hồi
        feedback_text = text
        if step_match:
            # Loại bỏ phần tiêu đề để lấy nội dung chính
            feedback_text = text[step_match.end():].strip()
        if question_match:
            # Tách phần trước câu hỏi làm feedback
            feedback_text = text[:question_match.start()].replace(step_match.group(0) if step_match else "", "").strip()

        if not feedback_text:
            feedback_text = text

        is_concluded = (step >= MAX_SOCRATIC_STEPS)
        explanation = None

        if step < MAX_SOCRATIC_STEPS:
            explanation = None
            is_concluded = False
            feedback_text = cls.sanitize_spoilers(feedback_text, step)
            if guidance_question:
                guidance_question = cls.sanitize_spoilers(guidance_question, step)
            else:
                # Nếu không bóc tách được dòng câu hỏi riêng, toàn bộ text là câu gợi mở
                guidance_question = feedback_text
        else:
            is_concluded = True
            explanation = text

        return SocraticFeedback(
            step=step,
            stage=stage,
            stage_name=stage_name,
            evaluation=detected_eval,
            feedback=feedback_text,
            guidance_question=guidance_question,
            explanation=explanation,
            is_concluded=is_concluded,
            wrong_streak=current_wrong_streak,
        )

    @classmethod
    def format_markdown_reply(cls, feedback: SocraticFeedback) -> str:
        """Định dạng phản hồi Markdown chuẩn xác theo đặc tả của socratic_system.md."""
        step = feedback.step
        stage_name = feedback.stage_name

        if step < MAX_SOCRATIC_STEPS:
            lines = [f"**Bước {step}/5 – {stage_name}**\n"]
            if feedback.feedback and feedback.feedback != feedback.guidance_question:
                lines.append(f"{feedback.feedback}\n")
            if feedback.guidance_question:
                lines.append(f"**Câu hỏi:** {feedback.guidance_question}")
            return "\n".join(lines).strip()

        # Bước 5: Đánh giá và tổng kết
        lines = [f"**Bước 5/5 – {stage_name}**\n"]
        if feedback.feedback:
            lines.append(f"{feedback.feedback}\n")
        if feedback.explanation and feedback.explanation != feedback.feedback:
            lines.append(f"{feedback.explanation}")
        return "\n".join(lines).strip()
