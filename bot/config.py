from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BOT_TOKEN: str
    DATABASE_URL: str

    POSTGRES_USER: str = "kaztoys"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "kaztoys"

    REFERRAL_PARAM: str = "ref"
    SUPPORT_CONTACT: str = "@support"
    VIDEO_INSTRUCTION_PATH: str = "assets/video_instruction.mp4"
    INACTIVITY_MINUTES: int = 10

    def video_path_resolved(self) -> Path:
        return Path(self.VIDEO_INSTRUCTION_PATH)


def load_config() -> Settings:
    return Settings()
