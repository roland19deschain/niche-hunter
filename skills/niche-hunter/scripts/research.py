#!/usr/bin/env python3
"""Niche Hunter: bounded public collection, permitted imports, and reporting."""

import argparse
import csv
import hashlib
import io
import importlib.util
import json
import math
import re
import sys
import time
import uuid
import zipfile
from datetime import date, datetime, time as day_time, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from reporting import build_report, markdown_report, text_report, validate_presentation

VERSION = "0.1.0"
UTC = timezone.utc
SKILL_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
CATALOG = json.loads((SKILL_DIR / "references/catalog.json").read_text())
PROVIDERS = CATALOG["default_providers"]
PUBLIC_ROUTES = {"app_store": "public_apple_catalog", "google_trends": "public_google_trends_rss"}
SIGNALS_URL = "https://cdn.openai.com/signals/data-download-csv.zip"
SIGNALS_PAGE = "https://openai.com/signals/data-download/"
SIGNALS_TABLE = "share_of_messages_by_topic_month.csv"
MAX_BYTES = 10 * 1024 * 1024
FAILURES = {"unconfigured", "auth_required", "not_supported", "rate_limited",
            "unavailable", "usage_terms_unconfirmed"}
SIGNAL_TYPES = {"typed_search", "topic_group", "recommended_keyword", "hashtag",
                "video", "sound", "comment", "discussion", "aggregate_usage", "unknown"}
QUALITIES = {"verified_official", "provider_claim_tested", "provider_claim_unverified",
             "proxy_content_signal", "missing"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "Timestamp must include a UTC offset")
    return parsed.astimezone(UTC)


def window(start, end, zone="UTC", semantics="calendar"):
    return {"start_at": iso(start), "end_at": iso(end), "timezone": zone,
            "semantics": semantics}


def validate_window(value):
    require(isinstance(value, dict), "Measurement window must be an object")
    require(value.get("semantics") in {"calendar", "rolling", "snapshot", "unknown"},
            "Unsupported window semantics")
    if value.get("start_at") is not None or value.get("end_at") is not None:
        require(timestamp(value["start_at"]) < timestamp(value["end_at"]),
                "Window must have increasing start/end timestamps")
    else:
        require(value["semantics"] in {"snapshot", "unknown"}, "Calendar/rolling window needs dates")
    require(isinstance(value.get("timezone"), str), "Window needs source timezone or 'unknown'")


def selected_providers(value):
    chosen = list(dict.fromkeys(item.strip().lower() for item in value.split(",")))
    require(chosen and all(item in PROVIDERS for item in chosen),
            "Supported providers: " + ", ".join(PROVIDERS))
    return chosen


def provider_scope(args):
    chosen = selected_providers(args.providers)
    excluded = selected_providers(args.exclude_providers) if args.exclude_providers else []
    chosen = [provider for provider in chosen if provider not in excluded]
    require(chosen, "Select at least one provider")
    return chosen


def public_request_plan(providers, offline=False, trends_csv=False):
    return {provider + "_requests": int(provider in providers and not offline
                                         and not (provider == "google_trends" and trends_csv))
            for provider in PUBLIC_ROUTES}


def readiness(args, configured=()):
    chosen = provider_scope(args)
    imports = {}
    for filename in args.import_file:
        payload = load_json(Path(filename))
        provider = payload["provider"]
        require(provider in chosen, "Import supplied for an unselected provider")
        require(provider in {"reddit", "tiktok", "youtube"}, "This provider does not accept a normalized import envelope")
        require(provider not in imports, "Supply one combined import envelope per provider")
        imports[provider] = payload
    require(not args.signals_file or "chatgpt" in chosen, "--signals-file needs selected chatgpt provider")
    trends_file = args.google_trends_file
    require(not trends_file or "google_trends" in chosen, "--google-trends-file needs selected google_trends provider")
    require(not trends_file or Path(trends_file).is_file(), "Google Trends CSV descriptor does not exist")
    states = []
    for provider in chosen:
        supplied = imports.get(provider)
        missing_access = supplied is not None and supplied.get("status") in {"unconfigured", "auth_required"} \
            and supplied.get("collection", {}).get("external_calls", 0) == 0
        if provider in imports and not missing_access:
            route = "supplied_result"
        elif provider == "chatgpt" and args.signals_file:
            require(Path(args.signals_file).is_file(), "Signals file does not exist")
            route = "public_release_replay"
        elif provider == "chatgpt" and not args.offline:
            route = "public_release_no_credentials"
        elif provider == "google_trends" and trends_file:
            route = "google_trends_web_csv"
        elif provider in PUBLIC_ROUTES and not args.offline:
            route = PUBLIC_ROUTES[provider]
        elif provider in configured and provider not in {*PUBLIC_ROUTES, "chatgpt"}:
            route = "client_connection_checked_by_caller"
        else:
            route = None
        states.append({"provider": provider, "ready": route is not None, "route": route,
                       "next_action": None if route else "Configure this selected provider or explicitly exclude it."})
    attempts = public_request_plan(chosen, args.offline, bool(trends_file))
    attempts["signals_downloads"] = 2 if "chatgpt" in chosen and not args.offline and not args.signals_file else 0
    return {"ready": all(item["ready"] for item in states), "providers": states,
            "public_attempt_ceiling": attempts}, imports


