from decimal import Decimal
from uuid import UUID


def calculate_quiz_score(
    total_questions: int,
    correct_count: int,
) -> Decimal:
    if total_questions == 0:
        return Decimal("0")
    return Decimal(str((correct_count / total_questions) * 100)).quantize(
        Decimal("0.01")
    )


def grade_quiz_attempt(
    total_questions: int,
    correct_count: int,
    pass_threshold: int,
) -> tuple[Decimal, bool]:
    score = calculate_quiz_score(total_questions, correct_count)
    passed = score >= pass_threshold
    return score, passed


def count_correct_answers(
    answers: list[tuple[UUID, UUID]],
    correct_pairs: set[tuple[UUID, UUID]],
) -> int:
    return sum(1 for pair in answers if pair in correct_pairs)
