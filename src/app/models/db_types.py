from sqlalchemy.dialects.postgresql import ENUM

user_role_enum = ENUM(
    "freelancer",
    "client",
    "admin",
    name="user_role",
    create_type=False,
)
job_status_enum = ENUM(
    "open",
    "pending_confirmation",
    "completed",
    "closed",
    "disputed",
    name="job_status",
    create_type=False,
)
conversation_phase_enum = ENUM(
    "active",
    "is_locked",
    name="conversation_phase",
    create_type=False,
)
application_status_enum = ENUM(
    "pending",
    "accepted",
    "rejected",
    "canceled",
    name="application_status",
    create_type=False,
)
dispute_status_enum = ENUM(
    "open",
    "under_review",
    "resolved",
    "closed",
    name="dispute_status",
    create_type=False,
)
quiz_result_enum = ENUM("pass", "fail", name="quiz_result", create_type=False)
