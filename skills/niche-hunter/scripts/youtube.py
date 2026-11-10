#!/usr/bin/env python3
"""Bounded YouTube Search Trends -> videos -> dated comments -> normalized evidence."""

import csv
import getpass
import json
import math
import os
import re
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from research import (CATALOG, FAILURES, MAX_BYTES, SKILL_DIR, UTC, VERSION, iso, parameters,
                      parser as research_parser, require, timestamp, validate_window, window)
from setup_access import PACKAGE, SetupParser, read_config, write_config
from youtube_trends import (digest, load_manifest, metric, normalize_scopes, query_url,
                            select_queries, trends_window)

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
COMMENT_ID = re.compile(r"[A-Za-z0-9_.-]{1,200}")
SNAPSHOT = {"start_at": None, "end_at": None, "timezone": "unknown", "semantics": "snapshot"}
METHODS = {"serpapi": {"related_queries"}, "youtube": {"search", "commentThreads", "comments"}}


def credential_path():
    directory = Path(os.environ.get("NICHE_HUNTER_CONFIG_DIR", Path.home() / ".config/niche-hunter"))
    return directory / "youtube.json"


def credentials():
    raw = read_config(credential_path())
    stored = json.loads(raw) if raw else {}
    require(isinstance(stored, dict), "Invalid private YouTube settings")
    return {"youtube_api_key": os.environ.get("YOUTUBE_API_KEY") or stored.get("youtube_api_key"),
            "serpapi_api_key": os.environ.get("SERPAPI_API_KEY") or stored.get("serpapi_api_key")}


