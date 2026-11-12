#!/usr/bin/env python3
"""Sample public discussions through an approved Reddit Data API connection."""

import getpass
import json
import os
import re
import sys
import warnings
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener

from public_sources import NoRedirect
from research import CATALOG, MAX_BYTES, UTC, VERSION, iso, parameters, parser as research_parser, require, timestamp, window
from setup_access import SetupParser, read_config, write_config
from youtube import prepare_output

ENDPOINT = "https://oauth.reddit.com"
TERMS = "https://redditinc.com/policies/data-api-terms"
TOKEN = re.compile(r"[A-Za-z0-9._~+/-]{8,2048}={0,2}")
USER_AGENT = re.compile(r"[A-Za-z0-9._-]{1,40}:[A-Za-z0-9._-]{1,100}:[A-Za-z0-9._-]{1,40} \(by /u/[A-Za-z0-9_-]{1,32}\)")
COMMUNITY = re.compile(r"[A-Za-z0-9_]{2,21}")
ITEM_ID = re.compile(r"[a-z0-9]{1,16}")
SNAPSHOT = {"start_at": None, "end_at": None, "timezone": "UTC", "semantics": "snapshot"}
ROUTE = "reddit_data_api"


def access_missing(token, agent, approved):
    missing = []
    if not isinstance(token, str) or not TOKEN.fullmatch(token):
        missing.append("Reddit OAuth access token")
    if (not isinstance(agent, str) or not USER_AGENT.fullmatch(agent)
            or (isinstance(token, str) and token and token in agent)):
        missing.append("Reddit API User-Agent")
    if approved is not True:
        missing.append("approved Reddit access for this use, AI processing and retention")
    return missing


def scope(topic, community):
    require(not topic or len(topic) <= 512, "Use a Reddit topic of at most 512 characters")
    if community is not None:
        community = community.strip().removeprefix("r/")
        require(COMMUNITY.fullmatch(community), "Use a single Reddit community name")
    elif not topic:
        community = CATALOG["categories"][0]["reddit"][0]
    return community


def config_path():
    return Path(os.environ.get("NICHE_HUNTER_CONFIG_DIR", Path.home() / ".config/niche-hunter")) / "reddit.json"


def credentials():
    path = config_path()
    raw = read_config(path)
    if raw:
        require(path.stat().st_mode & 0o077 == 0, "Reddit settings must be readable only by their owner")
    settings = json.loads(raw) if raw else {}
    require(isinstance(settings, dict), "Invalid private Reddit settings")
    return settings.get("token"), settings.get("user_agent"), settings.get("approved")


def setup(args):
    path = config_path()
    original = read_config(path)
    if args.remove:
        require(original is not None, "No private Reddit settings exist")
        write_config(path, original, "{}\n")
        print("Removed the local Reddit connection settings.")
        return
    require(original is None or original.strip() == b"{}" or args.replace,
            "Reddit settings already exist. Use --replace to rotate the token")
    require(sys.stdin.isatty(), "Run setup yourself in an interactive terminal")
    approved = input("Does your Reddit approval cover this use, AI processing and retention? [y/N] ").strip().lower() == "y"
    require(approved, "Obtain Reddit approval for this use before configuring the live collector")
    agent = input("Approved Reddit API User-Agent: ").strip()
    require(USER_AGENT.fullmatch(agent), "Use Reddit's platform:app-id:version (by /u/username) format")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        token = getpass.getpass("Reddit OAuth access token (hidden): ")
    require(not access_missing(token, agent, approved), "Check the OAuth access token and User-Agent")
    write_config(path, original, json.dumps({"token": token, "user_agent": agent, "approved": approved}) + "\n")
    print("Saved the private Reddit connection. Authentication has not been tested.")


def fetch(request):
    with build_opener(NoRedirect()).open(request, timeout=20) as response:
        data = response.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES, "Reddit response exceeded the size cap")
    return json.loads(data)


