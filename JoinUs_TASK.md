# JoinUs — Implementation Task List
**FastAPI + Neon Postgres (Async SQLModel / SQLAlchemy) — Backend Only**

> Execute sections in order. Dependencies flow top-to-bottom within each section.

---

## Section 1 — Project Scaffolding & Core Infrastructure

### 1.1 Python Environment & Dependencies
- [ ] Initialize project repository with a `src/` layout (`app/main.py` as entry point).
- [ ] Create `pyproject.toml` or `requirements.txt` declaring exact versions of: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `asyncpg`, `alembic`, `pydantic-settings`, `passlib[bcrypt]`, `pyjwt`.
- [ ] Confirm all imports resolve cleanly in a fresh virtual environment before writing any application code.

### 1.2 Configuration Layer
- [ ] Create `app/core/config.py` using Pydantic `BaseSettings`. Required fields: `DATABASE_URL` (Neon Postgres connection string), `SECRET_KEY`, `ALGORITHM` (JWT, e.g. `HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES`.
- [ ] Enforce `sslmode=require` in the `DATABASE_URL`. Document in `.env.example` that the Neon connection string must include `?sslmode=require`.
- [ ] Validate on startup that `DATABASE_URL` is present; raise a clear descriptive error if missing.

### 1.3 Async Database Engine & Session Dependency
- [ ] Create `app/db/engine.py`. Initialize an async SQLAlchemy engine via `create_async_engine` with `pool_pre_ping=True` and `connect_args={"ssl": "require"}`.
- [ ] Define an `async_session_maker` using `AsyncSession` and `expire_on_commit=False`.
- [ ] Implement `get_async_session` as an `async` generator FastAPI dependency that yields a session and commits or rolls back on exit.

### 1.4 Alembic Migration Configuration
- [ ] Run `alembic init migrations`. Configure `env.py` to use the async engine and import all SQLModel metadata.
- [ ] Write the initial migration creating all tables exactly as in `Schema.png`. Define all Postgres native enum types **before** the tables that reference them:
  - `user_role`: `freelancer`, `client`, `admin`
  - `job_status`: `open`, `pending_confirmation`, `completed`, `closed`, `disputed`
  - `conversation_phase`: `active`, `is_locked`
  - `application_status`: `pending`, `accepted`, `rejected`, `canceled`
  - `dispute_status`: `open`, `under_review`, `resolved`, `closed`
  - `quiz_result`: `pass`, `fail`
- [ ] Verify migration runs cleanly: `alembic upgrade head`.
- [ ] Verify `alembic downgrade -1` reverses the migration cleanly.

### 1.5 FastAPI App Bootstrap
- [ ] Create `app/main.py`. Initialize `FastAPI` instance with `title="JoinUs API"`, `version="1.0.0"`.
- [ ] Register all routers under the `/api/v1` prefix.
- [ ] Add startup/shutdown lifespan handlers for async engine disposal.
- [ ] Add RFC 7807-compliant exception handlers for `HTTPException` and `RequestValidationError`.

---

## Section 2 — User Profiles, Auth & Availability

### 2.1 SQLModel Table Definitions
- [ ] Define `User` in `app/models/user.py`. Fields: `id` (UUID pk, default `uuid4`), `email` (citext, unique, index), `password_hash` (str), `role` (`user_role` enum), `is_banned` (bool, default `False`), `ban_reason` (`Optional[str]`), `created_at` (timestamptz), `updated_at` (timestamptz).
- [ ] Define `FreelancerProfile`. Fields: `id`, `user_id` (FK → `users`, unique), `display_name`, `bio`, `available_for_work` (bool, default `True`), `avg_rating` (Numeric, default `0`), `review_count` (int, default `0`), `updated_at`.
- [ ] Define `ClientProfile`. Fields: `id`, `user_id` (FK → `users`, unique), `company_name`, `avg_rating` (Numeric), `review_count` (int), `updated_at`.
- [ ] Define `PortfolioLink`. Fields: `id`, `profile_id` (FK → `freelancer_profiles`), `label`, `url`, `position` (int).

### 2.2 Availability Serialization — CRITICAL
- [ ] Create `FreelancerProfileResponse` Pydantic schema in `app/schemas/freelancer.py`.
- [ ] Add a `@computed_field` or `@field_validator` named `availability_status`. Logic:
  - `available_for_work = True` → return the **exact** string `"Available for Work"`
  - `available_for_work = False` → return the **exact** string `"Not Available for work"`
  - The raw boolean must **not** appear in any outbound response payload.
- [ ] Write a unit test asserting both exact string outputs for both boolean states.

### 2.3 JWT & Auth Utilities
- [ ] Create `app/core/security.py`. Implement:
  - `hash_password(plain: str) → str` — `passlib` `CryptContext` with `bcrypt`.
  - `verify_password(plain: str, hashed: str) → bool`
  - `create_access_token(data: dict, expires_delta: timedelta) → str` — PyJWT, embed `sub` (user_id as str), `role`, `exp`.
  - `decode_access_token(token: str) → dict` — raise `HTTPException 401` on expired or invalid tokens.
- [ ] Implement `get_current_user` FastAPI dependency: extracts Bearer token from `Authorization` header, decodes it, fetches the `User` row, checks `is_banned` (raise `403` if `True`), returns the `User` object.
- [ ] Implement role guard dependencies: `require_freelancer`, `require_client`, `require_admin` — each calls `get_current_user` and checks `role`, raising `403` if mismatched.

### 2.4 Auth Routes
- [ ] `POST /api/v1/auth/register`: Accept `email`, `password`, `role`, and optional `display_name` or `company_name`. Hash password. Insert `User` row. Insert profile row based on `role`. Return `UserResponse` (no `password_hash` field). Return `409 Conflict` if email already exists.
- [ ] `POST /api/v1/auth/login`: Fetch user by email. Verify password. Return `{ access_token, token_type: "bearer" }`. Return `401` if credentials invalid.
- [ ] `GET /api/v1/auth/me`: Return current user's profile via `get_current_user` dependency.

### 2.5 Freelancer Profile Routes
- [ ] `PATCH /api/v1/freelancer/profile`: `require_freelancer`. Accept partial updates to `display_name`, `bio`, `available_for_work`. Return `FreelancerProfileResponse` with `availability_status` string — not the raw boolean.
- [ ] `POST /api/v1/freelancer/portfolio`: `require_freelancer`. Insert `portfolio_links` row. Return created record.

---

## Section 3 — Skill Repositories & Quiz Engine

### 3.1 SQLModel Table Definitions
- [ ] Define `Skill`: `id`, `name` (citext, unique), `is_active` (bool, default `True`), `created_at`, `created_by` (FK → `users`).
- [ ] Define `Quiz`: `id`, `skill_id` (FK → `skills`, unique), `pass_threshold` (int), `published` (bool, default `False`).
- [ ] Define `Question` (table name `quiz_questions`): `id`, `quiz_id` (FK → `quizzes`), `body`, `position` (int).
- [ ] Define `AnswerOption`: `id`, `question_id` (FK → `quiz_questions`), `body`, `is_correct` (bool).
- [ ] Define `QuizAttempt`: `id`, `quiz_id` (FK), `profile_id` (FK → `freelancer_profiles`), `score` (Numeric), `result` (`quiz_result` enum), `attempted_at`.
- [ ] Define `SkillBadge`: `id`, `profile_id` (FK → `freelancer_profiles`), `skill_id` (FK → `skills`), `score` (Numeric), `earned_at`. Add unique constraint on `(profile_id, skill_id)`.

### 3.2 Admin Skill & Quiz Routes
- [ ] `POST /api/v1/admin/skills`: `require_admin`. Validate `name` uniqueness. Insert `Skill` row with `created_by = current_user.id`.
- [ ] `POST /api/v1/admin/quizzes`: `require_admin`. Accept `skill_id`, `pass_threshold`, `published`. Insert `Quiz` row. Return with linked skill name.
- [ ] `POST /api/v1/admin/quizzes/{quiz_id}/questions`: `require_admin`. Insert `Question` row with `body`, `position`, `quiz_id`.
- [ ] `POST /api/v1/admin/questions/{question_id}/options`: `require_admin`. Insert `AnswerOption` rows. Enforce exactly one `is_correct = True` per question at both the route level and DB level (partial unique index or check constraint).

### 3.3 Quiz Attempt & Grading Engine
- [ ] `POST /api/v1/quizzes/{quiz_id}/attempt`: `require_freelancer`.
  - Validate quiz exists and `published = True`. Return `404` if not.
  - Accept payload: `List[{ question_id: UUID, selected_option_id: UUID }]`.
  - Fetch all `answer_options` for the quiz's questions in a **single query**.
  - Grade: count submissions where `selected_option_id` has `is_correct = True`. `score = (correct_count / total_questions) * 100`.
  - **PASS** (`score >= pass_threshold`): Insert `QuizAttempt(result="pass")`. Insert `SkillBadge`. Return `{ result: "pass", score }`.
  - **FAIL** (`score < pass_threshold`): Insert `QuizAttempt(result="fail")`. Return `{ result: "fail", score, resources: [...] }`.
  - Badge insertion is idempotent — if a `SkillBadge` already exists for `(profile_id, skill_id)`, skip insertion without error.

---

## Section 4 — Jobs, Multi-Skill Gate & Applicant Panel

### 4.1 SQLModel Table Definitions
- [ ] Define `Job`: `id`, `client_id` (FK → `users`), `title`, `description`, `deliverables`, `budget` (Numeric), `timeline`, `status` (`job_status` enum, default `open`), `posted_at`, `updated_at`.
- [ ] Define `JobRequiredSkill`: `skill_id` (FK → `skills`), `job_id` (FK → `jobs`). Composite PK `(skill_id, job_id)`.
- [ ] Define `Application`: `id`, `freelancer_id` (FK → `freelancer_profiles`), `job_id` (FK → `jobs`), `quiz_score_snapshot` (Numeric), `status` (`application_status` enum, default `pending`), `applied_at`. Unique constraint on `(freelancer_id, job_id)`.

### 4.2 Job Posting Route
- [ ] `POST /api/v1/jobs`: `require_client`.
  - Accept: `title`, `description`, `deliverables`, `budget`, `timeline`, `required_skill_ids` (`List[UUID]`, min length 1).
  - Validate all skill IDs exist in `skills` and `is_active = True`. Return `422` for any invalid skill ID.
  - In a **single transaction**: insert `Job` row; insert one `JobRequiredSkill` row per skill ID.
- [ ] `GET /api/v1/jobs`: Public. Paginated (`page`, `limit`). Filter to `status = open`. Include `required_skills` list in response.
- [ ] `GET /api/v1/jobs/{job_id}`: Public. Full detail including required skills.

### 4.3 Application Submission — Multi-Skill Gate
- [ ] `POST /api/v1/jobs/{job_id}/apply`: `require_freelancer`.
  - Verify job exists and `status = open`. Return `404` if not.
  - Fetch all `skill_id` values from `job_required_skills WHERE job_id = target`.
  - Fetch all `skill_id` values from `skill_badges WHERE profile_id = calling freelancer's profile_id`.
  - Compute set difference: `required_skills − badge_skills`. If non-empty → **return `403 Forbidden`**:
    ```json
    { "detail": "Missing required skill badges", "missing_skills": ["Skill Name A", "Skill Name B"] }
    ```
  - Check for duplicate application. Return `409 Conflict` if `(freelancer_id, job_id)` already exists.
  - Compute `quiz_score_snapshot`: max score across all `skill_badges` relevant to this job's required skills.
  - Insert `Application` row. Return `201`.

### 4.4 Applicant Panel — Sorting & Availability Flag
- [ ] `GET /api/v1/jobs/{job_id}/applicants`: `require_client`. Validate calling client owns the job (`client_id = current_user.id`). Return `403` if not.
  - Join: `applications → freelancer_profiles → users`.
  - Per-applicant response fields: `application_id`, `applied_at`, `quiz_score_snapshot`, `status`, `user.email`, `profile.display_name`, `profile.avg_rating`, `profile.review_count`, `availability_status`.
  - `availability_status` is re-evaluated at **query time** (not captured at application time):
    - `available_for_work = False` → `"Not Available for work"`
    - `available_for_work = True` → `"Available for Work"`
  - Accept query params: `sort_by` (`quiz_score_snapshot | avg_rating | applied_at`, default `applied_at`), `order` (`asc | desc`, default `desc`).
  - Implement dynamic `ORDER BY` using a whitelist map to SQLAlchemy column references. Return `422` for unknown `sort_by` values.

---

## Section 5 — Messaging Channel & Read-Only Lock

### 5.1 SQLModel Table Definitions
- [ ] Define `Conversation`: `id`, `client_id` (FK → `users`), `freelancer_id` (FK → `users`), `job_id` (FK → `jobs`), `phase` (`conversation_phase` enum, default `active`), `created_at`. Unique constraint on `(job_id, freelancer_id)`.
- [ ] Define `Message`: `id`, `conversation_id` (FK → `conversations`), `sender_id` (FK → `users`), `body` (text), `is_read` (bool, default `False`), `sent_at` (timestamptz, default `now()`).
- [ ] Define `CompletionSignal`: `id`, `job_id` (FK → `jobs`), `signalled_by` (FK → `users`), `signalled_at` (timestamptz, default `now()`). Unique constraint on `(job_id, signalled_by)`.

### 5.2 Conversation Initiation
- [ ] `POST /api/v1/conversations/initiate`: `require_client`.
  - Accept: `job_id`, `freelancer_id`.
  - Verify `job.client_id = current_user.id`. Return `403 Forbidden` if mismatch.
  - Verify the freelancer has an `applications` row for this `job_id` with `status` of `pending` or `accepted`. Return `422` if not.
  - Insert `Conversation` row. Return `409 Conflict` if `(job_id, freelancer_id)` pair already exists.

### 5.3 Message Insertion — Lock Check
- [ ] `POST /api/v1/conversations/{conversation_id}/messages`: Parties to the conversation.
  - Fetch conversation. Verify `current_user.id` is `client_id` or `freelancer_id` on the conversation. Return `403` if not.
  - **PRE-WRITE LOCK CHECK**:
    ```sql
    SELECT 1 FROM completion_signals WHERE job_id = conversation.job_id LIMIT 1
    ```
    If any row is returned → `403 Forbidden`: `{ "detail": "Conversation is locked." }`
  - Also check `conversation.phase = is_locked` → same `403` response.
  - Insert `Message` row. Return `201`.

### 5.4 Message Retrieval
- [ ] `GET /api/v1/conversations/{conversation_id}/messages`: Parties only. Return all messages ordered by `sent_at ASC`. Include `sender_id`, `body`, `is_read`, `sent_at`.
- [ ] On read by recipient: `UPDATE messages SET is_read = True WHERE conversation_id = target AND sender_id != current_user.id AND is_read = False`.

---

## Section 6 — Double-Blind Completion & Review Gate

### 6.1 Completion Signaling
- [ ] `POST /api/v1/jobs/{job_id}/complete`: Parties to the job (client or hired freelancer).
  - Verify job exists and `status` is `open` or `pending_confirmation`. Return `422` if `completed`, `closed`, or `disputed`.
  - Check for duplicate signal: `SELECT 1 FROM completion_signals WHERE job_id = target AND signalled_by = current_user.id`. Return `409` if exists.
  - Insert `CompletionSignal` row.
  - Count total `completion_signals` for this `job_id` after insertion:
    - **Count = 1** → `UPDATE jobs SET status = 'pending_confirmation' WHERE id = job_id`
    - **Count = 2** → `UPDATE conversations SET phase = 'is_locked' WHERE job_id = job_id`

### 6.2 Review Submission
- [ ] `POST /api/v1/jobs/{job_id}/review`: Parties to the job.
  - Validate `job.status = pending_confirmation`. Return `422` if not.
  - Validate payload:
    - `body.length >= 20` → return `422` with detail if not.
    - `rating` is `int` in `[1, 5]` → return `422` if not.
  - Determine `reviewee_id`: caller is client → reviewee is the freelancer; caller is freelancer → reviewee is the client.
  - Check for duplicate review: `SELECT 1 FROM reviews WHERE job_id = target AND reviewer_id = current_user.id`. Return `409` if exists.
  - Insert `Review` row with `is_published = False`.
  - After insert, check if **both** a client-authored and a freelancer-authored `reviews` row exist for this `job_id`. If both exist:
    - `UPDATE reviews SET is_published = True, published_at = NOW() WHERE job_id = target`
    - Recalculate `avg_rating` and `review_count` for freelancer profile:
      ```sql
      SELECT AVG(rating), COUNT(*) FROM reviews
      WHERE reviewee_id = freelancer_user_id AND is_published = True AND is_deleted = False
      ```
    - Apply same recalculation for client profile.
    - `UPDATE jobs SET status = 'completed' WHERE id = job_id`

### 6.3 Review Read Endpoint
- [ ] `GET /api/v1/users/{user_id}/reviews`: Public.
  ```sql
  SELECT * FROM reviews
  WHERE reviewee_id = user_id AND is_published = True AND is_deleted = False
  ORDER BY published_at DESC
  ```

### 6.4 Worker A — 48-Hour Reminder Cron
- [ ] Implement using `APScheduler` (`AsyncIOScheduler`) registered on app startup. Schedule: every 1 hour.
- [ ] Query: jobs where `status = pending_confirmation` and both `completion_signals` were written > 48 hours ago:
  ```sql
  SELECT job_id FROM completion_signals
  GROUP BY job_id HAVING COUNT(*) = 2
  AND MAX(signalled_at) <= NOW() - INTERVAL '48 hours'
  ```
  Join against `jobs WHERE status = 'pending_confirmation'`.
- [ ] For each qualifying job, identify which user has no `reviews` row for that `job_id`.
- [ ] Emit a notification for each missing reviewer (log entry at minimum; hook to notification service if configured).
- [ ] Track notified state (e.g., a `reminder_sent_at` column or a separate table) to avoid re-triggering on subsequent runs.

### 6.5 Worker B — 7-Day Force Closure Cron
- [ ] Schedule: every 1 hour. Same query as Worker A but threshold = `7 days`.
- [ ] For each qualifying job where `status` is still `pending_confirmation`:
  - [ ] Identify the absent reviewer (the party who has no `reviews` row for this `job_id`).
  - [ ] Insert a fallback `Review` row: `body = "No review given"`, `rating = 3`, `is_published = False`, `reviewer_id = absent_party_id`, `reviewee_id = other_party_id`.
  - [ ] `UPDATE reviews SET is_published = True, published_at = NOW() WHERE job_id = target` (both rows).
  - [ ] Recalculate `avg_rating` and `review_count` for both profile records.
  - [ ] `UPDATE jobs SET status = 'completed' WHERE id = job_id`

---

## Section 7 — Administrative Overrides & Moderation

### 7.1 Dispute Routes
- [ ] Define `Dispute` SQLModel: `id`, `job_id` (FK), `raised_by` (FK → `users`), `resolved_by` (FK → `users`, nullable), `description` (text), `status` (`dispute_status` enum, default `open`), `created_at`, `resolved_at` (nullable).
- [ ] `POST /api/v1/disputes`: Authenticated parties. Allow client or freelancer on a job to raise a dispute. Sets `job.status = disputed`. Return `409` if a dispute already exists for this `job_id`.
- [ ] `GET /api/v1/admin/disputes`: `require_admin`. Accept `status` filter query param. Paginated response.
- [ ] `PATCH /api/v1/admin/disputes/{dispute_id}`: `require_admin`. Accept: `resolution_notes`, `new_job_status` (any valid `job_status` value), dispute `status` transition. Update `disputes` and `jobs` rows in a **single transaction**. Set `resolved_by = admin_user.id`, `resolved_at = NOW()`.

### 7.2 Review Deletion
- [ ] `DELETE /api/v1/admin/reviews/{review_id}`: `require_admin`.
  - Soft delete: `UPDATE reviews SET is_deleted = True WHERE id = review_id`.
  - Recalculate reviewee's `avg_rating` and `review_count`:
    ```sql
    SELECT AVG(rating), COUNT(*) FROM reviews
    WHERE reviewee_id = target AND is_published = True AND is_deleted = False
    ```
  - Update `freelancer_profiles` or `client_profiles` accordingly.
  - Return `200` with updated profile stats summary.

### 7.3 Account Ban — Full Cascade
- [ ] `POST /api/v1/admin/users/{user_id}/ban`: `require_admin`. Payload: `{ ban_reason: str }` (required).
  - `UPDATE users SET is_banned = True, ban_reason = payload.ban_reason WHERE id = user_id`
  - Add `user_id` to a token blocklist (Redis or DB table). `get_current_user` dependency must check this list on every request.
  - **If role = `freelancer`**:
    - `DELETE FROM applications WHERE freelancer_id = profile.id AND status = 'pending'`
    - `UPDATE freelancer_profiles SET available_for_work = False WHERE user_id = target`
    - Excluded from all applicant panel responses via `WHERE users.is_banned = False` join filter.
  - **If role = `client`**:
    - `UPDATE jobs SET status = 'closed' WHERE client_id = target AND status = 'open'`
    - `UPDATE applications SET status = 'canceled' WHERE job_id IN (SELECT id FROM jobs WHERE client_id = target)`
  - Wrap **all** cascade operations in a single database transaction.
  - Return a summary of rows affected.

---

## Section 8 — Testing & Quality Gates

### 8.1 Unit Tests
- [ ] Availability serialization: assert both `"Available for Work"` and `"Not Available for work"` exact string outputs for both boolean inputs.
- [ ] Quiz grading math: test `0%`, `79%`, `80%`, `100%` score scenarios with correct `pass`/`fail` determination.
- [ ] JWT: creation, decoding, and expiry detection.
- [ ] bcrypt: hash and verify round-trip.

### 8.2 Integration Tests (`pytest` + `httpx.AsyncClient`)
- [ ] Full registration → login → profile update flow.
- [ ] Multi-skill gate: apply with all badges (→ `201`); apply with one missing badge (→ `403`); confirm `missing_skills` payload names the correct skill.
- [ ] Duplicate application (→ `409`).
- [ ] Freelancer attempting to initiate a conversation (→ `403`).
- [ ] Conversation lock: send message before any signal (→ `201`); send after first signal written (→ `403`).
- [ ] Double-blind review gate: both parties submit reviews → both `is_published = True` simultaneously; only one submits → neither visible in public read endpoint.
- [ ] Review validation: body < 20 chars (→ `422`); rating `0` or `6` (→ `422`).
- [ ] Ban cascade — freelancer: confirm pending applications deleted, profile `available_for_work = False`.
- [ ] Ban cascade — client: confirm open jobs set to `closed`, pending applications set to `canceled`.
- [ ] Applicant panel sort accuracy: verify ordering for all three `sort_by` axes.
- [ ] Admin soft-delete review: confirm `is_deleted = True`, confirm `avg_rating` recalculated on profile.

### 8.3 Cron Worker Tests
- [ ] Worker B force closure: seed a job with 2 signals older than 7 days and one missing review. Run worker. Assert:
  - Fallback review `body = "No review given"`.
  - Both review rows `is_published = True`.
  - `job.status = "completed"`.
  - `avg_rating` and `review_count` updated on both profiles.
