#!/usr/bin/env python3
"""Normalize bounded TokConnect MCP search captures; no network or credentials."""

import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from research import (FAILURES, MAX_BYTES, UTC, VERSION, require,
                      text_field, timestamp, validate_window)

DOCS = "https://tokconnect.com/docs/api/demand/"
METHODS = {"demand_find_topics": {"search", "feed", "trending"},
           "demand_topic": {"detail", "related"}, "demand_keywords": {"tiktok"}}
ERRORS = {401: "auth_required", 402: "rate_limited", 403: "not_supported",
          429: "rate_limited"}
UNKNOWN_WINDOW = {"start_at": None, "end_at": None, "timezone": "unknown", "semantics": "unknown"}
REASONS = {"unconfigured": "TokConnect is not connected; run TikTok setup in the calling client.",
           "auth_required": "TokConnect browser authorization is required or expired.",
           "rate_limited": "TokConnect credits or rate limits stopped collection; no automatic upgrade or retry.",
           "not_supported": "The account or tool cannot serve this request; no paid upgrade was attempted.",
           "usage_terms_unconfirmed": "Legacy capture status; a terms link is not required for local TikTok processing.",
           "unavailable": "TokConnect returned an error or unsupported response; inspect the live schema."}


def unwrap(response):
    require(isinstance(response, dict), "Tool response must be a JSON object")
    if "jsonrpc" in response:
        require("result" in response and "error" not in response, "MCP protocol error")
        response = response["result"]
    require(isinstance(response, dict) and not response.get("isError"), "MCP tool error")
    if response.get("structuredContent") is not None:
        response = response["structuredContent"]
    elif "content" in response:
        blocks = response["content"]
        require(isinstance(blocks, list) and all(isinstance(block, dict) for block in blocks),
                "MCP content must be an array of blocks")
        texts = [block["text"] for block in blocks if block.get("type") == "text"]
        require(len(texts) == 1, "Need one JSON tool result; prose and mixed results are unsupported")
        response = json.loads(texts[0])
    require(isinstance(response, dict) and "error" not in response, "Tool returned an error")
    data = response.get("data", response)
    require(isinstance(data, dict), "Compact tool data must be an object")
    return data


def metric(name, value, unit, kind, period, methodology):
    require(value is None or type(value) in (int, float) and math.isfinite(value) and value >= 0,
            "Supplier metric must be finite, nonnegative, or null")
    result = {"name": name, "value": value, "unit": unit, "kind": kind,
              "window": dict(period), "methodology": methodology}
    if value is None:
        result["missing_reason"] = "Not supplied by this tool response"
    return result