def request_listing(path, query, token, agent, transport, *, comments=False):
    request = Request(ENDPOINT + path + "?" + urlencode({"raw_json": 1, **query}),
                      headers={"Authorization": "Bearer " + token, "User-Agent": agent, "Accept": "application/json"})
    try:
        payload = transport(request)
        if comments:
            require(isinstance(payload, list) and len(payload) == 2, "Unknown Reddit comment tree")
            payload = payload[1]
        require(isinstance(payload, dict) and payload.get("kind") == "Listing", "Unknown Reddit listing")
        listing = payload.get("data")
        require(isinstance(listing, dict) and isinstance(listing.get("children"), list), "Unknown Reddit listing fields")
        return listing, "ok", None
    except HTTPError as error:
        error.close()
        status, reason = {
            401: ("auth_required", "Reddit rejected the OAuth token. Check or replace it in private settings."),
            403: ("not_supported", "Reddit denied access to this route or community. Check the approved scope."),
            404: ("not_supported", "Reddit did not expose this community or thread through the approved connection."),
            429: ("rate_limited", "Reddit rate limited the request."),
        }.get(error.code, ("unavailable", "Reddit could not serve the request."))
        return None, status, reason
    except (ValueError, OSError):
        return None, "unavailable", "Reddit request or response could not be read."


def listing_items(listing, kind, cap):
    for item in listing["children"][:cap]:
        if isinstance(item, dict) and item.get("kind") == kind and isinstance(item.get("data"), dict):
            yield item["data"]


def publication(item):
    value = item.get("created_utc")
    if type(value) in (int, float):
        try:
            return datetime.fromtimestamp(value, UTC)
        except (ValueError, OSError, OverflowError):
            pass
    return None


