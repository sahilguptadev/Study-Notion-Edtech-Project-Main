# StudyNotion

An ed-tech platform: instructors build and publish courses, students buy them with Razorpay and learn through video lectures with progress tracking, and admins manage categories.

- **Frontend:** React 18, Redux Toolkit, Tailwind CSS (this folder)
- **Backend:** FastAPI + MongoDB, see [backend/README.md](backend/README.md)

## Quick start
1. Start MongoDB on `localhost:27017`.
2. Backend: follow [backend/README.md](backend/README.md) (`cp .env.example .env`, fill it in, run uvicorn on port 4000).
3. Frontend: `cp .env.example .env && npm install && npm start`.
4. Optional demo data: `cd backend && .venv/bin/python scripts/seed.py`.

More detail for contributors is in [CLAUDE.md](CLAUDE.md).
