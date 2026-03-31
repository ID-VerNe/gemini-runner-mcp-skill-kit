import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import setup_mcp  # noqa: E402


class SetupMcpTests(unittest.TestCase):
    def test_setup_config_file_creates_and_writes(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            cfg = td_path / "mcp-config.json"
            script = td_path / "mcp_server.py"
            script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            ok = setup_mcp.setup_config_file(cfg, script, "TestApp")
            self.assertTrue(ok)
            data = json.loads(cfg.read_text(encoding="utf-8"))
            self.assertIn("mcpServers", data)
            self.assertIn("gemini-runner", data["mcpServers"])

    def test_setup_config_file_invalid_json_backup(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            cfg = td_path / "mcp-config.json"
            cfg.write_text("{bad json", encoding="utf-8")
            script = td_path / "mcp_server.py"
            script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            ok = setup_mcp.setup_config_file(cfg, script, "TestApp")
            self.assertTrue(ok)
            backup = td_path / "mcp-config.json.bak"
            self.assertTrue(backup.exists())
            data = json.loads(cfg.read_text(encoding="utf-8"))
            self.assertIn("mcpServers", data)


if __name__ == "__main__":
    unittest.main()

