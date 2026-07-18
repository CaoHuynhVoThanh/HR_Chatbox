import os
import unittest
from unittest.mock import patch

from app.core.config import get_backend_settings, get_settings


class SettingsTests(unittest.TestCase):
    def test_requires_gemini_api_key(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                get_settings()

    def test_reads_backend_address_from_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "BACKEND_HOST": "0.0.0.0",
                "BACKEND_PORT": "8080",
                "BACKEND_PUBLIC_URL": "https://api.example.com/",
            },
            clear=False,
        ):
            settings = get_backend_settings()
        self.assertEqual(settings.backend_host, "0.0.0.0")
        self.assertEqual(settings.backend_port, 8080)
        self.assertEqual(settings.backend_public_url, "https://api.example.com")
