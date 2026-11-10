"""YouTube fixtures exercise real request shapes; they are not live metric/access verification."""

import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from test_research import research

SCRIPTS = research.SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS))
import youtube
import youtube_trends as trends
from reporting import build_report, markdown_report, text_report
sys.path.pop(0)

KEY = "SYNTHETIC_NOT_A_KEY"
VID = "AAAAAAAAAAA"
NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)


def run(days=7, topic=None):
    args = research.parser().parse_args(["collect", "--providers", "youtube", "--days", str(days), "--out", "unused"])
    args.topic = topic
    result = research.parameters(args, NOW)
    result["generated_at"] = research.iso(NOW)
    return result


def scope(seed="synthetic", period=None):
    return {"property": "youtube", "seed": seed, "actual_window": period or run()["requested_window"],
        "retrieved_at": research.iso(NOW), "delivery": "synthetic_fixture",
        "related_queries": {"top": [{"query": "Synthetic query", "value": "100"}],
            "rising": [{"query": "Synthetic query", "value": "+250%"},
                       {"query": "Another query", "value": "Breakout", "extracted_value": 8700}]}}


def capture():
    source = scope()
    queries, _ = trends.normalize_scopes([source], NOW)
    query_id = queries[0]["source_id"]
    return {"schema_version": research.VERSION, "requested_window": run()["requested_window"], "topic": None,
        "scopes": [source], "selected_query_ids": [query_id],
        "videos": [{"video_id": VID, "title": "Synthetic older tutorial", "channel_id": "synthetic_creator",
            "published_at": "2025-01-01T00:00:00Z", "retrieved_at": research.iso(NOW), "query_ids": [query_id]}],
        "comments": [comment("low", 1), comment("high", 50), comment("unknown", None), comment("zero", 0)],
        "collection": {"external_calls": 0, "new_paid_spending_usd": 0}}


def comment(identifier, likes, published="2026-11-02T12:00:00Z"):
    return {"id": identifier, "video_id": VID, "text": "Synthetic question " + identifier,
            "published_at": published, "retrieved_at": research.iso(NOW), "like_count": likes}


class TrendsTests(unittest.TestCase):
    def test_top_rising_breakout_scope_and_indices_keep_their_meanings(self):
        records, receipts = trends.normalize_scopes([scope()], NOW)
        first = next(row for row in records if row["query"] == "Synthetic query")
        metrics = {row["name"]: row for row in first["measurements"]}
        self.assertEqual(metrics["trends_top_index"]["value"], 100)
        self.assertEqual(metrics["trends_growth_percent"]["value"], 250)
        breakout = next(row for row in records if row["query"] == "Another query")["measurements"][0]
        self.assertEqual((breakout["value"], breakout["kind"]), (5000, "range_lower"))
        self.assertNotIn("8700", json.dumps(records))
        baseline = receipts[0]["baseline_window"]
        self.assertEqual(baseline["end_at"], receipts[0]["actual_window"]["start_at"])
        other, _ = trends.normalize_scopes([scope("another_seed")], NOW)
        self.assertNotEqual(records[0]["source_id"], other[0]["source_id"])
        self.assertNotEqual(records[0]["measurements"][0]["comparison_group"], other[0]["measurements"][0]["comparison_group"])

    def test_csv_export_quotes_unknown_labels_and_property_validation(self):
        rows = trends.csv_queries('Category: All categories\n\nTOP\n"Synthetic, phrase",100\nRISING\nOther,+250%\nNew,Breakout\n')
        self.assertEqual(rows["top"][0]["query"], "Synthetic, phrase")
        source = scope()
        source["related_queries"]["rising"] = [{"query": "Unparsed", "value": "unrecognized label", "extracted_value": 9000}]
        records, _ = trends.normalize_scopes([source], NOW)
        self.assertIsNone(records[0]["measurements"][0]["value"])
        source["property"] = "web"
        with self.assertRaises(ValueError):
            trends.normalize_scopes([source], NOW)
        with self.assertRaises(ValueError):
            trends.csv_queries("Date,Interest\n2026-11-01,100\n")

    def test_csv_manifest_stays_local_and_metadata_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "related.csv").write_text("TOP\nSynthetic query,100\nRISING\nOther,+20%\n")
            item = scope()
            item.pop("property")
            item.pop("related_queries")
            item["csv_file"] = "related.csv"
            manifest = {"schema_version": research.VERSION, "property": "youtube", "scopes": [item]}
            path = base / "manifest.json"
            path.write_text(json.dumps(manifest))
            result = trends.load_manifest(path)
            records, _ = trends.normalize_scopes(result["scopes"], NOW)
            self.assertEqual(len(records), 2)
            manifest["scopes"][0]["csv_file"] = "../outside.csv"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                trends.load_manifest(path)

    def test_scopes_are_not_ranked_by_incompatible_normalized_values(self):
        first, second = scope("first"), scope("second")
        second["related_queries"] = {"top": [{"query": "Second scope", "value": 1}]}
        records, _ = trends.normalize_scopes([first, second], NOW)
        selected = trends.select_queries(records, 2)
        self.assertEqual({row["seed"] for row in selected}, {"first", "second"})
        for value in (float("nan"), float("inf")):
            first["related_queries"]["top"][0]["value"] = value
            with self.assertRaises(ValueError):
                trends.normalize_scopes([first], NOW)