def collect(run, token, agent, approved, *, community=None, maximum=20, attempts=2, transport=None, clock=None):
    require(1 <= attempts <= 2 and 1 <= maximum <= 100, "Use one or two Reddit attempts and up to 100 observations")
    transport = transport or fetch
    clock = clock or (lambda: datetime.now(UTC))
    topic = run["topic"]
    collection = {"external_calls": 0, "new_paid_spending_usd": 0}
    output = {"schema_version": VERSION, "provider": "reddit", "adapter": ROUTE,
              "collection": collection, "observations": []}
    if access_missing(token, agent, approved):
        return dict(output, status="auth_required", reason="Configure approved Reddit Data API access in private settings.")
    community = scope(topic, community)
    secret_forms = {token, quote(token, safe="")}
    if any(secret in (topic or "") or secret in (community or "") for secret in secret_forms):
        return dict(output, status="not_supported", reason="Use a Reddit search scope without credentials.")

    start = timestamp(run["requested_window"]["start_at"])
    end = timestamp(run["requested_window"]["end_at"])
    compare = run.get("hunt_mode") == "trend_hunt"
    first = timestamp(run["baseline_window"]["start_at"]) if compare else start
    path = f"/r/{community}" if community else ""
    limit = 100
    query = {"limit": limit}
    if topic:
        path += "/search"
        query.update(q=topic, sort="new", t="all", type="link", restrict_sr=str(bool(community)).lower())
    else:
        path += "/new"
    collection.update(external_calls=1, search_terms=[topic] if topic else [],
                      communities=[community] if community else [], post_page_limit=limit)
    listing, status, reason = request_listing(path, query, token, agent, transport)
    if listing is None:
        return dict(output, status=status, reason=reason)

    def safe_text(value, size):
        if not isinstance(value, str) or value.strip() in {"[deleted]", "[removed]"}:
            return ""
        for secret in secret_forms:
            value = value.replace(secret, "[redacted]")
        return " ".join(value.split())[:size]

    def evidence(item, source_id, url, title, summary, published_at, retrieved, kind):
        metrics = []
        for field, name, definition in (("score", "Reddit score", "Reddit score at retrieval; not exact votes"),
                                        ("num_comments", "Comment count", "Post comment counter at retrieval")):
            if type(item.get(field)) is int and (field == "score" or kind == "discussion"):
                metrics.append({"name": name, "unit": "score" if field == "score" else "comments",
                                "kind": "index" if field == "score" else "count", "value": item[field],
                                "methodology": definition, "window": SNAPSHOT})
        return {"source_id": source_id, "url": url, "title": title, "summary": summary,
                "topic_terms": [topic] if topic else [], "signal_type": kind, "quality": "verified_official",
                "published_at": iso(published_at), "metric_observed_at": retrieved if metrics else None,
                "retrieved_at": retrieved, "limitations": [], "measurements": metrics}

    retrieved = iso(clock())
    posts, seen, page_dates = [], set(), []
    periods = {"current": 0, "baseline": 0}
    for item in listing_items(listing, "t3", limit):
        published_at = publication(item)
        if published_at is None:
            continue
        page_dates.append(published_at)
        post_id, name = item.get("id", ""), item.get("subreddit", "")
        if not (first <= published_at < end and isinstance(post_id, str) and ITEM_ID.fullmatch(post_id)
                and isinstance(name, str) and COMMUNITY.fullmatch(name)):
            continue
        if (community and name.lower() != community.lower()) or post_id in seen:
            continue
        if (item.get("subreddit_type") not in ("public", "restricted")
                or any(secret in post_id or secret in name for secret in secret_forms) or item.get("over_18")
                or item.get("removed_by_category") or item.get("selftext") in ("[removed]", "[deleted]")):
            continue
        title = safe_text(item.get("title"), 160)
        if not title:
            continue
        seen.add(post_id)
        periods["current" if published_at >= start else "baseline"] += 1
        url = f"https://www.reddit.com/r/{name}/comments/{post_id}/"
        summary = f"r/{name}"
        excerpt = safe_text(item.get("selftext"), 240)
        if excerpt:
            summary += " · " + excerpt
        row = evidence(item, "t3_" + post_id, url, title, summary, published_at, retrieved, "discussion")
        num_comments = item.get("num_comments")
        posts.append((published_at, num_comments if type(num_comments) is int else 0, row))

    posts.sort(key=lambda entry: entry[0], reverse=True)
    bounded = bool(listing.get("after")) or len(listing["children"]) >= limit
    collection.update(new_posts_in_sample=periods, post_listing_truncated=bounded, comparison_requested=compare,
                      listing_reached_window_start=not bounded or bool(page_dates and min(page_dates) <= first))
    limits = ["Posts are a bounded newest-first listing. Sample counts describe publications, never Reddit search volume.",
              "Scores and comment counters are retrieval snapshots. Region and language are not filtered."]
    if compare:
        limits.append("Compare sampled post dates using the same query only when the listing reached the earlier window.")
    if listing["children"] and not page_dates:
        return dict(output, status="unavailable", reason="Reddit returned no post rows with usable publication dates.")

    replies = []
    parent_row = None
    parent = max((post for post in posts if post[0] >= start and post[1] > 0), default=None, key=lambda post: post[1])
    if attempts == 2 and maximum > 1 and parent:
        parent_row = parent[2]
        post_id = parent_row["source_id"].removeprefix("t3_")
        cap = min(6, max(1, maximum // 3))
        collection.update(external_calls=2, comment_thread_id=parent_row["source_id"], comment_page_limit=20)
        thread, status, reason = request_listing(f"/comments/{post_id}", {"sort": "top", "limit": 20, "depth": 1},
                                                 token, agent, transport, comments=True)
        collection["comments_status"] = status
        if thread is None:
            limits.append(reason)
        else:
            retrieved = iso(clock())
            seen_comments = set()
            for item in listing_items(thread, "t1", 20):
                comment_id = item.get("id", "")
                published_at = publication(item)
                body = safe_text(item.get("body"), 240)
                if not (isinstance(comment_id, str) and ITEM_ID.fullmatch(comment_id) and body
                        and published_at and start <= published_at < end and item.get("link_id") == "t3_" + post_id
                        and item.get("parent_id") == "t3_" + post_id and comment_id not in seen_comments
                        and all(secret not in comment_id for secret in secret_forms)):
                    continue
                seen_comments.add(comment_id)
                replies.append(evidence(item, "t1_" + comment_id, parent_row["url"] + f"_/{comment_id}/",
                                        body[:160], body, published_at, retrieved, "comment"))
            replies = replies[:cap]
            limits.append("Comments sample top-ranked replies from one current thread, filtered to the requested dates.")
    else:
        limits.append("No comment page was requested within this run's scope and budget.")
    post_slots = maximum - len(replies)
    current = [post[2] for post in posts if post[0] >= start]
    prior = [post[2] for post in posts if post[0] < start]
    # Preserve evidence from both periods where possible, and keep the sampled comments' parent.
    prior_slots = min(len(prior), max(post_slots - len(current), post_slots // 3, int(post_slots > 1)))
    kept_current = current[:post_slots - prior_slots]
    if replies and parent_row not in kept_current:
        kept_current[-1] = parent_row
    output["observations"] = kept_current + prior[:prior_slots] + replies
    reason = "Sampled Reddit discussions." if posts else "No eligible public discussions in the returned Reddit sample."
    return dict(output, status="partial", reason=reason, actual_window=window(first, end, run["timezone"]),
                effective_filters={"topic": topic, "region": None, "language": None}, limitations=limits,
                rights={"storage_permitted": True, "basis": "Operator-confirmed Reddit approval for this use.",
                        "reference": TERMS})


def main():
    parser = SetupParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("setup")
    action = command.add_mutually_exclusive_group()
    action.add_argument("--replace", action="store_true")
    action.add_argument("--remove", action="store_true")
    commands.add_parser("status")
    command = commands.add_parser("collect", help="Create one normalized Reddit import")
    command.add_argument("--out", required=True)
    command.add_argument("--community")
    command.add_argument("--max-records", type=int, default=20)
    command.add_argument("--max-calls", type=int, default=2, choices=(1, 2))
    command.add_argument("--days", type=int)
    for name in ("start", "end", "timezone", "topic", "hunt-mode"):
        command.add_argument("--" + name)
    args = parser.parse_args()
    try:
        if args.command == "setup":
            setup(args)
            return
        token, agent, approved = credentials()
        missing = access_missing(token, agent, approved)
        if args.command == "status":
            print(json.dumps({"provider": "reddit", "ready": not missing, "missing": missing,
                              "authentication_verified": False}))
            return
        require(not missing, "Configure approved Reddit Data API access before collection")
        forwarded = ["collect", "--providers", "reddit", "--out", args.out]
        for name in ("days", "start", "end", "timezone", "topic", "hunt_mode"):
            if getattr(args, name) is not None:
                forwarded += ["--" + name.replace("_", "-"), str(getattr(args, name))]
        run = parameters(research_parser().parse_args(forwarded), datetime.now(UTC))
        out = prepare_output(args.out)
        result = collect(run, token, agent, approved, community=args.community,
                         maximum=args.max_records, attempts=args.max_calls)
        with open(out, "x", encoding="utf-8", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps({"provider": "reddit", "status": result["status"], "observations": len(result["observations"])}))
    except (ValueError, TypeError, OSError, EOFError, getpass.GetPassWarning) as error:
        message = str(error) if str(error).startswith(("Use ", "Configure ", "Reddit settings ", "Obtain ", "Run setup ")) else ""
        parser.exit(2, (message or "Reddit setup or collection failed. Check the private settings, scope and output path.") + "\n")


if __name__ == "__main__":
    main()
