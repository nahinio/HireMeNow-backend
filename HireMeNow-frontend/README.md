# HireMeNow Frontend

Static HTML/CSS/JS frontend for the [HireMeNow API](https://hiremenow-backend-8la2.onrender.com).

This folder is self-contained — copy it to its own repo and deploy anywhere static files are hosted.

## Quick start

1. Serve the folder over HTTP (required for API calls and CORS):

```bash
cd HireMeNow-frontend
python -m http.server 8080
```

2. Open `http://localhost:8080`

3. **CORS:** Add your frontend origin to the backend `CORS_ORIGINS` env var on Render, e.g.:

```
http://localhost:8080,https://your-frontend.onrender.com
```

4. API URL is set in `js/config.js` (default: production Render backend).

**Password reset links:** Open this folder with Live Server (port 5500) from `index.html` here — not from the backend repo root. On Render, set backend `FRONTEND_RESET_URL` to your deployed frontend URL (e.g. `https://your-app.onrender.com/`).

## User flows

| Role | Features |
|------|----------|
| **Freelancer** | Register, profile, resume/picture upload, skill quizzes, apply to jobs, messaging, reviews, report clients |
| **Client** | Register, company profile, post jobs, view ranked applicants, select applicant, messaging, reviews, report freelancers |
| **Admin** | Login at `#/admin/login`, manage skills/quizzes, courses, reports, ban users, view all jobs |

Default admin (from backend bootstrap): `admin@hiremenow.com` / `password`

## Skill quizzes

Freelancers load published quizzes from the API:

- `GET /api/v1/skills` — lists skills with published quiz metadata
- `GET /api/v1/quizzes/{id}` — quiz questions (correct answers are not exposed)
- `POST /api/v1/quizzes/{id}/attempt` — submit answers

Admin must create a skill, add a course, then publish the quiz.

## Messaging

The API has no list-conversations endpoint. Conversations are saved in `localStorage` when:

- A client selects an applicant
- A user manually adds a conversation ID (freelancers receive the ID from the client after selection)

## Project structure

```
HireMeNow-frontend/
├── index.html
├── css/styles.css
├── js/
│   ├── config.js
│   ├── api.js
│   ├── auth.js
│   ├── router.js
│   └── pages/
└── README.md
```

## Deploy

Deploy as a static site (Netlify, Vercel, Render Static Site, GitHub Pages, etc.). Update `CORS_ORIGINS` on the backend to match your frontend URL.
