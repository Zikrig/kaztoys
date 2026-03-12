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
    ADMIN_IDS: str = ""

    def video_path_resolved(self) -> Path:
        return Path(self.VIDEO_INSTRUCTION_PATH)

    def admin_ids_set(self) -> set[int]:
        result: set[int] = set()
        for chunk in (self.ADMIN_IDS or "").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                result.add(int(chunk))
            except ValueError:
                continue
        return result

    def is_admin(self, telegram_id: int | None) -> bool:
        if telegram_id is None:
            return False
        return telegram_id in self.admin_ids_set()


def load_config() -> Settings:
    return Settings()
