#!/usr/bin/env python3
"""Collect a bounded, read-only sample from the official Meta Ad Library API."""

import getpass
import json
import os
import re
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, quote_plus, urlencode
from urllib.request import Request, build_opener

from public_sources import NoRedirect
from research import CATALOG, MAX_BYTES, UTC, VERSION, iso, parameters, parser as research_parser, require, timestamp, window
from setup_access import SetupParser, read_config, write_config
from youtube import prepare_output

ENDPOINT = "https://graph.facebook.com/v27.0/ads_archive"
EU_COUNTRIES = frozenset("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())
TIER_1 = ("DE", "FR", "IE", "NL")
TOKEN = re.compile(r"[A-Za-z0-9._~+/-]{8,2048}=*")
AD_ID = re.compile(r"[0-9]{1,30}")
COPY_FIELDS = ("ad_creative_link_titles", "ad_creative_bodies", "ad_creative_link_descriptions", "ad_creative_link_captions")
FIELDS = ("id", "page_id", "page_name", "ad_delivery_start_time", "ad_delivery_stop_time", "publisher_platforms", *COPY_FIELDS)


def countries_for(region):
    if not region or region.strip().lower() == "tier-1":
        return list(TIER_1)
    selected = list(dict.fromkeys(code.strip().upper() for code in region.split(",")))
    require(len(selected) <= len(EU_COUNTRIES) and all(code in EU_COUNTRIES for code in selected),
            "Use Tier 1 or one or more EU country codes for the Meta commercial archive. US and UK-only coverage is not enabled.")
    return selected


def credential_path():
    return Path(os.environ.get("NICHE_HUNTER_CONFIG_DIR", Path.home() / ".config/niche-hunter")) / "meta.json"


def credentials():
    token = os.environ.get("NICHE_HUNTER_META_TOKEN")
    if not token:
        path = credential_path()
        raw = read_config(path)
        if raw:
            require(path.stat().st_mode & 0o077 == 0, "Meta settings must be readable only by their owner")
        stored = json.loads(raw) if raw else {}
        require(isinstance(stored, dict), "Invalid private Meta settings")
        token = stored.get("meta_token")
    return token if isinstance(token, str) and TOKEN.fullmatch(token) else None


def setup(args):
    path = credential_path()
    original = read_config(path)
    if args.remove:
        require(original is not None, "No private Meta settings exist")
        write_config(path, original, "{}\n")
        print("Removed the local Meta token. Revoke it at Meta if needed.")
        return
    require(original is None or original.strip() == b"{}" or args.replace,
            "Meta settings already exist. Use --replace to rotate the token")
    require(sys.stdin.isatty(), "Run setup yourself in an interactive terminal")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        token = getpass.getpass("Meta Ad Library access token (hidden): ")
    require(TOKEN.fullmatch(token), "Enter only the Meta access token")
    write_config(path, original, json.dumps({"meta_token": token}) + "\n")
    print("Meta token saved in owner-only local settings. Access has not been tested.")


def fetch(request):
    with build_opener(NoRedirect()).open(request, timeout=20) as response:
        data = response.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES, "Meta response exceeded the size cap")
    return json.loads(data)


def failure(error, status=None):
    code = error.get("code") if isinstance(error, dict) else None
    if code in (102, 190) or status == 401:
        return "auth_required", "Meta rejected the access token. Check or replace it in private settings."
    if code in (4, 17, 32, 613) or status == 429:
        return "rate_limited", "Meta rate limited the archive request."
    if code in (10, 200, 294) or status == 403:
        return "not_supported", "The token or app lacks access to this Meta Ad Library request."
    return "unavailable", "Meta could not serve the archive request."


