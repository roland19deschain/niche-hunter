"""One compact report model shared by Markdown, terminal and PDF outputs."""

import math
import re
import textwrap
from datetime import datetime, time, timedelta
from itertools import zip_longest
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

NAMES = {"tiktok": "TikTok", "reddit": "Reddit", "chatgpt": "ChatGPT / OpenAI Signals", "youtube": "YouTube"}
THEME = {"background": "#1D1E20", "surface": "#191C1E", "surface_alt": "#24282B",
         "border": "#3A4145", "text": "#F3F5F7", "muted": "#A3ABB0",
         "accent": "#01A4FE", "cyan": "#5FCCE9", "teal": "#22C6AB",
         "lime": "#B6D46A", "positive": "#28D59C", "negative": "#F27870"}
LABELS = {"signal": "Signal", "data": "Observed data", "overall": "Overall", "suggestions": "Next steps",
          "ideas": "Product ideas", "requested": "Requested", "coverage": "Coverage",
          "unknown": "Unknown", "pending": "Analysis pending.", "end_exclusive": "end exclusive",
          "proposed": "Proposed channel",
          "supplier_popularity": "7-day popularity (supplier)", "matched_videos": "Matched videos",
          "share": "Topic share", "trends_index": "Trends Top index", "trends_growth": "Trends Rising",
          "trends_breakout": "Trends Breakout", "likes_snapshot": "Likes (current snapshot)",
          "comments_window": "Comments: requested interval", "no_comments": "No dated comments collected",
          "trends_seed": "Trends seed", "retained_comments": "Retained comments",
          "comment_videos": "Videos with retained comments", "research_first": "Research first",
          "cited_comments": "Cited comments", "cited_videos": "Videos with cited comments",
          "month_change": "Change vs prior month (pp)"}


