"""Synthetic TokConnect search shapes; no accounts, supplier data, or network calls."""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/niche-hunter/scripts"
sys.path.insert(0, str(SCRIPTS))
import tiktok  # noqa: E402
sys.path.pop(0)

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)


def topic(query_id="101", **changes):
    return {"queryId": query_id, "queryText": "Synthetic notes workflow", "searchVolume": 120,
            "popularity": 7, "videoCount": 0, "trend7d": [80, 100, 120], **changes}


def call(data=None, **changes):
    return {"tool": "demand_find_topics", "arguments": {"method": "search", "keyword": "notes", "limit": 3},
            "retrieved_at": "2026-11-04T10:00:00Z", "response": data if data is not None else
            {"topics": [topic()], "hasMore": False}, **changes}


def capture(calls=None):
    calls = calls if calls is not None else [call()]
    return {"schema_version": "0.1.0", "external_calls": len(calls), "new_paid_spending_usd": 0,
            "free_credits_before": 10, "topic": None,
            "rights": {"storage_permitted": True, "basis": "Synthetic fixture; not supplier permission",
                       "reference": "https://example.org/synthetic-fixture-license"}, "calls": calls}


class TikTokTests(unittest.TestCase):
    def test_client_namespaces_preserve_observations_and_callable_provenance(self):
        expected = tiktok.normalize(capture(), NOW)
        for name in ("mcp__plugin_niche-hunter_tokconnect__demand_find_topics",
                     "mcp__tokconnect__demand_find_topics"):
            with self.subTest(name=name):
                result = tiktok.normalize(capture([call(tool=name)]), NOW)
                self.assertEqual(result["observations"], expected["observations"])
                receipt = result["collection"]["calls"][0]
                self.assertEqual(receipt["tool"], "demand_find_topics")
                self.assertEqual(receipt["callable_tool"], name)
        for name in ("mcp__tokconnect__product_top_selling", "other__demand_find_topics",
                     "mcp__tokconnect__demand_find_topics/extra"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                tiktok.normalize(capture([call(tool=name)]), NOW)

    def test_supported_mcp_wrappers_preserve_missing_zero_and_unknown_semantics(self):
        data = {"topics": [topic(searchVolume=None)], "hasMore": False}
        wrappers = [data, {"data": data, "meta": {"request_id": "test"}},
                    {"structuredContent": data}, {"content": [{"type": "text", "text": json.dumps(data)}]},
                    {"structuredContent": None, "content": [{"type": "text", "text": json.dumps(data)}]},
                    {"jsonrpc": "2.0", "id": 1, "result": {"structuredContent": {"data": data}}}]
        for response in wrappers:
            with self.subTest(response=response):
                result = tiktok.normalize(capture([call(response)]), NOW)
                row = result["observations"][0]
                self.assertEqual(row["source_id"], "101")
                self.assertIsNone(row["measurements"][0]["value"])
                self.assertIn("missing_reason", row["measurements"][0])
                self.assertEqual(row["measurements"][2]["value"], 0)
                self.assertEqual(row["signal_type"], "unknown")
                self.assertEqual(row["quality"], "provider_claim_unverified")
                self.assertIsNone(row["metric_observed_at"])
                self.assertIsNone(result["actual_window"]["start_at"])

    def test_topic_detail_replaces_snapshot_without_summing_or_leaking_fields(self):
        first = call({"topics": [topic()], "hasMore": True, "next": "opaque_cursor"})
        second = call({"topic": topic(searchVolume=150, author="must not ship", access_token="must not ship")},
                      tool="demand_topic", arguments={"method": "detail", "id": "101", "Authorization": "must not ship"})
        result = tiktok.normalize(capture([first, second]), NOW)
        self.assertEqual(len(result["observations"]), 1)
        self.assertEqual(result["observations"][0]["measurements"][0]["value"], 150)
        self.assertEqual(result["collection"]["supplier_trend_readings"][0]["values"], [80, 100, 120])
        self.assertIsNone(result["collection"]["supplier_trend_readings"][0]["timestamps"])
        encoded = json.dumps(result)
        self.assertNotIn("must not ship", encoded)
        self.assertNotIn("opaque_cursor", encoded)

    def test_older_pages_cannot_replace_a_more_recent_metric_snapshot(self):
        newer = call({"topics": [topic(searchVolume=150)], "hasMore": False}, retrieved_at="2026-11-04T11:00:00Z")
        older = call({"topics": [topic(searchVolume=120)], "hasMore": False})
        result = tiktok.normalize(capture([newer, older]), NOW)
        row = result["observations"][0]
        self.assertEqual(row["measurements"][0]["value"], 150)
        self.assertEqual(row["retrieved_at"], newer["retrieved_at"])

    def test_autocomplete_has_stable_ids_but_no_volume_or_typed_search_claim(self):
        expected = None
        variants = [[{"text": "Notes tool"}, {"text": " notes tool "}],
                    ["Notes tool", " notes tool "], ["Notes tool", {"text": " notes tool "}]]
        for suggestions in variants:
            data = {"suggestions": suggestions}
            wrappers = [data, {"data": data}, {"structuredContent": {"data": data}},
                        {"content": [{"type": "text", "text": json.dumps({"data": data})}]},
                        {"jsonrpc": "2.0", "id": 1, "result": {"structuredContent": data}}]
            for response in wrappers:
                with self.subTest(suggestions=suggestions, response=response):
                    result = tiktok.normalize(capture([call(response,
                        tool="mcp__plugin_niche-hunter_tokconnect__demand_keywords",
                        arguments={"method": "tiktok", "keyword": "notes"})]), NOW)
                    self.assertEqual(len(result["observations"]), 1)
                    self.assertEqual(result["observations"][0]["signal_type"], "recommended_keyword")
                    self.assertEqual(result["observations"][0]["measurements"], [])
                    self.assertTrue(result["observations"][0]["source_id"].startswith("keyword:"))
                    if expected is None:
                        expected = result["observations"]
                    self.assertEqual(result["observations"], expected)

    def test_autocomplete_rejects_invalid_entries_and_does_not_accept_topic_strings(self):
        for item in (None, True, 123, [], {}, {"text": None}, {"text": 123}, "", "   "):
            with self.subTest(item=item), self.assertRaises(ValueError):
                tiktok.normalize(capture([call({"suggestions": [item]}, tool="demand_keywords",
                    arguments={"method": "tiktok", "keyword": "notes"})]), NOW)
        with self.assertRaises(ValueError):
            tiktok.normalize(capture([call({"topics": ["Not a topic object"]})]), NOW)

    def test_two_string_autocomplete_calls_reach_collector_without_new_provider_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            payload = capture([call({"data": {"suggestions": ["Synthetic phrase A", "Synthetic phrase B"]}},
                tool="mcp__plugin_niche-hunter_tokconnect__demand_keywords",
                arguments={"method": "tiktok", "keyword": "synthetic"}),
                call({"content": [{"type": "text", "text": json.dumps({"data": {
                    "suggestions": ["synthetic phrase a", "Synthetic phrase C"]}})}]},
                    tool="demand_keywords", arguments={"method": "tiktok", "keyword": "synthetic"})])
            source, imported, run = base / "capture.json", base / "import.json", base / "run"
            source.write_text(json.dumps(payload))
            normalized = subprocess.run([sys.executable, str(SCRIPTS / "tiktok.py"), "--input", str(source),
                                         "--out", str(imported)], capture_output=True, text=True)
            self.assertEqual(normalized.returncode, 0, normalized.stderr)
            captured = json.loads(imported.read_text())
            self.assertEqual(captured["collection"]["external_calls"], 2)
            self.assertEqual([item["status"] for item in captured["collection"]["calls"]], ["ok", "ok"])
            collected = subprocess.run([sys.executable, str(SCRIPTS / "research.py"), "collect", "--providers", "tiktok",
                "--offline", "--as-of", "2026-11-04T12:00:00Z", "--import-file", str(imported), "--out", str(run)],
                capture_output=True, text=True)
            self.assertEqual(collected.returncode, 0, collected.stderr)
            sources = json.loads((run / "results.json").read_text())["sources"]
            self.assertEqual([item["provider"] for item in sources], ["tiktok"])
            self.assertEqual(sources[0]["counts"]["accepted"], 3)
            self.assertEqual(sources[0]["usage"]["external_calls"], 2)
            self.assertTrue(all(item["signal_type"] == "recommended_keyword" and not item["measurements"]
                                for item in sources[0]["observations"]))

    def test_topic_relevance_selection_and_explicit_empty_selection(self):
        payload = capture()
        payload["topic"] = "notes"
        with self.assertRaises(ValueError):
            tiktok.normalize(payload, NOW)
        payload["topic_relevance_checked"] = True
        payload["calls"][0]["selected_ids"] = ["101"]
        self.assertEqual(tiktok.normalize(payload, NOW)["observations"][0]["topic_terms"], ["notes"])
        payload["calls"][0]["selected_ids"] = []
        self.assertEqual(tiktok.normalize(payload, NOW)["observations"], [])
        payload["calls"][0]["selected_ids"] = ["invented"]
        with self.assertRaises(ValueError):
            tiktok.normalize(payload, NOW)

    def test_failures_do_not_erase_successful_evidence_and_preserve_call_usage(self):
        for code, expected in ((401, "auth_required"), (402, "rate_limited"), (403, "not_supported"),
                               (429, "rate_limited"), (502, "unavailable")):
            with self.subTest(code=code):
                failed = call(http_status=code)
                del failed["response"]
                result = tiktok.normalize(capture([failed]), NOW)
                self.assertEqual(result["status"], expected)
                self.assertEqual(result["collection"]["external_calls"], 1)
                mixed = tiktok.normalize(capture([call(), failed]), NOW)
                self.assertEqual(mixed["status"], "partial")
                self.assertEqual(len(mixed["observations"]), 1)
                self.assertEqual(mixed["collection"]["external_calls"], 2)
        result = tiktok.normalize(capture([call({"isError": True, "content": [{"type": "text", "text": "private error"}]})]), NOW)
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("private error", json.dumps(result))

    def test_local_data_does_not_require_terms_link_or_permission_metadata(self):
        for rights in (None, {}, {"storage_permitted": False}, {"basis": "Caller-directed local processing"}):
            payload = capture()
            if rights is None:
                payload.pop("rights")
            else:
                payload["rights"] = rights
            result = tiktok.normalize(payload, NOW)
            self.assertEqual(result["status"], "partial")
            self.assertEqual(len(result["observations"]), 1)

    def test_no_account_failure_requires_no_fake_credentials_or_balance(self):
        payload = {"schema_version": "0.1.0", "status": "auth_required", "external_calls": 0,
                   "new_paid_spending_usd": 0, "calls": []}
        self.assertEqual(tiktok.normalize(payload, NOW)["status"], "auth_required")

    def test_limits_invalid_schema_and_unverified_free_balance_fail_closed(self):
        payloads = []
        for key, value in (("free_credits_before", 0), ("free_credits_before", None),
                           ("external_calls", 11), ("new_paid_spending_usd", 1)):
            payload = capture()
            payload[key] = value
            payloads.append(payload)
        payload = capture([call({"new_unverified_shape": []})])
        payloads.append(payload)
        payloads.append(capture([call(tool="product_top_selling")]))
        payload = capture()
        payload.update(external_calls=2, free_credits_before=1)
        payloads.append(payload)
        for value in (True, -1, float("nan"), "120"):
            payloads.append(capture([call({"topics": [topic(searchVolume=value)]})]))
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                tiktok.normalize(payload, NOW)

    def test_record_cap_and_partial_pagination_are_explicit(self):
        calls = [call({"topics": [topic(str(index)) for index in range(100)], "hasMore": True}),
                 call({"topics": [topic("101")], "hasMore": False})]
        result = tiktok.normalize(capture(calls), NOW)
        self.assertEqual(len(result["observations"]), 100)
        self.assertTrue(any("100-record cap" in limitation for limitation in result["limitations"]))
        self.assertFalse(result["collection"]["calls"][0]["pagination_complete"])

    def test_cli_to_existing_collector_preserves_actual_fallback_and_filter_gaps(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            payload = capture()
            period = {"start_at": "2026-10-28T00:00:00Z", "end_at": "2026-11-04T00:00:00Z",
                      "timezone": "UTC", "semantics": "rolling"}
            payload["actual_window"] = period
            payload["calls"][0]["measurement_window"] = period
            source, imported, run = base / "capture.json", base / "import.json", base / "run"
            source.write_text(json.dumps(payload))
            command = [sys.executable, str(SCRIPTS / "tiktok.py"), "--input", str(source), "--out", str(imported)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            # A second normalization must not overwrite a retained envelope.
            before = imported.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(imported.read_bytes(), before)
            result = subprocess.run([sys.executable, str(SCRIPTS / "research.py"), "collect", "--providers", "tiktok",
                "--days", "14", "--region", "CALLER_REGION", "--language", "CALLER_LANGUAGE",
                "--as-of", "2026-11-04T12:00:00Z", "--offline", "--import-file", str(imported), "--out", str(run)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((run / "results.json").read_text())
            self.assertEqual([row["provider"] for row in data["sources"]], ["tiktok"])
            source = data["sources"][0]
            self.assertEqual(source["actual_window"], period)
            self.assertEqual(source["unsupported_filters"], ["region", "language"])
            self.assertEqual(source["status"], "partial")
            self.assertEqual(source["counts"]["accepted"], 1)
            self.assertEqual(source["comparisons"], [])


if __name__ == "__main__":
    unittest.main()
