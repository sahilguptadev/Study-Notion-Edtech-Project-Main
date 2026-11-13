import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.routers import auth, contact, course, payments, profile
from app.utils.http import ApiError, send
from app.utils.uploader import cloudinary_connect

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.connect()
    cloudinary_connect()
    yield
    await database.disconnect()


app = FastAPI(title="StudyNotion API", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError):
    return send(exc.content, exc.status)


app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(profile.router, prefix="/api/v1/profile")
app.include_router(course.router, prefix="/api/v1/course")
app.include_router(payments.router, prefix="/api/v1/payment")
app.include_router(contact.router, prefix="/api/v1/reach")


@app.get("/")
async def root():
    return {"success": True, "message": "Your server is up and running ..."}
