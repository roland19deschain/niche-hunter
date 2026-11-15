"""Test local Semrush setup and lookups using synthetic credentials and responses."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/niche-hunter/scripts"
with patch.object(sys, "path", [str(SCRIPTS), *sys.path]):
    import semrush

KEY = "synthetic-local-semrush-key"


class SemrushHelperTests(unittest.TestCase):
    def test_local_setup_status_lookup_and_remove(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {"NICHE_HUNTER_CONFIG_DIR": directory}):
            path = Path(directory) / "semrush.json"
            with patch.object(semrush, "fetch", side_effect=AssertionError("Setup must be offline")):
                with (
                    patch.object(sys.stdin, "isatty", return_value=True),
                    patch("builtins.input", return_value="y"),
                    patch.object(semrush.getpass, "getpass", return_value=KEY),
                ):
                    self.assertEqual(self.invoke("setup")[0], 0)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                code, output = self.invoke("status")
                self.assertEqual(code, 0)
                self.assertTrue(json.loads(output)["ready"])
                self.assertFalse(json.loads(output)["authentication_verified"])

            response = {"meta": {"success": True, "country": "UK", "keyword": "synthetic notes", "month": "2026-10"},
                        "data": {"search_volume": 42, "cpc": 218, "trends": [61, 72]}}
            with patch.object(semrush, "fetch", return_value=response) as fetch:
                code, output = self.invoke("keyword", "--keyword", "synthetic notes", "--country", "GB")
            self.assertEqual(code, 0)
            result = json.loads(output)
            self.assertEqual((result["status"], result["metrics"]["cpc_usd"]), ("ok", 2.18))
            self.assertEqual(result["route"], "semrush_api_v4")
            request = fetch.call_args.args[0]
            self.assertEqual(request.get_header("Authorization"), "Apikey " + KEY)
            self.assertEqual(parse_qs(urlsplit(request.full_url).query)["country"], ["UK"])
            self.assertNotIn(KEY, request.full_url)
            self.assertEqual(self.invoke("setup", "--remove")[0], 0)
            self.assertNotIn(KEY, path.read_text())
            self.assertFalse(json.loads(self.invoke("status")[1])["ready"])

    def test_declining_setup_never_prompts_for_key_and_insecure_file_cannot_be_used(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {"NICHE_HUNTER_CONFIG_DIR": directory}):
            path = Path(directory) / "semrush.json"
            with (
                patch.object(sys.stdin, "isatty", return_value=True),
                patch("builtins.input", return_value="n"),
                patch.object(semrush.getpass, "getpass") as prompt,
            ):
                self.assertEqual(self.invoke("setup")[0], 1)
                prompt.assert_not_called()
                self.assertFalse(path.exists())
            path.write_text(json.dumps({"api_key": KEY, "approved": True}))
            path.chmod(0o644)
            with patch.object(semrush, "fetch") as fetch:
                self.assertEqual(self.invoke("keyword", "--keyword", "example", "--country", "US")[0], 1)
                fetch.assert_not_called()

    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = semrush.main(args)
        self.assertNotIn(KEY, stdout.getvalue() + stderr.getvalue())
        return code, stdout.getvalue()
