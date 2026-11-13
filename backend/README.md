# StudyNotion API

FastAPI + Beanie (MongoDB) backend for StudyNotion.

## Run
```bash
cd backend
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # then fill in the values
.venv/bin/uvicorn app.main:app --reload --port 4000
```
Interactive API docs: http://localhost:4000/docs

## Configuration (`backend/.env`)
| Variable | Purpose |
|---|---|
| `PORT`, `FRONTEND_URL` | server port; frontend origin used in password-reset links |
| `MONGODB_URL` | MongoDB connection string (the database name comes from the URL path) |
| `JWT_SECRET` | secret for signing login tokens |
| `MAIL_HOST`, `MAIL_PORT`, `MAIL_USER`, `MAIL_PASS` | SMTP server for OTP, reset and notification emails |
| `CLOUD_NAME`, `API_KEY`, `API_SECRET`, `FOLDER_NAME` | Cloudinary (thumbnails, lecture videos, avatars) |
| `RAZORPAY_KEY`, `RAZORPAY_SECRET` | Razorpay payments |

## Demo data
```bash
.venv/bin/python scripts/seed.py            # users for every role, courses, lectures, enrolments, reviews
.venv/bin/python scripts/seed.py --reset    # wipe ALL data first, then reseed
.venv/bin/python scripts/seed.py --enroll you@example.com   # also enrol an existing student
```
Every seeded account uses the password `Password@123`
(`admin@studynotion.local`, `instructor1..6@studynotion.local`, `student1..30@studynotion.local`).

## Layout
```
app/main.py            application, CORS, routers (/api/v1/{auth,profile,course,payment,reach})
app/config.py          settings
app/models/            Beanie documents (users, profiles, courses, sections, subsections, categories, ...)
app/routers/           auth, profile, course (courses, sections, categories, ratings, progress), payments, contact
app/core/              password hashing + JWT (security.py), auth and role dependencies (deps.py)
app/services/          helpers that resolve stored ids into full documents
app/utils/             request/response helpers, id casting, email, Cloudinary uploads
app/mail_templates/    HTML email templates
scripts/seed.py        demo data
```

## Roles
`Student` (buy courses, watch lectures, track progress, review), `Instructor` (create and publish courses,
view earnings), `Admin` (create categories). Protected routes expect `Authorization: Bearer <token>`.
