"""Synthetic fixtures only. These tests do not validate supplier access or market demand."""

import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

SCRIPT = Path(__file__).resolve().parents[1] / "skills/niche-hunter/scripts/research.py"
SPEC = importlib.util.spec_from_file_location("research", SCRIPT)
research = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research)
NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


def release(rows=None):
    # Deliberately synthetic values, not copied market observations.
    rows = rows or "2026-08-01,Writing,0.20\n2026-09-01,Writing,0.25\n2026-10-01,Writing,0.30\n"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("public_release_csv/" + research.SIGNALS_TABLE,
                         "month,topic,share_of_messages\n" + rows)
    return buffer.getvalue()


def observation(source_id="post1", published="2026-10-28T12:00:00Z"):
    return {"source_id": source_id, "url": "https://www.reddit.com/r/example/comments/" + source_id,
            "title": "Synthetic fixture", "summary": "Synthetic workflow complaint for tests only",
            "topic_terms": ["notes"], "signal_type": "discussion", "quality": "proxy_content_signal",
            "published_at": published, "metric_observed_at": "2026-10-31T12:00:00Z",
            "retrieved_at": "2026-10-31T12:00:00Z", "limitations": ["Synthetic; not live evidence"],
            "measurements": [{"name": "score", "value": None, "unit": "net_votes", "kind": "count",
                "window": {"start_at": None, "end_at": None, "timezone": "unknown", "semantics": "snapshot"},
                "missing_reason": "not provided", "methodology": "Current snapshot; no historical series"}]}


def envelope(run, rows=None):
    return {"schema_version": research.VERSION, "provider": "reddit", "adapter": "synthetic_test_fixture",
            "status": "ok", "reason": "Synthetic fixture with partial sample",
            "collection": {"external_calls": 0, "new_paid_spending_usd": 0, "pagination_complete": False},
            "rights": {"storage_permitted": True, "basis": "Synthetic test fixture, not third-party data",
                       "reference": "https://example.org/synthetic-fixture-license"},
            "effective_filters": {"topic": run["topic"], "region": None, "language": None},
            "actual_window": run["requested_window"], "limitations": ["Synthetic; no live access"],
            "observations": rows if rows is not None else [observation()]}


