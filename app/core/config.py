from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class BackendSettings:
    allowed_origins: tuple[str, ...]
    backend_host: str
    backend_port: int
    backend_public_url: str


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    enable_web_search: bool = False


def get_backend_settings() -> BackendSettings:
    """Load FastAPI storage, browser-origin and network settings from .env."""
    load_dotenv()
    # Platforms such as Render inject PORT at runtime. Prefer it over the
    # local BACKEND_PORT while keeping the latter for development.
    raw_port = os.getenv("PORT", os.getenv("BACKEND_PORT", "8000"))
    try:
        backend_port = int(raw_port)
    except ValueError as exc:
        raise RuntimeError("BACKEND_PORT phải là một số nguyên.") from exc
    if not 1 <= backend_port <= 65_535:
        raise RuntimeError("BACKEND_PORT phải nằm trong khoảng 1 đến 65535.")

    backend_host = os.getenv("BACKEND_HOST", "127.0.0.1").strip()
    if not backend_host:
        raise RuntimeError("BACKEND_HOST không được để trống.")
    return BackendSettings(
        allowed_origins=tuple(
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ),
        backend_host=backend_host,
        backend_port=backend_port,
        backend_public_url=os.getenv(
            "BACKEND_PUBLIC_URL", f"http://{backend_host}:{backend_port}"
        ).rstrip("/"),
    )


def get_settings() -> Settings:
    """Load runtime configuration without ever printing the API key."""
    backend = get_backend_settings()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "replace_me":
        raise RuntimeError(
            "Chưa cấu hình GEMINI_API_KEY. Hãy copy .env.example thành .env và điền API key."
        )
    return Settings(
        gemini_api_key=api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        enable_web_search=os.getenv("GEMINI_ENABLE_WEB_SEARCH", "true").strip().lower() in {"1", "true", "yes", "on"},
    )
