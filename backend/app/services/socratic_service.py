"""Triển khai máy trạng thái dẫn dắt sư phạm Socratic 5 bước (BR-02).

Tuân thủ thiết kế kỹ thuật tại Mục 4.2.3 (Bảng 8) tài liệu SDD:
- Quản lý 5 nấc gợi mở sư phạm (MAX_HINTS = 5).
- Tự động phát hiện điều kiện kết thúc: sinh viên trả lời đúng hoặc chạm mốc 5 bước.
- Xử lý luồng ngoại lệ 4a (SRS): sai liên tiếp 2 lần (wrong_streak >= 2) thì tăng nấc gợi ý.
"""
from dataclasses import dataclass
from app.models.chat import ChatSession, ChatSessionStatus

SOCRATIC_MAX_STEPS = 5


@dataclass
class SocraticInstruction:
    hint_level: int
    is_concluded: bool
    action: str  # "CONCLUDE_AND_SUMMARIZE" | "PROMPT_NEXT_QUESTION" | "PROVIDE_INTENSIVE_HINT"
    wrong_streak: int = 0


class SocraticEngine:
    MAX_HINTS: int = SOCRATIC_MAX_STEPS

    @classmethod
    def evaluate_next_step(cls, session: ChatSession, ai_evaluation: str = "") -> SocraticInstruction:
        """
        Xác định bước gợi mở tiếp theo dựa trên phản hồi của sinh viên.
        Nếu sinh viên sai liên tiếp 2 lần, tăng nấc gợi ý (hint_level + 1).
        Khi chạm mốc 5 bước hoặc sinh viên giải đúng, kết thúc phiên Socratic (BR-02).
        """
        current_hint = session.hint_level or 0
        wrong_streak = session.wrong_streak or 0
        eval_upper = (ai_evaluation or "").strip().upper()

        # Điều kiện kết thúc: Sinh viên trả lời đúng hoặc đã hết 5 lượt gợi ý
        if eval_upper == "CORRECT" or current_hint >= cls.MAX_HINTS:
            session.status = ChatSessionStatus.COMPLETED.value
            return SocraticInstruction(
                hint_level=max(current_hint, cls.MAX_HINTS),
                is_concluded=True,
                action="CONCLUDE_AND_SUMMARIZE",
                wrong_streak=0,
            )

        # Điều kiện chuyển nấc gợi mở
        if eval_upper in ("WRONG", "DONT_KNOW"):
            wrong_streak += 1
            if wrong_streak >= 2:
                current_hint = min(cls.MAX_HINTS, max(current_hint + 1, 3))
                wrong_streak = 0  # Đặt lại bộ đếm sau khi đã tăng nấc trợ giúp
                action = "PROVIDE_INTENSIVE_HINT"
            else:
                current_hint = min(cls.MAX_HINTS, current_hint + 1)
                action = "PROMPT_NEXT_QUESTION"
        else:
            wrong_streak = 0  # Sinh viên trả lời đúng một phần hoặc tiếp tục
            current_hint = min(cls.MAX_HINTS, current_hint + 1)
            action = "PROMPT_NEXT_QUESTION"

        is_concluded = (current_hint >= cls.MAX_HINTS)
        if is_concluded:
            session.status = ChatSessionStatus.COMPLETED.value
            action = "CONCLUDE_AND_SUMMARIZE"

        session.hint_level = current_hint
        session.wrong_streak = wrong_streak

        return SocraticInstruction(
            hint_level=current_hint,
            is_concluded=is_concluded,
            action=action,
            wrong_streak=wrong_streak,
        )
