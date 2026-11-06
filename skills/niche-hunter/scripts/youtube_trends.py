"""Offline Google Trends YouTube Search normalization; no credentials or network."""

import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime, time, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from research import MAX_BYTES, UTC, VERSION, iso, require, secure_url, timestamp, validate_window, window


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


def query_url(query, period, region=None, category=0):
    end = timestamp(period["end_at"]) - timedelta(microseconds=1)
    args = {"q": query, "gprop": "youtube", "date": timestamp(period["start_at"]).strftime("%Y-%m-%d") + " " + end.strftime("%Y-%m-%d")}
    if region:
        args["geo"] = region
    if category:
        args["cat"] = str(category)
    return "https://trends.google.com/trends/explore?" + urlencode(args)


def trends_window(requested, now=None):
    """Trends date ranges are inclusive UTC dates; disclose expanded sub-day bounds."""
    start = datetime.combine(timestamp(requested["start_at"]).date(), time(), UTC)
    end = datetime.combine((timestamp(requested["end_at"]) - timedelta(microseconds=1)).date(), time(), UTC) + timedelta(days=1)
    if now is not None:
        end = min(end, datetime.combine(now.date(), time(), UTC))
        if start >= end:
            start = end - timedelta(days=1)
    return window(start, end)


def csv_queries(text):
    """Read the native combined TOP/RISING related-queries CSV, preserving quoted commas."""
    result, section = {"top": [], "rising": []}, None
    for row in csv.reader(io.StringIO(text.lstrip("\ufeff"))):
        require(len(result["top"]) + len(result["rising"]) <= 1000, "Trends export exceeds the row cap")
        if not row or not any(value.strip() for value in row):
            continue
        if len(row) == 1 and row[0].strip().upper() in {"TOP", "RISING"}:
            section = row[0].strip().lower()
            continue
        if section and len(row) >= 2:
            if len(row) == 3 and row[0].strip().isdigit():
                row = row[1:]
            require(len(row) == 2, "Unsupported related-query CSV columns")
            query, value = row[0].strip(), row[1].strip()
            if query.casefold() == "query" and value.casefold() in {"value", "index", "score"}:
                continue
            if query and value:
                result[section].append({"query": query, "value": value})
    require(section is not None, "Use a native related-queries CSV with TOP/RISING sections; other charts are unsupported")
    return result


def load_manifest(path):
    require(path.stat().st_size <= MAX_BYTES, "Trends manifest exceeds the size cap")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(manifest, dict) and manifest.get("schema_version") == VERSION and manifest.get("property") == "youtube",
            "Trends manifest must explicitly describe YouTube Search, not Web Search or Trending Now")
    require(isinstance(manifest.get("scopes"), list) and len(manifest["scopes"]) <= 20,
            "Trends manifest needs at most twenty scopes")
    for scope in manifest["scopes"]:
        require(isinstance(scope, dict), "Invalid Trends scope")
        scope.setdefault("property", manifest["property"])
        if "csv_file" in scope:
            relative = Path(scope["csv_file"])
            target = (path.parent / relative).resolve()
            require(not relative.is_absolute() and target.is_relative_to(path.parent.resolve())
                    and target.suffix.lower() == ".csv", "CSV must be a relative file inside the manifest directory")
            require(target.stat().st_size <= MAX_BYTES, "Trends CSV exceeds the size cap")
            scope["related_queries"] = csv_queries(target.read_text(encoding="utf-8"))
            scope["delivery"] = "google_trends_csv"
    return manifest


def numeric(value):
    if type(value) in (int, float):
        require(math.isfinite(value), "Trends values must be finite")
        return value
    if isinstance(value, str) and re.fullmatch(r"\+?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?%?", value.strip()):
        return float(value.strip().replace(",", "").replace("%", ""))
    return None


def metric(name, value, unit, kind, period, group, methodology, missing=None):
    result = {"name": name, "value": value, "unit": unit, "kind": kind, "window": dict(period),
              "comparison_group": group, "methodology": methodology}
    if value is None:
        result["missing_reason"] = missing or "The source did not provide a numeric value"
    return result


