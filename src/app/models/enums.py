from enum import Enum


class UserRole(str, Enum):
    freelancer = "freelancer"
    client = "client"
    admin = "admin"


class JobStatus(str, Enum):
    open = "open"
    filled = "filled"
    pending_confirmation = "pending_confirmation"
    completed = "completed"
    closed = "closed"


class ConversationPhase(str, Enum):
    active = "active"
    is_locked = "is_locked"


class ApplicationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    canceled = "canceled"


class QuizResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class ReportStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
