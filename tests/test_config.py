import os
import unittest
from unittest.mock import patch

from app.core.config import get_settings


class SettingsTests(unittest.TestCase):
    def test_requires_gemini_api_key(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                get_settings()