def preflight(args):
    configured = selected_providers(args.configured_providers) if args.configured_providers else []
    state, _ = readiness(args, configured)
    pdf_ready = args.native_pdf or all(importlib.util.find_spec(name) is not None for name in ("reportlab", "emoji"))
    state["pdf"] = {"ready": pdf_ready, "backend": "calling_client" if args.native_pdf else "reportlab",
                    "next_action": None if pdf_ready else "Install the PDF requirements in the chosen Python environment or configure a native client PDF exporter."}
    state["ready"] = state["ready"] and pdf_ready
    print(json.dumps(state, indent=2))
    return state["ready"]


def parameters(args, now):
    chosen = provider_scope(args)
    zone = ZoneInfo(args.timezone or "UTC")
    require(bool(args.start) == bool(args.end), "Supply both --start and --end (exclusive)")
    require(not (args.start and args.days is not None), "Use dates or --days, not both")
    if args.start:
        def boundary(value):
            if len(value) == 10:
                return datetime.combine(date.fromisoformat(value), day_time(), zone)
            return timestamp(value).astimezone(zone)
        start, end = boundary(args.start), boundary(args.end)
    else:
        days = args.days if args.days is not None else 7
        require(0 < days <= 3660, "--days must be between 1 and 3660")
        end = datetime.combine(now.astimezone(zone).date(), day_time(), zone)
        start = end - timedelta(days=days)
    require(start < end, "Start must precede exclusive end")
    require(end.astimezone(UTC) <= now, "Research window cannot end in the future")
    require(1 <= args.max_records <= 10000, "--max-records must be between 1 and 10000")
    # Calendar boundaries stay aligned across DST; elapsed hours need not be identical.
    baseline_start = start - (end.replace(tzinfo=None) - start.replace(tzinfo=None))
    return {"id": str(uuid.uuid4()), "generated_at": iso(datetime.now(UTC)),
            "reference_at": iso(now), "providers": chosen, "original_request": args.request,
            "topic": args.topic.strip() if args.topic else None, "region": args.region,
            "language": args.language, "timezone": str(zone),
            "timezone_reason": "explicit_or_caller" if args.timezone else "disclosed_UTC_fallback",
            "requested_window": window(start, end, str(zone)),
            "baseline_window": window(baseline_start, start, str(zone)),
            "includes_partial_day": end.astimezone(zone).date() == now.astimezone(zone).date()
                and end.astimezone(zone).time() != day_time(),
            "limits": {"max_records_per_provider": args.max_records,
                       "max_helper_http_attempts": (2 if "chatgpt" in chosen else 0) + len(set(chosen) & PUBLIC_ROUTES.keys()),
                       "max_external_calls": 10,
                       "new_paid_spending_usd": 0}, "offline": args.offline}


def source_result(provider, run, adapter=None):
    return {"provider": provider, "adapter": adapter, "status": "unconfigured",
            "reason": "No permitted configured tool/export was supplied; see references/providers.md.",
            "requested_window": run["requested_window"], "actual_window": None,
            "coverage": "not_collected", "completeness": "unknown",
            "effective_filters": {}, "unsupported_filters": [], "limitations": [],
            "counts": {"received": 0, "accepted": 0, "duplicates": 0,
                       "outside_window": 0, "limited": 0},
            "usage": {"helper_http_attempts": 0, "external_calls": 0,
                      "new_paid_spending_usd": 0}, "provenance": {},
            "observations": [], "comparisons": []}


