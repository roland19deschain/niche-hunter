"""Release artifact checks; synthetic version transitions are not published releases."""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from zoneinfo import available_timezones

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = json.loads((ROOT / "plugin.json").read_text())["version"]
NEXT_VERSION = ".".join([*PACKAGE_VERSION.split(".")[:2], str(int(PACKAGE_VERSION.split(".")[2]) + 1)])
SPEC = importlib.util.spec_from_file_location("release", ROOT / "scripts/release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def fixture(root):
    for name in release.PACKAGE_FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    shutil.copytree(ROOT / "skills", root / "skills", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


class ReleaseTests(unittest.TestCase):
    def test_packaged_examples_reject_named_regional_timezones(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            regional_zone = next(zone for zone in sorted(available_timezones())
                                 if "/" in zone and not zone.startswith(("Etc/", "posix/", "right/")))
            path = root / "skills/niche-hunter/SKILL.md"
            path.write_text(path.read_text() + "\nExample timezone: " + regional_zone + "\n")
            with self.assertRaises(ValueError):
                release.validate(root)

    def test_rejects_mismatched_client_versions_and_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            self.assertEqual(release.validate(root, PACKAGE_VERSION), PACKAGE_VERSION)
            with self.assertRaises(ValueError):
                release.validate(root, "99.0.0")
            with self.assertRaises(ValueError):
                release.validate(root, "v" + PACKAGE_VERSION)
            path = root / ".claude-plugin/plugin.json"
            data = json.loads(path.read_text())
            data["version"] = "99.0.0"
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                release.validate(root)

    def test_marketplace_cannot_escape_pinned_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            path = root / ".agents/plugins/marketplace.json"
            data = json.loads(path.read_text())
            data["plugins"][0]["source"] = {"source": "url", "path": "./", "url": "https://example.org/unstable.git"}
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                release.validate(root)

    def test_bundled_connections_cannot_drift_or_ship_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            for name in ("mcp.json", ".claude-plugin/mcp.json"):
                path = root / name
                original = path.read_text()
                data = json.loads(original)
                data["mcpServers"]["tokconnect"]["headers"] = {"Authorization": "SYNTHETIC_NOT_A_SECRET"}
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    release.validate(root)
                path.write_text(original)
                data["mcpServers"]["tokconnect"].pop("headers")
                data["mcpServers"]["tokconnect"]["url"] = "https://example.org/unreviewed-server"
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    release.validate(root)
                path.write_text(original)

    def test_archive_is_reproducible_and_excludes_development_data(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            fixture(root)
            hidden = root / "skills/niche-hunter/scripts/__pycache__/private.pyc"
            hidden.parent.mkdir(parents=True)
            hidden.write_bytes(b"must not ship")
            (root / ".env").write_text("SYNTHETIC_NOT_A_SECRET=excluded\n")
            first = release.package(root, base / "first")
            second = release.package(root, base / "second")
            self.assertEqual(first.name, f"niche-hunter-{PACKAGE_VERSION}.zip")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            digest = hashlib.sha256(first.read_bytes()).hexdigest()
            self.assertEqual((first.parent / "SHA256SUMS").read_text(), f"{digest}  {first.name}\n")
            with zipfile.ZipFile(first) as archive:
                readme = archive.read("niche-hunter/README.md").decode("utf-8")
                repository = json.loads((root / "plugin.json").read_text())["repository"]
                self.assertIn(f"{repository}/blob/{PACKAGE_VERSION}/docs/releasing.md", readme)
                self.assertNotIn("/blob/v" + PACKAGE_VERSION + "/", readme)
                paths = archive.namelist()
                self.assertFalse(any("__pycache__" in name or name.endswith(".env") for name in paths))
                self.assertFalse(any(".." in Path(name).parts for name in paths))
                self.assertIn("niche-hunter/skills/niche-hunter/references/catalog.json", paths)
                self.assertIn("niche-hunter/skills/niche-hunter/scripts/tiktok.py", paths)
                self.assertIn("niche-hunter/skills/niche-hunter/scripts/setup_access.py", paths)
                self.assertIn("niche-hunter/skills/niche-hunter/references/access.md", paths)
                self.assertIn("niche-hunter/skills/niche-hunter/references/tiktok.md", paths)
                self.assertIn("niche-hunter/mcp.json", paths)
                self.assertIn("niche-hunter/.claude-plugin/mcp.json", paths)
                self.assertIn("niche-hunter/PRIVACY.md", paths)

    def test_extracted_install_update_and_rollback_keep_helper_usable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            fixture(root)
            old = release.package(root, base / "old")
            for name in release.MANIFESTS:
                path = root / name
                data = json.loads(path.read_text())
                data["version"] = NEXT_VERSION
                path.write_text(json.dumps(data))
            changelog = root / "CHANGELOG.md"
            changelog.write_text(f"# Changelog\n\n## [{NEXT_VERSION}] - 2026-11-02\n\nSynthetic update fixture.\n\n" + changelog.read_text())
            new = release.package(root, base / "new")
            for stage, artifact, expected in (("install", old, PACKAGE_VERSION), ("update", new, NEXT_VERSION), ("rollback", old, PACKAGE_VERSION)):
                installed = base / stage
                with zipfile.ZipFile(artifact) as archive:
                    archive.extractall(installed)
                plugin = installed / "niche-hunter"
                self.assertEqual(release.validate(plugin), expected)
                output = base / (stage + "-run")
                result = subprocess.run([sys.executable, str(plugin / "skills/niche-hunter/scripts/research.py"),
                    "collect", "--diagnostic", "--providers", "reddit", "--offline", "--as-of", "2026-11-01T12:00:00Z",
                    "--out", str(output)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads((output / "results.json").read_text())
                self.assertEqual(data["schema_version"], "0.1.0")
                self.assertEqual([x["provider"] for x in data["sources"]], ["reddit"])
                self.assertEqual(data["sources"][0]["status"], "unconfigured")


if __name__ == "__main__":
    unittest.main()
