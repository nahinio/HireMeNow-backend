# JoinUs — Product Requirements Document
**Backend System · v1.0**
> FastAPI + Neon Postgres (Async SQLModel / SQLAlchemy) — Backend only. No frontend scope.

---

## 1. Executive Summary

JoinUs is a skill-verified freelance marketplace backend. It is engineered to eliminate hiring noise, block application spam, and deliver objective end-of-lifecycle ratings through a double-blind review system.

---

## 2. Core System Pillars

### 2.1 Multi-Skill Application Gating
Freelancers are blocked from submitting applications unless they hold a passing `skill_badge` for **every** skill listed in a job's `job_required_skills` junction table. A missing badge on any single required skill triggers an immediate `403 Forbidden` at the application endpoint — no partial applications are permitted.

### 2.2 Explicit Availability Engine
Each `freelancer_profile` stores a boolean `available_for_work` field. The serialization layer enforces **exact** string output:

| DB value | API output string |
|---|---|
| `true` | `Available for Work` |
| `false` | `Not Available for work` |

If a freelancer with an active application subsequently sets `available_for_work` to `false`, the client-side applicant panel response must expose `Not Available for work` directly on that application card so the client is warned without any manual lookup.

### 2.3 Asymmetric Messaging Channel
New conversation records can only be created by a **client** acting directly from an application card. Freelancers have zero ability to initiate a conversation thread. Any `POST` to the conversation-creation endpoint by a non-client token is rejected with `403 Forbidden`.

### 2.4 Read-Only Conversation Lock
Once any `completion_signal` row is written for a given `job_id`, the message insertion route performs a pre-write query against `completion_signals`. If any matching record exists, the write is rejected with `403 Forbidden`, permanently freezing the channel. This preserves the full conversation context for dispute auditing.

### 2.5 Double-Blind Feedback Pipeline
Reviews are written with `is_published = false`. Read endpoints omit all unpublished reviews entirely. Reviews become visible only after both parties have submitted a review row for the same `job_id`, or after the 7-day cron timeout forces publication. This blocks tactical and retaliatory review manipulation.

---

## 3. System Roles & Access Matrix

| Role | Permitted Operations |
|---|---|
| **Guest** | View open job listings and public platform pages only. No access to profiles, applications, messages, or test suites. |
| **Freelancer** | Complete identity setup; toggle `available_for_work`; attempt skill quizzes; track `skill_badges`; submit applications to unlocked jobs; respond to active conversations; submit completion signals; submit blind reviews. |
| **Client** | Post jobs with multi-skill requirements; view and sort applicant panels; initiate conversation threads; execute hiring status changes; submit completion signals; submit blind reviews. |
| **Admin** | Create and configure skills, quizzes, questions, and `answer_options`; force-close disputes; delete toxic reviews; execute global account bans with downstream cascade logic. |

---

## 4. Database Schema Reference

All tables are implemented exactly as defined in `Schema.png`.

### 4.1 Core Identity Tables

#### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | Primary key, default `uuid4` |
| `email` | `citext` | Case-insensitive, unique, indexed |
| `password_hash` | `text` | bcrypt hashed, never returned in responses |
| `role` | `user_role` enum | `freelancer \| client \| admin` |
| `is_banned` | `boolean` | Default `false`; triggers cascade on ban |
| `ban_reason` | `text` | Nullable; set when `is_banned = true` |
| `created_at` | `timestamptz` | Auto-managed |
| `updated_at` | `timestamptz` | Auto-managed |

#### `freelancer_profiles`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `user_id` | `uuid fk → users` | Unique |
| `display_name` | `text` | |
| `bio` | `text` | |
| `available_for_work` | `boolean` | Serialized as exact strings per §2.2 |
| `avg_rating` | `numeric` | Recalculated on review publish/delete |
| `review_count` | `integer` | Recalculated on review publish/delete |
| `updated_at` | `timestamptz` | |

#### `client_profiles`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `user_id` | `uuid fk → users` | Unique |
| `company_name` | `text` | |
| `avg_rating` | `numeric` | |
| `review_count` | `integer` | |
| `updated_at` | `timestamptz` | |

#### `portfolio_links`
| Column | Type |
|---|---|
| `id` | `uuid pk` |
| `profile_id` | `uuid fk → freelancer_profiles` |
| `label` | `text` |
| `url` | `text` |
| `position` | `integer` |

---

### 4.2 Skill & Assessment Tables

#### `skills`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `name` | `citext` | Unique |
| `is_active` | `boolean` | Default `true` |
| `created_at` | `timestamptz` | |
| `created_by` | `uuid fk → users` | |

