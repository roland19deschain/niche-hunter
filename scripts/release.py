#!/usr/bin/env python3
"""Validate, package, and extract release notes for the shared Niche Hunter plugin."""

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "niche-hunter"
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json")
MARKETPLACES = (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json")
PACKAGE_FILES = (*MANIFESTS, *MARKETPLACES, "mcp.json", ".claude-plugin/mcp.json",
                 "README.md", "LICENSE", "PRIVACY.md", "CHANGELOG.md", "avatar.png")
SKILL_FILES = ("SKILL.md", "scripts/research.py", "scripts/tiktok.py", "scripts/youtube.py",
               "scripts/youtube_trends.py", "scripts/setup_access.py", "scripts/reporting.py", "scripts/report_pdf.py",
               "requirements-pdf.txt", "assets/fonts/NotoSans-Regular.ttf", "assets/fonts/NotoSans-Bold.ttf",
               "assets/fonts/OFL.txt", "assets/fonts/NOTICE.md", "references/catalog.json",
               "references/providers.md", "references/contracts.md", "references/analysis.md",
               "references/tiktok.md", "references/youtube.md", "references/access.md", "references/reporting.md", "agents/openai.yaml")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def notes(root, version):
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"^## \[" + re.escape(version) + r"\][^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    require(match is not None and match.group(1).strip(), "CHANGELOG.md needs notes for " + version)
    return match.group(1).strip() + "\n"


def validate(root=ROOT, tag=None):
    primary, compatibility = (read_json(root, name) for name in MANIFESTS)
    version = primary["version"]
    require(re.fullmatch(r"\d+\.\d+\.\d+", version), "Plugin version must be stable MAJOR.MINOR.PATCH")
    require(tag is None or tag == version, "Tag must equal " + version + " (without a v prefix)")
    for key in ("name", "version", "description", "author", "homepage", "repository", "license"):
        require(primary[key] == compatibility[key], "Client manifests disagree on " + key)
    require(primary["name"] == NAME, "Unexpected plugin identity")
    require(primary["extensions"]["com.openai"]["onboardingSkill"] == "./skills/niche-hunter/SKILL.md",
            "Onboarding must use the shared setup instructions")
    require(compatibility.get("mcpServers") == "./.claude-plugin/mcp.json", "Claude must load its bundled MCP config")
    for name, transport in (("mcp.json", "streamable-http"), (".claude-plugin/mcp.json", "http")):
        servers = read_json(root, name)["mcpServers"]
        require(servers == {"tokconnect": {"type": transport, "url": "https://mcp.tokconnect.com/mcp"}},
                "Bundle only the credential-free TokConnect endpoint with the correct client transport")
    for filename in MARKETPLACES:
        marketplace = read_json(root, filename)
        require(marketplace["name"] == NAME, "Unexpected marketplace identity")
        require(len(marketplace["plugins"]) == 1, "Marketplace must contain the shared plugin only")
        entry = marketplace["plugins"][0]
        require(entry["name"] == NAME, "Marketplace plugin identity mismatch")
        source = entry["source"]
        path = source["path"] if isinstance(source, dict) else source
        require(path == "./", "Marketplace must resolve the plugin at its own pinned root")
        if isinstance(source, dict):
            require(source["source"] == "local", "Do not bypass marketplace ref pinning with another remote")
    skill = root / "skills" / NAME
    for filename in SKILL_FILES:
        require((skill / filename).is_file(), "Missing shared skill file: " + filename)
    require(re.search(r"^name: niche-hunter$", (skill / "SKILL.md").read_text(), re.M), "Skill identity mismatch")
    for path in skill.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        require(path.relative_to(skill).as_posix() in SKILL_FILES,
                "Add new runtime resources to the explicit release allowlist: " + str(path.relative_to(skill)))
        require(not path.is_symlink(), "Runtime package must not depend on symlinks")
        require(path.resolve().is_relative_to(skill.resolve()), "Runtime file escapes the skill")
        if path.suffix in {".py", ".md", ".json", ".yaml"}:
            text = path.read_text(encoding="utf-8")
            require(not re.search(r"[\u0400-\u04ff]|/Users/|/home/|"
                                  r"\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)/"
                                  r"[A-Za-z_+-]+(?:/[A-Za-z_+-]+)?", text),
                    "Runtime content must remain portable: " + str(path.relative_to(root)))
    for filename in PACKAGE_FILES:
        require((root / filename).is_file(), "Missing package file: " + filename)
    notes(root, version)
    return version


def package(root, output, tag=None):
    version = validate(root, tag)
    paths = [root / name for name in PACKAGE_FILES]
    paths += [root / "skills" / NAME / name for name in SKILL_FILES]
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{NAME}-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as target:
        for path in sorted(paths):
            relative = path.relative_to(root)
            info = zipfile.ZipInfo((Path(NAME) / relative).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            content = path.read_bytes()
            if relative.as_posix() == "README.md":
                # Keep one maintained README; contributor-only links point to this release's source.
                source_url = read_json(root, "plugin.json")["repository"] + "/blob/" + version + "/"
                readme = re.sub(r"\]\(\./(docs/[^)]+|AGENTS\.md)\)",
                                lambda match: "](" + source_url + match.group(1) + ")", content.decode("utf-8"))
                content = ("This is a release runtime package. Contributor test/release commands require a source checkout.\n\n" + readme).encode("utf-8")
            target.writestr(info, content)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    (output / "release-notes.md").write_text(notes(root, version), encoding="utf-8")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "build", "notes"))
    parser.add_argument("--tag")
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        version = validate(ROOT, args.tag)
        if args.command == "build":
            print(package(ROOT, args.out, args.tag))
        elif args.command == "notes":
            print(notes(ROOT, version), end="")
        else:
            print(f"Niche Hunter {version}: client manifests, marketplaces, runtime files and notes agree")
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, f"Release validation failed: {error}\n")


if __name__ == "__main__":
    main()
