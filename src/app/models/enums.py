from enum import Enum


class UserRole(str, Enum):
    freelancer = "freelancer"
    client = "client"
    admin = "admin"


class JobStatus(str, Enum):
    open = "open"
    pending_confirmation = "pending_confirmation"
    completed = "completed"
    closed = "closed"
    disputed = "disputed"


class ConversationPhase(str, Enum):
    active = "active"
    is_locked = "is_locked"


class ApplicationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    canceled = "canceled"


class DisputeStatus(str, Enum):
    open = "open"
    under_review = "under_review"
    resolved = "resolved"
    closed = "closed"


class QuizResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