class ResearchTests(unittest.TestCase):
    def args(self, *flags):
        return research.parser().parse_args(["collect", "--out", "/tmp/unused-test-run", *flags])

    def run_params(self, *flags):
        run = research.parameters(self.args(*flags), NOW)
        run["generated_at"] = research.iso(NOW)  # fixture clock, independent of execution host
        return run

    def test_default_complete_days_and_explicit_14_days(self):
        run = self.run_params("--timezone", "UTC")
        self.assertEqual(run["providers"], ["reddit", "tiktok", "chatgpt"])
        self.assertEqual(run["requested_window"]["start_at"], "2026-10-25T00:00:00Z")
        self.assertEqual(run["requested_window"]["end_at"], "2026-11-01T00:00:00Z")
        self.assertFalse(run["includes_partial_day"])
        run = self.run_params("--days", "14")
        self.assertEqual(run["requested_window"]["start_at"], "2026-10-18T00:00:00Z")
        self.assertEqual(run["timezone_reason"], "disclosed_UTC_fallback")

    def test_calendar_days_across_dst_and_nonoverlapping_baseline(self):
        run = research.parameters(self.args("--timezone", "America/New_York"),
                                  datetime(2026, 11, 2, 12, tzinfo=timezone.utc))
        current = run["requested_window"]
        self.assertEqual(current["start_at"], "2026-10-26T04:00:00Z")
        self.assertEqual(current["end_at"], "2026-11-02T05:00:00Z")
        self.assertEqual(run["baseline_window"]["start_at"], "2026-10-19T04:00:00Z")
        self.assertEqual(run["baseline_window"]["end_at"], current["start_at"])

    def test_custom_dates_and_partial_day(self):
        run = self.run_params("--start", "2026-10-01", "--end", "2026-10-15", "--timezone", "UTC")
        self.assertEqual(run["requested_window"]["end_at"], "2026-10-15T00:00:00Z")
        partial = self.run_params("--start", "2026-10-31T12:00:00Z", "--end", "2026-11-01T10:00:00Z")
        self.assertTrue(partial["includes_partial_day"])

    def test_invalid_input_before_network(self):
        cases = [("--days", "0"), ("--providers", "youtube"), ("--start", "2026-10-01"),
                 ("--start", "2026-10-02", "--end", "2026-10-01"),
                 ("--start", "2026-10-01", "--end", "2026-10-15", "--days", "14"),
                 ("--start", "2026-10-01T12:00:00", "--end", "2026-10-15T12:00:00"),
                 ("--start", "2026-10-01", "--end", "2027-01-01")]
        with patch.object(research, "urlopen", side_effect=AssertionError("unexpected network")):
            for flags in cases:
                with self.subTest(flags=flags), self.assertRaises(ValueError):
                    self.run_params(*flags)

    def test_selected_unavailable_reddit_makes_no_other_calls(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            args = self.args("--providers", "reddit", "--out", directory)
            with patch.object(research, "urlopen", side_effect=AssertionError("unexpected network")):
                research.collect(args)
            result = json.loads((Path(directory) / "results.json").read_text())
            self.assertEqual([x["provider"] for x in result["sources"]], ["reddit"])
            self.assertEqual(result["sources"][0]["status"], "unconfigured")
            with self.assertRaises(ValueError):
                research.collect(args)  # protects previous artifacts

    def test_monthly_fallback_no_future_month_and_share_units(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release.zip"
            path.write_bytes(release())
            args = self.args("--signals-file", str(path), "--offline", "--topic", "Writing",
                             "--region", "US", "--language", "en")
            run = research.parameters(args, datetime(2026, 10, 15, 12, tzinfo=timezone.utc))
            with patch.object(research, "urlopen", side_effect=AssertionError("unexpected network")):
                source = research.collect_signals(run, args, Path(directory))
            self.assertEqual(source["actual_window"]["start_at"], "2026-09-01T00:00:00Z")
            self.assertEqual(source["actual_window"]["end_at"], "2026-10-01T00:00:00Z")
            self.assertEqual(source["unsupported_filters"], ["region", "language"])
            comparison = source["comparisons"][0]
            self.assertEqual(comparison["percentage_point_change"], 5.0)
            self.assertEqual(comparison["relative_change_pct"], 25.0)
            self.assertEqual(comparison["trend_classification"], "unassessed")
            self.assertIsNone(source["provenance"]["retrieved_at"])
            self.assertEqual(source["provenance"]["mode"], "offline_replay")
            self.assertEqual(source["observations"][0]["measurements"][0]["unit"], "fraction")

    def test_narrow_topic_and_offline_missing_file(self):
        args = self.args("--topic", "horoscopes")
        with patch.object(research, "urlopen", side_effect=AssertionError("unexpected network")):
            source = research.collect_signals(research.parameters(args, NOW), args, Path("/tmp"))
        self.assertEqual(source["status"], "not_supported")
        args = self.args("--offline")
        source = research.collect_signals(research.parameters(args, NOW), args, Path("/tmp"))
        self.assertEqual(source["status"], "unavailable")

    def test_bad_signals_does_not_stop_other_sources(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            base = Path(directory)
            path = base / "bad.zip"
            path.write_bytes(release("2026-09-01,Writing,nan\n"))
            args = self.args("--providers", "chatgpt,reddit", "--signals-file", str(path),
                             "--as-of", "2026-11-01T12:00:00Z", "--out", str(base / "run"))
            imported = base / "import.json"
            imported.write_text(json.dumps(envelope(research.parameters(args, NOW))))
            args.import_file = [str(imported)]
            research.collect(args)
            result = json.loads((base / "run/results.json").read_text())
            self.assertEqual(result["sources"][0]["status"], "unavailable")
            self.assertEqual(result["sources"][1]["counts"]["accepted"], 1)

    def test_dedup_exclusive_boundary_and_limits(self):
        run = self.run_params("--providers", "reddit", "--topic", "notes")
        rows = [observation(), observation(), observation("end", run["requested_window"]["end_at"]),
                observation("more")]
        source = research.collect_import(envelope(run, rows), run, 1)
        self.assertEqual(source["counts"], {"received": 4, "accepted": 1, "duplicates": 1,
                                           "outside_window": 1, "limited": 1})
        metric = source["observations"][0]["measurements"][0]
        self.assertIsNone(metric["value"])
        self.assertEqual(metric["missing_reason"], "not provided")

    def test_fallback_window_retained_and_no_rolling_aggregation(self):
        run = self.run_params("--providers", "tiktok", "--days", "14")
        payload = envelope(run, [])
        payload["provider"] = "tiktok"
        payload["actual_window"] = self.run_params()["requested_window"]
        payload["actual_window"]["semantics"] = "rolling"
        row = observation()
        row["signal_type"] = "topic_group"
        row["quality"] = "provider_claim_unverified"
        row["measurements"] = [{"name": "searchVolume", "value": 123, "unit": "supplier_reported_searches",
            "kind": "estimate", "window": payload["actual_window"], "methodology": "Synthetic rolling example"}]
        payload["observations"] = [row]
        source = research.collect_import(payload, run, 100)
        self.assertEqual(source["status"], "partial")
        self.assertEqual(source["actual_window"], payload["actual_window"])
        self.assertEqual(source["observations"][0]["signal_type"], "topic_group")
        self.assertEqual(source["comparisons"], [])
        self.assertEqual(source["observations"][0]["measurements"][0]["value"], 123)

    def test_rights_topic_and_extra_private_fields(self):
        run = self.run_params("--topic", "notes")
        payload = envelope(run)
        payload["rights"]["storage_permitted"] = False
        with self.assertRaises(ValueError):
            research.collect_import(payload, run, 100)
        payload = envelope(run)
        payload["effective_filters"]["topic"] = None
        self.assertEqual(research.collect_import(payload, run, 100)["status"], "not_supported")
        payload = envelope(run)
        payload["observations"][0]["author"] = "must not be retained"
        with self.assertRaises(ValueError):
            research.collect_import(payload, run, 100)

    def test_zero_and_missing_baselines(self):
        self.assertIsNone(research.change(3, 0)["relative_change_pct"])
        self.assertEqual(research.change(3, 0)["reason"], "zero_baseline")
        self.assertIsNone(research.change(3, None)["absolute_change"])
        self.assertEqual(research.change(3, 2)["relative_change_pct"], 50)

    def test_bounded_retries_and_retry_after(self):
        run = self.run_params()
        source = research.source_result("chatgpt", run)
        error = HTTPError(research.SIGNALS_URL, 429, "limited", {"Retry-After": "120"}, None)
        with patch.object(research, "urlopen", side_effect=error) as call, patch.object(research.time, "sleep") as sleep:
            self.assertIsNone(research.fetch_signals(source))
        self.assertEqual(call.call_count, 1)
        sleep.assert_not_called()
        self.assertEqual(source["status"], "rate_limited")
        source = research.source_result("chatgpt", run)
        with patch.object(research, "urlopen", side_effect=URLError("offline")) as call, patch.object(research.time, "sleep"):
            self.assertIsNone(research.fetch_signals(source))
        self.assertEqual(call.call_count, 2)
        self.assertEqual(source["usage"]["helper_http_attempts"], 2)

    def test_budget_and_unselected_import_fail_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "import.json"
            args = self.args("--providers", "chatgpt")
            payload = envelope(research.parameters(args, NOW))
            path.write_text(json.dumps(payload))
            args.import_file = [str(path)]
            with patch.object(research, "urlopen", side_effect=AssertionError("unexpected network")), self.assertRaises(ValueError):
                research.collect(args)
            args.providers = "reddit,tiktok,chatgpt"
            payload["collection"]["external_calls"] = 11
            path.write_text(json.dumps(payload))
            with patch.object(research, "urlopen", side_effect=AssertionError("unexpected network")), self.assertRaises(ValueError):
                research.collect(args)

    def test_analysis_ids_and_finalize_without_recollection(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            args = self.args("--providers", "reddit", "--offline", "--out", directory)
            research.collect(args)
            run_file = Path(directory) / "results.json"
            before = run_file.read_bytes()
            analysis = {"schema_version": research.VERSION, "summary": "No available evidence.",
                        "findings": [], "hypotheses": [], "gaps": ["No permitted access"]}
            path = Path(directory) / "analysis.json"
            invalid = copy.deepcopy(analysis)
            invalid["findings"] = [{"evidence_ids": ["invented"], "confidence": "high"}]
            path.write_text(json.dumps(invalid))
            finalize_args = research.parser().parse_args(["finalize", "--run", directory, "--analysis", str(path)])
            with self.assertRaises(ValueError):
                research.finalize(finalize_args)
            self.assertEqual(run_file.read_bytes(), before)
            path.write_text(json.dumps(analysis))
            with patch.object(research, "urlopen", side_effect=AssertionError("unexpected network")):
                research.finalize(finalize_args)
            result = json.loads(run_file.read_text())
            self.assertEqual(result["analysis"]["status"], "complete")
            self.assertEqual(result["analysis"]["hypotheses"], [])


if __name__ == "__main__":
    unittest.main()
