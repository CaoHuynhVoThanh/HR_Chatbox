"""Start FastAPI using BACKEND_HOST and BACKEND_PORT from .env."""

from __future__ import annotations

import argparse

import uvicorn

from app.core.config import get_backend_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the HR CV Chatbot FastAPI backend")
    parser.add_argument("--reload", action="store_true", help="Restart server automatically when source files change")
    args = parser.parse_args()
    settings = get_backend_settings()
    print(f"Backend: {settings.backend_public_url}")
    uvicorn.run(
        "app.server:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
