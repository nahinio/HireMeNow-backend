from decimal import Decimal

from app.services.quiz_grading import calculate_quiz_score, grade_quiz_attempt


def test_quiz_score_zero_percent():
    score, passed = grade_quiz_attempt(total_questions=5, correct_count=0, pass_threshold=80)
    assert score == Decimal("0.00")
    assert passed is False


def test_quiz_score_seventy_nine_percent_fails():
    score, passed = grade_quiz_attempt(total_questions=100, correct_count=79, pass_threshold=80)
    assert score == Decimal("79.00")
    assert passed is False


def test_quiz_score_eighty_percent_passes():
    score, passed = grade_quiz_attempt(total_questions=5, correct_count=4, pass_threshold=80)
    assert score == Decimal("80.00")
    assert passed is True


def test_quiz_score_one_hundred_percent():
    score = calculate_quiz_score(total_questions=4, correct_count=4)
    assert score == Decimal("100.00")
    _, passed = grade_quiz_attempt(total_questions=4, correct_count=4, pass_threshold=80)
    assert passed is True
