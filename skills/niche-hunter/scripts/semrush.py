#!/usr/bin/env python3
"""Check one keyword through the Semrush v4 API from Desktop or a local CLI."""

import getpass
import json
import os
import re
import sys
import warnings
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, quote_plus, urlencode
from urllib.request import ProxyHandler, Request, build_opener

from public_sources import NoRedirect
from research import MAX_BYTES
from setup_access import SetupError, SetupParser, read_config, require, write_config

ENDPOINT = "https://api.semrush.com/apis/v4/keywords/v1/metrics"
KEYWORD_UNITS = 20
KEY_PATTERN = re.compile(r"[A-Za-z0-9._~+/-]{8,500}={0,2}")
API_ERRORS = {
    400: ("not_supported", "Semrush rejected the keyword or country."),
    401: ("auth_required", "Semrush rejected the API key."),
    402: ("rate_limited", "Check the Semrush API unit balance."),
    403: ("not_supported", "Check Semrush API access, country availability and unit balance."),
    429: ("rate_limited", "Semrush limited the request."),
}


def status(key, approved):
    configured = isinstance(key, str) and bool(KEY_PATTERN.fullmatch(key))
    return {"ready": configured and approved is True, "key_configured": configured,
            "access_confirmed_by_operator": approved is True, "authentication_verified": False,
            "planned_units_per_lookup": KEYWORD_UNITS}


def fetch(request):
    with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=20) as response:
        data = response.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES, "Semrush response exceeded the size cap")
    return json.loads(data)


def lookup(keyword, country, key, approved):
    state = status(key, approved)
    secret_forms = {key, quote(key, safe=""), quote_plus(key)} if state["key_configured"] else set()
    require(not any(secret in keyword or secret in country for secret in secret_forms),
            "Keep credentials in private Semrush settings")
    keyword, country = keyword.strip(), country.strip().upper()
    country = "UK" if country == "GB" else country
    require(0 < len(keyword) <= 255 and keyword.isprintable() and re.fullmatch(r"[A-Z]{2}", country),
            "Use one keyword and a two-letter Semrush country code")
    details = {"route": "semrush_api_v4", "keyword": keyword, "country": country, "external_calls": 0}
    if not state["key_configured"]:
        return dict(details, status="unconfigured", reason="Configure a Semrush key in private settings.")
    if not state["ready"]:
        return dict(details, status="not_supported", reason="Confirm approved Semrush access in private settings.")

    request = Request(ENDPOINT + "?" + urlencode({"keyword": keyword, "country": country}),
                      headers={"Authorization": "Apikey " + key, "Accept": "application/json"})
    details.update(external_calls=1, documented_units_per_lookup=KEYWORD_UNITS)
    try:
        payload = fetch(request)
        serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        require(not any(secret in serialized for secret in secret_forms), "Semrush echoed a credential")
        meta, data = payload["meta"], payload["data"]
        month = meta["month"]
        require(meta["success"] is True and meta["country"] == country
                and meta["keyword"].casefold() == keyword.casefold()
                and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month), "Unexpected Semrush snapshot scope")
        metrics = {}
        for name in ("search_volume", "cpc", "keyword_difficulty", "competitive_density", "number_of_results"):
            value = data.get(name)
            require(value is None or type(value) is int and value >= 0, "Invalid Semrush metric")
            metrics[name] = value
        cpc = metrics.pop("cpc")
        metrics["cpc_usd"] = cpc / 100 if cpc is not None else None
        for name in ("intents", "serp_features"):
            values = data.get(name, [])
            require(isinstance(values, list) and all(isinstance(value, str)
                    and re.fullmatch(r"[A-Z0-9_]{1,80}", value) for value in values), "Invalid Semrush labels")
            metrics[name] = values
        trends = data.get("trends", [])
        require(isinstance(trends, list) and len(trends) <= 12
                and all(type(value) is int and 0 <= value <= 100 for value in trends), "Invalid Semrush trend")
        metrics["trends"] = trends
        result_status = "ok" if any(value is not None and value != [] for value in metrics.values()) else "no_data"
        return dict(details, status=result_status, snapshot_month=month, metrics=metrics)
    except HTTPError as error:
        error.close()
        result_status, reason = API_ERRORS.get(error.code, ("unavailable", "Semrush could not serve the lookup."))
        return dict(details, status=result_status, reason=reason)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError):
        return dict(details, status="unavailable", reason="Semrush response or connection could not be verified.")


def credential_path():
    return Path(os.environ.get("NICHE_HUNTER_CONFIG_DIR", Path.home() / ".config/niche-hunter")) / "semrush.json"


def credentials(path):
    raw = read_config(path)
    if raw is None:
        return None, False
    require(path.stat().st_mode & 0o077 == 0, "Semrush settings must be readable only by their owner")
    saved = json.loads(raw)
    require(isinstance(saved, dict), "Invalid private Semrush settings")
    return saved.get("api_key"), saved.get("approved", False)


def setup(path, args):
    original = read_config(path)
    if args.remove:
        require(original is not None, "No local Semrush settings exist")
        write_config(path, original, "{}\n")
        print("Removed the local Semrush key. Revoke it at Semrush if needed.")
        return
    require(original is None or original.strip() == b"{}" or args.replace,
            "Semrush settings already exist. Use --replace to rotate the key")
    require(sys.stdin.isatty(), "Run Semrush setup yourself in an interactive terminal")
    answer = input("Do your Semrush terms authorize this integration and AI processing in the clients you will use? [y/N] ")
    require(answer.strip().lower() == "y", "Configure an approved Semrush connection before using an API key")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        key = getpass.getpass("Semrush v4 API key (hidden): ")
    require(KEY_PATTERN.fullmatch(key), "Enter only the Semrush v4 API key")
    write_config(path, original, json.dumps({"api_key": key, "approved": True}) + "\n")
    print("Saved the key in owner-only Niche Hunter settings. Authentication was not tested.")


def main(argv=None):
    parser = SetupParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("setup", help="Configure the key in your own interactive terminal")
    action = command.add_mutually_exclusive_group()
    action.add_argument("--replace", action="store_true")
    action.add_argument("--remove", action="store_true")
    commands.add_parser("status", help="Check local settings without using API units")
    command = commands.add_parser("keyword", help="Fetch one keyword snapshot after approval")
    command.add_argument("--keyword", required=True)
    command.add_argument("--country", required=True)
    args = parser.parse_args(argv)
    try:
        path = credential_path()
        if args.command == "setup":
            setup(path, args)
            return 0
        key, approved = credentials(path)
        result = status(key, approved) if args.command == "status" else lookup(args.keyword, args.country, key, approved)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except SetupError as error:
        print(str(error), file=sys.stderr)
    except (ValueError, OSError, EOFError, getpass.GetPassWarning):
        print("Semrush settings or lookup could not be read. Check the private configuration and inputs.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nSemrush setup or lookup cancelled.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
