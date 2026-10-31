#!/usr/bin/env python3
"""Niche Hunter v0.1: bounded public Signals collection, permitted imports, reporting."""

import argparse
import csv
import hashlib
import io
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
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = "0.1.0"
UTC = timezone.utc
SKILL_DIR = Path(__file__).resolve().parents[1]
CATALOG = json.loads((SKILL_DIR / "references/catalog.json").read_text())
PROVIDERS = CATALOG["default_providers"]
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


def parameters(args, now):
    chosen = selected_providers(args.providers)
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
                       "max_helper_http_attempts": 2, "max_external_calls": 10,
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


def secure_url(value):
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password
            and not parsed.query, "Evidence URL must be HTTPS without credentials/query tokens")


def collect_import(payload, run, max_records, source=None):
    require(payload.get("schema_version") == VERSION, "Unsupported import schema_version")
    provider = payload["provider"]
    require(provider in {"reddit", "tiktok"}, "Imports support reddit and tiktok only")
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
    rights = payload["rights"]
    require(rights.get("storage_permitted") is True, "Import needs explicit permitted-storage basis")
    text_field(rights, "basis")
    secure_url(rights["reference"])
    source["provenance"]["rights"] = rights
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
        secure_url(row["url"])
        require(row["signal_type"] in SIGNAL_TYPES, "Invalid signal_type")
        if provider == "reddit":
            require(row["signal_type"] in {"discussion", "comment"}, "Reddit import must be discussion/comment evidence")
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
        if row["source_id"] in seen:
            source["counts"]["duplicates"] += 1
            continue
        seen.add(row["source_id"])
        actual = source["actual_window"]
        if row["published_at"] and actual["start_at"] and row["signal_type"] in {"discussion", "comment", "video"}:
            if not timestamp(actual["start_at"]) <= timestamp(row["published_at"]) < timestamp(actual["end_at"]):
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


def md(value):
    return re.sub(r"([\\`*_{}\[\]<>|])", r"\\\1", str(value)).replace("\n", " ").replace("\r", " ")


def render(result):
    run = result["run"]
    requested = run["requested_window"]
    lines = ["# Niche Hunter", "", f"Requested: [{requested['start_at']}, {requested['end_at']}) · {run['timezone']}",
             f"Topic: {md(run['topic'] or 'bounded catalog survey')} · providers: {', '.join(run['providers'])}",
             f"Region: {md(run['region'] or 'unspecified')} · language filter: {md(run['language'] or 'unspecified')}",
             f"Time zone: {run['timezone_reason']} · partial day: {run['includes_partial_day']}", "",
             "## Coverage", "", "| Provider | Status | Actual window | Retained | Limitation |",
             "| --- | --- | --- | ---: | --- |"]
    for source in result["sources"]:
        actual = source["actual_window"]
        period = f"[{actual['start_at']}, {actual['end_at']})" if actual else "unknown"
        lines.append(f"| {source['provider']} | {source['status']} | {period} | {source['counts']['accepted']} | {md(source['reason'])} |")
    lines += ["", "Coverage is source-specific; sampled records and monthly context do not prove requested-period completeness.",
              "The requested comparison interval is recorded in results.json; monthly comparisons below use their own baseline."]
    for source in result["sources"]:
        if source["unsupported_filters"]:
            lines += ["", f"{source['provider']}: unsupported filters: {', '.join(source['unsupported_filters'])}."]
        if source["observations"]:
            lines += ["", f"## {source['provider']} evidence", ""]
            for row in source["observations"][:20]:
                measures = []
                for metric in row["measurements"]:
                    value = metric["value"]
                    display = f"{value * 100:.2f}%" if metric["unit"] == "fraction" and value is not None else str(value)
                    period = metric["window"]
                    measures.append(f"{md(metric['name'])}: {display} {md(metric['unit'])} [{period['start_at']}, {period['end_at']})")
                lines.append(f"- [{md(row['title'])}]({row['url']}) — {md(row['summary'])} {'; '.join(measures)}. Evidence `{row['id']}` ({row['quality']}).")
            if len(source["observations"]) > 20:
                lines.append("- Additional evidence is retained in results.json.")
        if source["comparisons"]:
            lines += ["", "Monthly share changes (derived; not absolute usage growth):", ""]
            for item in source["comparisons"]:
                lines.append(f"- {md(item['topic'])}: {item['percentage_point_change']} percentage points; relative share change {item['relative_change_pct']}%; classification {item['trend_classification']}.")
        if source["provenance"].get("license"):
            lines += ["", f"Source: [OpenAI Signals]({SIGNALS_PAGE}), CC BY 4.0. Derived comparisons by Niche Hunter. Mode: {source['provenance']['mode']}."]
    analysis = result["analysis"]
    lines += ["", "## Analysis", "", f"Status: {analysis['status']}.", md(analysis.get("summary", "Calling agent analysis has not been added."))]
    for finding in analysis.get("findings", []):
        lines += ["", f"- {finding['kind']}: {md(finding['text'])} Evidence: {', '.join(finding['evidence_ids'])}; confidence: {finding['confidence']}; trend: {finding['trend_classification']}."]
    for item in analysis.get("hypotheses", []):
        lines += ["", f"### Hypothesis: {md(item['title'])}", ""]
        for key in ("audience", "job", "problem", "alternatives", "value_proposition", "product_format",
                    "minimal_mvp", "channel", "distribution_hook", "monetization", "risks", "experiment",
                    "success_criteria", "stop_criteria", "confidence", "missing_data"):
            lines.append(f"- {key}: {md(item[key])}")
        lines.append("- Evidence: " + ", ".join(item["evidence_ids"]))
    lines += ["", "## Gaps and next checks", ""]
    for gap in analysis.get("gaps", ["Analysis and product validation are pending."]):
        lines.append("- " + md(gap))
    for source in result["sources"]:
        for limitation in source["limitations"]:
            lines.append(f"- {source['provider']}: {md(limitation)}")
    lines += ["", "Unknowns are not zero. No automatic scoring, purchase-intent inference, or verified product economics.", ""]
    return "\n".join(lines)


