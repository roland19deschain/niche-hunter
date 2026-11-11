"""Bounded, credential-free App Store and Google Web Search observations."""

import csv
import json
import re
from datetime import date, datetime, time
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

from research import MAX_BYTES, UTC, iso, load_json, require, timestamp, window
from youtube_trends import csv_queries, digest, metric, normalize_scopes


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url):
    request = Request(url, headers={"User-Agent": "Niche Hunter public data reader"})
    with build_opener(NoRedirect()).open(request, timeout=15) as response:
        data = response.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES, "Public response exceeds the size cap")
    return data


def load_trends_file(path):
    manifest = load_json(path)
    require(isinstance(manifest, dict), "Trends CSV descriptor must be an object")
    relative = Path(manifest["csv_file"])
    target = (path.parent / relative).resolve()
    require(not relative.is_absolute() and target.is_relative_to(path.parent.resolve())
            and target.suffix.lower() == ".csv", "CSV must be a relative file inside the descriptor directory")
    require(target.stat().st_size <= MAX_BYTES, "Trends CSV exceeds the size cap")
    return {**manifest, "csv": target.read_text(encoding="utf-8-sig")}


def observation(provider, key, url, title, summary, topic, retrieved, metrics, signal, published=None):
    return {"id": provider + ":" + digest(key), "source_id": key, "url": url, "title": title,
            "summary": summary, "topic_terms": [topic] if topic else [], "signal_type": signal,
            "quality": "verified_official", "published_at": published, "metric_observed_at": retrieved,
            "retrieved_at": retrieved, "limitations": [], "measurements": metrics}


def app_store(data, region, topic, retrieved, source):
    payload = json.loads(data)
    entries = payload["results"] if topic else payload["feed"]["results"]
    require(isinstance(entries, list), "Expected an App Store results list")
    source["counts"]["received"] = len(entries)
    period = source["actual_window"]
    listings = source["provenance"]["listings"] = {}
    rows = []
    for position, entry in enumerate(entries, 1):
        app_id = str(entry["trackId"] if topic else entry["id"])
        require(re.fullmatch(r"[0-9]{1,20}", app_id), "Invalid App Store app ID")
        title = entry["trackName"] if topic else entry["name"]
        require(isinstance(title, str) and title.strip(), "Missing App Store title")
        seller = entry.get("sellerName") or entry.get("artistName")
        category = entry.get("primaryGenreName")
        if not topic and entry.get("genres"):
            category = entry["genres"][0].get("name")
        key = f"{region}:{app_id}"
        if key in listings:
            source["counts"]["duplicates"] += 1
            continue
        metrics = []
        if topic:
            currency = entry.get("currency") or "unknown"
            price = entry.get("price")
            rating = entry.get("averageUserRating")
            count = entry.get("userRatingCount")
            require(isinstance(currency, str) and (currency == "unknown" or re.fullmatch(r"[A-Z]{3}", currency)),
                    "Invalid listing currency")
            require(price is None or (type(price) in (int, float) and 0 <= price < float("inf")), "Invalid listing price")
            require(rating is None or (type(rating) in (int, float) and 0 <= rating <= 5), "Invalid listing rating")
            require(count is None or (type(count) is int and count >= 0), "Invalid listing rating count")
            if not rating and count == 0:
                rating = None
            metrics = [metric("app_list_price", price, currency, "estimate", period, region,
                              "Storefront list price at retrieval; excludes subscriptions and in-app purchases."),
                       metric("app_rating", rating, "stars_out_of_5", "index", period, region,
                              "Average user rating returned by Apple at retrieval."),
                       metric("app_rating_count", count, "ratings", "count", period, region,
                              "Current aggregate rating count, without a requested-period breakdown.")]
        else:
            metrics = [metric("app_chart_position", position, "position", "index", period, region,
                              "Position in the retrieved Top Free feed; download counts are unavailable.")]
        listings[key] = {"seller": seller, "category": category, "released_at": entry.get("releaseDate"),
                         "updated_at": entry.get("currentVersionReleaseDate")}
        summary = " · ".join(value for value in (seller, category) if isinstance(value, str) and value.strip())
        rows.append(observation("app_store", key, f"https://apps.apple.com/{region.lower()}/app/id{app_id}",
                                title, summary or "Public App Store listing.", topic, retrieved, metrics, "app_listing"))
    return rows


