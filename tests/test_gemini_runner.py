import json
import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gemini_runner  # noqa: E402


class GeminiRunnerTests(unittest.TestCase):
    def test_build_args_default(self):
        cfg = gemini_runner.RunnerConfig(
            task="hello",
            cwd=".",
            cmd="gemini",
            model="",
            mode="default",
            timeout_seconds=10,
            output_dir=".gemini-runs",
            machine=True,
            human_stream=False,
            human_render="compact",
            resume_session="",
        )
        args = gemini_runner._build_args(cfg)
        self.assertEqual(args[:2], ["--output-format", "stream-json"])
        self.assertIn("-p", args)

    def test_build_args_with_resume_and_model(self):
        cfg = gemini_runner.RunnerConfig(
            task="audit",
            cwd=".",
            cmd="gemini",
            model="gemini-2.5-pro",
            mode="auto_edit",
            timeout_seconds=10,
            output_dir=".gemini-runs",
            machine=True,
            human_stream=False,
            human_render="compact",
            resume_session="sid-123",
        )
        args = gemini_runner._build_args(cfg)
        self.assertIn("--resume", args)
        self.assertIn("sid-123", args)
        self.assertIn("-m", args)
        self.assertIn("gemini-2.5-pro", args)
        self.assertIn("--approval-mode", args)
        self.assertIn("auto_edit", args)

    def test_safe_json_line(self):
        obj = gemini_runner._safe_json_line('{"type":"message","content":"x"}')
        self.assertIsInstance(obj, dict)
        self.assertEqual(obj["type"], "message")
        self.assertIsNone(gemini_runner._safe_json_line("not-json"))
        self.assertIsNone(gemini_runner._safe_json_line("[]"))

    def test_get_gemini_cmd(self):
        """Verify gemini command detection works."""
        cmd = gemini_runner._get_gemini_cmd()
        # Should return a valid command (either full path or "gemini")
        self.assertIsInstance(cmd, str)
        self.assertGreater(len(cmd), 0)

    def test_run_spawn_error_writes_result(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = gemini_runner.RunnerConfig(
                task="audit",
                cwd=".",
                cmd="nonexistent-gemini-binary",
                model="",
                mode="default",
                timeout_seconds=2,
                output_dir=td,
                machine=True,
                human_stream=False,
                human_render="compact",
                resume_session="",
            )
            out = gemini_runner.run_task(cfg)
            result_path = Path(out["result_path"])
            self.assertTrue(result_path.exists())
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "spawn_error")
            self.assertTrue(len(data["errors"]) >= 1)

    def test_timeout_seconds_non_positive_falls_back(self):
        cfg = gemini_runner.RunnerConfig(
            task="audit",
            cwd=".",
            cmd="nonexistent-gemini-binary",
            model="",
            mode="default",
            timeout_seconds=0,
            output_dir=".gemini-runs",
            machine=True,
            human_stream=False,
            human_render="compact",
            resume_session="",
        )
        out = gemini_runner.run_task(cfg)
        data = json.loads(Path(out["result_path"]).read_text(encoding="utf-8"))
        # Spawn error path should still execute deterministically.
        self.assertEqual(data["status"], "spawn_error")


if __name__ == "__main__":
    unittest.main()