def prepare_output(value):
    path = Path(value)
    require(not path.exists(), "Choose a fresh import/capture output path")
    resolved = path.resolve()
    require(not resolved.is_relative_to(SKILL_DIR.resolve()), "Keep outputs outside the skill directory")
    if not (PACKAGE / ".git").exists():
        require(not resolved.is_relative_to(PACKAGE.resolve()), "Keep outputs outside the installed plugin package")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def setup(args):
    path = credential_path()
    original = read_config(path)
    if args.remove:
        require(original is not None, "No private YouTube settings exist")
        # Atomic empty settings remove the keys without deleting unrelated paths.
        write_config(path, original, "{}\n")
        print("Local YouTube keys removed. Provider keys were not revoked.")
        return
    require(original is None or original.strip() == b"{}" or args.replace,
            "YouTube settings already exist; reuse them or use --replace")
    require(sys.stdin.isatty(), "Run setup yourself in an interactive terminal; never send keys in chat or stdin")
    data = {}
    print("Keys stay in private plaintext settings with owner-only POSIX permissions. No network calls are made.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        for key, label in (("youtube_api_key", "YouTube Data API key"), ("serpapi_api_key", "SerpApi key for Google Trends")):
            if key == "serpapi_api_key" and args.csv_only:
                continue
            value = getpass.getpass(label + " (hidden): ")
            require(bool(re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", value)), "Enter only the key without spaces or a prefix")
            data[key] = value
    write_config(path, original, json.dumps(data, indent=2) + "\n")
    print("YouTube settings saved. Authentication and allowances are not verified by saving keys.")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


class Network:
    """Count attempts before I/O; never persist request URLs, keys or raw errors."""

    def __init__(self, keys, maximum, free_trends_calls, existing_calls=0, transport=None, clock=None):
        require(type(maximum) is int and 1 <= maximum <= 10 and type(existing_calls) is int
                and 0 <= existing_calls <= maximum and type(free_trends_calls) is int and free_trends_calls >= 0,
                "Invalid network budget")
        self.keys, self.maximum, self.free_trends_calls = keys, maximum, free_trends_calls
        self.existing_calls, self.calls, self.stops = existing_calls, [], []
        self.transport = transport or build_opener(NoRedirect()).open
        self.clock = clock or (lambda: datetime.now(UTC))
        self.blocked = set()

    @property
    def used(self):
        return self.existing_calls + len(self.calls)

    def available(self, service):
        return self.used < self.maximum and service not in self.blocked and (
            service != "serpapi" or sum(row["service"] == "serpapi" for row in self.calls) < self.free_trends_calls)

    def request(self, service, method, arguments):
        require(service in METHODS and method in METHODS[service], "Unsupported network method")
        if not self.available(service):
            self.stops.append("Run budget, confirmed free allowance, or an earlier access failure stopped " + service)
            return None, None
        receipt = {"service": service, "method": method, "retrieved_at": iso(self.clock()), "status": "unavailable"}
        self.calls.append(receipt)
        args = dict(arguments)
        if service == "serpapi":
            args["api_key"] = self.keys["serpapi_api_key"]
            endpoint = "https://serpapi.com/search.json"
        else:
            args["key"] = self.keys["youtube_api_key"]
            endpoint = "https://www.googleapis.com/youtube/v3/" + method
        request = Request(endpoint + "?" + urlencode(args), headers={"User-Agent": "NicheHunter/YouTube-v1", "Accept": "application/json"})
        try:
            with self.transport(request, timeout=20) as response:
                raw = response.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, "Provider response exceeded the size cap")
            data = json.loads(raw)
            require(isinstance(data, dict), "Provider response must be an object")
            receipt["retrieved_at"] = iso(self.clock())
            if "error" in data:
                receipt["status"] = "unavailable"
                self.blocked.add(service)
                return None, receipt
            if service == "youtube":
                require(isinstance(data.get("items"), list) and len(data["items"]) <= 100,
                        "Unknown or excessive YouTube result page")
            receipt["status"] = "ok"
            receipt["pagination_complete"] = not bool(data.get("nextPageToken"))
            if service == "youtube":
                receipt["returned"] = len(data["items"])
            else:
                # SerpApi delivers Trends rows under related_queries, not a YouTube-style items page.
                related = data.get("related_queries")
                related = related if isinstance(related, dict) else {}
                receipt["returned"] = sum(len(related[kind]) for kind in ("top", "rising")
                                          if isinstance(related.get(kind), list))
            return data, receipt
        except HTTPError as error:
            code, reason = error.code, None
            try:
                body = json.loads(error.read(MAX_BYTES))
                reasons = body.get("error", {}).get("errors", [])
                reason = reasons[0].get("reason") if reasons else None
            except (ValueError, AttributeError, TypeError):
                pass
            finally:
                error.close()
            reason = reason if isinstance(reason, str) else None
            status = "auth_required" if code == 401 or reason in {"keyInvalid", "authError"} else "unavailable"
            if code in {402, 429} or reason in {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}:
                status = "rate_limited"
            elif code == 403 and status != "auth_required":
                status = "not_supported"
            receipt.update(http_status=code, status=status)
            if reason in {"commentsDisabled", "videoNotFound", "commentNotFound"}:
                receipt["reason"] = reason
            else:
                self.blocked.add(service)
            return None, receipt
        except (URLError, TimeoutError, OSError, ValueError, TypeError):
            self.blocked.add(service)
            return None, receipt


def clean_comment(item, video_id, retrieved):
    require(isinstance(item, dict) and isinstance(item.get("snippet"), dict), "Unknown comment schema")
    snippet, comment_id = item["snippet"], item.get("id")
    require(isinstance(comment_id, str) and COMMENT_ID.fullmatch(comment_id), "Invalid comment ID")
    text = snippet.get("textDisplay")
    require(isinstance(text, str), "Comment text is missing")
    likes = snippet.get("likeCount")
    require(likes is None or type(likes) is int and likes >= 0, "Invalid comment like count")
    return {"id": comment_id, "video_id": video_id, "parent_id": snippet.get("parentId"),
            "text": text.encode("utf-8")[:2000].decode("utf-8", errors="ignore"), "like_count": likes, "published_at": snippet.get("publishedAt"),
            "updated_at": snippet.get("updatedAt"), "retrieved_at": retrieved}


def choose_videos(searches, maximum):
    groups, channels, selected, seen = list(searches), set(), [], set()
    # Prefer different creators while keeping at least one candidate from each query.
    for allow_repeat in (False, True):
        for query_id, items in groups:
            for item in items:
                if len(selected) >= maximum:
                    break
                if not isinstance(item, dict) or not isinstance(item.get("id"), dict):
                    continue
                video_id = item["id"].get("videoId")
                snippet = item.get("snippet", {})
                if not isinstance(snippet, dict):
                    continue
                if not isinstance(video_id, str) or not VIDEO_ID.fullmatch(video_id):
                    continue
                if video_id in seen:
                    existing = next(row for row in selected if row["video_id"] == video_id)
                    if query_id not in existing["query_ids"]:
                        existing["query_ids"].append(query_id)
                    continue
                channel = snippet.get("channelId")
                if not allow_repeat and channel in channels:
                    continue
                if not isinstance(snippet.get("title"), str):
                    continue
                selected.append({"video_id": video_id, "title": snippet["title"][:300],
                    "channel_id": channel if isinstance(channel, str) else None,
                    "published_at": snippet.get("publishedAt"), "query_ids": [query_id],
                    "retrieved_at": item.get("_retrieved_at")})
                seen.add(video_id)
                channels.add(channel)
                break
    for query_id, items in groups:
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), dict):
                continue
            for row in selected:
                if row["video_id"] == item["id"].get("videoId") and query_id not in row["query_ids"]:
                    row["query_ids"].append(query_id)
    return selected