def load_json(path):
    require(path.stat().st_size <= MAX_BYTES, "JSON exceeds 10 MiB limit")
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_signals(source):
    for attempt in range(2):
        source["usage"]["helper_http_attempts"] += 1
        try:
            request = Request(SIGNALS_URL, headers={"User-Agent": "NicheHunter/0.1 public-data research"})
            with urlopen(request, timeout=20) as response:
                data = response.read(MAX_BYTES + 1)
            require(len(data) <= MAX_BYTES, "Signals ZIP exceeds 10 MiB limit")
            return data
        except HTTPError as error:
            source["status"] = {401: "auth_required", 403: "auth_required", 429: "rate_limited"}.get(
                error.code, "unavailable")
            if attempt == 0 and error.code in {429, 500, 502, 503, 504}:
                delay = error.headers.get("Retry-After", "1")
                if delay.isdigit() and int(delay) <= 2:
                    time.sleep(int(delay))
                    continue
            source["reason"] = f"Signals HTTP {error.code}; stopped within retry budget."
            return None
        except (URLError, TimeoutError, OSError):
            if attempt == 0:
                time.sleep(1)
                continue
            source.update(status="unavailable", reason="Signals network failure after two bounded attempts.")
            return None


def next_month(value):
    return value.replace(year=value.year + 1, month=1) if value.month == 12 else value.replace(month=value.month + 1)


def previous_month(value):
    return value.replace(year=value.year - 1, month=12) if value.month == 1 else value.replace(month=value.month - 1)


def change(current, baseline):
    if current is None or baseline is None:
        return {"absolute_change": None, "relative_change_pct": None, "reason": "missing_measurement"}
    return {"absolute_change": round(current - baseline, 12),
            "relative_change_pct": round((current - baseline) / baseline * 100, 6) if baseline else None,
            "reason": "zero_baseline" if baseline == 0 else None}


