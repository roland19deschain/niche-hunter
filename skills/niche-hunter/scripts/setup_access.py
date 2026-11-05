#!/usr/bin/env python3
"""Configure a private TokConnect API-key connection without sending research requests."""

import argparse
import getpass
import json
import os
import re
import sys
import tempfile
import warnings
from pathlib import Path

try:
    import tomllib
except ImportError:
    tomllib = None

SERVER = "niche-hunter-tokconnect"
URL = "https://mcp.tokconnect.com/mcp"
BEGIN = "# BEGIN Niche Hunter API-key connection"
END = "# END Niche Hunter API-key connection"
SKILL_DIRECTORY = Path(__file__).resolve().parents[1]
PLUGIN_DIRECTORY = SKILL_DIRECTORY.parent.parent
PACKAGE = PLUGIN_DIRECTORY if (PLUGIN_DIRECTORY / "plugin.json").is_file() else SKILL_DIRECTORY


class SetupError(ValueError):
    """A fixed, nonsecret message that can be shown to the user."""


class SetupParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Invalid setup options. Use --help; never put a key in command arguments.\n")


def require(condition, message):
    if not condition:
        raise SetupError(message)


def config_path(client):
    if client == "codex":
        return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        return Path(os.environ["CLAUDE_CONFIG_DIR"]) / ".claude.json"
    return Path.home() / ".claude.json"


def read_config(path):
    require(not path.is_symlink(), "Refusing a symlinked client configuration; use the client's own settings.")
    resolved = path.resolve()
    require(not resolved.is_relative_to(PACKAGE), "Credentials cannot be stored inside the plugin package.")
    require(not any((parent / ".git").exists() for parent in resolved.parents),
            "Credentials cannot be stored inside a Git working tree.")
    return path.read_bytes() if path.exists() else None


def parse_config(client, original):
    text = (original or b"").decode("utf-8")
    try:
        if client == "codex":
            require(tomllib is not None, "Codex setup requires Python 3.11+ for safe TOML editing.")
            data = tomllib.loads(text)
            servers = data.get("mcp_servers", {})
        else:
            data = json.loads(text) if text.strip() else {}
            require(isinstance(data, dict), "Client configuration must be an object.")
            servers = data.get("mcpServers", {})
        require(isinstance(servers, dict), "The client's MCP server configuration must be an object.")
        return text, data, servers
    except SetupError:
        raise
    except ValueError:
        raise SetupError("Client configuration is invalid; repair it in the client before setup.") from None


def managed_span(text):
    starts = list(re.finditer(r"(?m)^" + re.escape(BEGIN) + r"\r?\n", text))
    ends = list(re.finditer(r"(?m)^" + re.escape(END) + r"(?:\r?\n|$)", text))
    if not starts and not ends:
        return None
    require(len(starts) == len(ends) == 1 and starts[0].end() <= ends[0].start(),
            "The managed connection block is invalid; repair it before setup.")
    return starts[0].start(), ends[0].end()


def inspect_config(client, original, replace=False, remove=False):
    text, data, servers = parse_config(client, original)
    current = servers.get(SERVER)
    if current is None and not remove:
        require(not any(isinstance(server, dict) and str(server.get("url", "")).rstrip("/") == URL
                        for server in servers.values()),
                "TokConnect already has a manual connection. Reuse or update it in the client instead of adding a duplicate.")
    if current is not None:
        require(isinstance(current, dict) and current.get("url") == URL,
                "The reserved connection name belongs to another server; it was not changed.")
        require(replace or remove, "API-key connection already exists. Reuse it, or use --replace to rotate its key.")
    elif remove:
        raise SetupError("No managed API-key connection exists in this client configuration.")
    if client == "codex":
        span = managed_span(text)
        require((current is None) == (span is None),
                "An existing connection was not created by this helper; use the client's settings to change it.")
        if span:
            block = tomllib.loads(text[span[0]:span[1]])
            require(set(block) == {"mcp_servers"} and block["mcp_servers"] == {SERVER: current},
                    "The managed block includes unrelated settings; it was not changed.")
            remainder = text[:span[0]] + text[span[1]:]
            require(SERVER not in tomllib.loads(remainder).get("mcp_servers", {}),
                    "The connection has settings outside its managed block; it was not changed.")
    return text, data, servers