def collect(run, token, *, region=None, maximum=20, transport=None, clock=None):
    clock = clock or (lambda: datetime.now(UTC))
    topic = run["topic"]
    collection = {"external_calls": 0, "new_paid_spending_usd": 0}
    output = {"schema_version": VERSION, "provider": "meta", "adapter": "meta_ads_archive",
              "collection": collection, "observations": []}
    if not isinstance(token, str) or not TOKEN.fullmatch(token):
        return dict(output, status="auth_required", reason="Configure the Meta Ad Library access token.")
    secret_forms = {token, quote(token, safe=""), quote_plus(token)}
    try:
        countries = countries_for(region if region is not None else run["region"])
    except ValueError as error:
        return dict(output, status="not_supported", reason=str(error))
    seed = topic or CATALOG["categories"][0]["seeds"][-1]
    if any(secret in seed for secret in secret_forms):
        return dict(output, status="not_supported", reason="Use a search topic without credentials.")
    if len(seed) > 100:
        return dict(output, status="not_supported", reason="Use a Meta search topic of at most 100 characters.")
    start = timestamp(run["requested_window"]["start_at"])
    end = timestamp(run["requested_window"]["end_at"])
    baseline = timestamp(run["baseline_window"]["start_at"])
    trend_hunt = run.get("hunt_mode") == "trend_hunt"
    first = baseline if trend_hunt else start
    # The official archive exposes up to one year. Keep the requested interval separate.
    cutoff = clock().date() - timedelta(days=365)
    first = max(first, datetime.combine(cutoff, datetime.min.time(), UTC))
    if first >= end:
        return dict(output, status="not_supported", reason="The requested interval is outside Meta's commercial archive window.")
    limit = min(maximum, 50)
    query = {"ad_type": "ALL", "ad_active_status": "ALL", "ad_reached_countries": json.dumps(countries),
             "ad_delivery_date_min": first.date().isoformat(),
             "ad_delivery_date_max": (end - timedelta(microseconds=1)).date().isoformat(),
             "search_terms": seed, "fields": ",".join(FIELDS), "limit": limit}
    # Meta's endpoint documents access_token as a query parameter. Never persist the request or follow paging URLs.
    request = Request(ENDPOINT + "?" + urlencode({**query, "access_token": token}),
                      headers={"Accept": "application/json", "User-Agent": "NicheHunter/MetaArchive"})
    collection.update(external_calls=1, search_terms=[seed], reached_countries=countries, page_limit=limit,
                      delivery_date_min=query["ad_delivery_date_min"], delivery_date_max=query["ad_delivery_date_max"])
    try:
        payload = (transport or fetch)(request)
        if isinstance(payload, dict) and "error" in payload:
            status, reason = failure(payload["error"])
            return dict(output, status=status, reason=reason)
        require(isinstance(payload, dict) and isinstance(payload.get("data"), list), "Unknown Meta response schema")
    except HTTPError as error:
        try:
            body = json.loads(error.read(MAX_BYTES))
        except (ValueError, OSError):
            body = None
        finally:
            error.close()
        status, reason = failure(body.get("error") if isinstance(body, dict) else None, error.code)
        return dict(output, status=status, reason=reason)
    except (ValueError, OSError):
        return dict(output, status="unavailable", reason="Meta archive request or response could not be read.")

    retrieved = iso(clock())

    def safe_text(value, size):
        if not isinstance(value, str):
            return ""
        for secret in secret_forms:
            value = value.replace(secret, "[redacted]")
        return " ".join(value.split())[:size]

    ads, seen = {}, set()
    periods = {"current": 0, "baseline": 0}
    entries = payload["data"]
    malformed = 0
    for entry in entries[:limit]:
        if not isinstance(entry, dict):
            malformed += 1
            continue
        ad_id = str(entry.get("id", ""))
        if not AD_ID.fullmatch(ad_id) or any(secret in ad_id for secret in secret_forms):
            malformed += 1
            continue
        if ad_id in seen:
            continue
        try:
            started = timestamp(entry["ad_delivery_start_time"])
        except (ValueError, TypeError, AttributeError, KeyError):
            malformed += 1
            continue
        if not first <= started < end:
            continue
        seen.add(ad_id)
        period = "current" if started >= start else "baseline"
        periods[period] += 1
        name = safe_text(entry.get("page_name"), 120) or "Unknown advertiser"
        variants = []
        for field in COPY_FIELDS:
            if isinstance(entry.get(field), list):
                variants.extend(safe_text(value, 220) for value in entry[field][:3])
        copy = " | ".join(dict.fromkeys(value for value in variants if value))[:550]
        platforms = entry.get("publisher_platforms")
        platforms = [safe_text(value, 32) for value in platforms[:8] if isinstance(value, str)] if isinstance(platforms, list) else []
        page_id = str(entry.get("page_id", ""))
        page_id = page_id if AD_ID.fullmatch(page_id) and all(secret not in page_id for secret in secret_forms) else None
        stop = entry.get("ad_delivery_stop_time")
        try:
            stop = iso(timestamp(stop)) if isinstance(stop, str) else None
        except ValueError:
            stop = None
        ads[ad_id] = {"period": period, "page_id": page_id, "platforms": platforms, "delivery_stopped_at": stop}
        summary = " · ".join(filter(None, (started.date().isoformat(), ", ".join(platforms), copy)))
        output["observations"].append({"source_id": ad_id, "url": "https://www.facebook.com/ads/library/?id=" + ad_id,
            "title": name, "summary": summary, "topic_terms": [topic] if topic else [], "signal_type": "ad_creative",
            "quality": "verified_official", "published_at": iso(started), "metric_observed_at": None,
            "retrieved_at": retrieved, "limitations": ["Public archive metadata and bounded copy only."], "measurements": []})

    paging = payload.get("paging")
    complete = len(entries) < limit and not (isinstance(paging, dict) and paging.get("next"))
    if malformed and malformed == min(len(entries), limit):
        return dict(output, status="unavailable", reason="Meta returned no rows with a usable ad ID and delivery start.")
    collection.update(archive_rows=len(entries), malformed_rows=malformed, pagination_complete=complete,
                      new_ads_in_sample=periods, ads=ads,
                      comparison_requested=trend_hunt, baseline_clipped=trend_hunt and first > baseline,
                      comparable_periods=trend_hunt and first == baseline and complete and not malformed)
    output["observations"].sort(key=lambda row: row["published_at"], reverse=True)
    reason = ("Sample of ads with recorded starts in the selected archive interval." if periods["current"] or periods["baseline"]
              else "No matching ad starts in the returned archive sample.")
    return dict(output, status="partial", reason=reason,
                actual_window=window(first, end, run["timezone"]),
                effective_filters={"topic": topic, "region": ",".join(countries), "language": None},
                limitations=["Search results are a bounded archive sample. No images, video, spend, conversions or ROAS are collected.",
                             "Ad starts describe advertiser activity. Ads running from an earlier start are outside this sample.",
                             "A truncated response or clipped baseline cannot support period-over-period growth claims."])