def collect_signals(run, args, out, source=None):
    source = source if source is not None else source_result("chatgpt", run)
    source["adapter"] = "openai_signals_csv"
    canonical_topic = None
    if run["topic"]:
        canonical_topic = next((key for key, aliases in CATALOG["signals_topics"].items()
                                if run["topic"].casefold() in [a.casefold() for a in aliases]), None)
        if canonical_topic is None:
            source.update(status="not_supported", reason="Signals table has broad monthly categories only; requested topic is not represented.")
            return source
    if args.offline and not args.signals_file:
        source.update(status="unavailable", reason="Offline mode: no --signals-file supplied.")
        return source
    replay = bool(args.signals_file)
    if replay:
        path = Path(args.signals_file)
        require(path.stat().st_size <= MAX_BYTES, "Signals ZIP exceeds 10 MiB limit")
        data = path.read_bytes()
    else:
        data = fetch_signals(source)
        if data is None:
            return source
    digest = hashlib.sha256(data).hexdigest()
    raw = out / "raw"
    raw.mkdir(exist_ok=True)
    (raw / "signals.zip").write_bytes(data)
    source["provenance"] = {"source_url": SIGNALS_URL, "methodology_url": SIGNALS_PAGE,
                            "sha256": digest, "snapshot": "raw/signals.zip",
                            "mode": "offline_replay" if replay else "live_public_download",
                            "retrieved_at": None if replay else iso(datetime.now(UTC)),
                            "processed_at": iso(datetime.now(UTC)),
                            "license": "CC BY 4.0", "attribution": "OpenAI Signals; derived comparisons by Niche Hunter"}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = [info for info in archive.infolist() if Path(info.filename).name == SIGNALS_TABLE]
        require(len(members) == 1, "Signals CSV table missing or ambiguous; inspect updated release")
        member = members[0]
        require(member.file_size <= MAX_BYTES, "Signals table exceeds 10 MiB limit")
        reader = csv.DictReader(io.StringIO(archive.read(member).decode("utf-8-sig")))
        require(set(reader.fieldnames or []) == {"month", "topic", "share_of_messages"},
                "Signals schema changed; expected month, topic, share_of_messages")
        records = {}
        for row in reader:
            month = date.fromisoformat(row["month"])
            require(month.day == 1, "Signals month must be a UTC month-start label")
            value = float(row["share_of_messages"])
            require(math.isfinite(value) and 0 <= value <= 1, "Signals share must be finite in [0,1]")
            key = (month, row["topic"])
            if key in records:
                require(records[key] == value, "Conflicting duplicate Signals row")
                source["counts"]["duplicates"] += 1
            records[key] = value
            source["counts"]["received"] += 1
    end = timestamp(run["requested_window"]["end_at"])
    months = [m for m, topic in records if datetime.combine(next_month(m), day_time(), UTC) <= end
              and (not canonical_topic or topic == canonical_topic)]
    if not months:
        source.update(status="not_supported", reason="No complete Signals month available before requested end.")
        return source
    current_month = max(months)
    baseline_month = previous_month(current_month)
    source["actual_window"] = window(datetime.combine(current_month, day_time(), UTC),
                                      datetime.combine(next_month(current_month), day_time(), UTC))
    source.update(status="partial", coverage="context_only", completeness="monthly_aggregate_only",
                  reason="Latest eligible monthly category shares; requested-period and narrow-topic demand are unavailable.")
    source["effective_filters"] = {"topic": canonical_topic, "region": "global", "language": None}
    source["unsupported_filters"] = [key for key in ("region", "language") if run[key]]
    source["limitations"] = ["Differentially private weighted shares, not counts or raw prompts.",
                              "Only one global broad-topic table is supported; no weekly baseline or narrow-topic demand.",
                              "Share growth does not establish absolute usage growth, a problem, or willingness to pay.",
                              "Publication time is unknown; replay does not establish original retrieval time."]
    source["lag_days"] = max(0, (end - timestamp(source["actual_window"]["end_at"])).days)
    source["provenance"]["table"] = member.filename
    topics = sorted(topic for m, topic in records if m == current_month and (not canonical_topic or topic == canonical_topic))
    # A comparison requires both records. Do not cut a pair at the observation limit.
    for topic in topics:
        pair = [(m, records[(m, topic)]) for m in (current_month, baseline_month) if (m, topic) in records]
        if len(source["observations"]) + len(pair) > args.max_records:
            source["counts"]["limited"] += len(pair)
            continue
        evidence_ids = []
        for month, value in pair:
            evidence_id = "chatgpt:" + hashlib.sha256(f"{digest}:{month}:{topic}".encode()).hexdigest()[:16]
            evidence_ids.append(evidence_id)
            measurement_window = window(datetime.combine(month, day_time(), UTC),
                                        datetime.combine(next_month(month), day_time(), UTC))
            source["observations"].append({"id": evidence_id, "source_id": f"{month}:{topic}",
                "url": SIGNALS_PAGE, "title": topic, "summary": "Published aggregate message share, not an observed user complaint.",
                "topic_terms": [topic], "signal_type": "aggregate_usage", "published_at": None,
                "metric_observed_at": None, "retrieved_at": source["provenance"]["retrieved_at"],
                "quality": "verified_official", "limitations": source["limitations"],
                "measurements": [{"name": "share_of_messages", "value": value, "unit": "fraction",
                    "kind": "estimate", "window": measurement_window, "missing_reason": None,
                    "methodology": "P(topic | UTC month), differentially private weighted share; see source dictionary"}]})
        current, baseline = records[(current_month, topic)], records.get((baseline_month, topic))
        derived = change(current, baseline)
        source["comparisons"].append({"topic": topic, "evidence_ids": evidence_ids,
            "method": "adjacent_calendar_month_share_change", "current": current,
            "baseline": baseline, "baseline_window": window(datetime.combine(baseline_month, day_time(), UTC),
                datetime.combine(current_month, day_time(), UTC)), **derived,
            "percentage_point_change": round(derived["absolute_change"] * 100, 6) if baseline is not None else None,
            "trend_classification": "unassessed", "confidence": "context_only"})
    source["counts"]["accepted"] = len(source["observations"])
    return source


def text_field(obj, key):
    require(isinstance(obj.get(key), str) and bool(obj[key].strip()), f"Missing nonempty text field: {key}")


