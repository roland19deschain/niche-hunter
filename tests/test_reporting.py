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

from test_research import NOW, decision_analysis, envelope, release, research

sys.path.insert(0, str(research.SKILL_DIR / "scripts"))
from reporting import THEME, build_report, markdown_report, text_report
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
    def test_preflight_requires_emoji_for_python_pdf_export(self):
        args = research.parser().parse_args(["preflight", "--providers", "chatgpt"])
        with patch.object(research.importlib.util, "find_spec",
                          side_effect=lambda name: None if name == "emoji" else object()):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertFalse(research.preflight(args))
            self.assertFalse(json.loads(output.getvalue())["pdf"]["ready"])
            args.native_pdf = True
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(research.preflight(args))

    def test_preflight_requires_every_selected_route_and_reuses_checked_clients(self):
        args = research.parser().parse_args(["preflight", "--native-pdf"])
        with patch.object(research, "urlopen", side_effect=AssertionError("preflight must not collect")):
            status, _ = research.readiness(args)
            self.assertEqual([item["provider"] for item in status["providers"] if not item["ready"]], ["reddit", "tiktok", "youtube"])
            status, _ = research.readiness(args, ["reddit", "tiktok", "youtube"])
        self.assertTrue(status["ready"])

    def test_exclusions_apply_before_configuration_and_unknown_providers_are_not_substituted(self):
        args = research.parser().parse_args(["preflight", "--exclude-providers", "reddit,tiktok,youtube,app_store,google_trends", "--native-pdf"])
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
    def test_signals_table_and_chart_use_signed_percentage_point_changes(self):
        from pypdf import PdfReader
        rows = ("2026-09-01,Decline,0.35\n2026-10-01,Decline,0.31\n"
                "2026-09-01,Growth,0.20\n2026-10-01,Growth,0.25\n"
                "2026-10-01,Missing,0.12\n"
                "2026-09-01,Stable,0.20\n2026-10-01,Stable,0.20\n")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "signals.zip"
            path.write_bytes(release(rows))
            args = research.parser().parse_args(["collect", "--providers", "chatgpt", "--offline",
                                                 "--signals-file", str(path), "--out", directory])
            run = research.parameters(args, NOW)
            source = research.collect_signals(run, args, root)
        model = build_report({"run": run, "sources": [source], "analysis": {"summary": "Synthetic comparison."}})
        section = model["providers"][0]
        self.assertEqual([row["delta"] for row in section["rows"]], ["-4", "+5", "Unknown", "0"])
        self.assertEqual([item["value"] for item in section["chart"]], [-4, 5, 0])
        markdown = markdown_report(model)
        self.assertIn("| Topic share: 31.00% | -4 |", markdown)
        self.assertIn("| Topic share: 12.00% | Unknown |", markdown)
        self.assertIn("#######|", markdown)
        self.assertIn("|#########", text_report(model))
        reader = PdfReader(io.BytesIO(pdf_bytes(model)))
        text = " ".join(page.extract_text() for page in reader.pages)
        self.assertIn("Change vs prior month (pp)", text)
        self.assertIn("+5", text)
        self.assertIn("-4", text)

    def test_requested_period_shows_inclusive_local_dates_and_partial_day_times(self):
        result = fixture()
        run = result["run"]
        run["timezone"] = "Etc/GMT-3"
        run["requested_window"].update(start_at="2026-10-24T21:00:00Z", end_at="2026-10-31T21:00:00Z")
        self.assertEqual(build_report(result)["period"], "2026-10-25 – 2026-10-31 (Etc/GMT-3)")
        run["requested_window"]["end_at"] = "2026-10-25T10:45:00Z"
        self.assertEqual(build_report(result)["period"],
                         "2026-10-25 00:00+03:00 – 2026-10-25 13:45+03:00 (Etc/GMT-3, end exclusive)")
        self.assertEqual(run["requested_window"]["end_at"], "2026-10-25T10:45:00Z")

    def test_single_provider_keeps_its_conclusion_suggestions_and_ideas_without_overall(self):
        from pypdf import PdfReader
        result = fixture()
        reference = result["sources"][0]["observations"][0]["id"]
        result["analysis"]["presentation"] = {"providers": [{"provider": "reddit",
            "conclusion": "Synthetic repeated workflow friction; acquisition remains untested.",
            "suggestions": ["Check independent discussions.", "Verify search intent."],
            "evidence_ids": [reference], "row_ids": [reference]}]}
        research.validate_analysis(result["analysis"], result)
        model = build_report(result)
        pdf = PdfReader(io.BytesIO(pdf_bytes(model)))
        for report in (markdown_report(model), text_report(model), " ".join(page.extract_text() for page in pdf.pages)):
            expected = ("Observed data", "Synthetic repeated workflow friction", "Next steps",
                        "Check independent discussions.", "Verify search intent.", "Product ideas", "Proposed channel")
            self.assertEqual(list(map(report.index, expected)), sorted(map(report.index, expected)))
            self.assertNotIn("Overall", report)
            self.assertNotIn(result["analysis"]["summary"], report)
            self.assertIn(result["analysis"]["hypotheses"][0]["brief"], " ".join(report.split()))

    def test_multiple_providers_end_with_one_comparison_and_a_shortlist(self):
        from pypdf import PdfReader
        result = fixture()
        result["run"]["providers"].append("tiktok")
        payload = envelope(result["run"])
        payload["provider"] = "tiktok"
        payload["observations"][0].update(signal_type="unknown", url="https://www.tiktok.com/tag/example")
        result["sources"].append(research.collect_import(payload, result["run"], 100))
        result["analysis"]["summary"] = "Discussions suggest a need; the content sample leaves channel fit open."
        result["analysis"]["presentation"] = {"labels": {"suggestions": "Suggested checks"}, "providers": [
            {"provider": source["provider"], "conclusion": f"{source['provider']} synthetic conclusion.",
             "evidence_ids": [source["observations"][0]["id"]], "suggestions": [f"Verify {source['provider']} fit."]}
            for source in result["sources"]]}
        research.validate_analysis(result["analysis"], result)
        model = build_report(result)
        pdf = PdfReader(io.BytesIO(pdf_bytes(model)))
        for report in (markdown_report(model), text_report(model), " ".join(page.extract_text() for page in pdf.pages)):
            expected = ("reddit synthetic conclusion.", "Verify reddit fit.", "tiktok synthetic conclusion.",
                        "Verify tiktok fit.", "Overall", result["analysis"]["summary"], "Product ideas")
            self.assertEqual(list(map(report.index, expected)), sorted(map(report.index, expected)))
            self.assertEqual(report.count("Suggested checks"), 2)
            self.assertEqual(report.count("Overall"), 1)
        self.assertIn("### Product ideas", markdown_report(model))

    def test_provider_suggestions_must_be_short_actions(self):
        result = fixture()
        reference = result["sources"][0]["observations"][0]["id"]
        provider = {"provider": "reddit", "conclusion": "Synthetic fixture", "evidence_ids": [reference]}
        result["analysis"]["presentation"] = {"providers": [provider]}
        for invalid in ("One action", ["Check a source", " ", "Third action"], [" "], ["x" * 181]):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "Provider suggestions"):
                provider["suggestions"] = invalid
                research.validate_analysis(result["analysis"], result)

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

    def test_youtube_short_report_surfaces_cited_comments_and_marks_research_first(self):
        result = fixture()
        source = result["sources"][0]
        source["provider"] = "youtube"
        source["provenance"] = {"collection": {"trends_scopes": [
            {"seed": "synthetic workflow", "actual_window": result["run"]["requested_window"]},
        ]}}
        template = source["observations"][0]
        source["observations"] = [
            {**template, "id": "query", "signal_type": "typed_search", "title": "Synthetic query"},
            {**template, "id": "second-query", "signal_type": "typed_search", "title": "Second synthetic query"},
            *[{**template, "id": f"comment-{index}", "signal_type": "comment", "title": f"Comment {index}",
               "url": f"https://www.youtube.com/watch?v=abcdefghijk&lc={index}"} for index in range(7)],
        ]
        idea = result["analysis"]["hypotheses"][0]
        idea["evidence_ids"] = ["query", "comment-5", "comment-6"]
        idea["opportunity"]["demand_evidence_ids"] = ["comment-5", "comment-6"]
        model = build_report(result)
        self.assertEqual([row["id"] for row in model["providers"][0]["rows"][:3]],
                         ["query", "comment-5", "comment-6"])
        for text in (markdown_report(model), text_report(model)):
            self.assertIn("Trends seed: synthetic workflow", text)
            self.assertIn("Retained comments: 7", text)
            self.assertIn("Research first", text)
            self.assertIn("Cited comments: 2. Videos with cited comments: 1.", " ".join(text.split()))

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
    def test_dark_theme_keeps_body_labels_links_and_deltas_readable(self):
        def luminance(color):
            channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in channels]
            return sum(weight * value for weight, value in zip((.2126, .7152, .0722), linear))

        for surface in ("background", "surface", "surface_alt"):
            self.assertLess(luminance(THEME[surface]), .03)
            for foreground in ("text", "muted", "cyan", "positive", "negative"):
                contrast = (luminance(THEME[foreground]) + .05) / (luminance(THEME[surface]) + .05)
                with self.subTest(surface=surface, foreground=foreground):
                    self.assertGreaterEqual(contrast, 4.5)

    def test_every_pdf_page_stays_dark_with_legacy_theme_and_preserves_report_content(self):
        from pypdf import PdfReader
        result = fixture()
        second = copy.deepcopy(result["sources"][0]["observations"][0])
        second.update(id="synthetic:second", title="Second synthetic signal")
        second["measurements"][0]["value"] = 7
        result["sources"][0]["observations"].append(second)
        model = build_report(result)
        model["providers"] = [copy.deepcopy(model["providers"][0]) for _ in range(4)]
        markdown, terminal = markdown_report(model), text_report(model)
        model["theme"] = {"paper": "#FFFFFF", "ink": "#000000"}
        self.assertEqual(markdown_report(model), markdown)
        self.assertEqual(text_report(model), terminal)
        reader = PdfReader(io.BytesIO(pdf_bytes(model)))
        self.assertGreaterEqual(len(reader.pages), 2)
        for page in reader.pages:
            fills = [values for values, operator in page.get_contents().operations if operator == b"rg"]
            self.assertTrue(fills)
            self.assertTrue(all(float(value) < .15 for value in fills[0]))
        self.assertIn("Second synthetic signal", " ".join(page.extract_text() for page in reader.pages))

    def test_unicode_report_text_survives_pdf_export(self):
        from pypdf import PdfReader
        result = fixture()
        text = "Unicode " + chr(0x03A9) + " " + chr(0x0416)
        result["analysis"]["summary"] = text
        reader = PdfReader(io.BytesIO(pdf_bytes(build_report(result))))
        self.assertIn(text, " ".join(page.extract_text() for page in reader.pages))

    def test_pdf_omits_uncovered_emoji_and_maps_arrows_without_changing_markdown(self):
        from pypdf import PdfReader
        result = fixture()
        result["sources"][0]["observations"][0]["title"] = "Synthetic comment " + chr(0x1F680) + chr(0xFE0F)
        result["analysis"]["summary"] = "Search " + chr(0x2192) + " tutorial " + chr(0x2192) + " tool " + chr(0x1F44D) + chr(0x1F3FD)
        model = build_report(result)
        markdown = markdown_report(model)
        self.assertIn(chr(0x1F680), markdown)
        text = " ".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf_bytes(model))).pages)
        self.assertIn("Synthetic comment", text)
        self.assertIn("Search -> tutorial -> tool", text)
        self.assertFalse({chr(0x1F680), chr(0x1F44D), chr(0x2192)} & set(text))
        self.assertEqual(markdown_report(model), markdown)

    def test_pdf_handles_emoji_sequences_and_preserves_other_unicode_symbols(self):
        import emoji
        from report_pdf import printable
        sequences = ("\U0001F44D\U0001F3FD", "\U0001F469\u200D\U0001F4BB",
                     "\U0001F3F3\uFE0F\u200D\U0001F308", "\U0001F3F3\u200D\U0001F308",
                     "\U0001F1FA\U0001F1F3", "1\uFE0F\u20E3",
                     "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F")
        for sequence in sequences:
            with self.subTest(sequence=repr(sequence)):
                result = fixture()
                result["analysis"]["summary"] = "Before " + sequence + " after"
                model = build_report(result)
                self.assertIn(sequence, markdown_report(model))
                self.assertTrue(pdf_bytes(model).startswith(b"%PDF-"))
                self.assertEqual(printable(sequence, lambda code: True, emoji), sequence)
        for code in (0x1D11E, 0x2E80, 0x00A9, 0x200D):
            with self.subTest(code=code):
                char = chr(code)
                self.assertEqual(printable(char, lambda value: False, emoji), char)
        for code in (0x1D11E, 0x2E80):
            with self.subTest(code=code):
                result = fixture()
                result["analysis"]["summary"] = chr(code)
                with self.assertRaisesRegex(ValueError, f"U\\+{code:04X}"):
                    pdf_bytes(build_report(result))

    def test_pdf_contains_same_short_report_and_clickable_evidence(self):
        from pypdf import PdfReader
        result = fixture()
        data = pdf_bytes(build_report(result))
        reader = PdfReader(io.BytesIO(data))
        text = " ".join(page.extract_text() for page in reader.pages)
        for value in ("Niche Hunter", "Reddit", "Synthetic fixture", result["analysis"]["summary"], "Action-list export"):
            self.assertIn(value, text)
        self.assertNotIn("Overall", text)
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
            with self.assertRaisesRegex(ValueError, r"font does not cover report text \(U\+4E2D\)"):
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
