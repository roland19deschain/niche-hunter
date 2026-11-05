"""Synthetic configuration, compact-output and PDF invariants; no live research."""

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_research import NOW, decision_analysis, envelope, research

sys.path.insert(0, str(research.SKILL_DIR / "scripts"))
from reporting import build_report, markdown_report, text_report
from report_pdf import pdf_bytes
sys.path.pop(0)


def fixture():
    args = research.parser().parse_args(["collect", "--providers", "reddit", "--out", "unused"])
    run = research.parameters(args, NOW)
    source = research.collect_import(envelope(run), run, 100)
    analysis = decision_analysis(source["observations"][0]["id"])
    analysis["hypotheses"][0]["brief"] = "A focused synthetic workflow tool. One small task with immediate output."
    return {"schema_version": research.VERSION, "run": run, "sources": [source], "analysis": analysis}


class ConfigurationTests(unittest.TestCase):
    def test_preflight_requires_every_selected_route_and_reuses_checked_clients(self):
        args = research.parser().parse_args(["preflight", "--native-pdf"])
        with patch.object(research, "urlopen", side_effect=AssertionError("preflight must not collect")):
            status, _ = research.readiness(args)
            self.assertEqual([item["provider"] for item in status["providers"] if not item["ready"]], ["reddit", "tiktok"])
            status, _ = research.readiness(args, ["reddit", "tiktok"])
        self.assertTrue(status["ready"])

    def test_exclusions_apply_before_configuration_and_unknown_providers_are_not_substituted(self):
        args = research.parser().parse_args(["preflight", "--exclude-providers", "reddit,tiktok", "--native-pdf"])
        status, _ = research.readiness(args)
        self.assertEqual([item["provider"] for item in status["providers"]], ["chatgpt"])
        self.assertTrue(status["ready"])
        args.providers = "unimplemented,chatgpt"
        with self.assertRaises(ValueError):
            research.readiness(args)

    def test_missing_configuration_stops_before_http_or_run_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            args = research.parser().parse_args(["collect", "--out", str(output)])
            with patch.object(research, "urlopen", side_effect=AssertionError("unexpected collection")), self.assertRaises(ValueError):
                research.collect(args)
            self.assertFalse(output.exists())

    def test_initial_failure_import_cannot_silently_replace_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            payload = {"provider": "tiktok", "status": "auth_required", "collection": {"external_calls": 0}}
            path.write_text(json.dumps(payload))
            args = research.parser().parse_args(["preflight", "--providers", "tiktok", "--import-file", str(path)])
            status, _ = research.readiness(args)
            self.assertFalse(status["ready"])
            payload["collection"]["external_calls"] = 1
            path.write_text(json.dumps(payload))
            status, _ = research.readiness(args)
            self.assertTrue(status["ready"])

    def test_tiktok_import_without_terms_metadata_is_accepted(self):
        result = fixture()
        payload = envelope(result["run"])
        payload.update(provider="tiktok")
        payload.pop("rights")
        payload["observations"][0]["signal_type"] = "unknown"
        source = research.collect_import(payload, result["run"], 100)
        self.assertEqual(len(source["observations"]), 1)
        self.assertNotIn("rights", source["provenance"])


class CompactReportTests(unittest.TestCase):
    def test_provider_data_precedes_conclusion_overall_and_short_ideas(self):
        result = fixture()
        reference = result["sources"][0]["observations"][0]["id"]
        result["analysis"]["presentation"] = {"providers": [{"provider": "reddit",
            "conclusion": "Synthetic repeated workflow friction; acquisition remains untested.",
            "evidence_ids": [reference], "row_ids": [reference]}]}
        research.validate_analysis(result["analysis"], result)
        report = markdown_report(build_report(result))
        self.assertLess(report.index("| Signal |"), report.index("Synthetic repeated workflow friction"))
        self.assertLess(report.index("Synthetic repeated workflow friction"), report.index("## Overall"))
        self.assertLess(report.index("## Overall"), report.index("## Product ideas"))
        for value in ("monetization:", "success_criteria:", "Evidence appendix", "Caller constraints"):
            self.assertNotIn(value, report)
        self.assertIn("Proposed channel", report)
        self.assertIn(result["analysis"]["hypotheses"][0]["brief"], report)
        self.assertIn("acquisition_path", json.dumps(result))

    def test_provider_display_cannot_use_an_unselected_source_or_invented_rows(self):
        result = fixture()
        result["analysis"]["presentation"] = {"providers": [{"provider": "tiktok", "conclusion": "Not selected"}]}
        with self.assertRaises(ValueError):
            research.validate_analysis(result["analysis"], result)
        result["analysis"]["presentation"]["providers"] = [{"provider": "reddit", "conclusion": "Synthetic", "row_ids": ["invented"]}]
        with self.assertRaises(ValueError):
            research.validate_analysis(result["analysis"], result)

    def test_zero_ideas_and_incompatible_metrics_do_not_create_ideas_or_charts(self):
        result = fixture()
        result["analysis"]["hypotheses"] = []
        row = copy.deepcopy(result["sources"][0]["observations"][0])
        row["id"] += "2"
        result["sources"][0]["observations"].append(row)
        model = build_report(result)
        self.assertFalse(model["products"])
        self.assertIsNone(model["providers"][0]["chart"])
        self.assertNotIn("## Product ideas", markdown_report(model))

    def test_only_three_best_non_deferred_ideas_are_displayed(self):
        result = fixture()
        ideas = []
        for index in range(6):
            item = copy.deepcopy(result["analysis"]["hypotheses"][0])
            item["title"] = "Synthetic idea " + str(index)
            if index == 0:
                item["opportunity"]["priority"] = "defer"
            ideas.append(item)
        result["analysis"]["hypotheses"] = ideas
        model = build_report(result)
        self.assertEqual([item["title"] for item in model["products"]],
                         ["Synthetic idea 1", "Synthetic idea 2", "Synthetic idea 3"])
        self.assertEqual(len(result["analysis"]["hypotheses"]), 6)

    def test_native_and_terminal_present_same_values_without_metric_mixing(self):
        result = fixture()
        source = result["sources"][0]
        rows = source["observations"]
        rows[0]["measurements"][0].update(value=3)
        other = copy.deepcopy(rows[0])
        other.update(id="synthetic:second", title="Second synthetic signal")
        other["measurements"][0]["value"] = 7
        rows.append(other)
        model = build_report(result)
        self.assertEqual([item["value"] for item in model["providers"][0]["chart"]], [3, 7])
        terminal = text_report(model)
        self.assertIn("#", terminal)
        self.assertIn("score: 7 net votes", terminal)
        other["measurements"][0]["unit"] = "different_unit"
        self.assertIsNone(build_report(result)["providers"][0]["chart"])


