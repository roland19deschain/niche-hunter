"""Private setup checks use synthetic keys and temporary client configuration only."""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "skills/niche-hunter/scripts/setup_access.py"
SPEC = importlib.util.spec_from_file_location("setup_access", SCRIPT)
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)
TOKEN = "SYNTHETIC_NOT_A_REAL_KEY"
ROTATED = "SYNTHETIC_ROTATED_KEY"


class SetupAccessTests(unittest.TestCase):
    def test_claude_config_preserves_other_settings_and_supports_rotation_and_removal(self):
        original = {"theme": "dark", "projects": {"synthetic": {"allowedTools": []}},
                    "mcpServers": {"other": {"type": "http", "url": "https://example.org/mcp"}}}
        first = setup.connection_text("claude-code", json.dumps(original).encode(), TOKEN)
        installed = json.loads(first)
        self.assertEqual(installed["mcpServers"][setup.SERVER],
                         {"type": "http", "url": setup.URL, "headers": {"Authorization": "Bearer " + TOKEN}})
        self.assertEqual({k: v for k, v in installed.items() if k != "mcpServers"},
                         {k: v for k, v in original.items() if k != "mcpServers"})
        self.assertEqual(installed["mcpServers"]["other"], original["mcpServers"]["other"])
        with self.assertRaises(setup.SetupError):
            setup.connection_text("claude-code", first.encode(), ROTATED)
        replaced = setup.connection_text("claude-code", first.encode(), ROTATED, replace=True)
        self.assertNotIn(TOKEN, replaced)
        self.assertIn(ROTATED, replaced)
        removed = setup.connection_text("claude-code", replaced.encode(), remove=True)
        self.assertEqual(json.loads(removed), original)

    @unittest.skipIf(setup.tomllib is None, "Codex setup requires Python 3.11+ TOML parsing")
    def test_codex_preserves_comments_tables_and_values_during_rotation_and_removal(self):
        original = '# Keep this comment\nmodel = "synthetic-model"\n[mcp_servers.other]\nurl = "https://example.org/mcp"\n'
        first = setup.connection_text("codex", original.encode(), TOKEN)
        self.assertTrue(first.startswith(original))
        parsed = setup.tomllib.loads(first)
        self.assertEqual(parsed["mcp_servers"][setup.SERVER]["http_headers"], {"Authorization": "Bearer " + TOKEN})
        self.assertEqual(parsed["mcp_servers"]["other"], {"url": "https://example.org/mcp"})
        with self.assertRaises(setup.SetupError):
            setup.connection_text("codex", first.encode(), ROTATED)
        replaced = setup.connection_text("codex", first.encode(), ROTATED, replace=True)
        self.assertNotIn(TOKEN, replaced)
        removed = setup.connection_text("codex", replaced.encode(), remove=True)
        self.assertEqual(removed.strip(), original.strip())
        self.assertNotIn(ROTATED, removed)

    @unittest.skipIf(setup.tomllib is None, "Codex setup requires Python 3.11+ TOML parsing")
    def test_codex_fails_closed_for_unmanaged_or_conflicting_tables_and_markers(self):
        configurations = [
            '[mcp_servers.' + setup.SERVER + ']\nurl = "' + setup.URL + '"\n',
            'mcp_servers = {}\n',
            setup.BEGIN + '\nmodel = "synthetic"\n',
            setup.END + '\n',
            setup.BEGIN + '\n[mcp_servers.' + setup.SERVER + ']\nurl = "' + setup.URL + '"\n'
            + '[mcp_servers.other]\nurl = "https://example.org/mcp"\n' + setup.END + '\n',
        ]
        for text in configurations:
            with self.subTest(configuration=text), self.assertRaises(setup.SetupError):
                setup.connection_text("codex", text.encode(), TOKEN, replace=True)

    def test_empty_configs_foreign_server_and_invalid_credentials(self):
        clients = ["claude-code"] + (["codex"] if setup.tomllib else [])
        for client in clients:
            with self.subTest(client=client):
                first = setup.connection_text(client, None, TOKEN)
                setup.connection_text(client, first.encode(), remove=True)
                with self.assertRaises(setup.SetupError):
                    setup.connection_text(client, None, remove=True)
                for key in (None, "", "Bearer " + TOKEN, TOKEN + "\n", TOKEN + " ", "bad\r\nheader"):
                    with self.subTest(key=key), self.assertRaises(setup.SetupError):
                        setup.connection_text(client, None, key)
        foreign = json.dumps({"mcpServers": {setup.SERVER: {"url": "https://example.org/mcp"}}}).encode()
        for options in ({"replace": True}, {"remove": True}):
            with self.assertRaises(setup.SetupError):
                setup.connection_text("claude-code", foreign, TOKEN, **options)
        existing = json.dumps({"mcpServers": {"existing-tokconnect": {"type": "http", "url": setup.URL}}}).encode()
        with self.assertRaisesRegex(setup.SetupError, "already has a manual connection"):
            setup.connection_text("claude-code", existing, TOKEN)

    def test_private_atomic_write_refuses_concurrent_changes_and_unsafe_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            path = base / "private" / "settings.json"
            content = setup.connection_text("claude-code", None, TOKEN)
            setup.write_config(path, None, content)
            self.assertEqual(path.read_text(), content)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(setup.SetupError):
                setup.write_config(path, b"stale", "must not replace current settings")
            self.assertEqual(path.read_text(), content)
            self.assertEqual(list(path.parent.iterdir()), [path])
            link = base / "symlink.json"
            link.symlink_to(path)
            with self.assertRaises(setup.SetupError):
                setup.read_config(link)
            (base / ".git").mkdir()
            with self.assertRaises(setup.SetupError):
                setup.read_config(path)
        with self.assertRaises(setup.SetupError):
            setup.read_config(SCRIPT.parent / "credentials.json")

    def test_cli_rejects_noninteractive_and_secret_arguments_without_echo_or_files(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, "CLAUDE_CONFIG_DIR": directory}
            for options in ([], ["--api-key", TOKEN]):
                result = subprocess.run([sys.executable, str(SCRIPT), "--client", "claude-code", *options],
                    env=env, input=TOKEN, text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(TOKEN, result.stdout + result.stderr)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_main_hidden_entry_and_errors_never_print_key_or_call_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {"CLAUDE_CONFIG_DIR": directory}
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, env), mock.patch.object(sys.stdin, "isatty", return_value=True), \
                 mock.patch.object(setup.getpass, "getpass", return_value=TOKEN) as prompt, \
                 mock.patch("socket.socket", side_effect=AssertionError("No network during setup")), \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(setup.main(["--client", "claude-code"]), 0)
                prompt.assert_called_once()
                self.assertEqual(setup.main(["--client", "claude-code"]), 1)
                self.assertEqual(prompt.call_count, 1)
                self.assertEqual(setup.main(["--client", "claude-code", "--remove"]), 0)
            self.assertNotIn(TOKEN, stdout.getvalue() + stderr.getvalue())
            self.assertNotIn(TOKEN, (Path(directory) / ".claude.json").read_text())

    def test_malformed_configuration_does_not_leak_or_overwrite_existing_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".claude.json"
            original = ('{"' + TOKEN + '": broken}').encode()
            path.write_bytes(original)
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": directory}), \
                 mock.patch.object(setup.getpass, "getpass") as prompt, \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(setup.main(["--client", "claude-code"]), 1)
                prompt.assert_not_called()
            self.assertNotIn(TOKEN, stdout.getvalue() + stderr.getvalue())
            self.assertEqual(path.read_bytes(), original)

    def test_no_toml_parser_has_clear_failure_before_prompt(self):
        with mock.patch.object(setup, "tomllib", None):
            with self.assertRaisesRegex(setup.SetupError, "Python 3.11"):
                setup.inspect_config("codex", None)

    def test_standalone_skill_does_not_treat_the_entire_client_directory_as_a_package(self):
        with tempfile.TemporaryDirectory() as directory:
            client = Path(directory) / "client"
            installed = client / "skills/niche-hunter/scripts/setup_access.py"
            installed.parent.mkdir(parents=True)
            shutil.copyfile(SCRIPT, installed)
            spec = importlib.util.spec_from_file_location("standalone_setup", installed)
            standalone = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(standalone)
            self.assertEqual(standalone.PACKAGE, installed.resolve().parents[1])
            self.assertIsNone(standalone.read_config(client / "config.toml"))
            with self.assertRaises(standalone.SetupError):
                standalone.read_config(installed.parent / "credentials.json")


if __name__ == "__main__":
    unittest.main()
