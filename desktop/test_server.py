"""Synthetic Desktop transport and report checks. No real keys or endpoints are used."""

import io
import json
import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import httpx
from pypdf import PdfReader

from desktop import server

KEYS = {"tokconnect": "fixture-tokconnect-key", "youtube_api_key": "fixture-youtube-key",
        "serpapi_api_key": "fixture-serpapi-key"}
VIDEO = "abcdefghijk"
ANALYSIS = {"schema_version": "0.1.0", "summary": "Synthetic review only.", "gaps": [],
            "findings": [], "hypotheses": []}


class DesktopTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name) / "reports"
        self.desktop = server.DesktopResearch(KEYS, self.root, dict.fromkeys(server.QUOTA_CAPS, 1))

    async def collect(self, **changes):
        args = {"providers": "tiktok,youtube", "days": 7, "start": None, "end": None, "timezone": None,
                "topic": "synthetic", "region": None, "language": None, "free_tokconnect_credits": 1,
                "free_serpapi_searches": 1, "youtube_search_calls": 1, "youtube_comment_units": 1,
                "max_records": 20, "imports": []}
        return await self.desktop.collect(**{**args, **changes})

    async def test_preflight_blocks_default_reddit_and_explicit_zero_overrides(self):
        with patch.object(server, "collect_tokconnect", new_callable=AsyncMock) as tiktok:
            result = await self.collect(providers="reddit,tiktok,youtube,chatgpt")
            self.assertFalse(result["ready"])
            with self.assertRaisesRegex(ValueError, "exclude YouTube"):
                await self.collect(free_serpapi_searches=0)
            with self.assertRaisesRegex(ValueError, "exclude YouTube"):
                await self.collect(youtube_comment_units=0)
            with self.assertRaisesRegex(ValueError, "credentials"):
                await self.collect(topic=KEYS["tokconnect"])
        tiktok.assert_not_called()
        self.assertFalse(self.root.exists())

    async def test_public_sources_need_no_keys_and_report_attempts_and_snapshot_coverage(self):
        self.desktop = server.DesktopResearch({}, self.root)
        selected = "app_store,google_trends"
        self.assertTrue(self.desktop.status(selected)["ready"])
        app = {"trackId": 123, "trackName": "Synthetic notes", "sellerName": "Synthetic publisher",
               "price": 0, "currency": "GBP", "averageUserRating": 4.5, "userRatingCount": 42}
        rss = b'''<rss xmlns:ht="urn:fixture"><channel><item><title>Synthetic notes</title>
            <pubDate>Sun, 01 Nov 2026 12:00:00 GMT</pubDate><ht:approx_traffic>1,000+</ht:approx_traffic>
            </item></channel></rss>'''
        with patch("public_sources.fetch", side_effect=[json.dumps({"results": [app]}).encode(), rss]) as fetch:
            result = await self.collect(providers=selected, topic="notes", region="CA",
                                        hunt_mode="trend_hunt",
                                        app_store_region="GB", google_trends_region="AU")
        self.assertEqual([urlsplit(call.args[0]).hostname for call in fetch.call_args_list],
                         ["itunes.apple.com", "trends.google.com"])
        self.assertEqual([source["effective_filters"]["region"] for source in result["sources"]], ["GB", "AU"])
        budget = result["run"]["desktop_budget"]
        self.assertEqual(sum(budget["planned_attempts"].values()), 2)
        self.assertEqual(budget["planned_attempts"], budget["actual_attempts"])
        self.assertTrue(all(source["status"] == "partial" and source["actual_window"]["semantics"] == "snapshot"
                            for source in result["sources"]))
        self.assertEqual(result["run"]["hunt_mode"], "trend_hunt")
        analysis = {**ANALYSIS, "presentation": {"providers": [
            {"provider": source["provider"], "conclusion": "Synthetic provider conclusion.",
             "evidence_ids": [source["observations"][0]["id"]]} for source in result["sources"]]}}
        report = self.desktop.finalize(result["run"]["id"], analysis, None)
        self.assertIn("Collection scope: Topic: notes", report["markdown"])
        self.assertNotIn("## Overall", report["markdown"])
        self.assertIn("Current snapshot", report["markdown"])
        self.assertIn("Rating: 4.50/5", report["markdown"])
        self.assertIn("1,000+", report["markdown"])

    async def test_app_store_defaults_to_two_separate_storefronts_and_keeps_available_results(self):
        self.desktop = server.DesktopResearch({}, self.root)
        self.assertEqual(self.desktop.status("app_store")["maximum_planned_attempts"]["app_store_requests"], 2)
        self.assertEqual(self.desktop.status("app_store", region="GB")["maximum_planned_attempts"]["app_store_requests"], 1)
        chart = json.dumps({"feed": {"results": [{"id": "123", "name": "Shared listing"}]}}).encode()
        for british_result in (chart, HTTPError("https://rss.marketingtools.apple.com/", 429, "limited", {}, None)):
            with patch("public_sources.fetch", side_effect=[chart, british_result]) as fetch:
                result = await self.collect(providers="app_store", topic=None)
            self.assertEqual([urlsplit(call.args[0]).path.split("/")[3] for call in fetch.call_args_list], ["us", "gb"])
            source, = result["sources"]
            self.assertEqual(source["usage"]["helper_http_attempts"], 2)
            self.assertEqual(source["status"], "partial")
            report = self.desktop.finalize(result["run"]["id"], ANALYSIS, None)["markdown"]
            self.assertIn("US · Shared listing", report)
            if isinstance(british_result, HTTPError):
                self.assertIn("GB (rate_limited)", report)
                self.assertEqual(len(source["observations"]), 1)
            else:
                self.assertIn("GB · Shared listing", report)
                self.assertEqual([row["measurements"][0]["value"] for row in source["observations"]], [1, 1])
                self.assertEqual(len({row["id"] for row in source["observations"]}), 2)

    async def test_tier_1_defaults_are_separate_and_top_free_can_override_a_common_topic(self):
        self.desktop = server.DesktopResearch({}, self.root)
        chart = json.dumps({"feed": {"results": [{"id": "123", "name": "Synthetic listing"}]}}).encode()
        rss = b"<rss><channel/></rss>"
        with patch("public_sources.fetch", side_effect=[chart, chart, rss]) as fetch:
            result = await self.collect(providers="app_store,google_trends", region="CA", app_store_region="tier-1",
                                        app_store_topic="", google_trends_region="tier-1")
        self.assertEqual([urlsplit(call.args[0]).path.split("/")[3] for call in fetch.call_args_list[:2]], ["us", "gb"])
        self.assertEqual(parse_qs(urlsplit(fetch.call_args_list[2].args[0]).query), {"geo": ["US"]})
        self.assertEqual([source["effective_filters"]["topic"] for source in result["sources"]], [None, "synthetic"])
        self.assertEqual(sum(result["run"]["desktop_budget"]["actual_attempts"].values()), 3)

    async def test_provider_numbers_cannot_bypass_owner_settings(self):
        self.desktop = server.DesktopResearch(KEYS, self.root, {"youtube_comment_units": 0})
        with patch.object(server.youtube, "collect_capture") as collect:
            result = await self.collect(providers="youtube", youtube_comment_units=8)
        self.assertFalse(result["ready"])
        self.assertIn("youtube_comment_units per-run limit", result["providers"][0]["missing"])
        self.assertTrue(self.desktop.status("chatgpt")["ready"])
        self.assertTrue(self.desktop.status("youtube", ["youtube"])["ready"])
        self.assertEqual(result["extension_version"], json.loads(server.MANIFEST.read_text())["version"])
        collect.assert_not_called()
        self.assertFalse(self.root.exists())

    def test_blank_limit_settings_use_defaults_and_explicit_values_take_precedence(self):
        with patch.dict(os.environ, {"NICHE_HUNTER_TOKCONNECT_CREDITS_PER_RUN": "",
                                    "NICHE_HUNTER_SERPAPI_SEARCHES_PER_RUN": "0",
                                    "NICHE_HUNTER_YOUTUBE_COMMENT_UNITS_PER_RUN": "8"}, clear=True):
            limits = server.injected_limits()
        self.assertEqual(limits, {"tokconnect_credits": 1, "serpapi_searches": 0,
                                  "youtube_search_calls": 1, "youtube_comment_units": 8})
        self.desktop = server.DesktopResearch(KEYS, self.root)
        status = self.desktop.status(",".join(server.research.PROVIDERS), ["reddit"])
        self.assertTrue(status["ready"])
        self.assertEqual(status["limit_defaults"]["youtube_comment_units"], 6)
        self.assertEqual(sum(status["maximum_planned_attempts"].values()), 10)
        self.assertEqual(status["maximum_planned_attempts"]["youtube_comment_units"], 2)

    async def test_tokconnect_protocol_uses_one_fixed_bearer_authenticated_tool_call(self):
        calls = []
        actual_client = httpx.AsyncClient

        def send(request):
            self.assertEqual(str(request.url), server.TOKCONNECT_URL)
            self.assertEqual(request.headers["Authorization"], "Bearer " + KEYS["tokconnect"])
            message = json.loads(request.content)
            method = message["method"]
            calls.append(method)
            if method == "notifications/initialized":
                return httpx.Response(202)
            if method == "initialize":
                result = {"protocolVersion": message["params"]["protocolVersion"], "capabilities": {"tools": {}},
                          "serverInfo": {"name": "fixture", "version": "1.0.0"}}
            elif method == "tools/list":
                result = {"tools": [{"name": "demand_find_topics", "inputSchema": {"type": "object",
                          "required": ["method", "keyword", "limit"]}}]}
            else:
                self.assertEqual(message["params"], {"name": "demand_find_topics", "arguments":
                                 {"method": "search", "keyword": "synthetic", "limit": 20}})
                result = {"content": [], "structuredContent": {"data": {"topics": [], "hasMore": False}}}
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": message["id"], "result": result})

        def client(**options):
            return actual_client(**options, transport=httpx.MockTransport(send))

        with patch.object(server.httpx, "AsyncClient", side_effect=client):
            capture = await server.collect_tokconnect(KEYS["tokconnect"], "synthetic", 100)
        self.assertEqual(calls, ["initialize", "notifications/initialized", "tools/list", "tools/call"])
        self.assertEqual(capture["external_calls"], 1)
        self.assertEqual(len(capture["calls"]), 1)
        self.assertNotIn(KEYS["tokconnect"], json.dumps(capture))

    async def test_normalized_live_sources_finalize_with_review_and_no_second_collection(self):
        self.desktop = server.DesktopResearch(KEYS, self.root)
        published = server.research.iso(server.now() - timedelta(days=2))
        capture = {"schema_version": "0.1.0", "external_calls": 1, "new_paid_spending_usd": 0,
                   "calls": [{"tool": "demand_find_topics", "arguments": {"method": "search"},
                              "retrieved_at": server.research.iso(server.now()),
                              "response": {"data": {"hasMore": False, "topics": [
                                  {"queryId": "one", "queryText": "Synthetic candidate"},
                                  {"queryId": "two", "queryText": "Discarded candidate"}]}}}]}
        requests = []

        def send(request, timeout):
            url = urlsplit(request.full_url)
            query = parse_qs(url.query)
            requests.append((url.hostname, url.path))
            if url.hostname == "serpapi.com":
                self.assertEqual(query["api_key"], [KEYS["serpapi_api_key"]])
                self.assertEqual(query["gprop"], ["youtube"])
                data = {"search_parameters": {key: query[key][0] for key in ("gprop", "q", "date", "data_type")},
                        "related_queries": {"top": [{"query": "synthetic query", "value": "100"}]},
                        "ignored_metadata": {"key": KEYS["serpapi_api_key"]}}
            elif url.path.endswith("/search"):
                self.assertEqual(query["key"], [KEYS["youtube_api_key"]])
                data = {"items": [{"id": {"videoId": VIDEO}, "snippet": {"title": "Synthetic video",
                                  "publishedAt": published}}]}
            else:
                data = {"items": [{"snippet": {"topLevelComment": {"id": "synthetic-comment",
                    "snippet": {"publishedAt": published, "textDisplay": "Synthetic comment", "likeCount": 3}}}}]}
            return io.BytesIO(json.dumps(data).encode())

        network = server.youtube.Network

        def fixture_network(*args):
            return network(*args, transport=send)

        with patch.object(server, "collect_tokconnect", new_callable=AsyncMock, return_value=capture) as tiktok:
            with patch.object(server.youtube, "Network", side_effect=fixture_network):
                result = await self.collect(free_tokconnect_credits=None, free_serpapi_searches=None,
                                            youtube_search_calls=None, youtube_comment_units=None)
            tik, yt = result["sources"]
            self.assertTrue(tik["topic_review_pending"])
            self.assertEqual(yt["usage"]["external_calls"], 4)
            self.assertEqual([row["signal_type"] for row in yt["observations"]].count("comment"), 1)
            self.assertNotIn("free_credits_before", tik["provenance"]["collection"])
            self.assertNotIn("free_trends_calls_confirmed", yt["provenance"]["collection"])
            chosen, discarded = [row["id"] for row in tik["observations"]]
            with self.assertRaisesRegex(ValueError, "reviewed TikTok"):
                self.desktop.finalize(result["run"]["id"], ANALYSIS, None)
            invalid = {**ANALYSIS, "findings": [{"evidence_ids": [discarded]}]}
            with self.assertRaisesRegex(ValueError, "unknown evidence"):
                self.desktop.finalize(result["run"]["id"], invalid, [chosen])
            report = self.desktop.finalize(result["run"]["id"], ANALYSIS, [chosen])
        tiktok.assert_awaited_once()
        self.assertEqual(len(requests), 4)
        self.assertIn("Synthetic review only.", report["markdown"])
        pdf = PdfReader(report["files"]["report.pdf"])
        self.assertIn("Synthetic review only.", pdf.pages[0].extract_text())
        saved = Path(report["files"]["results.json"]).read_text()
        self.assertEqual([row["id"] for row in json.loads(saved)["sources"][0]["observations"]], [chosen])
        budget = json.loads(saved)["run"]["desktop_budget"]
        self.assertEqual(budget["requested_overrides"], {})
        self.assertEqual(budget["planned_attempts"]["youtube_comment_units"], 6)
        self.assertEqual(budget["actual_attempts"]["youtube_comment_units"], 2)
        self.assertEqual(budget["actual_attempts"]["serpapi_searches"], 1)
        self.assertEqual(budget["actual_attempts"]["youtube_search_calls"], 1)
        self.assertEqual(json.loads(saved)["run"]["extension_version"], self.desktop.status("youtube")["extension_version"])
        for key in KEYS.values():
            self.assertNotIn(key, saved)
            self.assertNotIn(key, report["markdown"])

    async def test_broad_youtube_seed_uses_the_existing_single_search_budget(self):
        with patch.object(server.youtube, "collect_capture", return_value={
            "schema_version": server.research.VERSION, "status": "unavailable",
            "collection": {"external_calls": 0, "new_paid_spending_usd": 0},
        }) as collect:
            with self.assertRaisesRegex(ValueError, "Use youtube_seed"):
                await self.collect(providers="youtube", youtube_seed="synthetic workflow")
            self.assertFalse(self.root.exists())
            await self.collect(providers="youtube", topic=None, youtube_seed="synthetic workflow")
        collect.assert_called_once()
        options = collect.call_args.args[1]
        self.assertEqual(options.seed, ["synthetic workflow"])
        self.assertEqual(options.max_trends_calls, 1)
        self.assertEqual(options.max_calls, 3)

    async def test_provider_echo_of_credential_is_dropped_and_attempt_is_counted(self):
        capture = {"external_calls": 1, "response": KEYS["tokconnect"]}
        with patch.object(server, "collect_tokconnect", new_callable=AsyncMock, return_value=capture):
            result = await self.collect(providers="tiktok")
        source, = result["sources"]
        self.assertEqual(source["status"], "unavailable")
        self.assertEqual(source["usage"]["external_calls"], 1)
        self.assertNotIn(KEYS["tokconnect"], json.dumps(result))
