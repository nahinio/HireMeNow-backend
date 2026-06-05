AVAILABLE_FOR_WORK = "Available for Work"
NOT_AVAILABLE_FOR_WORK = "Not Available for work"


def serialize_availability(available_for_work: bool) -> str:
    return AVAILABLE_FOR_WORK if available_for_work else NOT_AVAILABLE_FOR_WORK