def secure_url(value, provider=None):
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password
            and parsed.port in (None, 443), "Evidence URL must be HTTPS without credentials")
    if provider == "youtube":
        query = parse_qs(parsed.query, keep_blank_values=True)
        require(query and all(len(values) == 1 for values in query.values()) and not parsed.fragment,
                "YouTube evidence URL has repeated parameters or a fragment")
        if parsed.hostname in {"youtube.com", "www.youtube.com"} and parsed.path == "/watch":
            require(set(query) <= {"v", "lc"} and "v" in query
                    and re.fullmatch(r"[A-Za-z0-9_-]{11}", query["v"][0])
                    and ("lc" not in query or re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", query["lc"][0])),
                    "Only canonical video/comment parameters are allowed")
        else:
            require(parsed.hostname == "trends.google.com" and parsed.path == "/trends/explore"
                    and set(query) <= {"q", "date", "gprop", "geo", "cat"}
                    and query.get("gprop") == ["youtube"],
                    "Only YouTube Search Trends evidence parameters are allowed")
    else:
        require(not parsed.query, "Evidence URL must not contain query tokens")


def collect_import(payload, run, max_records, source=None):
    require(payload.get("schema_version") == VERSION, "Unsupported import schema_version")
    provider = payload["provider"]
    require(provider in {"reddit", "tiktok", "youtube"}, "Unsupported import provider")
    source = source if source is not None else source_result(provider, run)
    source["adapter"] = payload.get("adapter")
    text_field(payload, "adapter")
    text_field(payload, "reason")
    status = payload["status"]
    require(status in FAILURES | {"ok", "partial"}, "Invalid provider status")
    require(isinstance(payload.get("observations"), list), "observations must be an array")
    collection = payload["collection"]
    require(type(collection.get("external_calls")) is int and 0 <= collection["external_calls"] <= 10,
            "External calls must be 0..10 (total run limit also applies)")
    require(collection.get("new_paid_spending_usd") == 0, "Free pilot accepts no new paid spending")
    source["usage"]["external_calls"] = collection["external_calls"]
    source.update(status=status, reason=payload["reason"])
    source["provenance"] = {"collection": collection, "mode": "permitted_import"}
    if status in FAILURES:
        require(not payload["observations"], "Failure status cannot include observations")
        return source
    rights = payload.get("rights")
    if provider == "reddit":
        require(isinstance(rights, dict) and rights.get("storage_permitted") is True,
                "Reddit import needs an established access/storage basis")
        text_field(rights, "basis")
        secure_url(rights["reference"])
    if isinstance(rights, dict):
        source["provenance"]["rights"] = {key: rights[key] for key in ("storage_permitted", "basis", "reference")
                                          if key in rights and type(rights[key]) in (str, bool)}
    source["effective_filters"] = payload["effective_filters"]
    source["unsupported_filters"] = [key for key in ("topic", "region", "language")
        if run[key] and payload["effective_filters"].get(key) != run[key]]
    if "topic" in source["unsupported_filters"]:
        source.update(status="not_supported", reason="Import did not apply the requested topic filter.")
        return source
    validate_window(payload["actual_window"])
    source["actual_window"] = payload["actual_window"]
    require(isinstance(payload.get("limitations"), list) and all(isinstance(x, str) for x in payload["limitations"]),
            "Import needs text limitations array")
    source["limitations"] = payload["limitations"]
    source.update(coverage="sampled", completeness="not_established")
    if source["actual_window"] != run["requested_window"] or source["unsupported_filters"]:
        source["status"] = "partial"
    seen = set()
    for row in payload["observations"]:
        source["counts"]["received"] += 1
        require(set(row) <= {"source_id", "url", "title", "summary", "topic_terms", "signal_type",
                            "quality", "published_at", "metric_observed_at", "retrieved_at",
                            "limitations", "measurements"}, "Unexpected evidence fields; retain only normalized permitted fields")
        for key in ("source_id", "title", "summary"):
            text_field(row, key)
        secure_url(row["url"], provider)
        require(row["signal_type"] in SIGNAL_TYPES, "Invalid signal_type")
        if provider == "reddit":
            require(row["signal_type"] in {"discussion", "comment"}, "Reddit import must be discussion/comment evidence")
        if provider == "youtube":
            require(row["signal_type"] in {"typed_search", "topic_group", "video", "comment"},
                    "YouTube evidence must be a Trends query/topic, context video or comment")
        require(row["quality"] in QUALITIES, "Invalid evidence quality")
        require(isinstance(row.get("limitations"), list) and all(isinstance(x, str) for x in row["limitations"]),
                "Evidence needs text limitations array")
        require(isinstance(row.get("topic_terms"), list) and all(isinstance(x, str) for x in row["topic_terms"]),
                "Evidence needs text topic_terms array")
        if run["topic"]:
            require(run["topic"].casefold() in [term.casefold() for term in row["topic_terms"]],
                    "Topic-scoped evidence must retain the caller's term in topic_terms")
        for key in ("published_at", "metric_observed_at", "retrieved_at"):
            require(key in row, f"Evidence missing {key}; use null if unknown")
            if row[key] is not None:
                require(timestamp(row[key]) <= timestamp(run["generated_at"]), "Evidence timestamp is in the future")
        require(row["retrieved_at"] is not None, "Imported evidence needs its actual retrieval time")
        if provider == "youtube" and row["signal_type"] in {"comment", "video"}:
            require(timestamp(run["generated_at"]) - timestamp(row["retrieved_at"]) <= timedelta(days=30),
                    "YouTube snapshot expired; refresh or delete source data before reuse")
            if row["signal_type"] == "comment":
                require(row["published_at"] is not None, "Dated YouTube comments need original publication time")
        require(isinstance(row.get("measurements"), list), "Evidence needs measurements array (may be empty)")
        for metric in row["measurements"]:
            for key in ("name", "unit", "methodology"):
                text_field(metric, key)
            require(metric["kind"] in {"count", "index", "estimate", "derived", "range_lower", "range_upper"},
                    "Invalid metric kind")
            value = metric["value"]
            require(value is None or (type(value) in (int, float) and math.isfinite(value)), "Metric must be finite or null")
            if value is None:
                text_field(metric, "missing_reason")
            validate_window(metric["window"])
            if "comparison_group" in metric:
                text_field(metric, "comparison_group")
        if row["source_id"] in seen:
            source["counts"]["duplicates"] += 1
            continue
        seen.add(row["source_id"])
        actual = source["actual_window"]
        temporal = run["requested_window"] if provider == "youtube" else actual
        windowed = row["signal_type"] in {"discussion", "comment", "video"}
        if provider == "youtube" and row["signal_type"] == "video":
            windowed = False  # Older relevant videos can contain comments from the requested period.
        if row["published_at"] and temporal["start_at"] and windowed:
            if not timestamp(temporal["start_at"]) <= timestamp(row["published_at"]) < timestamp(temporal["end_at"]):
                source["counts"]["outside_window"] += 1
                continue
        if len(source["observations"]) >= max_records:
            source["counts"]["limited"] += 1
            continue
        row = dict(row)
        row["id"] = provider + ":" + hashlib.sha256(row["source_id"].encode()).hexdigest()[:16]
        source["observations"].append(row)
    source["counts"]["accepted"] = len(source["observations"])
    if source["counts"]["limited"] or source["counts"]["outside_window"] or not source["observations"]:
        source["status"] = "partial"
    return source


def render(result):
    return markdown_report(build_report(result))


def save_run(out, result, pdf=None):
    # Render and stage every artifact before replacing existing outputs.
    document = build_report(result)
    report = markdown_report(document)
    artifacts = {"report.md": report.encode("utf-8")}
    if pdf is not None:
        artifacts["report.pdf"] = pdf
    result = {**result, "report": document,
              "exports": {name: {"sha256": hashlib.sha256(data).hexdigest()} for name, data in artifacts.items()}}
    artifacts["results.json"] = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    for name, data in artifacts.items():
        (out / (name + ".tmp")).write_bytes(data)
    for name in artifacts:
        (out / (name + ".tmp")).replace(out / name)


def collect(args):
    now = timestamp(args.as_of) if args.as_of else datetime.now(UTC)
    run = parameters(args, now)
    require(not args.signals_file or "chatgpt" in run["providers"], "--signals-file needs selected chatgpt provider")
    state, imports = readiness(args)
    require(state["ready"] or args.diagnostic,
            "Configure every selected provider before collection, or explicitly exclude it: " +
            ", ".join(item["provider"] for item in state["providers"] if not item["ready"]))
    planned = state["public_attempt_ceiling"]
    require(sum(item["collection"]["external_calls"] for item in imports.values()) + sum(planned.values()) <= 10,
            "Imports and reserved public attempts exceed the total 10 external-call run budget")
    run["public_attempt_ceiling"] = planned
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    require(not any(out.iterdir()), "Output directory must be empty; choose a fresh run directory")
    sources = []
    for provider in run["providers"]:
        source = source_result(provider, run)
        try:
            if provider == "chatgpt":
                source = collect_signals(run, args, out, source)
            elif provider in PUBLIC_ROUTES:
                from public_sources import collect_public

                csv_input = Path(args.google_trends_file) if args.google_trends_file else None
                source = collect_public(run, source, csv_input)
            elif provider in imports:
                source = collect_import(imports[provider], run, args.max_records, source)
        except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile, UnicodeError, csv.Error) as error:
            # Source errors must not stop other selected providers. Avoid echoing raw content/secrets.
            source.update(status="unavailable", reason=f"{provider} input/schema failure ({type(error).__name__}); validate the documented contract.")
            source["observations"] = []
            source["comparisons"] = []
            source["counts"]["accepted"] = 0
        sources.append(source)
    result = {"schema_version": VERSION, "run": run,
              "catalog": {"version": CATALOG["version"], "categories": [item["id"] for item in CATALOG["categories"]],
                          "scope": CATALOG["scope"]},
              "sources": sources, "analysis": {"status": "pending", "findings": [], "hypotheses": [],
                  "gaps": ["Calling-agent analysis pending; broad aggregates alone do not validate product problems."]}}
    save_run(out, result)
    print(json.dumps({"run": str(out.resolve()), "sources": [
        {"provider": item["provider"], "status": item["status"], "observations": item["counts"]["accepted"]} for item in sources]}))