def normalize_scopes(scopes, now):
    require(isinstance(scopes, list) and len(scopes) <= 20, "Need bounded Trends scopes")
    records, scope_receipts = {}, []
    for scope in scopes:
        require(isinstance(scope, dict) and scope.get("property") == "youtube", "Trends property must be youtube")
        period = scope["actual_window"]
        validate_window(period)
        require(period["start_at"] and period["end_at"] and period["semantics"] == "calendar",
                "Trends needs actual calendar coverage, not an invented requested interval")
        require(period["timezone"] == "UTC" and all(timestamp(period[key]).time() == time() for key in ("start_at", "end_at")),
                "Trends dates must describe whole UTC dates; keep the comment window separately")
        require(timestamp(period["end_at"]) <= now, "Trends actual coverage must not include future data")
        retrieved = scope["retrieved_at"]
        require(timestamp(retrieved) <= now, "Trends retrieval cannot be in the future")
        seed = scope.get("seed")
        require(isinstance(seed, str) and 0 < len(seed.strip()) <= 100, "Each Trends scope needs its seed")
        region, category = scope.get("region"), scope.get("category", 0)
        require(region is None or isinstance(region, str), "Invalid Trends region")
        require(type(category) is int and category >= 0, "Invalid Trends category")
        source = scope.get("source_url") or query_url(seed, period, region, category)
        secure_url(source, "youtube")
        require(source.startswith("https://trends.google.com/trends/explore?"), "Trends needs its public Explore link")
        require(parse_qs(urlsplit(source).query) == parse_qs(urlsplit(query_url(seed, period, region, category)).query),
                "Trends source link must match its seed, property, dates, region and category")
        data = scope.get("related_queries")
        require(isinstance(data, dict) and any(key in data for key in ("top", "rising")), "Unknown related-queries schema")
        group = "trends_scope:" + digest([seed.casefold(), region, category, period])
        duration = timestamp(period["end_at"]) - timestamp(period["start_at"])
        baseline = window(timestamp(period["start_at"]) - duration, timestamp(period["start_at"]))
        delivery = scope.get("delivery", "caller_export")
        require(delivery in {"serpapi", "google_trends_csv", "caller_export", "synthetic_fixture"}, "Unknown Trends delivery")
        scope_receipts.append({"id": group, "seed": seed, "property": "youtube", "actual_window": period,
            "baseline_window": baseline, "region": region, "category": category, "source_url": source,
            "retrieved_at": retrieved, "delivery": delivery})
        for kind in ("rising", "top"):
            items = data.get(kind, [])
            require(isinstance(items, list) and len(items) <= 1000, "Related queries must be a bounded list")
            for position, item in enumerate(items):
                require(isinstance(item, dict) and isinstance(item.get("query"), str)
                        and 0 < len(item["query"].strip()) <= 300, "Invalid related query")
                query = item["query"].strip()
                source_id = "trends_query:" + digest([group, query.casefold()])
                require(len(records) < 5000 or source_id in records, "Too many distinct Trends queries")
                record = records.setdefault(source_id, {"source_id": source_id, "query": query, "scope_id": group,
                    "seed": seed, "url": source, "retrieved_at": retrieved,
                    "measurements": [], "labels": {}, "positions": {}})
                require(record["retrieved_at"] == retrieved, "Combine repeated scope snapshots separately before normalization")
                raw = item.get("value")
                require(raw is None or type(raw) in (str, int, float), "Invalid Trends label type")
                label = str(raw) if raw is not None else "Unknown"
                record["labels"][kind] = label
                record["positions"][kind] = position
                value = numeric(raw)
                if kind == "top":
                    value = value if value is not None else numeric(item.get("extracted_value"))
                    require(value is None or 0 <= value <= 100, "Top values are normalized indices in [0,100]")
                    measurement = metric("trends_top_index", value, "relative_index_0_100", "index", period, group,
                        "Google Trends Top index within this exact seed/window/region. Not a search count or comparable across independently scaled scopes.")
                elif label.casefold() == "breakout":
                    measurement = metric("trends_breakout_lower_bound", 5000, "percent", "range_lower", period, group,
                        "Google Trends Breakout means growth greater than 5000%; no exact growth or volume is asserted.")
                else:
                    # Unknown/localized text labels remain unknown even if a supplier guesses a number.
                    require(value is None or value >= 0, "Rising growth cannot be negative")
                    measurement = metric("trends_growth_percent", value, "percent", "derived", period, group,
                        "Source-reported increase against the preceding comparable period, not growth computed from independently scaled indices.",
                        "Unparsed/missing source growth label; retained in provenance")
                previous = next((m for m in record["measurements"] if m["name"] == measurement["name"]), None)
                require(previous is None or previous == measurement, "Conflicting duplicate Trends values")
                if previous is None:
                    record["measurements"].append(measurement)
    return list(records.values()), scope_receipts


def select_queries(records, limit):
    """Round-robin scopes; ranks and normalized values from different scopes are not merged."""
    groups = {}
    for row in records:
        groups.setdefault(row["scope_id"], []).append(row)
    for values in groups.values():
        values.sort(key=lambda row: ("rising" not in row["positions"],
                                     row["positions"].get("rising", row["positions"].get("top", 0))))
    selected, seen = [], set()
    while len(selected) < limit and any(groups.values()):
        for values in groups.values():
            while values and values[0]["query"].casefold() in seen:
                values.pop(0)
            if values and len(selected) < limit:
                row = values.pop(0)
                selected.append(row)
                seen.add(row["query"].casefold())
    return selected
