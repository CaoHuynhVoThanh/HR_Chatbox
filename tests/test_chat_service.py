import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core.chat_service import CVChatService
from app.core.config import Settings


class MergeCVTests(unittest.TestCase):
    @patch("app.core.chat_service.ChatGoogleGenerativeAI")
    def test_merge_returns_harvard_json_without_attaching_source_pdf(self, model_class) -> None:
        model_class.return_value.invoke.return_value = SimpleNamespace(
            content=json.dumps(
                {
                    "full_name": "Nguyen Van A",
                    "headline": "Backend Developer",
                    "contact": {},
                    "summary": "Python developer",
                    "experience": [],
                    "education": [],
                    "projects": [],
                    "skills": ["Python"],
                    "certifications": [],
                    "additional": [],
                }
            )
        )
        service = object.__new__(CVChatService)
        service.settings = Settings("test-key", "gemini-2.5-flash")

        result = service.merge_cvs_harvard(
            "Primary CV",
            "Secondary CV",
            "primary.pdf",
            "secondary.docx",
            "Backend Developer",
        )

        self.assertEqual(result["full_name"], "Nguyen Van A")
        self.assertEqual(result["contact"]["email"], "")
        messages = model_class.return_value.invoke.call_args.args[0]
        self.assertEqual(messages[0].type, "system")
        self.assertEqual(messages[1].type, "human")
        self.assertIn("primary.pdf", messages[1].content)
        self.assertIn("secondary.docx", messages[1].content)
        self.assertNotIsInstance(messages[1].content, list)