#### `quizzes`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `skill_id` | `uuid fk → skills` | Unique (one quiz per skill) |
| `pass_threshold` | `integer` | Typically `80` |
| `published` | `boolean` | Default `false` |

#### `quiz_questions` (table alias: `questions`)
| Column | Type |
|---|---|
| `id` | `uuid pk` |
| `quiz_id` | `uuid fk → quizzes` |
| `body` | `text` |
| `position` | `integer` |

#### `answer_options`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `question_id` | `uuid fk → quiz_questions` | |
| `body` | `text` | |
| `is_correct` | `boolean` | Exactly one `true` per question |

#### `quiz_attempts`
| Column | Type |
|---|---|
| `id` | `uuid pk` |
| `quiz_id` | `uuid fk → quizzes` |
| `profile_id` | `uuid fk → freelancer_profiles` |
| `score` | `numeric` |
| `result` | `quiz_result` enum (`pass \| fail`) |
| `attempted_at` | `timestamptz` |

#### `skill_badges`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `profile_id` | `uuid fk → freelancer_profiles` | |
| `skill_id` | `uuid fk → skills` | |
| `score` | `numeric` | |
| `earned_at` | `timestamptz` | |

> Unique constraint on `(profile_id, skill_id)`.

---

### 4.3 Job & Application Tables