def save_run(out, result):
    # Prepare both before replacing either file, so validation/render errors preserve earlier artifacts.
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    report = render(result)
    for name, content in (("results.json", encoded), ("report.md", report)):
        temporary = out / (name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(out / name)


def collect(args):
    now = timestamp(args.as_of) if args.as_of else datetime.now(UTC)
    run = parameters(args, now)
    require(not args.signals_file or "chatgpt" in run["providers"], "--signals-file needs selected chatgpt provider")
    imports = {}
    for path in args.import_file:
        payload = load_json(Path(path))
        provider = payload["provider"]
        require(provider in {"reddit", "tiktok"}, "Imports support reddit and tiktok only")
        require(provider in run["providers"], "Import supplied for an unselected provider")
        require(provider not in imports, "Supply one combined import envelope per provider")
        imports[provider] = payload
    require(sum(item["collection"]["external_calls"] for item in imports.values()) <= 10,
            "Imports exceed the total 10 external-call run budget")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    require(not any(out.iterdir()), "Output directory must be empty; choose a fresh run directory")
    sources = []
    for provider in run["providers"]:
        source = source_result(provider, run)
        try:
            if provider == "chatgpt":
                source = collect_signals(run, args, out, source)
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
    return {**analysis, "status": "complete", "method": "calling_agent_analysis_not_independently_verified"}


def finalize(args):
    out = Path(args.run)
    result = load_json(out / "results.json")
    require(result.get("schema_version") == VERSION, "Unsupported results schema_version")
    result["analysis"] = validate_analysis(load_json(Path(args.analysis)), result)
    save_run(out, result)
    print(f"Finalized {out.resolve() / 'report.md'} (no collection/network requests)")


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    command = commands.add_parser("collect", help="Collect public Signals and/or permitted normalized imports")
    command.add_argument("--providers", default=",".join(PROVIDERS))
    command.add_argument("--days", type=int)
    command.add_argument("--start", help="Local ISO date or timestamp with offset")
    command.add_argument("--end", help="Exclusive local ISO date or timestamp with offset")
    command.add_argument("--timezone", help="Caller IANA zone; disclosed UTC fallback if omitted")
    for name in ("topic", "region", "language", "request", "as-of", "signals-file"):
        command.add_argument("--" + name)
    command.add_argument("--import-file", action="append", default=[])
    command.add_argument("--offline", action="store_true")
    command.add_argument("--max-records", type=int, default=100)
    command.add_argument("--out", required=True, help="Fresh/empty output directory")
    command = commands.add_parser("finalize", help="Validate calling-agent analysis and render; no network")
    command.add_argument("--run", required=True)
    command.add_argument("--analysis", required=True)
    return root


def main():
    root = parser()
    args = root.parse_args()
    try:
        collect(args) if args.command == "collect" else finalize(args)
    except (ValueError, KeyError, TypeError, OSError, ZoneInfoNotFoundError) as error:
        # Do not echo source payloads or local credential-bearing paths on failure.
        message = str(error) if isinstance(error, ValueError) else type(error).__name__
        root.exit(2, f"niche-hunter: {message}\n")


if __name__ == "__main__":
    main()