class YouTubeTests(unittest.TestCase):
    def test_dates_likes_dedup_and_old_video_context_reach_the_collector(self):
        payload = capture()
        payload["comments"] += [comment("old", 10000, "2026-10-01T00:00:00Z"),
            comment("end", 999, run()["requested_window"]["end_at"]),
            {**comment("undated", 99), "published_at": None},
            {**comment("high", 40), "retrieved_at": research.iso(NOW - timedelta(minutes=1))}]
        normalized = youtube.normalize(payload, NOW)
        rows = [row for row in normalized["observations"] if row["signal_type"] == "comment"]
        self.assertEqual([row["source_id"] for row in rows], ["comment:high", "comment:low", "comment:zero", "comment:unknown"])
        self.assertEqual(rows[0]["measurements"][0]["value"], 50)
        self.assertIsNone(rows[-1]["measurements"][0]["value"])
        source = research.collect_import(normalized, run(), 100)
        self.assertEqual(source["counts"]["accepted"], len(normalized["observations"]))
        self.assertTrue(any(row["signal_type"] == "video" for row in source["observations"]))
        self.assertEqual(normalized["collection"]["selection"]["comments_outside_window"], 2)
        self.assertEqual(normalized["collection"]["selection"]["comments_without_dates"], 1)

    def test_exact_evidence_links_reject_credentials_and_unknown_parameters(self):
        good = ['https://www.youtube.com/watch?v=' + VID + '&lc=sample',
                'https://trends.google.com/trends/explore?q=synthetic&gprop=youtube&date=2026-10-28+2026-11-03']
        for value in good:
            research.secure_url(value, "youtube")
        for value in (good[0] + '&key=' + KEY, good[1] + '&api_key=' + KEY,
                      'https://example.org/watch?v=' + VID, 'https://example.org/no-query', good[0] + '#private',
                      good[0] + '&lc=duplicate', good[1].replace('youtube','web')):
            with self.assertRaises(ValueError):
                research.secure_url(value, "youtube")
        with self.assertRaises(ValueError):
            research.secure_url(good[0], "tiktok")

    def test_normalization_never_retains_authors_headers_or_raw_supplier_links(self):
        payload = capture()
        payload["collection"].update(headers={"Authorization": KEY}, errors=[KEY], api_key=KEY)
        payload["comments"][0].update(authorDisplayName=KEY, authorChannelId=KEY, cookie=KEY)
        payload["scopes"][0]["related_queries"]["top"][0]["serpapi_link"] = 'https://serpapi.com/search?api_key=' + KEY
        normalized = youtube.normalize(payload, NOW)
        self.assertNotIn(KEY, json.dumps(normalized))
        self.assertTrue(normalized["collection"]["links"])
        self.assertIn("refresh_or_delete_by", normalized["collection"])

    def test_bad_dates_counts_references_and_expired_snapshots_fail(self):
        changes = [("like_count", -1), ("like_count", True), ("published_at", "2027-01-01T00:00:00Z"),
                   ("video_id", "BBBBBBBBBBB"), ("parent_id", "unsafe&key=value")]
        for key, value in changes:
            payload = capture()
            payload["comments"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                youtube.normalize(payload, NOW)
        with self.assertRaisesRegex(ValueError, "expired"):
            youtube.normalize(capture(), NOW + timedelta(days=31))

    def test_queries_and_comment_rows_have_a_separate_youtube_report_section(self):
        source = research.collect_import(youtube.normalize(capture(), NOW), run(), 100)
        result = {"run": run(), "sources": [source], "analysis": {"summary": "Synthetic overview", "hypotheses": []}}
        report = build_report(result)
        self.assertEqual(report["providers"][0]["name"], "YouTube")
        self.assertTrue(all(row["signal"] != "Synthetic older tutorial" for row in report["providers"][0]["rows"]))
        self.assertIn("Trends Rising: +250%", markdown_report(report))
        self.assertIn("Likes (current snapshot): 50", text_report(report))
        self.assertIn("Likes (current snapshot): Unknown", text_report(report))
        self.assertIsNone(report["providers"][0]["chart"])

    def test_http_budget_no_retries_and_secret_safe_failure_receipts(self):
        calls = []
        def denied(request, timeout):
            calls.append(request)
            raise HTTPError(request.full_url, 429, KEY, {}, io.BytesIO(json.dumps({"error": {"message": KEY}}).encode()))
        net = youtube.Network({"youtube_api_key": KEY}, 2, 0, transport=denied, clock=lambda: NOW)
        self.assertIsNone(net.request("youtube", "search", {"q":"synthetic"})[0])
        self.assertIsNone(net.request("youtube", "search", {"q":"synthetic"})[0])
        self.assertEqual(len(calls), 1)
        self.assertEqual(net.calls[0]["status"], "rate_limited")
        self.assertNotIn(KEY, json.dumps(net.calls))
        self.assertIn('key=', calls[0].full_url)

    def test_live_request_shapes_complete_trends_videos_comments_without_real_network(self):
        requests = []
        def respond(request, timeout):
            url, params = urlsplit(request.full_url), parse_qs(urlsplit(request.full_url).query)
            requests.append((url.path, params))
            if url.hostname == 'serpapi.com':
                data = {"search_parameters": {key: params[key][0] for key in ("gprop", "q", "date", "data_type")},
                        "related_queries": scope()["related_queries"], "search_metadata": {"api_key": KEY}}
            elif url.path.endswith('/search'):
                data = {"items": [{"id": {"videoId": VID}, "snippet": {"title": "Synthetic tutorial", "channelId": "creator",
                    "publishedAt": "2025-01-01T00:00:00Z"}}]}
            elif url.path.endswith('/commentThreads'):
                data = {"items": [{"snippet": {"totalReplyCount": 1, "topLevelComment": {"id": "head", "snippet": {
                    "textDisplay": "A synthetic question", "likeCount": 10, "publishedAt": "2026-11-02T00:00:00Z"}}},
                    "replies": {"comments": []}}]}
            else:
                data = {"items": [{"id": "reply", "snippet": {"parentId": "head", "textDisplay": "A synthetic reply",
                    "likeCount": 5, "publishedAt": "2026-11-03T00:00:00Z"}}]}
            return io.BytesIO(json.dumps(data).encode())
        args = type('Args', (), dict(max_calls=10, max_queries=2, max_videos=3, max_trends_calls=2,
            pages_per_video=1, trends_file=None, seed=[], free_trends_calls=2, select_query=[]))()
        net = youtube.Network({"youtube_api_key": KEY, "serpapi_api_key": KEY}, 10, 2,
                              transport=respond, clock=lambda: NOW)
        payload = youtube.collect_capture(run(topic="synthetic"), args, net.keys, net, NOW)
        normalized = youtube.normalize(payload, NOW)
        self.assertLessEqual(len(requests), 10)
        self.assertEqual(normalized["collection"]["external_calls"], len(requests))
        self.assertEqual(payload["videos"][0]["query_ids"], payload["selected_query_ids"])
        self.assertEqual(len([row for row in normalized["observations"] if row["signal_type"] == "comment"]), 2)
        self.assertNotIn(KEY, json.dumps(normalized))
        self.assertEqual(requests[0][1]["gprop"], ["youtube"])
        self.assertEqual(requests[0][1]["date"], ['2026-10-28 2026-11-03'])
        # One Top row and two Rising rows; SerpApi has no YouTube-style items list.
        self.assertEqual([row["returned"] for row in net.calls if row["service"] == "serpapi"], [3])
        self.assertTrue(all(row["returned"] == 1 for row in net.calls if row["service"] == "youtube"))
        searches = [values for path, values in requests if path.endswith('/search')]
        self.assertTrue(all('publishedAfter' not in values for values in searches))

    def test_offline_cli_capture_import_path_does_not_recollect(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, imported, out = base / 'capture.json', base / 'import.json', base / 'run'
            # Exercise real CLI clocks without making the fixture expire in future CI runs.
            current = datetime.now(timezone.utc) - timedelta(seconds=1)
            payload = capture()
            period_args = research.parser().parse_args(['collect', '--providers', 'youtube', '--out', 'unused'])
            payload['requested_window'] = research.parameters(period_args, current)['requested_window']
            for value in payload['scopes']:
                value.update(actual_window=payload['requested_window'], retrieved_at=research.iso(current))
            queries, _ = trends.normalize_scopes(payload['scopes'], current)
            payload['selected_query_ids'] = [queries[0]['source_id']]
            payload['videos'][0].update(query_ids=payload['selected_query_ids'], retrieved_at=research.iso(current))
            for value in payload['comments']:
                value.update(published_at=research.iso(current - timedelta(days=1)), retrieved_at=research.iso(current))
            source.write_text(json.dumps(payload))
            first = subprocess.run([sys.executable, str(SCRIPTS / 'youtube.py'), 'normalize', '--input', str(source), '--out', str(imported)], capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run([sys.executable, str(SCRIPTS / 'research.py'), 'collect', '--providers', 'youtube', '--offline',
                '--as-of', research.iso(current), '--import-file', str(imported), '--out', str(out)], capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            data = json.loads((out / 'results.json').read_text())
            self.assertEqual(data['sources'][0]['provider'], 'youtube')
            self.assertEqual(data['sources'][0]['counts']['accepted'], 6)
            replay = subprocess.run([sys.executable, str(SCRIPTS / 'youtube.py'), 'normalize', '--input', str(source), '--out', str(imported)], capture_output=True, text=True)
            self.assertNotEqual(replay.returncode, 0)


class AccessAndCoverageTests(unittest.TestCase):
    def args(self, **overrides):
        values = dict(max_calls=10, max_queries=2, max_videos=3, max_trends_calls=2,
            pages_per_video=1, trends_file=None, seed=[], free_trends_calls=2, select_query=[])
        values.update(overrides)
        return type('Args', (), values)()

    def test_missing_keys_or_unconfirmed_free_allowance_make_no_calls(self):
        for keys, allowance in (({}, 2), ({'youtube_api_key': KEY}, 2),
                                ({'youtube_api_key': KEY, 'serpapi_api_key': KEY}, 0)):
            net = youtube.Network(keys, 10, allowance, transport=lambda *a, **k: self.fail('unexpected I/O'), clock=lambda: NOW)
            with self.subTest(allowance=allowance), self.assertRaises(ValueError):
                youtube.collect_capture(run(), self.args(free_trends_calls=allowance), keys, net, NOW)
            self.assertEqual(net.used, 0)

    def test_private_setup_status_rotation_removal_and_noninteractive_guard(self):
        from contextlib import redirect_stdout, redirect_stderr
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'NICHE_HUNTER_CONFIG_DIR': directory}), \
                patch.object(youtube.sys.stdin, 'isatty', return_value=True), \
                patch.object(youtube.getpass, 'getpass', return_value=KEY), \
                patch.dict(os.environ, {'YOUTUBE_API_KEY': '', 'SERPAPI_API_KEY': ''}):
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                self.assertEqual(youtube.main(['setup']), 0)
                path = Path(directory) / 'youtube.json'
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(youtube.main(['status']), 0)
                self.assertEqual(youtube.main(['setup', '--replace', '--csv-only']), 0)
                self.assertNotIn('serpapi_api_key', json.loads(path.read_text()))
                self.assertEqual(youtube.main(['setup', '--remove']), 0)
                self.assertEqual(json.loads(path.read_text()), {})
                with patch.object(youtube.sys.stdin, 'isatty', return_value=False):
                    self.assertEqual(youtube.main(['setup']), 2)
            self.assertNotIn(KEY, output.getvalue())

    def test_14_day_comments_are_not_cut_to_shorter_trends_coverage(self):
        payload = capture()
        payload['requested_window'] = run(14)['requested_window']
        payload['comments'].append(comment('older-in-14d', 90, '2026-10-24T12:00:00Z'))
        normalized = youtube.normalize(payload, NOW)
        source = research.collect_import(normalized, run(14), 100)
        self.assertIn('comment:older-in-14d', [row['source_id'] for row in source['observations']])
        self.assertNotEqual(source['actual_window'], run(14)['requested_window'])
        self.assertEqual(normalized['collection']['components']['comments']['window'], run(14)['requested_window'])
        self.assertTrue(any('coverage differs' in note for note in normalized['limitations']))
        report = build_report({'run': run(14), 'sources': [source], 'analysis': {'hypotheses': []}})
        self.assertIn('Trends:', report['providers'][0]['coverage'])
        self.assertIn('Comments: requested interval', report['providers'][0]['coverage'])
        actual = trends.trends_window(run(14)['requested_window'], NOW)
        self.assertEqual(actual['start_at'], '2026-10-21T00:00:00Z')
        requested = research.window(NOW - timedelta(hours=3), NOW)
        actual = trends.trends_window(requested, NOW)
        self.assertEqual(actual['end_at'], '2026-11-04T00:00:00Z')
        self.assertEqual(actual['start_at'], '2026-11-03T00:00:00Z')

    def test_free_and_total_call_caps_stop_without_retries(self):
        for limit in (1, 2, 10):
            called = []
            def empty(request, timeout):
                called.append(request)
                return io.BytesIO(b'{"items": []}')
            net = youtube.Network({'youtube_api_key': KEY, 'serpapi_api_key': KEY}, limit, 1, transport=empty, clock=lambda: NOW)
            for _ in range(15):
                net.request('youtube', 'search', {'q': 'synthetic'})
            self.assertEqual(len(called), limit)
            self.assertEqual(net.used, limit)
        net = youtube.Network({'serpapi_api_key': KEY}, 10, 1, transport=lambda *a, **k: io.BytesIO(b'{}'), clock=lambda: NOW)
        net.request('serpapi', 'related_queries', {})
        net.request('serpapi', 'related_queries', {})
        self.assertEqual(net.used, 1)

    def test_disabled_comments_do_not_block_other_videos(self):
        attempts = []
        def response(request, timeout):
            attempts.append(request)
            if len(attempts) == 1:
                raise HTTPError(request.full_url, 403, 'disabled', {}, io.BytesIO(b'{"error":{"errors":[{"reason":"commentsDisabled"}]}}'))
            return io.BytesIO(b'{"items": []}')
        net = youtube.Network({'youtube_api_key': KEY}, 3, 0, transport=response, clock=lambda: NOW)
        self.assertIsNone(net.request('youtube', 'commentThreads', {'videoId': VID})[0])
        self.assertIsNotNone(net.request('youtube', 'commentThreads', {'videoId': 'BBBBBBBBBBB'})[0])
        self.assertEqual(net.used, 2)
        self.assertEqual(net.calls[0]['status'], 'not_supported')

    def test_malformed_export_and_topic_mismatch_fail_before_video_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'trends.json'
            data = {'schema_version': research.VERSION, 'property': 'youtube', 'scopes': [scope()]}
            manifest.write_text(json.dumps(data))
            keys = {'youtube_api_key': KEY}
            net = youtube.Network(keys, 10, 0, transport=lambda *a, **k: self.fail('unexpected I/O'), clock=lambda: NOW)
            with self.assertRaises(ValueError):
                youtube.collect_capture(run(topic='different topic'), self.args(trends_file=str(manifest)), keys, net, NOW)
            data['scopes'][0]['property'] = 'web'
            manifest.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                youtube.collect_capture(run(), self.args(trends_file=str(manifest)), keys, net, NOW)
            self.assertEqual(net.used, 0)

    def test_post_call_schema_failure_keeps_safe_attempt_accounting(self):
        from contextlib import redirect_stdout, redirect_stderr
        def broken(run_parameters, args, keys, network, now):
            network.calls.append({'service': 'youtube', 'method': 'search', 'retrieved_at': research.iso(now), 'status': 'unavailable'})
            raise ValueError('Untrusted provider error ' + KEY)
        with tempfile.TemporaryDirectory() as directory, patch.object(youtube, 'credentials', return_value={'youtube_api_key': KEY}), \
                patch.object(youtube, 'collect_capture', side_effect=broken):
            output = Path(directory) / 'import.json'
            messages = io.StringIO()
            with redirect_stdout(messages), redirect_stderr(messages):
                result = youtube.main(['collect', '--out', str(output)])
            self.assertEqual(result, 0)
            saved = json.loads(output.read_text())
            self.assertEqual(saved['status'], 'unavailable')
            self.assertEqual(saved['collection']['external_calls'], 1)
            self.assertEqual(saved['observations'], [])
            self.assertNotIn(KEY, output.read_text() + messages.getvalue())

    def test_combined_budget_reserves_live_signals_before_io(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = youtube.normalize(capture(), NOW)
            payload['collection']['external_calls'] = 9
            imported = root / 'import.json'
            imported.write_text(json.dumps(payload))
            output = root / 'run'
            args = research.parser().parse_args(['collect', '--providers', 'youtube,chatgpt',
                '--import-file', str(imported), '--out', str(output)])
            with patch.object(research, 'urlopen', side_effect=AssertionError('unexpected I/O')), self.assertRaisesRegex(ValueError, 'budget'):
                research.collect(args)
            self.assertFalse(output.exists())

    def test_scope_link_mismatch_and_independent_index_charts_are_rejected(self):
        mismatch = scope()
        mismatch['source_url'] = trends.query_url('unrelated seed', run()['requested_window'])
        with self.assertRaises(ValueError):
            trends.normalize_scopes([mismatch], NOW)
        payload = capture()
        payload['scopes'].append(scope('independent'))
        queries, _ = trends.normalize_scopes(payload['scopes'], NOW)
        payload['selected_query_ids'] = [row['source_id'] for row in queries if row['query'] == 'Synthetic query']
        for value in payload['scopes']:
            value['related_queries']['rising'] = []
        source = research.collect_import(youtube.normalize(payload, NOW), run(), 100)
        ids = [row['id'] for row in source['observations'] if row['signal_type'] == 'typed_search']
        result = {'run': run(), 'sources': [source], 'analysis': {'presentation': {'providers': [
            {'provider': 'youtube', 'row_ids': ids, 'conclusion': 'Synthetic only'}]}, 'hypotheses': []}}
        self.assertIsNone(build_report(result)['providers'][0]['chart'])


    def test_small_run_budgets_reserve_a_dated_comment_page(self):
        for maximum in (3, 4):
            def respond(request, timeout):
                params = parse_qs(urlsplit(request.full_url).query)
                if urlsplit(request.full_url).hostname == 'serpapi.com':
                    data = {'search_parameters': {key: params[key][0] for key in ('gprop', 'q', 'date', 'data_type')},
                            'related_queries': scope()['related_queries']}
                elif urlsplit(request.full_url).path.endswith('/search'):
                    data = {'items': [{'id': {'videoId': VID}, 'snippet': {'title': 'Synthetic tutorial',
                        'publishedAt': '2025-01-01T00:00:00Z', 'channelId': 'creator'}}]}
                else:
                    data = {'items': [{'snippet': {'totalReplyCount': 0, 'topLevelComment': {'id': 'budget-comment',
                        'snippet': {'textDisplay': 'Synthetic need', 'publishedAt': '2026-11-02T00:00:00Z', 'likeCount': 4}}}}]}
                return io.BytesIO(json.dumps(data).encode())
            net = youtube.Network({'youtube_api_key': KEY, 'serpapi_api_key': KEY}, maximum, 2,
                transport=respond, clock=lambda: NOW)
            payload = youtube.collect_capture(run(), self.args(max_calls=maximum), net.keys, net, NOW)
            normalized = youtube.normalize(payload, NOW)
            self.assertLessEqual(net.used, maximum)
            self.assertTrue(any(row['signal_type'] == 'comment' for row in normalized['observations']))
            self.assertEqual(len(payload['selected_query_ids']), 1)


    def test_first_pages_are_fair_and_disabled_video_comments_are_not_retried(self):
        for disable_first in (False, True):
            searches, comment_requests = [], []
            def respond(request, timeout):
                url = urlsplit(request.full_url)
                params = parse_qs(url.query)
                if url.hostname == 'serpapi.com':
                    data = {'search_parameters': {key: params[key][0] for key in ('gprop', 'q', 'date', 'data_type')},
                            'related_queries': scope()['related_queries']}
                elif url.path.endswith('/search'):
                    video = VID if not searches else 'BBBBBBBBBBB'
                    searches.append(video)
                    data = {'items': [{'id': {'videoId': video}, 'snippet': {'title': 'Synthetic video', 'channelId': video,
                        'publishedAt': '2025-01-01T00:00:00Z'}}]}
                else:
                    video = params['videoId'][0]
                    comment_requests.append(video)
                    if disable_first and video == VID:
                        raise HTTPError(request.full_url, 403, 'disabled', {},
                            io.BytesIO(b'{"error":{"errors":[{"reason":"commentsDisabled"}]}}'))
                    data = {'items': [], 'nextPageToken': 'more'}
                return io.BytesIO(json.dumps(data).encode())
            maximum = 8 if disable_first else 6
            net = youtube.Network({'youtube_api_key': KEY, 'serpapi_api_key': KEY}, maximum, 2,
                transport=respond, clock=lambda: NOW)
            payload = youtube.collect_capture(run(), self.args(max_calls=maximum, pages_per_video=3), net.keys, net, NOW)
            self.assertEqual(comment_requests[:2], [VID, 'BBBBBBBBBBB'])
            if disable_first:
                self.assertEqual(comment_requests.count(VID), 1)
            self.assertLessEqual(net.used, maximum)
            self.assertTrue(youtube.normalize(payload, NOW)['collection']['pagination_incomplete'])


if __name__ == '__main__':
    unittest.main()
