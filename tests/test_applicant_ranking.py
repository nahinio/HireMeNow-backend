from decimal import Decimal

import pytest

from app.utils.applicant_ranking import compute_composite_score


def test_composite_score_with_reviews():
    score, no_review = compute_composite_score(
        quiz_score=Decimal("80"),
        avg_rating=Decimal("4"),
        review_count=3,
    )
    assert no_review is False
    assert score == Decimal("80.00")


def test_composite_score_without_reviews_uses_full_review_weight():
    score, no_review = compute_composite_score(
        quiz_score=Decimal("60"),
        avg_rating=Decimal("0"),
        review_count=0,
    )
    assert no_review is True
    assert score == Decimal("72.00")


def test_composite_score_perfect_quiz_and_reviews():
    score, no_review = compute_composite_score(
        quiz_score=Decimal("100"),
        avg_rating=Decimal("5"),
        review_count=10,
    )
    assert no_review is False
    assert score == Decimal("100.00")