def main():
    parser = SetupParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("setup")
    action = command.add_mutually_exclusive_group()
    action.add_argument("--replace", action="store_true")
    action.add_argument("--remove", action="store_true")
    commands.add_parser("status")
    command = commands.add_parser("collect", help="Create one normalized Meta import")
    command.add_argument("--out", required=True)
    command.add_argument("--max-records", type=int, default=20)
    command.add_argument("--days", type=int)
    for name in ("start", "end", "timezone", "topic", "region", "hunt-mode"):
        command.add_argument("--" + name)
    args = parser.parse_args()
    try:
        if args.command == "setup":
            setup(args)
            return
        token = credentials()
        if args.command == "status":
            print(json.dumps({"provider": "meta", "token_configured": bool(token), "authentication_verified": False}))
            return
        require(token is not None, "Configure the Meta access token before collection")
        require(1 <= args.max_records <= 50, "Use 1 to 50 Meta records")
        forwarded = ["collect", "--providers", "meta", "--out", args.out]
        for key in ("days", "start", "end", "timezone", "topic", "region", "hunt_mode"):
            if getattr(args, key) is not None:
                forwarded += ["--" + key.replace("_", "-"), str(getattr(args, key))]
        run = parameters(research_parser().parse_args(forwarded), datetime.now(UTC))
        out = prepare_output(args.out)
        result = collect(run, token, maximum=args.max_records)
        with out.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps({"provider": "meta", "status": result["status"], "observations": len(result["observations"])}))
    except (ValueError, TypeError, OSError, getpass.GetPassWarning):
        parser.exit(2, "Meta setup or collection failed. Check the private settings, scope and output path.\n")


if __name__ == "__main__":
    main()