def compact(value, limit=420):
    value = " ".join(re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", str(value)).split())
    return value if len(value) <= limit else value[:limit - 3].rsplit(" ", 1)[0] + "..."


def validate_presentation(analysis, result):
    presentation = analysis.get("presentation")
    if presentation is None:
        return
    if not isinstance(presentation, dict):
        raise ValueError("presentation must be an object")
    if "title" in presentation and not isinstance(presentation["title"], str):
        raise ValueError("Report title must be text")
    labels = presentation.get("labels", {})
    if not isinstance(labels, dict) or not all(key in LABELS and isinstance(value, str) and value.strip()
                                               for key, value in labels.items()):
        raise ValueError("Presentation labels must translate the supported report labels")
    providers = presentation.get("providers")
    if not isinstance(providers, list):
        raise ValueError("presentation.providers must include every selected provider")
    sources = {source["provider"]: source for source in result["sources"]}
    seen = set()
    for item in providers:
        if not isinstance(item, dict):
            raise ValueError("Provider presentation must be an object")
        provider = item.get("provider")
        if provider not in sources or provider in seen:
            raise ValueError("Presentation contains an unselected or duplicate provider")
        seen.add(provider)
        if not isinstance(item.get("conclusion"), str) or not item["conclusion"].strip() or len(item["conclusion"]) > 420:
            raise ValueError("Each provider needs a short conclusion")
        known = {row["id"] for row in sources[provider]["observations"]}
        refs = item.get("evidence_ids", [])
        if not isinstance(refs, list) or any(ref not in known for ref in refs) or known and not refs:
            raise ValueError("Provider conclusions must reference that provider's evidence")
        suggestions = item.get("suggestions", [])
        if (not isinstance(suggestions, list) or len(suggestions) > 2
                or any(not isinstance(text, str) or not text.strip() or len(text) > 180 for text in suggestions)):
            raise ValueError("Provider suggestions must contain at most two short actions (180 characters each)")
        selected = item.get("row_ids")
        if selected is not None and (not isinstance(selected, list) or not 1 <= len(selected) <= 6
                                     or len(set(selected)) != len(selected) or any(ref not in known for ref in selected)):
            raise ValueError("Select one to six distinct existing rows from the provider")
    if seen != set(sources):
        raise ValueError("Presentation must cover every selected provider")


def metric_text(metric, labels):
    value = metric["value"]
    if value is None:
        missing_names = {"comment_like_count": "likes_snapshot", "trends_top_index": "trends_index",
                         "trends_growth_percent": "trends_growth"}
        if metric["name"] in missing_names:
            return labels[missing_names[metric["name"]]] + ": " + labels["unknown"]
        return None
    if metric["unit"] == "fraction":
        return f"{labels['share']}: {value * 100:.2f}%"
    names = {"searchVolume": labels["supplier_popularity"], "videoCount": labels["matched_videos"]}
    if metric["name"] == "trends_top_index":
        return f"{labels['trends_index']}: {value:g}/100"
    if metric["name"] == "trends_growth_percent":
        return f"{labels['trends_growth']}: +{value:g}%"
    if metric["name"] == "trends_breakout_lower_bound":
        return f"{labels['trends_breakout']}: >{value:g}%"
    if metric["name"] == "comment_like_count":
        return f"{labels['likes_snapshot']}: {value:,}"
    name = names.get(metric["name"], metric["name"])
    number = f"{value:,.2f}".rstrip("0").rstrip(".") if isinstance(value, float) else f"{value:,}"
    unit = "" if metric["name"] in names else " " + metric["unit"].replace("_", " ")
    return f"{name}: {number}{unit}"


def youtube_comment_sample(rows):
    comments = [row for row in rows if row["signal_type"] == "comment"]
    videos = {video for row in comments for video in parse_qs(urlsplit(row["url"]).query).get("v", [])}
    return len(comments), len(videos)


def requested_period(run, labels):
    window, zone = run["requested_window"], ZoneInfo(run["timezone"])
    start, end = (datetime.fromisoformat(window[key].replace("Z", "+00:00")).astimezone(zone)
                  for key in ("start_at", "end_at"))
    if start.time() == end.time() == time.min:
        first, last = start.date(), end.date() - timedelta(days=1)
        dates = str(first) if first == last else f"{first} – {last}"
        return f"{dates} ({run['timezone']})"
    first, last = (value.isoformat(sep=" ", timespec="auto" if value.second or value.microsecond else "minutes")
                   for value in (start, end))
    return f"{first} – {last} ({run['timezone']}, {labels['end_exclusive']})"


def build_report(result):
    analysis, run = result["analysis"], result["run"]
    presentation = analysis.get("presentation", {})
    labels = {**LABELS, **presentation.get("labels", {})}
    supplied = {item["provider"]: item for item in presentation.get("providers", [])}
    requested = run["requested_window"]
    hypotheses = [item for item in analysis.get("hypotheses", [])
                  if item.get("opportunity", {}).get("priority") != "defer"][:3]
    need_refs = {ref for item in hypotheses for ref in
                 item.get("opportunity", {}).get("demand_evidence_ids", item["evidence_ids"])}
    youtube_evidence = {}
    sources = result["sources"]
    document = {"title": compact(presentation.get("title") or "Niche Hunter", 100),
                "period": requested_period(run, labels),
                "theme": dict(THEME),
                "labels": labels, "providers": [],
                "overall": compact(analysis.get("summary", labels["pending"])) if len(sources) > 1 else "",
                "products": [], "attributions": []}
    for source in sources:
        provider = source["provider"]
        custom = supplied.get(provider, {})
        observations = source["observations"]
        by_id = {row["id"]: row for row in observations}
        if provider == "youtube":
            youtube_evidence = by_id
        if custom.get("row_ids"):
            selected = [by_id[value] for value in custom["row_ids"]]
        else:
            selected = observations
            if provider == "youtube":
                selected = [row for row in selected if row["signal_type"] != "video"]
                conclusion_refs = set(custom.get("evidence_ids", []))
                primary_query = next((row["id"] for row in selected if row["signal_type"] == "typed_search"), None)
                selected = sorted(selected, key=lambda row: (
                    row["id"] != primary_query, row["id"] not in need_refs,
                    row["id"] not in conclusion_refs, row["signal_type"] != "typed_search"))
            if provider == "chatgpt" and source.get("actual_window"):
                start = source["actual_window"]["start_at"]
                selected = [row for row in selected if any(m["window"]["start_at"] == start for m in row["measurements"])]
            selected = selected[:6]
        rows = []
        for row in selected:
            metrics = [metric_text(metric, labels) for metric in row["measurements"]]
            metrics = [value for value in metrics if value]
            rows.append({"id": row["id"], "signal": compact(row["title"], 110), "url": row["url"],
                         "data": "; ".join(metrics[:3]) if metrics else compact(row["summary"], 160),
                         "measurements": row["measurements"]})
        actual = source.get("actual_window")
        coverage = ""
        if actual and actual != requested:
            if actual.get("start_at") and actual.get("end_at"):
                coverage = actual["start_at"][:10] + " / " + actual["end_at"][:10] + " (" + labels["end_exclusive"] + ")"
            else:
                coverage = labels["unknown"] + " (" + actual.get("semantics", "unknown") + ")"
        elif not actual:
            coverage = labels["unknown"]
        if provider == "youtube" and observations:
            scopes = source.get("provenance", {}).get("collection", {}).get("trends_scopes", [])
            ranges = list(dict.fromkeys(scope["actual_window"]["start_at"][:10] + " / "
                + scope["actual_window"]["end_at"][:10] for scope in scopes if scope["actual_window"] != requested))
            if ranges:
                coverage = "Trends: " + "; ".join(ranges[:2]) + " (" + labels["end_exclusive"] + "); " + labels["comments_window"]
            seeds = list(dict.fromkeys(scope["seed"] for scope in scopes if scope.get("seed")))
            comments, videos = youtube_comment_sample(observations)
            details = [coverage] if coverage else []
            if seeds:
                details.append(labels["trends_seed"] + ": " + ", ".join(seeds))
            if comments:
                details += [f"{labels['retained_comments']}: {comments}", f"{labels['comment_videos']}: {videos}"]
            else:
                details.append(labels["no_comments"])
            coverage = ". ".join(details)
        conclusion = custom.get("conclusion")
        if not conclusion and len(sources) == 1 and observations:
            conclusion = analysis.get("summary")
        if not conclusion:
            known = set(by_id)
            findings = [item["text"] for item in analysis.get("findings", [])
                        if known.intersection(item["evidence_ids"])]
            conclusion = " ".join(findings[:2]) or source["reason"]
            if len(sources) == 1 and analysis.get("status") == "pending":
                conclusion = f"{labels['pending']} {conclusion}"
        section = {"provider": provider, "name": NAMES.get(provider, provider), "rows": rows,
                   "coverage": coverage, "conclusion": compact(conclusion), "status": source["status"],
                   "suggestions": [compact(text, 180) for text in custom.get("suggestions", [])],
                   "chart": None}
        if provider == "chatgpt" and rows:
            section["delta_column"] = labels["month_change"]
            changes = {}
            for comparison in source.get("comparisons", []):
                refs = comparison.get("evidence_ids", [])
                delta = comparison.get("percentage_point_change")
                if (comparison.get("method") == "adjacent_calendar_month_share_change" and len(refs) == 2
                        and all(ref in by_id for ref in refs) and type(delta) in (int, float) and math.isfinite(delta)):
                    changes[refs[0]] = round(delta, 2)
            candidates = []
            for row in rows:
                delta = changes.get(row["id"])
                if delta is None:
                    row["delta"] = labels["unknown"]
                    continue
                row["delta"] = f"{delta:+g}" if delta else "0"
                candidates.append({"label": row["signal"], "value": delta, "display": row["delta"],
                                   "formatted_value": row["delta"], "evidence_id": row["id"]})
            if len(candidates) >= 2 and any(item["value"] for item in candidates):
                section["chart"] = candidates
        else:
            # Compare compatible observations only, using their original units and windows.
            candidates, signatures = [], set()
            for row in rows:
                metrics = row["measurements"]
                if not metrics or metrics[0]["value"] is None:
                    break
                metric = metrics[0]
                value = metric["value"]
                if value < 0:
                    break
                signatures.add((metric["name"], metric["unit"], str(sorted(metric["window"].items())),
                                metric.get("comparison_group")))
                display = metric_text(metric, labels)
                candidates.append({"label": row["signal"], "value": value, "display": display,
                                   "formatted_value": display.split(": ", 1)[-1], "evidence_id": row["id"]})
            if len(candidates) == len(rows) and len(rows) >= 2 and len(signatures) == 1 and any(item["value"] > 0 for item in candidates):
                section["chart"] = candidates
        document["providers"].append(section)
        if source.get("provenance", {}).get("license"):
            document["attributions"].append("OpenAI Signals, CC BY 4.0. Derived presentation by Niche Hunter.")
        if provider == "youtube" and observations:
            document["attributions"].append("Data sources: Google Trends (YouTube Search) and YouTube. Relative interest is not a search count; likes are current snapshots.")
    # The calling agent orders its best ideas. The short report displays at most three.
    for hypothesis in hypotheses:
        opportunity = hypothesis.get("opportunity", {})
        description = hypothesis.get("brief") or hypothesis["value_proposition"] + ". " + hypothesis["product_format"]
        cited = dict.fromkeys(opportunity.get("demand_evidence_ids", hypothesis["evidence_ids"]))
        comments, videos = youtube_comment_sample(youtube_evidence[ref] for ref in cited if ref in youtube_evidence)
        document["products"].append({"title": compact(hypothesis["title"], 100),
            "channel": compact(hypothesis["channel"], 100), "need": compact(hypothesis["problem"], 180),
            "description": compact(description, 400), "untested": opportunity.get("channel_fit") == "untested",
            "action": labels["research_first"] if opportunity.get("priority") == "research_more" else "",
            "evidence": f"{labels['cited_comments']}: {comments}. {labels['cited_videos']}: {videos}." if comments else ""})
    return document


def escape_md(value):
    return re.sub(r"([\\`*_{}\[\]<>|])", r"\\\1", str(value)).replace("\n", " ")


def chart_lines(section):
    delta_column = section.get("delta_column")
    maximum = max(abs(item["value"]) for item in section["chart"])
    lines = [delta_column] if delta_column else []
    for item in section["chart"]:
        value = item["value"]
        if delta_column:
            bar = "#" * round(abs(value) / maximum * 9)
            left, right = (bar, "") if value < 0 else ("", bar)
            bars = f"{left:>9}|{right:<9}"
        else:
            bars = ("#" * round(value / maximum * 18)).ljust(18)
        lines.append(f"{compact(item['label'], 30):<30} {bars} {item['display']}")
    return lines


def markdown_report(document):
    labels = document["labels"]
    lines = ["# " + escape_md(document["title"]), "", labels["requested"] + ": " + document["period"], ""]
    for section in document["providers"]:
        lines += ["## " + section["name"], ""]
        if section["coverage"]:
            lines += [labels["coverage"] + ": " + section["coverage"], ""]
        headers = [labels["signal"], labels["data"]]
        if section.get("delta_column"):
            headers.append(section["delta_column"])
        lines += ["| " + " | ".join(escape_md(value) for value in headers) + " |",
                  "| " + " | ".join(["---"] * len(headers)) + " |"]
        if section["rows"]:
            for row in section["rows"]:
                cells = [f"[{escape_md(row['signal'])}]({row['url']})", escape_md(row["data"])]
                if section.get("delta_column"):
                    cells.append(escape_md(row["delta"]))
                lines.append("| " + " | ".join(cells) + " |")
        else:
            lines.append(f"| - | {escape_md(section['status'])} |")
        if section["chart"]:
            lines += ["", "```text", *chart_lines(section), "```"]
        lines += ["", escape_md(section["conclusion"]), ""]
        if section["suggestions"]:
            lines += ["**" + escape_md(labels["suggestions"]) + "**", "",
                      *["- " + escape_md(text) for text in section["suggestions"]], ""]
    if document["overall"]:
        lines += ["## " + labels["overall"], "", escape_md(document["overall"]), ""]
    if document["products"]:
        lines += [("### " if document["overall"] else "## ") + labels["ideas"], ""]
        for index, item in enumerate(document["products"], 1):
            route = item["channel"] + (" (" + labels["proposed"] + ")" if item["untested"] else "")
            action = escape_md(item["action"]) + ". " if item.get("action") else ""
            description = " ".join(filter(None, (item["description"], item.get("evidence"))))
            lines += [f"{index}. **{action}{escape_md(route)} -> {escape_md(item['need'])} -> {escape_md(item['title'])}.** "
                      + escape_md(description), ""]
    for attribution in document["attributions"]:
        lines += [attribution, ""]
    return "\n".join(lines)


def text_row(cells, widths):
    wrapped = [textwrap.wrap(value, width) or [""] for value, width in zip(cells, widths)]
    return ["| " + " | ".join(f"{value:<{width}}" for value, width in zip(line, widths)) + " |"
            for line in zip_longest(*wrapped, fillvalue="")]


def text_report(document, width=96):
    labels = document["labels"]
    lines = [document["title"], "=" * min(width, len(document["title"])), labels["requested"] + ": " + document["period"], ""]
    for section in document["providers"]:
        lines += [section["name"], "-" * len(section["name"])]
        if section["coverage"]:
            lines += [labels["coverage"] + ": " + section["coverage"]]
        headers = [labels["signal"], labels["data"]]
        widths = [34, width - 41]
        if section.get("delta_column"):
            headers.append(section["delta_column"])
            usable = width - 10
            left, delta = min(34, usable * 4 // 10), min(28, usable * 3 // 10)
            widths = [left, usable - left - delta, delta]
        lines += text_row(headers, widths)
        lines.append("+" + "+".join("-" * (column + 2) for column in widths) + "+")
        rows = section["rows"] or [{"signal": "-", "data": section["status"]}]
        for row in rows:
            cells = [row["signal"], row["data"]]
            if section.get("delta_column"):
                cells.append(row["delta"])
            lines += text_row(cells, widths)
        lines += [""]
        if section["chart"]:
            lines += [*chart_lines(section), ""]
        lines += textwrap.wrap(section["conclusion"], width) + [""]
        if section["suggestions"]:
            lines.append(labels["suggestions"] + ":")
            for text in section["suggestions"]:
                lines += textwrap.wrap(text, width, initial_indent="- ", subsequent_indent="  ")
            lines.append("")
    if document["overall"]:
        lines += [labels["overall"], "-" * len(labels["overall"])] + textwrap.wrap(document["overall"], width) + [""]
    if document["products"]:
        lines += [labels["ideas"] + ":"] if document["overall"] else [labels["ideas"], "-" * len(labels["ideas"])]
        for index, item in enumerate(document["products"], 1):
            proposed = " (" + labels["proposed"] + ")" if item["untested"] else ""
            action = item["action"] + ". " if item.get("action") else ""
            description = " ".join(filter(None, (item["description"], item.get("evidence"))))
            route = f"{index}. {action}{item['channel']}{proposed} -> {item['need']} -> {item['title']}."
            lines += textwrap.wrap(f"{route} {description}", width) + [""]
    for attribution in document["attributions"]:
        lines += textwrap.wrap(attribution, width) + [""]
    return "\n".join(lines)