def validate_analysis(analysis, result):
    require(analysis.get("schema_version") == VERSION, "Unsupported analysis schema_version")
    text_field(analysis, "summary")
    require(isinstance(analysis.get("gaps"), list) and all(isinstance(x, str) for x in analysis["gaps"]), "gaps must be text array")
    if "research_context" in analysis:
        context = analysis["research_context"]
        require(isinstance(context, dict), "research_context must be an object")
        require(context.get("mode") in {"discovery", "refinement"}, "Invalid research mode")
        require("product" in context and (context["product"] is None or
                isinstance(context["product"], str) and context["product"].strip()), "Product must be text or null")
        if context["mode"] == "refinement":
            text_field(context, "product")
        for key in ("constraints", "target_channels"):
            require(isinstance(context.get(key), list) and
                    all(isinstance(value, str) and value.strip() for value in context[key]), f"{key} must be text array")
    known = {row["id"] for source in result["sources"] for row in source["observations"]}
    for group in ("findings", "hypotheses"):
        require(isinstance(analysis.get(group), list), f"{group} must be array")
        for item in analysis[group]:
            refs = item.get("evidence_ids")
            require(isinstance(refs, list) and refs and all(ref in known for ref in refs), "Analysis contains missing/unknown evidence IDs")
            require(item.get("confidence") in {"low", "medium", "high"}, "Confidence must be low/medium/high")
            if group == "findings":
                require(item.get("kind") in {"observed_fact", "estimate", "inference", "hypothesis", "test_needed"}, "Invalid finding kind")
                require(item.get("trend_classification") in {"emerging", "sustained", "declining", "spike-only", "unassessed"}, "Invalid trend classification")
                text_field(item, "text")
            else:
                for key in ("title", "audience", "job", "problem", "alternatives", "value_proposition",
                            "product_format", "minimal_mvp", "channel", "distribution_hook", "monetization",
                            "risks", "experiment", "success_criteria", "stop_criteria", "missing_data"):
                    text_field(item, key)
                if "brief" in item:
                    text_field(item, "brief")
                    require(len(item["brief"]) <= 400, "Product brief must be at most 400 characters")
                if "research_context" in analysis:
                    require("opportunity" in item, "New analyses require an opportunity assessment per hypothesis")
                if "opportunity" in item:
                    opportunity = item["opportunity"]
                    require(isinstance(opportunity, dict), "opportunity must be an object")
                    require(opportunity.get("channel_fit") in {"supported", "inferred", "untested"}, "Invalid channel fit")
                    require(opportunity.get("priority") in {"test_next", "research_more", "defer"}, "Invalid opportunity priority")
                    for key in ("market", "entry_point", "acquisition_path", "fit_reasoning", "counterevidence", "priority_reason"):
                        text_field(opportunity, key)
                    for key in ("demand_evidence_ids", "channel_evidence_ids"):
                        evidence = opportunity.get(key)
                        require(isinstance(evidence, list) and all(ref in refs for ref in evidence),
                                "Opportunity evidence must reference this hypothesis's evidence IDs")
                    require(bool(opportunity["demand_evidence_ids"]), "Opportunity needs demand evidence")
                    require(bool(opportunity["channel_evidence_ids"]) == (opportunity["channel_fit"] != "untested"),
                            "Supported/inferred channel fit needs evidence; untested fit needs an empty channel evidence array")
    validate_presentation(analysis, result)
    return {**analysis, "status": "complete", "method": "calling_agent_analysis_not_independently_verified"}


