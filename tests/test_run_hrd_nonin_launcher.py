import importlib.util
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


def load_launcher_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "run_hrd_nonin.py"
    spec = importlib.util.spec_from_file_location("run_hrd_nonin", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestRunHrdNoninLauncher(TestCase):
    def setUp(self):
        self.launcher = load_launcher_module()

    def test_resolve_run_details_with_cli_args_does_not_open_dialog(self):
        args = SimpleNamespace(
            subject_num="P001",
            breathwork_phase="post",
            session="HRD",
        )

        with patch.object(
            self.launcher,
            "prompt_run_details",
            side_effect=AssertionError("dialog should not be opened"),
        ):
            self.assertEqual(
                self.launcher.resolve_run_details(args),
                ("P001", "2", "after", "HRD2"),
            )

    def test_prompt_run_details_falls_back_to_console(self):
        with (
            patch.object(
                self.launcher,
                "prompt_run_details_dialog",
                side_effect=RuntimeError("no GUI available"),
            ),
            patch.object(
                self.launcher,
                "prompt_run_details_console",
                return_value=("P002", "1"),
            ),
            patch("sys.stderr", new_callable=StringIO),
        ):
            self.assertEqual(
                self.launcher.prompt_run_details(None, None),
                ("P002", "1"),
            )

    def test_prompt_run_details_reprompts_after_invalid_console_value(self):
        with (
            patch.object(
                self.launcher,
                "prompt_run_details_dialog",
                side_effect=RuntimeError("no GUI available"),
            ),
            patch.object(
                self.launcher,
                "prompt_run_details_console",
                side_effect=[("", "before"), ("P003", "before")],
            ),
            patch("sys.stderr", new_callable=StringIO),
        ):
            self.assertEqual(
                self.launcher.prompt_run_details(None, None),
                ("P003", "1"),
            )

    def test_filename_unsafe_participant_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.launcher.validate_participant_id("P/001")

    def test_audio_dependency_message_includes_windows_repair_command(self):
        message = self.launcher.audio_dependency_message(
            OSError("cannot load library 'libsndfile.dll'")
        )

        self.assertIn("PsychoPy audio dependency problem", message)
        self.assertIn("libsndfile", message)
        self.assertIn("python-soundfile", message)

    def test_hrd_wrapper_imports_without_psychopy_gui(self):
        repo_root = Path(__file__).resolve().parents[1]
        wrapper_path = repo_root / "wrappers" / "hrd.py"
        spec = importlib.util.spec_from_file_location("hrd_wrapper", wrapper_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        self.assertTrue(callable(module._load_launcher))