class PDFReportTests(unittest.TestCase):
    def test_unicode_report_text_survives_pdf_export(self):
        from pypdf import PdfReader
        result = fixture()
        text = "Unicode " + chr(0x03A9) + " " + chr(0x0416)
        result["analysis"]["summary"] = text
        reader = PdfReader(io.BytesIO(pdf_bytes(build_report(result))))
        self.assertIn(text, " ".join(page.extract_text() for page in reader.pages))

    def test_pdf_contains_same_short_report_and_clickable_evidence(self):
        from pypdf import PdfReader
        model = build_report(fixture())
        data = pdf_bytes(model)
        reader = PdfReader(io.BytesIO(data))
        text = " ".join(page.extract_text() for page in reader.pages)
        for value in ("Niche Hunter", "Reddit", "Synthetic fixture", "Overall", "Action-list export"):
            self.assertIn(value, text)
        links = [annotation.get_object() for page in reader.pages for annotation in page.get("/Annots", [])]
        self.assertTrue(any(item.get("/A", {}).get("/URI", "").startswith("https://www.reddit.com/") for item in links))

    def test_unsupported_font_fails_explicitly_and_preserves_existing_artifacts(self):
        result = fixture()
        result["analysis"]["summary"] = chr(0x4E2D)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            research.save_run(root, result, b"previous-pdf")
            before = {name: (root / name).read_bytes() for name in ("results.json", "report.md", "report.pdf")}
            path = root / "analysis.json"
            path.write_text(json.dumps(result["analysis"]))
            args = research.parser().parse_args(["finalize", "--run", str(root), "--analysis", str(path)])
            with self.assertRaisesRegex(ValueError, "font does not cover"):
                research.finalize(args)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in before})

    def test_finalize_creates_both_exports_without_new_collection(self):
        from pypdf import PdfReader
        result = fixture()
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            research.save_run(root, result)
            path = root / "analysis.json"
            path.write_text(json.dumps(result["analysis"]))
            args = research.parser().parse_args(["finalize", "--run", str(root), "--analysis", str(path)])
            with patch.object(research, "urlopen", side_effect=AssertionError("unexpected collection")):
                research.finalize(args)
            self.assertGreater(len(PdfReader(root / "report.pdf").pages), 0)
            data = json.loads((root / "results.json").read_text())
            self.assertEqual(set(data["exports"]), {"report.md", "report.pdf"})
            self.assertEqual(data["sources"], result["sources"])

    def test_native_pdf_route_reuses_export_and_rejects_incomplete_files(self):
        result = fixture()
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            research.save_run(root, result)
            path = root / "analysis.json"
            path.write_text(json.dumps(result["analysis"]))
            exported = root / "native.pdf"
            exported.write_bytes(b"not an exported PDF")
            args = research.parser().parse_args(["finalize", "--run", str(root), "--analysis", str(path),
                                                 "--pdf-file", str(exported)])
            before = (root / "results.json").read_bytes()
            with self.assertRaises(ValueError):
                research.finalize(args)
            self.assertEqual((root / "results.json").read_bytes(), before)
            exported.write_bytes(pdf_bytes(build_report(result)))
            research.finalize(args)
            self.assertEqual((root / "report.pdf").read_bytes(), exported.read_bytes())


if __name__ == "__main__":
    unittest.main()
