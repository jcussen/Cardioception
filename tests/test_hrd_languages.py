import importlib.util
from pathlib import Path
from unittest import TestCase


def load_languages_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "cardioception" / "HRD" / "languages.py"
    spec = importlib.util.spec_from_file_location("hrd_languages", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestHrdLanguages(TestCase):
    def setUp(self):
        self.languages = load_languages_module()

    def test_english_mouse_text_matches_default_buttons(self):
        texts = self.languages.english(
            device="mouse", setup="behavioral", exteroception=True
        )

        self.assertIn("LEFT mouse button for slower", texts["responseText"])
        self.assertIn("RIGHT mouse button for faster", texts["responseText"])
        self.assertIn("faster (RIGHT mouse button)", texts["Tutorial3_responses"])
        self.assertIn("slower (LEFT mouse button)", texts["Tutorial3_responses"])

    def test_english_mouse_text_matches_swapped_buttons(self):
        texts = self.languages.english(
            device="mouse",
            setup="behavioral",
            exteroception=True,
            mouse_response_buttons={"Less": "right", "More": "left"},
        )

        self.assertIn("RIGHT mouse button for slower", texts["responseText"])
        self.assertIn("LEFT mouse button for faster", texts["responseText"])
        self.assertIn("faster (LEFT mouse button)", texts["Tutorial3_responses"])
        self.assertIn("slower (RIGHT mouse button)", texts["Tutorial3_responses"])

    def test_keyboard_text_is_unchanged_by_mouse_mapping(self):
        texts = self.languages.french(
            device="keyboard",
            setup="behavioral",
            exteroception=True,
            mouse_response_buttons={"Less": "right", "More": "left"},
        )

        self.assertIn("flèche vers le BAS", texts["responseText"])
        self.assertIn("vers le HAUT", texts["responseText"])
