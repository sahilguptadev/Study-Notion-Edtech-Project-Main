import asyncio
import os
import shutil
import tempfile

import cloudinary
import cloudinary.uploader
from starlette.datastructures import UploadFile

from app.config import settings


def cloudinary_connect() -> None:
    cloudinary.config(
        cloud_name=settings.CLOUD_NAME,
        api_key=settings.API_KEY,
        api_secret=settings.API_SECRET,
    )


async def upload_to_cloudinary(file: UploadFile, folder: str, height: int | None = None, quality: int | None = None) -> dict:
    options: dict = {"folder": folder, "resource_type": "auto"}
    if height:
        options["height"] = height
    if quality:
        options["quality"] = quality
    suffix = os.path.splitext(file.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        path = tmp.name
    try:
        return await asyncio.to_thread(cloudinary.uploader.upload, path, **options)
    finally:
        os.unlink(path)
