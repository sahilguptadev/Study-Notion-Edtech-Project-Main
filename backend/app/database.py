from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.config import settings
from app.models import ALL_MODELS

_client: AsyncIOMotorClient | None = None


async def connect() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    # Use the "test" database when the connection URL has no database path.
    db = _client.get_default_database(default="test")
    await init_beanie(database=db, document_models=ALL_MODELS)


async def disconnect() -> None:
    if _client is not None:
        _client.close()
