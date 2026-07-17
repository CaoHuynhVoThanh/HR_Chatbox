from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str


def get_settings() -> Settings:
    """Load runtime configuration without ever printing the API key."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "replace_me":
        raise RuntimeError(
            "Chưa cấu hình GEMINI_API_KEY. Hãy copy .env.example thành .env và điền API key."
        )
    return Settings(
        gemini_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
    )

