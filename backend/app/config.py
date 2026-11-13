from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PORT: int = 4000
    FRONTEND_URL: str = "https://studynotion-edtech-project.vercel.app"
    MONGODB_URL: str = "mongodb://localhost:27017/studynotion"
    JWT_SECRET: str = ""
    MAIL_HOST: str = ""
    MAIL_PORT: int = 587
    MAIL_USER: str = ""
    MAIL_PASS: str = ""
    CLOUD_NAME: str = ""
    API_KEY: str = ""
    API_SECRET: str = ""
    FOLDER_NAME: str = ""
    RAZORPAY_KEY: str = ""
    RAZORPAY_SECRET: str = ""


settings = Settings()