def collect_capture(run, args, keys, network=None, now=None):
    now = now or datetime.now(UTC)
    require(1 <= args.max_calls <= 10 and 1 <= args.max_queries <= 5 and 1 <= args.max_videos <= 5,
            "Use 1..10 calls, 1..5 queries and 1..5 videos")
    require(isinstance(keys.get("youtube_api_key"), str) and keys["youtube_api_key"], "YouTube API key is missing; complete setup")
    imported = load_manifest(Path(args.trends_file)) if args.trends_file else None
    existing = imported.get("external_calls", 0) if imported else 0
    require(type(existing) is int and 0 <= existing <= args.max_calls, "Invalid imported call accounting")
    if imported is None:
        require(keys.get("serpapi_api_key"), "SerpApi key is missing; supply Trends exports or complete setup")
        require(type(args.free_trends_calls) is int and args.free_trends_calls > 0,
                "Confirm remaining free SerpApi searches with --free-trends-calls; no paid searches are assumed")
    net = network or Network(keys, args.max_calls, args.free_trends_calls or 0, existing)
    scopes = imported["scopes"] if imported else []
    # Reject malformed exports before a single video/comment request is made.
    if imported is not None:
        normalize_scopes(scopes, now)
        if run["topic"]:
            require(all(scope["seed"].strip().casefold() == run["topic"].strip().casefold() for scope in scopes),
                    "Topic-scoped CSV imports must use the same topic seed; keep broader exports in a broad run")
    seeds = args.seed or ([run["topic"]] if run["topic"] else [row["youtube"][0] for row in CATALOG["categories"]])
    require(all(isinstance(seed, str) and 0 < len(seed.strip()) <= 100 and "," not in seed for seed in seeds),
            "Each seed must be a single nonempty Trends term, at most 100 characters")
    period = trends_window(run["requested_window"], now)
    if imported is None:
        # Preserve room for at least one video search and one comment page when possible.
        seed_limit = min(args.max_trends_calls, args.free_trends_calls, max(1, args.max_calls - net.used - 2))
        for seed in seeds[:seed_limit]:
            params = {"engine": "google_trends", "data_type": "RELATED_QUERIES", "q": seed,
                      "gprop": "youtube", "tz": 0}
            # Construct API dates directly rather than reusing URL-encoded link parameters.
            params["date"] = timestamp(period["start_at"]).strftime("%Y-%m-%d") + " " + (
                timestamp(period["end_at"]) - timedelta(microseconds=1)).strftime("%Y-%m-%d")
            if run["region"]:
                params["geo"] = run["region"]
            if run["language"]:
                params["hl"] = run["language"]
            response, receipt = net.request("serpapi", "related_queries", params)
            if response is None:
                continue
            echo = response.get("search_parameters", {})
            candidate = {"property": "youtube", "seed": seed, "region": run["region"], "category": 0,
                "actual_window": period, "retrieved_at": receipt["retrieved_at"], "delivery": "serpapi",
                "related_queries": response.get("related_queries")}
            try:
                require(echo.get("gprop") == "youtube" and echo.get("data_type") == "RELATED_QUERIES"
                        and echo.get("q") == seed and echo.get("date") == params["date"], "Trends scope mismatch")
                normalize_scopes([candidate], max(now, net.clock()))
                scopes.append(candidate)
            except (ValueError, KeyError, TypeError):
                receipt["status"] = "unavailable"
                net.blocked.add("serpapi")
    queries, scope_receipts = normalize_scopes(scopes, max(now, net.clock()))
    query_limit = min(args.max_queries, max(1, (args.max_calls - net.used) // 2))
    selected = select_queries(queries, query_limit)
    if args.select_query:
        selected = [row for row in queries if row["source_id"] in args.select_query]
        require(set(args.select_query) == {row["source_id"] for row in selected}, "Selected query is absent from Trends")
        selected = selected[:query_limit]
    searches = []
    for query in selected:
        response, receipt = net.request("youtube", "search", {"part": "snippet", "type": "video", "q": query["query"],
            "maxResults": 10, "order": "relevance"})
        if response is not None:
            require(isinstance(response.get("items"), list), "Unknown video search schema")
            searches.append((query["source_id"], [{**item, "_retrieved_at": receipt["retrieved_at"]}
                for item in response["items"] if isinstance(item, dict)]))
    video_limit = min(args.max_videos, max(1, args.max_calls - net.used))
    videos = choose_videos(searches, video_limit)
    comments, thread_heads, paging, disabled = [], {}, [], set()
    candidate_limit_reached = False

    def store_comment(item, video_id, retrieved):
        nonlocal candidate_limit_reached
        if len(comments) >= 3000:
            candidate_limit_reached = True
            net.blocked.add("youtube")
            return None
        comment = clean_comment(item, video_id, retrieved)
        comments.append(comment)
        return comment

    for order in ("time", "relevance"):
        for video_index, video in enumerate(videos):
            if video["video_id"] in disabled:
                continue
            if not net.available("youtube"):
                break
            token = None
            for page_index in range(args.pages_per_video if order == "time" else 1):
                if page_index > 0 and net.maximum - net.used <= len(videos) - video_index - 1:
                    break  # Give each remaining video its first newest-comment page.
                params = {"part": "snippet,replies", "videoId": video["video_id"], "order": order,
                          "textFormat": "plainText", "maxResults": 100}
                if token:
                    params["pageToken"] = token
                response, receipt = net.request("youtube", "commentThreads", params)
                if response is None:
                    if receipt and receipt.get("reason") in {"commentsDisabled", "videoNotFound"}:
                        disabled.add(video["video_id"])
                    break
                require(isinstance(response.get("items"), list), "Unknown comment-thread schema")
                try:
                    for thread in response["items"]:
                        top = thread.get("snippet", {}).get("topLevelComment")
                        require(isinstance(top, dict), "Unknown top-level comment schema")
                        comment = store_comment(top, video["video_id"], receipt["retrieved_at"])
                        if comment is None:
                            continue
                        for reply in thread.get("replies", {}).get("comments", []):
                            store_comment(reply, video["video_id"], receipt["retrieved_at"])
                        count = thread.get("snippet", {}).get("totalReplyCount", 0)
                        if type(count) is int and count > 0:
                            inline = len(thread.get("replies", {}).get("comments", []))
                            if count > inline:
                                thread_heads[comment["id"]] = (comment, count)
                except (ValueError, KeyError, TypeError, AttributeError):
                    receipt["status"] = "unavailable"
                    net.blocked.add("youtube")
                    break
                token = response.get("nextPageToken")
                paging.append({"video_id": video["video_id"], "order": order, "complete": not bool(token)})
                if not token or not net.available("youtube"):
                    break
                dated = [item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {}).get("publishedAt")
                         for item in response["items"]]
                if order == "time" and dated and all(value and timestamp(value) < timestamp(run["requested_window"]["start_at"]) for value in dated):
                    break
    # Extra replies are sampled only after every selected video had a chance at fresh comments.
    for head, count in sorted(thread_heads.values(), key=lambda pair: (pair[0]["like_count"] is not None, pair[0]["like_count"] or 0), reverse=True):
        if not net.available("youtube"):
            break
        response, receipt = net.request("youtube", "comments", {"part": "snippet", "parentId": head["id"],
            "textFormat": "plainText", "maxResults": 100})
        if response is not None:
            try:
                for reply in response["items"]:
                    store_comment(reply, head["video_id"], receipt["retrieved_at"])
            except (ValueError, KeyError, TypeError, AttributeError):
                receipt["status"] = "unavailable"
                net.blocked.add("youtube")
            paging.append({"parent_id": head["id"], "complete": not bool(response.get("nextPageToken"))})
    safe_scopes = []
    for scope in scopes:
        safe = {key: scope[key] for key in ("property", "seed", "region", "category", "actual_window", "retrieved_at", "delivery", "source_url") if key in scope}
        safe["related_queries"] = {}
        for kind in ("top", "rising"):
            safe["related_queries"][kind] = []
            for item in scope["related_queries"].get(kind, []):
                entry = {key: item[key] for key in ("query", "value") if key in item}
                value = item.get("extracted_value")
                if type(value) in (int, float) and math.isfinite(value):
                    entry["extracted_value"] = value
                safe["related_queries"][kind].append(entry)
        safe_scopes.append(safe)
    return {"schema_version": VERSION, "requested_window": run["requested_window"], "topic": run["topic"],
        "region": run["region"], "language": run["language"], "scopes": safe_scopes,
        "selected_query_ids": [row["source_id"] for row in selected], "videos": videos, "comments": comments,
        "collection": {"external_calls": net.used, "new_paid_spending_usd": 0, "calls": net.calls,
            "imported_trends_calls": existing, "free_trends_calls_confirmed": args.free_trends_calls or 0,
            "max_calls": args.max_calls, "pagination": paging, "stops": list(dict.fromkeys(net.stops)),
            "comment_candidate_limit_reached": candidate_limit_reached,
            "catalog_seeds_total": len(seeds), "trends_scopes_collected": len(scope_receipts)}}


def safe_collection(value, now):
    require(isinstance(value, dict) and type(value.get("external_calls")) is int
            and 0 <= value["external_calls"] <= 10 and value.get("new_paid_spending_usd") == 0,
            "Collection must preserve all attempts within ten calls and zero new paid spending")
    output = {"external_calls": value["external_calls"], "new_paid_spending_usd": 0, "calls": []}
    calls = value.get("calls", [])
    require(isinstance(calls, list) and len(calls) <= value["external_calls"], "Invalid call receipts")
    for call in calls:
        require(call.get("service") in METHODS and call.get("method") in METHODS[call["service"]], "Unknown receipt method")
        require(call.get("status") in FAILURES | {"ok", "partial"}, "Unknown receipt status")
        require(timestamp(call["retrieved_at"]) <= now, "Call receipt is in the future")
        row = {key: call[key] for key in ("service", "method", "status", "retrieved_at")}
        for key in ("http_status", "returned", "pagination_complete"):
            if key in call and type(call[key]) in (int, bool):
                row[key] = call[key]
        output["calls"].append(row)
    for key in ("imported_trends_calls", "free_trends_calls_confirmed", "max_calls", "catalog_seeds_total", "trends_scopes_collected"):
        if type(value.get(key)) is int and value[key] >= 0:
            output[key] = value[key]
    # Paging identifiers are rebuilt from validated entities; raw response metadata is never copied.
    paging = value.get("pagination", [])
    require(isinstance(paging, list) and all(isinstance(item, dict) for item in paging), "Invalid paging receipts")
    output["pagination_incomplete"] = any(item.get("complete") is not True for item in paging)
    output["comment_candidate_limit_reached"] = value.get("comment_candidate_limit_reached") is True
    return output


def normalize(capture, now=None, maximum=100):
    now = now or datetime.now(UTC)
    require(isinstance(capture, dict) and capture.get("schema_version") == VERSION, "Unsupported YouTube capture")
    require(1 <= maximum <= 100, "YouTube normalization retains at most 100 observations")
    collection = safe_collection(capture["collection"], now)
    output = {"schema_version": VERSION, "provider": "youtube", "adapter": "youtube_trends_comments_v1",
        "status": "partial", "reason": "Sampled YouTube Search interest and dated comments ranked by current likes; not complete demand or a platform-wide top.",
        "collection": collection, "observations": []}
    if capture.get("status") in FAILURES:
        require(not capture.get("comments") and not capture.get("videos") and not capture.get("scopes"), "Failure capture cannot include evidence")
        output.update(status=capture["status"], reason="YouTube access is unavailable; complete the selected route or explicitly exclude it.")
        return output
    require(capture.get("status") is None, "Unknown capture status")
    period = capture["requested_window"]
    validate_window(period)
    require(period["start_at"] and timestamp(period["end_at"]) <= now, "Requested comment period must be known and not future")
    topic = capture.get("topic")
    require(topic is None or isinstance(topic, str) and topic.strip(), "Topic must be nonempty text or null")
    queries, scopes = normalize_scopes(capture.get("scopes", []), now)
    by_query = {row["source_id"]: row for row in queries}
    selected = capture.get("selected_query_ids", list(by_query))
    require(isinstance(selected, list) and set(selected) <= set(by_query) and len(selected) <= 5, "Unknown selected Trends query")
    collection["trends_scopes"] = scopes
    collection["comment_window"] = period
    collection["links"] = []
    output["effective_filters"] = {"topic": topic, "region": None, "language": None}
    periods = {json.dumps(scope["actual_window"], sort_keys=True) for scope in scopes}
    output["actual_window"] = json.loads(next(iter(periods))) if len(periods) == 1 else dict(period)
    output["limitations"] = [
        "Trends Top indices are normalized within each scope, not search volumes or comparable across independent seeds.",
        "Rising is source-reported growth; Breakout is only a greater-than-5000-percent bound, not an exact value.",
        "Comments are filtered by original publication within the requested interval; updated old comments do not become new.",
        "Likes are current API snapshots, not likes gained during the requested interval or proof of willingness to pay.",
        "The ranking covers only fetched comments on selected videos; relevance order is not like order and a global maximum is not established.",
        "Older videos are discovery context. Fresh replies on unfetched old threads and unsampled videos can be missed.",
        "Region affects Trends only; commenter geography and comment language are not inferred or guaranteed by search filters.",
        "Trend delivery, metric accuracy, permissions for additional analytics and source completeness require separate validation."]
    if any(scope["actual_window"] != period for scope in scopes):
        output["limitations"].append("Trends coverage differs from the requested comment interval; each component's actual dates are retained separately.")
    if len(scopes) < collection.get("catalog_seeds_total", len(scopes)):
        output["limitations"].append("Only a bounded subset of discovery seeds was sampled; other catalog categories were not surveyed.")
    output["limitations"].append("Retrieval time is known; upstream Trends refresh/cache age is not verified.")
    if collection["pagination_incomplete"]:
        output["limitations"].append("At least one comment/reply listing was not completely paginated.")
    if collection["comment_candidate_limit_reached"]:
        output["limitations"].append("The 3000-comment candidate cap stopped further collection before the final observation selection.")
    rows, video_queries, videos = {}, {}, {}

    def evidence(source_id, url, title, summary, signal, retrieved, published=None, measurements=None, quality="verified_official"):
        require(timestamp(retrieved) <= now, "Evidence retrieval cannot be in the future")
        if signal in {"video", "comment"}:
            require(now - timestamp(retrieved) <= timedelta(days=30), "YouTube snapshot expired; refresh or delete source data")
        return {"source_id": source_id, "url": url, "title": title[:300], "summary": summary[:2000],
            "topic_terms": [topic] if topic else [], "signal_type": signal, "quality": quality,
            "published_at": published, "retrieved_at": retrieved,
            "metric_observed_at": retrieved if signal == "comment" else None,
            "measurements": measurements or [], "limitations": []}

    for source_id in selected:
        query = by_query[source_id]
        summary = "YouTube Search query from Google Trends; source labels: " + json.dumps(query["labels"], ensure_ascii=False)
        rows[source_id] = evidence(source_id, query["url"], query["query"], summary, "typed_search", query["retrieved_at"],
            measurements=query["measurements"], quality="provider_claim_unverified")
    raw_videos = capture.get("videos", [])
    require(isinstance(raw_videos, list) and len(raw_videos) <= 50, "Too many video candidates")
    for item in raw_videos:
        video_id = item["video_id"]
        require(isinstance(video_id, str) and VIDEO_ID.fullmatch(video_id), "Invalid video ID")
        refs = item["query_ids"]
        require(isinstance(refs, list) and refs and set(refs) <= set(selected), "Video must link to selected Trends queries")
        require(isinstance(item.get("title"), str), "Video title is missing")
        published = item.get("published_at")
        require(published is None or timestamp(published) <= now, "Video publication is in the future")
        row = evidence("video:" + video_id, "https://www.youtube.com/watch?" + urlencode({"v": video_id}),
            item["title"], "Relevant video discovery context, not evidence of search volume or publication within the requested period.",
            "video", item["retrieved_at"], published)
        if video_id not in videos:
            videos[video_id] = row
            video_queries[video_id] = list(refs)
        else:
            video_queries[video_id] = list(dict.fromkeys(video_queries[video_id] + refs))
        for ref in refs:
            collection["links"].append({"query_source_id": ref, "video_source_id": row["source_id"],
                "channel_id": item.get("channel_id") if isinstance(item.get("channel_id"), str) else None})
    comments, outside, undated = {}, 0, 0
    raw_comments = capture.get("comments", [])
    require(isinstance(raw_comments, list) and len(raw_comments) <= 3000, "Too many comment candidates")
    for item in raw_comments:
        comment_id, video_id = item["id"], item["video_id"]
        require(isinstance(comment_id, str) and COMMENT_ID.fullmatch(comment_id) and video_id in videos, "Invalid comment or video reference")
        published = item.get("published_at")
        if published is None:
            undated += 1
            continue
        require(timestamp(published) <= now, "Comment publication is in the future")
        if not timestamp(period["start_at"]) <= timestamp(published) < timestamp(period["end_at"]):
            outside += 1
            continue
        retrieved = item["retrieved_at"]
        require(timestamp(retrieved) >= timestamp(published), "Comment retrieval precedes publication")
        require(now - timestamp(retrieved) <= timedelta(days=30), "YouTube snapshot expired; refresh or delete source data")
        likes = item.get("like_count")
        require(likes is None or type(likes) is int and likes >= 0, "Comment likes must be nonnegative or unknown")
        require(isinstance(item.get("text"), str) and item["text"].strip(), "Comment text is missing")
        parent = item.get("parent_id")
        require(parent is None or isinstance(parent, str) and COMMENT_ID.fullmatch(parent), "Invalid reply parent")
        source_id = "comment:" + comment_id
        if source_id in comments and timestamp(comments[source_id]["retrieved_at"]) >= timestamp(retrieved):
            continue
        count = metric("comment_like_count", likes, "likes", "count", SNAPSHOT, "youtube_current_like_snapshots",
            "Current API like count observed at retrieval. Not likes gained during the requested period.", "API did not supply a like count")
        row = evidence(source_id, "https://www.youtube.com/watch?" + urlencode({"v": video_id, "lc": comment_id}),
            item["text"][:180], item["text"], "comment", retrieved, published, [count])
        comments[source_id] = row
        collection["links"].append({"comment_source_id": source_id, "video_source_id": "video:" + video_id,
            "query_source_ids": video_queries[video_id], "parent_source_id": "comment:" + parent if parent else None})
    ranked = sorted(comments.values(), key=lambda row: (row["measurements"][0]["value"] is None,
        -(row["measurements"][0]["value"] or 0), -timestamp(row["published_at"]).timestamp(), row["source_id"]))
    # Reserve context records, then keep the most liked fetched comments. Unknown likes are never zero-imputed.
    context = list(rows.values()) + list(videos.values())
    retained_context = context[:maximum]
    slots = max(0, maximum - len(retained_context))
    retained_comments, comment_ids = [], set()
    for query_id in selected:
        for row in ranked:
            if row["source_id"] not in comment_ids and any(link.get("comment_source_id") == row["source_id"]
                    and query_id in link.get("query_source_ids", []) for link in collection["links"]):
                if len(retained_comments) < slots:
                    retained_comments.append(row)
                    comment_ids.add(row["source_id"])
                break
    retained_comments += [row for row in ranked if row["source_id"] not in comment_ids][:max(0, slots - len(retained_comments))]
    ordered, used = [], set()
    for query_id in selected:
        if query_id in {row["source_id"] for row in retained_context}:
            ordered.append(rows[query_id])
            used.add(query_id)
        related = [row for row in retained_comments if row["source_id"] not in used and any(
            link.get("comment_source_id") == row["source_id"] and query_id in link.get("query_source_ids", [])
            for link in collection["links"])]
        for row in related[:2]:
            ordered.append(row)
            used.add(row["source_id"])
    ordered += [row for row in retained_comments + retained_context if row["source_id"] not in used]
    output["observations"] = ordered
    retained = {row["source_id"] for row in ordered}
    collection["links"] = [link for link in collection["links"] if link.get("video_source_id") in retained
        and (not link.get("comment_source_id") or link["comment_source_id"] in retained)]
    collection["links"] = list({json.dumps(link, sort_keys=True): link for link in collection["links"]}.values())
    collection["selection"] = {"ranking": "like_count_desc_within_fetched_dated_comments", "comments_outside_window": outside,
        "comments_without_dates": undated, "comments_unique_in_window": len(ranked), "comments_retained": len(retained_comments),
        "observations_limited": max(0, len(context) + len(ranked) - maximum)}
    dated = [timestamp(row["retrieved_at"]) for row in ordered if row["signal_type"] in {"comment", "video"}]
    if dated:
        collection["refresh_or_delete_by"] = iso(min(dated) + timedelta(days=30))
    collection["components"] = {"trends": {"scopes": len(scopes), "queries_selected": len(selected),
        "actual_windows": [scope["actual_window"] for scope in scopes]},
        "videos": {"sampled": len(videos), "temporal_role": "discovery_context"},
        "comments": {"retained": len(retained_comments), "window": period,
                     "ranking_scope": "fetched_sample_only", "likes_scope": "current_snapshot"}}
    if not retained_comments:
        output["limitations"].append("No dated comments were retained; the source cannot support audience-problem conclusions from comments in this run.")
        output["reason"] = "YouTube Search interest only: no dated comments were retained for the requested interval; audience problems are unverified."
    if not scopes:
        output["limitations"].append("No Google Trends YouTube Search scopes were available.")
    if not ordered:
        failed = [row["status"] for row in collection["calls"] if row["status"] in FAILURES]
        if failed:
            output.update(status=failed[0], reason="The configured YouTube collection failed; no evidence was obtained.")
        else:
            output["reason"] = "No related queries or dated comments were returned for the sampled YouTube Search scopes."
    return output


def main(argv=None):
    parser = SetupParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("setup")
    command.add_argument("--csv-only", action="store_true", help="Save only the YouTube key; use supplied Trends exports")
    modes = command.add_mutually_exclusive_group()
    modes.add_argument("--replace", action="store_true")
    modes.add_argument("--remove", action="store_true")
    commands.add_parser("status", help="Print configuration presence only; no network or secret values")
    command = commands.add_parser("normalize", help="Normalize a safe capture offline without repeat provider calls")
    command.add_argument("--input", required=True)
    command.add_argument("--out", required=True)
    command.add_argument("--max-records", type=int, default=100)
    command = commands.add_parser("collect")
    for key in ("days", "max-calls", "max-queries", "max-videos", "max-trends-calls", "pages-per-video", "free-trends-calls", "max-records"):
        defaults = {"max-calls": 10, "max-queries": 2, "max-videos": 3, "max-trends-calls": 2, "pages-per-video": 1, "max-records": 100}
        command.add_argument("--" + key, type=int, default=defaults.get(key))
    for key in ("start", "end", "timezone", "topic", "region", "language", "as-of", "trends-file", "capture-out"):
        command.add_argument("--" + key)
    command.add_argument("--seed", action="append", default=[])
    command.add_argument("--select-query", action="append", default=[])
    command.add_argument("--out", required=True, help="New normalized YouTube import path")
    args = parser.parse_args(argv)
    try:
        if args.command == "setup":
            setup(args)
            return 0
        if args.command == "status":
            keys = credentials()
            print(json.dumps({"provider": "youtube", "youtube_key_configured": bool(keys["youtube_api_key"]),
                "trends_key_configured": bool(keys["serpapi_api_key"]), "authentication_verified": False,
                "allowance_verified": False, "network_calls": 0}))
            return 0
        out = prepare_output(args.out)
        if args.command == "normalize":
            path = Path(args.input)
            require(path.stat().st_size <= MAX_BYTES, "Capture exceeds the size cap")
            result = normalize(json.loads(path.read_text(encoding="utf-8")), maximum=args.max_records)
        else:
            require(1 <= args.pages_per_video <= 3 and 1 <= args.max_trends_calls <= 5 and 1 <= args.max_records <= 100,
                    "Use bounded page, seed and record limits")
            if args.capture_out:
                require(Path(args.capture_out).resolve() != out.resolve(), "Choose fresh distinct capture/import paths")
                prepare_output(args.capture_out)
            forwarded = ["collect", "--providers", "youtube", "--out", str(out)]
            for key in ("days", "start", "end", "timezone", "topic", "region", "language", "as_of"):
                if getattr(args, key) is not None:
                    forwarded += ["--" + key.replace("_", "-"), str(getattr(args, key))]
            params = research_parser().parse_args(forwarded)
            now = datetime.now(UTC)
            run = parameters(params, timestamp(args.as_of) if args.as_of else now)
            keys = credentials()
            existing = load_manifest(Path(args.trends_file)).get("external_calls", 0) if args.trends_file else 0
            net = Network(keys, args.max_calls, args.free_trends_calls or 0, existing)
            try:
                capture = collect_capture(run, args, keys, network=net, now=now)
                result = normalize(capture, now=datetime.now(UTC), maximum=args.max_records)
            except (ValueError, KeyError, TypeError, AttributeError, csv.Error):
                if not net.calls:
                    raise
                # Preserve charged/failed attempts even when a changed provider schema is unusable.
                capture = {"schema_version": VERSION, "status": "unavailable", "collection": {
                    "external_calls": net.used, "new_paid_spending_usd": 0, "calls": net.calls}}
                result = normalize(capture, now=datetime.now(UTC), maximum=args.max_records)
            if args.capture_out:
                with Path(args.capture_out).open("x", encoding="utf-8") as stream:
                    json.dump(capture, stream, indent=2, ensure_ascii=False, allow_nan=False)
        with out.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        print(json.dumps({"provider": "youtube", "status": result["status"], "observations": len(result["observations"]),
                          "external_calls": result["collection"]["external_calls"]}))
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, csv.Error, OSError, getpass.GetPassWarning, EOFError):
        # Provider errors and malformed data can contain keys; never echo their values or URLs.
        print("YouTube setup/input/provider validation failed. Check configuration, dates, free allowance and the documented capture contract; do not paste keys in chat.", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("YouTube operation cancelled.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
