#!/usr/bin/env python3
"""Build the local macOS MCPB and its companion Claude skill ZIP."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import zipfile
from importlib.metadata import distributions
from pathlib import Path

from release import NAME, ROOT, SKILL_FILES, require, validate

DESKTOP = ROOT / "desktop"
SKILL = ROOT / "skills" / NAME


def build(output):
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("Build the Apple silicon package using native arm64 Python on macOS")
    manifest_path = DESKTOP / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = validate()
    require(manifest["version"] == version, "Desktop extension version must match the plugin version")
    executable = manifest["server"]["entry_point"]
    bundle = output / f"{manifest['name']}-{version}-macos-arm64.mcpb"
    skill_zip = output / f"{NAME}-skill-{version}.zip"
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="niche-hunter-desktop-") as folder:
        work = Path(folder)
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
                        "--name", Path(executable).name, "--target-architecture", "arm64",
                        "--paths", str(SKILL / "scripts"), "--copy-metadata", "mcp",
                        "--add-data", str(SKILL / "references/catalog.json") + ":references",
                        "--add-data", str(SKILL / "assets/fonts") + ":assets/fonts",
                        "--collect-data", "tzdata",
                        "--distpath", str(work / "dist"), "--workpath", str(work / "build"),
                        "--specpath", str(work), str(DESKTOP / "server.py")],
                       check=True, cwd=ROOT, env={**os.environ, "PYINSTALLER_CONFIG_DIR": str(work / "cache")})
        binary = work / "dist" / Path(executable).name
        with zipfile.ZipFile(work / bundle.name, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(manifest_path, "manifest.json")
            archive.write(binary, executable)
            archive.write(ROOT / "LICENSE", "LICENSE")
            archive.write(Path(sysconfig.get_path("stdlib")) / "LICENSE.txt", "licenses/Python-LICENSE.txt")
            for dist in distributions():
                for file in dist.files or []:
                    # Wheels record license notices under their distribution metadata.
                    if ".dist-info/" in file.as_posix() and (
                            "licenses" in file.parts or file.name.lower().startswith(("license", "notice"))):
                        archive.write(dist.locate_file(file), f"licenses/{file.as_posix()}")
        with zipfile.ZipFile(work / skill_zip.name, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in SKILL_FILES:
                archive.write(SKILL / file, f"{NAME}/{file}")
        for path in (bundle, skill_zip):
            # The build workspace and output can live on different filesystems.
            shutil.copyfile(work / path.name, path)
            print(path)

    checksums = []
    for path in (bundle, skill_zip):
        with path.open("rb") as stream:
            checksums.append(f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {path.name}\n")
    (output / "SHA256SUMS").write_text("".join(checksums), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "claude-desktop")
    build(parser.parse_args().out.resolve())