#### `jobs`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `client_id` | `uuid fk → users` | |
| `title` | `text` | |
| `description` | `text` | |
| `deliverables` | `text` | |
| `budget` | `numeric` | |
| `timeline` | `text` | |
| `status` | `job_status` enum | `open \| pending_confirmation \| completed \| closed \| disputed` |
| `posted_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

#### `job_required_skills`
| Column | Type | Notes |
|---|---|---|
| `skill_id` | `uuid fk → skills` | Composite PK |
| `job_id` | `uuid fk → jobs` | Composite PK |

#### `applications`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `freelancer_id` | `uuid fk → freelancer_profiles` | |
| `job_id` | `uuid fk → jobs` | |
| `quiz_score_snapshot` | `numeric` | Captured at application time |
| `status` | `application_status` enum | `pending \| accepted \| rejected \| canceled` |
| `applied_at` | `timestamptz` | |

> Unique constraint on `(freelancer_id, job_id)`.

---

### 4.4 Messaging Tables

#### `conversations`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `client_id` | `uuid fk → users` | |
| `freelancer_id` | `uuid fk → users` | |
| `job_id` | `uuid fk → jobs` | |
| `phase` | `conversation_phase` enum | `active \| is_locked` |
| `created_at` | `timestamptz` | |

> Unique constraint on `(job_id, freelancer_id)`.

#### `messages`
| Column | Type |
|---|---|
| `id` | `uuid pk` |
| `conversation_id` | `uuid fk → conversations` |
| `sender_id` | `uuid fk → users` |
| `body` | `text` |
| `is_read` | `boolean` |
| `sent_at` | `timestamptz` |

#### `completion_signals`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `job_id` | `uuid fk → jobs` | |
| `signalled_by` | `uuid fk → users` | |
| `signalled_at` | `timestamptz` | |

> Unique constraint on `(job_id, signalled_by)`. This table drives all lock and status-transition logic.

---

### 4.5 Review & Dispute Tables

#### `reviews`
| Column | Type | Notes |
|---|---|---|
| `id` | `uuid pk` | |
| `job_id` | `uuid fk → jobs` | |
| `reviewer_id` | `uuid fk → users` | |
| `reviewee_id` | `uuid fk → users` | |
| `rating` | `smallint` | Range `1–5` |
| `body` | `text` | Min 20 characters |
| `is_published` | `boolean` | Default `false` |
| `is_deleted` | `boolean` | Default `false` (soft delete) |
| `submitted_at` | `timestamptz` | |
| `published_at` | `timestamptz` | |

#### `disputes`
| Column | Type |
|---|---|
| `id` | `uuid pk` |
| `job_id` | `uuid fk → jobs` |
| `raised_by` | `uuid fk → users` |
| `resolved_by` | `uuid fk → users` (nullable) |
| `description` | `text` |
| `status` | `dispute_status` enum (`open \| under_review \| resolved \| closed`) |
| `created_at` | `timestamptz` |
| `resolved_at` | `timestamptz` (nullable) |

---

## 5. Feature Specifications

### 5.1 User Registration & Authentication

- `POST /api/v1/auth/register` — Creates a `users` row (bcrypt-hashed password), then creates the appropriate profile row (`freelancer_profiles` or `client_profiles`) based on `role`. Returns `UserResponse` (no `password_hash`). Returns `409` if email already exists.
- `POST /api/v1/auth/login` — Validates credentials, returns `{ access_token, token_type: "bearer" }`. JWT payload contains `user_id` and `role`. Expiry configurable via `pydantic-settings`.
- `GET /api/v1/auth/me` — Returns calling user's profile. Requires valid JWT via `get_current_user` dependency.
- All protected routes inject `get_current_user`. Banned users receive `403` on every protected route.

---

### 5.2 Freelancer Profile & Availability

- `PATCH /api/v1/freelancer/profile` — Updates `display_name`, `bio`, `available_for_work`. Response schema serializes `available_for_work` as the exact strings defined in §2.2 — the raw boolean must **never** appear in any outbound response.
- `POST /api/v1/freelancer/portfolio` — Inserts a `portfolio_links` row (label, url, position) linked to the calling freelancer's `profile_id`.

---

### 5.3 Skill Administration (Admin only)

- `POST /api/v1/admin/skills` — Creates a `skills` record with `name`, `is_active`, `created_by`.
- `POST /api/v1/admin/quizzes` — Creates a `quizzes` record: `skill_id`, `pass_threshold` (integer), `published`.
- `POST /api/v1/admin/quizzes/{quiz_id}/questions` — Inserts a `quiz_questions` row: `body`, `position`, `quiz_id`.
- `POST /api/v1/admin/questions/{question_id}/options` — Inserts `answer_options` rows. Enforces exactly one `is_correct = true` per question at both the route and DB level.

---

### 5.4 Quiz Attempt & Badge Issuance

`POST /api/v1/quizzes/{quiz_id}/attempt` — Freelancer only.

- Accepts: `List[{ question_id, selected_option_id }]`
- Validates quiz exists and `published = true`. Returns `404` if not.
- Grades by fetching all `answer_options` for the quiz in one query. `score = (correct_count / total_questions) * 100`
- **PASS** (`score >= pass_threshold`): writes passing `quiz_attempts` row; inserts `skill_badges` row (`profile_id`, `skill_id`, `score`, `earned_at`). Returns `{ result: "pass", score }`.
- **FAIL** (`score < pass_threshold`): writes failing `quiz_attempts` row. Returns `{ result: "fail", score, resources: [...] }`.
- Badge insertion is idempotent — re-passing does not create a duplicate badge.

---

### 5.5 Job Posting

- `POST /api/v1/jobs` — Client only. Payload: `title`, `description`, `deliverables`, `budget`, `timeline`, `required_skill_ids` (array of UUIDs, min length 1). Validates all skill IDs exist and `is_active = true`. In a single atomic transaction: inserts one `jobs` row and one `job_required_skills` row per skill ID.
- `GET /api/v1/jobs` — Public. Paginated. Filters to `status = open`. Includes `required_skills` list.
- `GET /api/v1/jobs/{job_id}` — Public. Full job detail including required skills.

---

### 5.6 Application Submission — Multi-Skill Gate

`POST /api/v1/jobs/{job_id}/apply` — Freelancer only.

1. Verify job exists and `status = open`. Return `404` if not.
2. Fetch all `skill_id` values from `job_required_skills` for the job.
3. Fetch all `skill_id` values from `skill_badges` for the calling freelancer's `profile_id`.
4. Compute set difference: `required_skills − badge_skills`. If non-empty → return `403 Forbidden`:
   ```json
   { "detail": "Missing required skill badges", "missing_skills": ["Skill Name A", ...] }
   ```
5. Check for duplicate application via `(freelancer_id, job_id)` unique constraint. Return `409` if already applied.
6. Compute `quiz_score_snapshot`: max score across all `skill_badges` relevant to this job's required skills.
7. Insert `applications` row. Return `201`.

---

### 5.7 Applicant Panel & Sorting

`GET /api/v1/jobs/{job_id}/applicants` — Client only. Caller must own the job.

- Joins: `applications → freelancer_profiles → users`
- Per-applicant response fields: `application_id`, `applied_at`, `quiz_score_snapshot`, `status`, `user.email`, `profile.display_name`, `profile.avg_rating`, `profile.review_count`, `availability_status`
- `availability_status` is re-evaluated at query time (not at application time):
  - `available_for_work = false` → `"Not Available for work"`
  - `available_for_work = true` → `"Available for Work"`
- Query params:
  - `sort_by`: `quiz_score_snapshot | avg_rating | applied_at` (default: `applied_at`)
  - `order`: `asc | desc` (default: `desc`)
- Use a whitelist map of allowed sort columns to SQLAlchemy column references. Return `422` for unknown `sort_by` values.

---

### 5.8 Conversation Initiation & Messaging

- `POST /api/v1/conversations/initiate` — Client only. Caller's `id` must match `job.client_id`. Any other token → `403 Forbidden`. Payload: `job_id`, `freelancer_id` (must have an active application on that job). Returns `409` if a conversation for the same `(job_id, freelancer_id)` pair already exists.

- `POST /api/v1/conversations/{conversation_id}/messages` — Parties to the conversation.
  - Verify caller is `client_id` or `freelancer_id` on the conversation. Return `403` if not.
  - **PRE-WRITE LOCK CHECK**: `SELECT 1 FROM completion_signals WHERE job_id = conversation.job_id LIMIT 1`. If any row exists → `403 Forbidden`: `{ "detail": "Conversation is locked." }`
  - Also check `conversation.phase = is_locked` → same `403` response.
  - Insert `messages` row. Return `201`.

- `GET /api/v1/conversations/{conversation_id}/messages` — Parties only. Returns messages ordered by `sent_at ASC`. On read by recipient: mark unread messages `is_read = true`.

---

### 5.9 Job Completion Signaling

`POST /api/v1/jobs/{job_id}/complete` — Client or freelancer who are parties to the job.

1. Verify job `status` is `open` or `pending_confirmation`. Return `422` if already `completed` or `closed`.
2. Check for duplicate signal from this user. Return `409` if already signalled.
3. Insert `completion_signals` row.
4. Count total `completion_signals` for this `job_id` after insertion:
   - **Count = 1** → `UPDATE jobs SET status = 'pending_confirmation'`
   - **Count = 2** → `UPDATE conversations SET phase = 'is_locked' WHERE job_id = target`

---

### 5.10 Blind Review Submission

`POST /api/v1/jobs/{job_id}/review` — Parties to the job.

1. Validate `job.status = pending_confirmation`. Return `422` if not.
2. Validate payload: `body.length >= 20` (422 if not); `rating` in `[1, 5]` (422 if not).
3. Determine `reviewee_id`: caller is client → reviewee is the freelancer; caller is freelancer → reviewee is the client.
4. Check for duplicate review from this user on this job. Return `409` if exists.
5. Insert `reviews` row with `is_published = false`.
6. After insert, check if both a client-authored and a freelancer-authored review row exist for this `job_id`. If both exist:
   - `UPDATE reviews SET is_published = true WHERE job_id = target`
   - Set `published_at = NOW()` on both rows.
   - Recalculate `avg_rating` and `review_count` on both `freelancer_profiles` and `client_profiles`.
   - `UPDATE jobs SET status = 'completed'`

`GET /api/v1/users/{user_id}/reviews` — Public. Returns only rows where `is_published = true` and `is_deleted = false`, ordered by `published_at DESC`.

---

### 5.11 Background Workers (Cron)

#### Worker A — 48-Hour Reminder
- Runs every hour.
- Finds jobs where `status = pending_confirmation` and both `completion_signals` were written more than 48 hours ago.
- For each qualifying job, identifies which party has not yet submitted a `reviews` row.
- Emits a notification for each missing reviewer (log entry or notification hook).
- Tracks notified state to avoid re-triggering on subsequent hourly runs.

#### Worker B — 7-Day Force Closure
- Runs every hour.
- Same query as Worker A but threshold = 7 days.
- For each qualifying job where `status` is still `pending_confirmation`:
  1. Identify the absent reviewer.
  2. Insert a fallback `reviews` row: `body = "No review given"`, `rating = 3`, `is_published = false`.
  3. `UPDATE reviews SET is_published = true WHERE job_id = target` (both rows).
  4. Set `published_at = NOW()` on both rows.
  5. Recalculate `avg_rating` and `review_count` for both profile records.
  6. `UPDATE jobs SET status = 'completed'`

---

### 5.12 Administrative Override Routes

#### Dispute Resolution
- `GET /api/v1/admin/disputes` — Admin only. List all disputes with `status` filter support. Paginated.
- `POST /api/v1/disputes` — Authenticated parties. Client or freelancer on a job may raise a dispute. Sets `job.status = disputed`.
- `PATCH /api/v1/admin/disputes/{dispute_id}` — Admin only. Accept: `resolution_notes`, `new_job_status`, dispute `status` transition. Update dispute and job in a single transaction. Set `resolved_by = admin_user_id`, `resolved_at = now()`.

#### Review Deletion
- `DELETE /api/v1/admin/reviews/{review_id}` — Admin only. Soft delete: `UPDATE reviews SET is_deleted = true`. Recalculates `avg_rating` and `review_count` on the affected reviewee's profile. Returns `200` with updated profile stats summary.

#### Account Ban
- `POST /api/v1/admin/users/{user_id}/ban` — Admin only. Payload: `{ ban_reason: string (required) }`.
  - `UPDATE users SET is_banned = true, ban_reason = payload.ban_reason`
  - Add `user_id` to a token blocklist. `get_current_user` dependency checks this list on every request.
  - **If role = `freelancer`**:
    - Delete all pending `applications` rows for this freelancer.
    - `UPDATE freelancer_profiles SET available_for_work = false`
    - Exclude from all applicant panel queries via `WHERE users.is_banned = false` join filter.
  - **If role = `client`**:
    - `UPDATE jobs SET status = 'closed' WHERE client_id = target AND status = 'open'`
    - `UPDATE applications SET status = 'canceled' WHERE job_id IN (SELECT id FROM jobs WHERE client_id = target)`
  - All cascade operations run in a single database transaction. Return a summary of rows affected.

---

## 6. Non-Functional Requirements

- **Database**: Neon Postgres (serverless). All connections via `asyncpg` with `sslmode=require`. Connection strings loaded from environment via `pydantic-settings`.
- **ORM**: SQLModel (SQLAlchemy async). All DB operations are async. Session lifecycle managed via `get_async_session` FastAPI dependency.
- **Migrations**: Alembic. All enums (`user_role`, `job_status`, `conversation_phase`, `application_status`, `dispute_status`, `quiz_result`) defined as **native Postgres enum types** in migration scripts.
- **Auth**: PyJWT with HS256. Token expiry configurable. Banned user check injected into `get_current_user`.
- **Passwords**: `passlib` with `bcrypt` context. `password_hash` never returned in any response schema.
- **Numeric precision**: All financial/score fields use Postgres `NUMERIC` type, not `FLOAT`.
- **Timestamps**: All timestamps are `timestamptz` (UTC). No naive `datetime` fields.
- **Error format**: All `4xx` and `5xx` responses follow RFC 7807 Problem Details format.

---

## 7. Complete API Route Reference

| Method | Route | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Public | Register user |
| `POST` | `/api/v1/auth/login` | Public | Login, receive JWT |
| `GET` | `/api/v1/auth/me` | JWT | Own profile |
| `PATCH` | `/api/v1/freelancer/profile` | Freelancer | Update profile / availability |
| `POST` | `/api/v1/freelancer/portfolio` | Freelancer | Add portfolio link |
| `POST` | `/api/v1/admin/skills` | Admin | Create skill |
| `POST` | `/api/v1/admin/quizzes` | Admin | Create quiz |
| `POST` | `/api/v1/admin/quizzes/{id}/questions` | Admin | Add question to quiz |
| `POST` | `/api/v1/admin/questions/{id}/options` | Admin | Add answer options |
| `POST` | `/api/v1/quizzes/{id}/attempt` | Freelancer | Submit quiz attempt |
| `POST` | `/api/v1/jobs` | Client | Post a job |
| `GET` | `/api/v1/jobs` | Public | List open jobs (paginated) |
| `GET` | `/api/v1/jobs/{id}` | Public | Job detail |
| `POST` | `/api/v1/jobs/{id}/apply` | Freelancer | Apply (multi-skill gate) |
| `GET` | `/api/v1/jobs/{id}/applicants` | Client (owner) | Applicant panel with sorting |
| `POST` | `/api/v1/conversations/initiate` | Client (owner) | Start conversation |
| `POST` | `/api/v1/conversations/{id}/messages` | Party to job | Send message (lock check) |
| `GET` | `/api/v1/conversations/{id}/messages` | Party to job | Message history |
| `POST` | `/api/v1/jobs/{id}/complete` | Party to job | Completion signal |
| `POST` | `/api/v1/jobs/{id}/review` | Party to job | Submit blind review |
| `GET` | `/api/v1/users/{id}/reviews` | Public | Published reviews only |
| `POST` | `/api/v1/disputes` | Authenticated party | Raise a dispute |
| `GET` | `/api/v1/admin/disputes` | Admin | List disputes |
| `PATCH` | `/api/v1/admin/disputes/{id}` | Admin | Resolve dispute |
| `DELETE` | `/api/v1/admin/reviews/{id}` | Admin | Soft-delete review |
| `POST` | `/api/v1/admin/users/{id}/ban` | Admin | Ban user (cascade) |