def trends_rss(data, region, topic, retrieved, source):
    require(not re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", data, re.I), "RSS declarations are unsupported")
    root = ElementTree.fromstring(data.decode("utf-8-sig"))
    channel = root.find("channel")
    require(root.tag == "rss" and channel is not None, "Expected Google Trends RSS")
    entries = channel.findall("item")
    source["counts"]["received"] = len(entries)
    source["counts"]["topic_filtered"] = 0
    tokens = set(re.findall(r"\w+", topic.casefold())) if topic else set()
    rows, seen = [], set()
    for entry in entries:
        title = (entry.findtext("title") or "").strip()
        published = parsedate_to_datetime(entry.findtext("pubDate", ""))
        require(title and published.tzinfo is not None and published <= timestamp(retrieved), "Invalid RSS trend item")
        if topic and (not tokens or not tokens.issubset(re.findall(r"\w+", title.casefold()))):
            source["counts"]["topic_filtered"] += 1
            continue
        key = digest([region, title.casefold(), iso(published)])
        if key in seen:
            source["counts"]["duplicates"] += 1
            continue
        seen.add(key)
        traffic = next((node.text for node in entry if node.tag.rsplit("}", 1)[-1] == "approx_traffic"), "") or ""
        lower = re.fullmatch(r"([0-9][0-9,]{0,15})\+", traffic.strip())
        metrics = [metric("trends_rss_traffic", int(lower[1].replace(",", "")) if lower else None,
                          "searches", "range_lower", source["actual_window"], region,
                          "Lower bound of the published traffic bucket; RSS measurement interval is unspecified.")]
        rows.append(observation("google_trends", key, "https://trends.google.com/trending?" + urlencode({"geo": region}),
                                title, "Trending Now snapshot.", topic, retrieved, metrics, "topic_group", iso(published)))
    return rows


def trends_csv(data, run, source):
    require(isinstance(data, dict) and data.get("property") == "web", "Use a Google Trends Web Search CSV descriptor")
    seed = data["seed"]
    require(isinstance(seed, str) and 0 < len(seed.strip()) <= 100, "Use a single Trends seed of at most 100 characters")
    require("," not in seed, "Use a single Trends seed")
    seed = seed.strip()
    region = data.get("region")
    category = data.get("category", 0)
    require(region is None or (isinstance(region, str) and re.fullmatch(r"[A-Z]{2}(?:-[A-Z0-9]{1,6})?", region)),
            "Use the actual Trends region or omit it for worldwide coverage")
    require(type(category) is int and 0 <= category <= 999999, "Use the numeric category of the export")
    if (run["topic"] and run["topic"].casefold() != seed.casefold()) or (run["region"] and run["region"].upper() != region):
        source.update(status="not_supported", reason="The CSV seed or region does not match the requested scope.")
        return []
    start, end = (datetime.combine(date.fromisoformat(data[key]), time(), UTC) for key in ("start", "end"))
    retrieved = timestamp(data["retrieved_at"])
    require(start < end <= retrieved <= datetime.now(UTC), "CSV dates or retrieval time are invalid")
    period = window(start, end)
    require(isinstance(data["csv"], str) and len(data["csv"].encode("utf-8")) <= MAX_BYTES, "Trends CSV exceeds the size cap")
    queries = csv_queries(data["csv"])
    records, scopes = normalize_scopes([{"property": "web", "seed": seed, "region": region, "category": category,
                                         "actual_window": period, "retrieved_at": iso(retrieved),
                                         "delivery": "google_trends_csv", "related_queries": queries}],
                                       retrieved, property_name="web")
    source.update(actual_window=period, effective_filters={"topic": seed, "region": region, "language": None})
    source["provenance"].update(scopes=scopes, labels={row["source_id"]: row["labels"] for row in records})
    source["counts"]["received"] = len(records)
    return [observation("google_trends", row["source_id"], row["url"], row["query"], "Related Google Web Search query.",
                        seed, row["retrieved_at"], row["measurements"], "typed_search") for row in records]


def collect_public(run, source, csv_input=None):
    provider = source["provider"]
    region, topic = run["region"], run["topic"]
    use_csv = provider == "google_trends" and csv_input is not None
    source.update(adapter="google_trends_web_csv" if use_csv else
                  ("google_trends_rss" if provider == "google_trends" else ("itunes_search" if topic else "apple_top_free")))
    source["provenance"] = {"mode": "permitted_csv" if use_csv else "public_https"}
    try:
        if use_csv:
            data = load_trends_file(csv_input) if isinstance(csv_input, Path) else csv_input
            rows = trends_csv(data, run, source)
            if source["status"] == "not_supported":
                return source
            source["limitations"] = ["Top and Rising apply to the supplied seed, region, category and CSV interval only."]
        else:
            if run["offline"]:
                source["reason"] = "Offline mode requires a Google Trends CSV; App Store needs a live request."
                return source
            if not region or not re.fullmatch(r"[A-Za-z]{2}", region):
                source.update(status="not_supported", reason="Supply a two-letter country code for this public source.")
                return source
            region = region.upper()
            maximum = min(run["limits"]["max_records_per_provider"], 20)
            if provider == "app_store" and topic:
                require(len(topic) <= 100, "Use an App Store search term of at most 100 characters")
                url = "https://itunes.apple.com/search?" + urlencode({"term": topic, "country": region,
                                                                      "entity": "software", "limit": maximum})
            elif provider == "app_store":
                url = f"https://rss.marketingtools.apple.com/api/v2/{region.lower()}/apps/top-free/{10 if maximum <= 10 else 25}/apps.json"
            else:
                url = "https://trends.google.com/trending/rss?" + urlencode({"geo": region})
            source["provenance"]["url"] = url
            source["usage"]["helper_http_attempts"] += 1
            data = fetch(url)
            retrieved = iso(datetime.now(UTC))
            source.update(actual_window={"start_at": None, "end_at": None, "timezone": "UTC", "semantics": "snapshot"},
                          effective_filters={"topic": topic, "region": region, "language": None})
            source["provenance"]["retrieved_at"] = retrieved
            if provider == "app_store":
                rows = app_store(data, region, topic, retrieved, source)
                source["limitations"] = ["Current storefront sample; no historical ranking, installs, search volume or review text."]
            else:
                rows = trends_rss(data, region, topic, retrieved, source)
                source["limitations"] = ["Latest regional RSS snapshot; the feed does not specify its measurement interval.",
                                         "Topic filtering uses words in the returned titles; the feed is not Explore keyword search."]
        limit = min(run["limits"]["max_records_per_provider"], 20) if provider == "app_store" else run["limits"]["max_records_per_provider"]
        source["observations"] = rows[:limit]
        source["counts"].update(accepted=len(source["observations"]), limited=max(0, len(rows) - limit))
        source["unsupported_filters"] = ["language"] if run["language"] else []
        exact = use_csv and source["actual_window"] == run["requested_window"] and len(rows) <= limit and not run["language"]
        source.update(status="ok" if rows and exact else "partial", coverage="sampled",
                      reason=(source["limitations"][0] if rows else "No matching observations in this source sample."))
    except HTTPError as error:
        error.close()
        source.update(status="rate_limited" if error.code == 429 else "unavailable", reason=f"Public source HTTP {error.code}; no retry.")
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError, csv.Error, ElementTree.ParseError) as error:
        source.update(status="unavailable", reason=f"Public source request or format failed ({type(error).__name__}).")
    return source
