"""Kiem thu bo sung TK-18 cho JSON de thi AI.

Su dung truc tiep Pydantic schema QuizBundleOut co san trong LearnMate AI.
Khong sua file code goc.
Chay tai thu muc ai-service:
python -m pytest -q tests/test_tk18_quiz_json_validator.py
"""
import pytest
from pydantic import ValidationError

from app.schemas.quiz_schema import QuizBundleOut
import json


def make_valid_quiz():
    return {
        "title": "Kiem tra kien thuc Python",
        "difficulty": "MEDIUM",
        "total_questions": 1,
        "questions": [
            {
                "content": "Ham nao dung de in du lieu trong Python?",
                "options": [
                    {"opt_label": "A", "content": "print()", "is_correct": True},
                    {"opt_label": "B", "content": "input()", "is_correct": False},
                    {"opt_label": "C", "content": "len()", "is_correct": False},
                    {"opt_label": "D", "content": "type()", "is_correct": False},
                ],
                "explanation": "print() dung de hien thi du lieu ra man hinh.",
            }
        ],
    }


def test_valid_quiz_is_accepted_by_validator():
    result = QuizBundleOut.model_validate(make_valid_quiz())
    assert isinstance(result, QuizBundleOut)
    assert len(result.questions[0].options) == 4


def test_valid_json_string_is_accepted_directly():
    data = make_valid_quiz()
    raw_json = json.dumps(data, ensure_ascii=False)
    result = QuizBundleOut.model_validate_json(raw_json)
    assert result.title == data["title"]


def test_invalid_json_string_is_rejected():
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate_json("{ invalid json }")


def test_question_with_only_three_options_is_rejected():
    data = make_valid_quiz()
    data["questions"][0]["options"].pop()
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_blank_option_content_is_rejected(blank):
    data = make_valid_quiz()
    data["questions"][0]["options"][0]["content"] = blank
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


def test_question_with_no_correct_option_is_rejected():
    data = make_valid_quiz()
    for option in data["questions"][0]["options"]:
        option["is_correct"] = False
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


def test_question_with_two_correct_options_is_rejected():
    data = make_valid_quiz()
    data["questions"][0]["options"][1]["is_correct"] = True
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


def test_duplicate_option_labels_are_rejected():
    data = make_valid_quiz()
    data["questions"][0]["options"][3]["opt_label"] = "C"
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


def test_option_label_outside_a_to_d_is_rejected():
    data = make_valid_quiz()
    data["questions"][0]["options"][0]["opt_label"] = "E"
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


def test_invalid_difficulty_is_rejected():
    data = make_valid_quiz()
    data["difficulty"] = "EXTREME"
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


def test_question_content_is_required():
    data = make_valid_quiz()
    data["questions"][0]["content"] = "abc"
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


def test_explanation_is_required():
    data = make_valid_quiz()
    data["questions"][0]["explanation"] = "abc"
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


@pytest.mark.xfail(
    reason="Schema hien tai chua tu choi khi total_questions khong bang so phan tu questions."
)
def test_total_questions_must_match_actual_question_count():
    data = make_valid_quiz()
    data["total_questions"] = 2
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


@pytest.mark.xfail(
    reason="Schema hien tai chua kiem tra noi dung cac phuong an bi trung lap."
)
def test_option_contents_should_be_unique():
    data = make_valid_quiz()
    data["questions"][0]["options"][1]["content"] = "print()"
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


@pytest.mark.xfail(
    reason="Schema hien tai chi kiem tra min_length, chua strip noi dung cau hoi."
)
def test_question_whitespace_only_should_be_rejected():
    data = make_valid_quiz()
    data["questions"][0]["content"] = "     "
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)


@pytest.mark.xfail(
    reason="Schema hien tai chi kiem tra min_length, chua strip noi dung giai thich."
)
def test_explanation_whitespace_only_should_be_rejected():
    data = make_valid_quiz()
    data["questions"][0]["explanation"] = "     "
    with pytest.raises(ValidationError):
        QuizBundleOut.model_validate(data)