def connection_text(client, original, token=None, replace=False, remove=False):
    text, data, servers = inspect_config(client, original, replace, remove)
    if not remove:
        require(isinstance(token, str) and bool(re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token)),
                "Enter only the API key, without a Bearer prefix, spaces or line breaks.")
        authorization = "Bearer " + token
    if client == "claude-code":
        if remove:
            del servers[SERVER]
        else:
            servers[SERVER] = {"type": "http", "url": URL, "headers": {"Authorization": authorization}}
        data["mcpServers"] = servers
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    span = managed_span(text)
    if remove:
        candidate = text[:span[0]] + text[span[1]:]
    else:
        block = (BEGIN + "\n[mcp_servers." + SERVER + "]\nurl = " + json.dumps(URL)
                 + "\nhttp_headers = { Authorization = " + json.dumps(authorization) + " }\n" + END + "\n")
        candidate = text[:span[0]] + block + text[span[1]:] if span else text + ("\n" if text else "") + block
    try:
        parsed = tomllib.loads(candidate)
    except ValueError:
        raise SetupError("The connection conflicts with existing TOML settings; no file was changed.") from None
    expected = dict(servers)
    if remove:
        del expected[SERVER]
    else:
        expected[SERVER] = {"url": URL, "http_headers": {"Authorization": authorization}}
    unchanged = dict(data)
    unchanged["mcp_servers"] = expected
    # Removing the sole table can also remove the otherwise empty parent table.
    if not expected and "mcp_servers" not in parsed:
        unchanged.pop("mcp_servers", None)
    require(parsed == unchanged, "The edit would change unrelated settings; no file was changed.")
    return candidate


def write_config(path, original, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".niche-hunter-", delete=False) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        require(read_config(path) == original, "Client configuration changed during setup. Close the client and retry.")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = SetupParser(description=__doc__)
    parser.add_argument("--client", required=True, choices=("codex", "claude-code"))
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--replace", action="store_true", help="Replace the existing helper-managed API key")
    action.add_argument("--remove", action="store_true", help="Remove only this helper's API-key connection")
    args = parser.parse_args(argv)
    try:
        path = config_path(args.client)
        original = read_config(path)
        inspect_config(args.client, original, args.replace, args.remove)
        token = None
        if not args.remove:
            require(sys.stdin.isatty(), "Run this command yourself in an interactive terminal. Never send the key in chat or stdin.")
            print("Enter a TokConnect API key supplied by its owner. No TokConnect login is needed.")
            print("The key is stored as plaintext in private client settings (owner-only file permissions on POSIX).")
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                token = getpass.getpass("TokConnect API key (hidden): ")
        content = connection_text(args.client, original, token, args.replace, args.remove)
        write_config(path, original, content)
    except SetupError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (ValueError, OSError, UnicodeError, getpass.GetPassWarning, EOFError):
        # Do not print exceptions: parsers and filesystem errors can contain credential-bearing text.
        print("Setup could not complete. Check the client configuration, Python version and terminal access.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nSetup cancelled.", file=sys.stderr)
        return 1
    print("API-key connection removed." if args.remove else "API-key connection saved. No authentication or research calls were made.")
    if not args.remove:
        print("Restart the client, keep the Niche Hunter skill enabled, and use the " + SERVER + " connection.")
        print("If an unauthenticated bundled TokConnect duplicate remains visible, disable only that duplicate in MCP settings.")
        print("Confirm supported tools and the owner's available credit allowance before research; saving a key does not verify access.")
    else:
        print("Restart the client. This does not revoke the provider key or remove other connections.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
