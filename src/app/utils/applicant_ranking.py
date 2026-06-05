from decimal import Decimal

QUIZ_WEIGHT = Decimal("0.7")
REVIEW_WEIGHT = Decimal("0.3")
MAX_RATING = Decimal("5")


def normalize_rating_to_percent(avg_rating: Decimal) -> Decimal:
    if avg_rating <= 0:
        return Decimal("0")
    return (avg_rating / MAX_RATING) * Decimal("100")


def compute_composite_score(
    quiz_score: Decimal,
    avg_rating: Decimal,
    review_count: int,
) -> tuple[Decimal, bool]:
    no_review_experience = review_count == 0
    review_percent = (
        Decimal("100")
        if no_review_experience
        else normalize_rating_to_percent(avg_rating)
    )
    composite = (quiz_score * QUIZ_WEIGHT) + (review_percent * REVIEW_WEIGHT)
    return composite.quantize(Decimal("0.01")), no_review_experience
