"""Bộ kiểm thử cho SocraticEngine tại Backend Core (Bảng 8 SDD / BR-02)."""
import pytest
from app.models.chat import ChatSession, ChatSessionStatus
from app.services.socratic_service import SocraticEngine, SOCRATIC_MAX_STEPS


def test_socratic_engine_progression():
    session = ChatSession(hint_level=0, wrong_streak=0, status=ChatSessionStatus.ACTIVE.value)

    # Lượt 1: Bắt đầu từ 0 -> tăng lên 1
    i1 = SocraticEngine.evaluate_next_step(session)
    assert i1.hint_level == 1
    assert i1.is_concluded is False
    assert i1.action == "PROMPT_NEXT_QUESTION"
    assert session.status == ChatSessionStatus.ACTIVE.value

    # Lượt 2 -> tăng lên 2
    i2 = SocraticEngine.evaluate_next_step(session)
    assert i2.hint_level == 2
    assert i2.is_concluded is False

    # Lượt 3 -> tăng lên 3
    i3 = SocraticEngine.evaluate_next_step(session)
    assert i3.hint_level == 3

    # Lượt 4 -> tăng lên 4
    i4 = SocraticEngine.evaluate_next_step(session)
    assert i4.hint_level == 4

    # Lượt 5 -> chạm mốc MAX_HINTS (5) -> Hoàn thành phiên hội thoại (BR-02)
    i5 = SocraticEngine.evaluate_next_step(session)
    assert i5.hint_level == 5
    assert i5.is_concluded is True
    assert i5.action == "CONCLUDE_AND_SUMMARIZE"
    assert session.status == ChatSessionStatus.COMPLETED.value


def test_socratic_engine_early_conclusion_when_correct():
    session = ChatSession(hint_level=2, wrong_streak=0, status=ChatSessionStatus.ACTIVE.value)
    instruction = SocraticEngine.evaluate_next_step(session, ai_evaluation="CORRECT")
    assert instruction.is_concluded is True
    assert instruction.action == "CONCLUDE_AND_SUMMARIZE"
    assert session.status == ChatSessionStatus.COMPLETED.value


def test_socratic_engine_wrong_streak_escalation():
    """SRS Ngoại lệ 4a: Sai liên tiếp 2 lần -> tăng nấc gợi ý."""
    session = ChatSession(hint_level=1, wrong_streak=0, status=ChatSessionStatus.ACTIVE.value)

    # Lần 1: Sai
    i1 = SocraticEngine.evaluate_next_step(session, ai_evaluation="WRONG")
    assert i1.wrong_streak == 1
    assert i1.hint_level == 2

    # Lần 2: Tiếp tục sai -> wrong_streak >= 2 -> kích hoạt PROVIDE_INTENSIVE_HINT
    i2 = SocraticEngine.evaluate_next_step(session, ai_evaluation="WRONG")
    assert i2.action == "PROVIDE_INTENSIVE_HINT"
    assert i2.wrong_streak == 0  # Đã reset
    assert i2.hint_level >= 3