def finalize(args):
    out = Path(args.run)
    result = load_json(out / "results.json")
    require(result.get("schema_version") == VERSION, "Unsupported results schema_version")
    result["analysis"] = validate_analysis(load_json(Path(args.analysis)), result)
    if args.pdf_file:
        path = Path(args.pdf_file)
        require(path.stat().st_size <= 20 * 1024 * 1024, "Native PDF exceeds 20 MiB")
        pdf = path.read_bytes()
        require(pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-1024:], "Supply a complete PDF from the native client exporter")
    else:
        from report_pdf import pdf_bytes
        pdf = pdf_bytes(build_report(result), args.font_regular, args.font_bold)
    save_run(out, result, pdf)
    print(f"Finalized report.md, report.pdf and results.json in {out.resolve()} (no collection/network requests)")


def show_report(args):
    result = load_json(Path(args.run) / "results.json")
    if args.analysis:
        result["analysis"] = validate_analysis(load_json(Path(args.analysis)), result)
    document = build_report(result)
    print(text_report(document) if args.format == "text" else markdown_report(document), end="")


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    scope = argparse.ArgumentParser(add_help=False)
    scope.add_argument("--providers", default=",".join(PROVIDERS))
    scope.add_argument("--exclude-providers", default="")
    scope.add_argument("--signals-file")
    scope.add_argument("--google-trends-file", help="Descriptor JSON for a local Google Trends Web Search related-queries CSV")
    scope.add_argument("--import-file", action="append", default=[])
    scope.add_argument("--offline", action="store_true")
    command = commands.add_parser("preflight", parents=[scope], help="Check selected provider/output configuration; no research calls")
    command.add_argument("--configured-providers", default="", help="Client connections actually checked by the calling agent")
    command.add_argument("--native-pdf", action="store_true", help="Calling client has a configured native PDF exporter")
    command = commands.add_parser("collect", parents=[scope], help="Collect selected public sources and/or permitted imports")
    command.add_argument("--diagnostic", action="store_true", help="Explicit diagnostic run allowing unconfigured providers; not normal research")
    command.add_argument("--days", type=int)
    command.add_argument("--start", help="ISO date in the selected time zone or timestamp with offset")
    command.add_argument("--end", help="Exclusive ISO date in the selected time zone or timestamp with offset")
    command.add_argument("--timezone", help="Caller IANA zone; disclosed UTC fallback if omitted")
    for name in ("topic", "region", "language", "request", "as-of"):
        command.add_argument("--" + name)
    command.add_argument("--max-records", type=int, default=100)
    command.add_argument("--out", required=True, help="Fresh/empty output directory")
    command = commands.add_parser("finalize", help="Validate calling-agent analysis and render; no network")
    command.add_argument("--run", required=True)
    command.add_argument("--analysis", required=True)
    command.add_argument("--font-regular", help="Optional TrueType font covering the report language")
    command.add_argument("--font-bold", help="Matching bold TrueType font")
    command.add_argument("--pdf-file", help="Already rendered native client PDF of this same report")
    command = commands.add_parser("report", help="Print the same compact report as Markdown or a terminal table")
    command.add_argument("--run", required=True)
    command.add_argument("--analysis", help="Preview validated analysis before native PDF export")
    command.add_argument("--format", choices=("markdown", "text"), default="text")
    return root


def main():
    root = parser()
    args = root.parse_args()
    try:
        if args.command == "preflight":
            if not preflight(args):
                root.exit(2)
        elif args.command == "report":
            show_report(args)
        elif args.command == "collect":
            collect(args)
        else:
            finalize(args)
    except (ValueError, KeyError, TypeError, OSError, ZoneInfoNotFoundError) as error:
        # Do not echo source payloads or local credential-bearing paths on failure.
        message = str(error) if isinstance(error, ValueError) else type(error).__name__
        root.exit(2, f"niche-hunter: {message}\n")


if __name__ == "__main__":
    main()
