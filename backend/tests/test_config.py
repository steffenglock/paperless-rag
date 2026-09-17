import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import DEFAULT_RAG_CONTEXT_MAX_CHARS, Settings


class SettingsTests(unittest.TestCase):
    def test_rag_context_budget_uses_documented_default(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)

        self.assertEqual(
            settings.rag_context_max_chars,
            DEFAULT_RAG_CONTEXT_MAX_CHARS,
        )
        self.assertEqual(settings.rag_context_max_chars, 12000)

    def test_rag_context_budget_is_loaded_from_environment(self):
        with patch.dict(
            os.environ,
            {"RAG_CONTEXT_MAX_CHARS": "4321"},
            clear=True,
        ):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.rag_context_max_chars, 4321)

    def test_rag_context_budget_rejects_non_positive_values(self):
        with (
            patch.dict(
                os.environ,
                {"RAG_CONTEXT_MAX_CHARS": "0"},
                clear=True,
            ),
            self.assertRaises(ValueError),
        ):
            Settings(_env_file=None)


if __name__ == "__main__":
    unittest.main()