def normalize(capture, now=None):
    now = now or datetime.now(UTC)
    require(isinstance(capture, dict), "Capture must be an object")
    require(capture.get("schema_version") == VERSION, "Unsupported capture schema_version")
    calls = capture.get("calls")
    require(isinstance(calls, list) and len(calls) <= 10, "Capture needs at most 10 tool calls")
    total = capture.get("external_calls")
    require(type(total) is int and len(calls) <= total <= 10, "External calls must include all attempts, at most 10")
    require(capture.get("new_paid_spending_usd") == 0, "Free pilot permits no new paid spending")
    output = {"schema_version": VERSION, "provider": "tiktok", "adapter": "tokconnect_mcp_search_v1",
              "status": "partial", "reason": "Sampled TokConnect search signals; seven-day popularity is a supplier claim, with exact coverage shown separately.",
              "collection": {"external_calls": total, "new_paid_spending_usd": 0, "calls": []},
              "observations": []}
    status = capture.get("status")
    if status in FAILURES:
        require(not calls, "Failure-only captures must not contain tool responses")
        output.update(status=status, reason=REASONS[status])
        return output
    require(status is None, "Use a documented failure status or omit status")
    balance = capture.get("free_credits_before")
    require(type(balance) is int and balance >= total, "Verify enough free credits before all external attempts")
    output["collection"]["free_credits_before"] = balance
    # Optional source metadata is not a prerequisite for caller-directed local processing.
    rights = capture.get("rights")
    if isinstance(rights, dict):
        output["rights"] = {key: rights[key] for key in ("storage_permitted", "basis", "reference")
                            if key in rights and type(rights[key]) in (str, bool)}
    topic = capture.get("topic")
    require(topic is None or isinstance(topic, str) and topic.strip(), "Topic must be nonempty text or null")
    if topic:
        require(capture.get("topic_relevance_checked") is True,
                "Caller must check each retained observation's relevance to the requested topic")
    output["effective_filters"] = {"topic": topic, "region": None, "language": None}
    output["actual_window"] = dict(capture.get("actual_window", UNKNOWN_WINDOW))
    validate_window(output["actual_window"])
    output["limitations"] = [
        "Third-party supplier claims; metric accuracy, literal-query identity and completeness are not independently verified.",
        "Search topics may pool multiple typed phrases; no topic is automatically classified as a literal typed search.",
        "searchVolume is supplier-reported seven-day search popularity, not verified exact query counts or monthly volume.",
        "Exact metric bounds and freshness stay unknown unless established from the response; retrieval time is not a measurement boundary.",
        "Region and content-language filters are not verified by this adapter and remain unsupported.",
        "Autocomplete is a current recommendation snapshot, not observed search volume or proof of a recurring need.",
        "No baseline growth or independent user counts are computed; trend7d readings are not summed."]
    rows, series, failures = {}, {}, []
    for call in calls:
        require(isinstance(call, dict), "Captured calls must be objects")
        callable_tool, arguments = call.get("tool"), call.get("arguments")
        tool = callable_tool
        if isinstance(tool, str) and re.fullmatch(r"mcp__[A-Za-z0-9_-]+__[A-Za-z0-9_]+", tool):
            tool = tool.rsplit("__", 1)[1]
        require(isinstance(tool, str) and tool in METHODS and isinstance(arguments, dict), "Unsupported search tool or missing arguments")
        method = arguments.get("method")
        require(method in METHODS[tool], "Unsupported search tool method")
        retrieved = call.get("retrieved_at")
        require(isinstance(retrieved, str) and timestamp(retrieved) <= now, "Need actual non-future tool retrieval time")
        # No headers, arbitrary input fields, raw errors, or response bodies enter the output receipt.
        receipt = {"tool": tool, "method": method, "retrieved_at": retrieved, "status": "partial"}
        if callable_tool != tool:
            receipt["callable_tool"] = callable_tool
        receipt["arguments"] = {key: value for key, value in arguments.items()
                                if key in {"method", "keyword", "id", "limit", "channel", "category", "language"}
                                and type(value) in (str, int)}
        receipt["cursor_supplied"] = bool(arguments.get("cursor"))
        output["collection"]["calls"].append(receipt)
        http_status = call.get("http_status", 200)
        require(type(http_status) is int and 200 <= http_status <= 599, "http_status must be an actual HTTP status")
        if http_status >= 400:
            failure = ERRORS.get(call["http_status"], "unavailable")
            receipt["status"] = failure
            failures.append(failure)
            continue
        try:
            data = unwrap(call["response"])
        except (ValueError, KeyError, TypeError):
            receipt["status"] = "unavailable"
            failures.append("unavailable")
            continue
        if tool == "demand_keywords":
            require(isinstance(data.get("suggestions"), list), "Unknown autocomplete schema")
            candidates = data["suggestions"]
        elif tool == "demand_topic" and method == "detail":
            require(isinstance(data.get("topic"), dict), "Unknown topic detail schema")
            candidates = [data["topic"]]
        else:
            require(isinstance(data.get("topics"), list), "Unknown search topic schema")
            candidates = data["topics"]
        require(len(candidates) <= 100, "Response exceeds bounded page size")
        selected = call.get("selected_ids")
        require(selected is None or isinstance(selected, list) and all(isinstance(value, str) for value in selected),
                "selected_ids must be an array of source IDs")
        if topic:
            require(selected is not None, "Topic-scoped calls need explicitly reviewed selected_ids")
        period = dict(call.get("measurement_window", UNKNOWN_WINDOW))
        validate_window(period)
        receipt.update(status="ok", returned=len(candidates), retained=0)
        has_more = data.get("hasMore")
        require(has_more is None or type(has_more) is bool, "hasMore must be boolean when present")
        receipt["pagination_complete"] = has_more is False
        receipt["has_more"] = has_more
        # Cursors are opaque paging values, not evidence URLs; don't persist them by default.
        if has_more is not False and not (tool == "demand_topic" and method == "detail"):
            output["limitations"].append("Pagination is incomplete or unknown for at least one sampled call.")
        seen = set()
        for item in candidates:
            autocomplete = tool == "demand_keywords"
            if autocomplete and isinstance(item, str):
                item = {"text": item}
            require(isinstance(item, dict), "Search records must be objects or autocomplete strings")
            text_field(item, "text" if autocomplete else "queryText")
            title = item["text" if autocomplete else "queryText"]
            if autocomplete:
                source_id = "keyword:" + hashlib.sha256(title.strip().casefold().encode()).hexdigest()[:24]
            else:
                text_field(item, "queryId")
                source_id = item["queryId"]
            seen.add(source_id)
            if selected is not None and source_id not in selected:
                continue
            if source_id in rows and timestamp(rows[source_id]["retrieved_at"]) > timestamp(retrieved):
                continue
            if source_id not in rows and len(rows) >= 100:
                output["limitations"].append("The adapter's 100-record cap excluded additional observations.")
                continue
            snapshot = {**UNKNOWN_WINDOW, "semantics": "snapshot"}
            measurements = [] if autocomplete else [
                metric("searchVolume", item.get("searchVolume"), "supplier_search_popularity", "estimate", period,
                       "TokConnect claims seven-day topic popularity; exact query identity/count semantics are unverified."),
                metric("popularity", item.get("popularity"), "supplier_index", "index", snapshot,
                       "Supplier index; scale and measurement time unverified."),
                metric("videoCount", item.get("videoCount"), "matched_videos", "count", snapshot,
                       "Supplier-reported matched-video snapshot, not historical uploads or complete supply.")]
            rows[source_id] = {"source_id": source_id,
                "url": DOCS if autocomplete else "https://api.tokconnect.com/v1/searches/" + quote(source_id, safe=""), "title": title,
                "summary": "Supplier autocomplete recommendation." if autocomplete else "Supplier search topic; literal typed-query identity is unverified.",
                "topic_terms": [topic] if topic else [],
                "signal_type": "recommended_keyword" if autocomplete else "unknown",
                "quality": "provider_claim_unverified", "published_at": None,
                "metric_observed_at": None, "retrieved_at": retrieved,
                "limitations": ["Source URL is the documented supplier method/entity endpoint; access may require authorization.",
                                "Publication and metric observation timestamps are not supplied by compact search responses."],
                "measurements": measurements}
            category = item.get("category")
            if isinstance(category, str) and category.strip():
                rows[source_id]["summary"] += " Supplier category: " + category
            trend = item.get("trend7d")
            if trend is not None:
                require(isinstance(trend, list) and len(trend) <= 31 and
                        all(value is None or type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in trend),
                        "Unsupported trend7d readings")
                series[source_id] = {"source_id": source_id, "values": trend,
                                     "timestamps": None, "semantics": "unverified_supplier_readings_not_daily_counts"}
            else:
                series.pop(source_id, None)
            receipt["retained"] += 1
        if selected is not None:
            require(set(selected) <= seen, "selected_ids references a record absent from this response")
    output["collection"]["supplier_trend_readings"] = list(series.values())
    output["observations"] = list(rows.values())
    output["limitations"] = list(dict.fromkeys(output["limitations"]))
    if failures:
        output["limitations"].extend(REASONS[value] for value in dict.fromkeys(failures))
        if not rows:
            output.update(status=failures[0], reason=REASONS[failures[0]])
    elif not calls:
        output.update(status="unconfigured", reason=REASONS["unconfigured"])
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Permitted MCP capture JSON")
    parser.add_argument("--out", required=True, help="New normalized import file")
    args = parser.parse_args()
    try:
        source, out = Path(args.input), Path(args.out)
        require(source.stat().st_size <= MAX_BYTES, "Capture exceeds 10 MiB limit")
        output = normalize(json.loads(source.read_text(encoding="utf-8")))
        with out.open("x", encoding="utf-8") as target:
            target.write(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"provider": "tiktok", "status": output["status"], "observations": len(output["observations"])}))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"tiktok adapter: invalid capture ({type(error).__name__}); check the documented contract.\n")


if __name__ == "__main__":
    main()
