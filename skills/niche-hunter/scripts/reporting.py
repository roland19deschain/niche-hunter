"""One compact report model shared by Markdown, terminal and PDF outputs."""

import re
import textwrap

NAMES = {"tiktok": "TikTok", "reddit": "Reddit", "chatgpt": "ChatGPT / OpenAI Signals", "youtube": "YouTube"}
THEME = {"background": "#1D1E20", "surface": "#191C1E", "surface_alt": "#24282B",
         "border": "#3A4145", "text": "#F3F5F7", "muted": "#A3ABB0",
         "accent": "#01A4FE", "cyan": "#5FCCE9", "teal": "#22C6AB",
         "lime": "#B6D46A", "positive": "#28D59C", "negative": "#F27870"}
LABELS = {"signal": "Signal", "data": "Observed data", "overall": "Overall",
          "ideas": "Product ideas", "requested": "Requested", "coverage": "Coverage",
          "unknown": "Unknown", "pending": "Analysis pending.", "end_exclusive": "end exclusive",
          "proposed": "Proposed channel",
          "supplier_popularity": "7-day popularity (supplier)", "matched_videos": "Matched videos",
          "share": "Topic share", "trends_index": "Trends Top index", "trends_growth": "Trends Rising",
          "trends_breakout": "Trends Breakout", "likes_snapshot": "Likes (current snapshot)",
          "comments_window": "Comments: requested interval", "no_comments": "No dated comments collected"}


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


def build_report(result):
    analysis, run = result["analysis"], result["run"]
    presentation = analysis.get("presentation", {})
    labels = {**LABELS, **presentation.get("labels", {})}
    supplied = {item["provider"]: item for item in presentation.get("providers", [])}
    requested = run["requested_window"]
    period = f"{requested['start_at']} / {requested['end_at']} ({run['timezone']}, {labels['end_exclusive']})"
    document = {"title": compact(presentation.get("title") or "Niche Hunter", 100), "period": period,
                "theme": dict(THEME),
                "labels": labels, "providers": [], "summary": compact(analysis.get("summary", labels["pending"])),
                "products": [], "attributions": []}
    for source in result["sources"]:
        provider = source["provider"]
        custom = supplied.get(provider, {})
        observations = source["observations"]
        by_id = {row["id"]: row for row in observations}
        if custom.get("row_ids"):
            selected = [by_id[value] for value in custom["row_ids"]]
        else:
            selected = observations
            if provider == "youtube":
                selected = [row for row in selected if row["signal_type"] != "video"]
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
            if not any(row["signal_type"] == "comment" for row in observations):
                coverage = (coverage + "; " if coverage else "") + labels["no_comments"]
        conclusion = custom.get("conclusion")
        if not conclusion:
            known = set(by_id)
            findings = [item["text"] for item in analysis.get("findings", [])
                        if known.intersection(item["evidence_ids"])]
            conclusion = " ".join(findings[:2]) or source["reason"]
        section = {"provider": provider, "name": NAMES.get(provider, provider), "rows": rows,
                   "coverage": coverage, "conclusion": compact(conclusion), "status": source["status"],
                   "chart": None}
        # A chart is useful only for compatible observed measurements, never synthetic growth.
        candidates = []
        signatures = set()
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
            candidates.append({"label": row["signal"], "value": value,
                               "display": metric_text(metric, labels), "formatted_value": metric_text(metric, labels).split(": ", 1)[-1],
                               "evidence_id": row["id"]})
        if len(candidates) == len(rows) and len(rows) >= 2 and len(signatures) == 1 and any(item["value"] > 0 for item in candidates):
            section["chart"] = candidates
        document["providers"].append(section)
        if source.get("provenance", {}).get("license"):
            document["attributions"].append("OpenAI Signals, CC BY 4.0. Derived presentation by Niche Hunter.")
        if provider == "youtube" and observations:
            document["attributions"].append("Data sources: Google Trends (YouTube Search) and YouTube. Relative interest is not a search count; likes are current snapshots.")
    # The calling agent orders its best ideas. The short report displays at most three.
    for hypothesis in analysis.get("hypotheses", []):
        opportunity = hypothesis.get("opportunity", {})
        if opportunity.get("priority") == "defer":
            continue
        description = hypothesis.get("brief") or hypothesis["value_proposition"] + ". " + hypothesis["product_format"]
        document["products"].append({"title": compact(hypothesis["title"], 100),
            "channel": compact(hypothesis["channel"], 100), "need": compact(hypothesis["problem"], 180),
            "description": compact(description, 400), "untested": opportunity.get("channel_fit") == "untested"})
        if len(document["products"]) == 3:
            break
    return document


def escape_md(value):
    return re.sub(r"([\\`*_{}\[\]<>|])", r"\\\1", str(value)).replace("\n", " ")


def markdown_report(document):
    labels = document["labels"]
    lines = ["# " + escape_md(document["title"]), "", labels["requested"] + ": " + document["period"], ""]
    for section in document["providers"]:
        lines += ["## " + section["name"], ""]
        if section["coverage"]:
            lines += [labels["coverage"] + ": " + section["coverage"], ""]
        if section["rows"]:
            lines += [f"| {labels['signal']} | {labels['data']} |", "| --- | --- |"]
            for row in section["rows"]:
                lines.append(f"| [{escape_md(row['signal'])}]({row['url']}) | {escape_md(row['data'])} |")
        else:
            lines += [f"| {labels['signal']} | {labels['data']} |", "| --- | --- |",
                      f"| - | {escape_md(section['status'])} |"]
        if section["chart"]:
            maximum = max(item["value"] for item in section["chart"])
            lines += ["", "```text"]
            for item in section["chart"]:
                bar = "#" * max(0, round(item["value"] / maximum * 18))
                lines.append(f"{compact(item['label'], 30):<30} {bar:<18} {item['display']}")
            lines += ["```"]
        lines += ["", escape_md(section["conclusion"]), ""]
    lines += ["## " + labels["overall"], "", escape_md(document["summary"]), ""]
    if document["products"]:
        lines += ["## " + labels["ideas"], ""]
        for index, item in enumerate(document["products"], 1):
            route = item["channel"] + (" (" + labels["proposed"] + ")" if item["untested"] else "")
            lines += [f"{index}. **{escape_md(route)} -> {escape_md(item['need'])} -> {escape_md(item['title'])}.** "
                      + escape_md(item["description"]), ""]
    for attribution in document["attributions"]:
        lines += [attribution, ""]
    return "\n".join(lines)


def text_report(document, width=96):
    labels = document["labels"]
    lines = [document["title"], "=" * min(width, len(document["title"])), labels["requested"] + ": " + document["period"], ""]
    left, right = 34, width - 41
    for section in document["providers"]:
        lines += [section["name"], "-" * len(section["name"])]
        if section["coverage"]:
            lines += [labels["coverage"] + ": " + section["coverage"]]
        lines += [f"| {labels['signal']:<{left}} | {labels['data']:<{right}} |", "+" + "-" * (left + 2) + "+" + "-" * (right + 2) + "+"]
        rows = section["rows"] or [{"signal": "-", "data": section["status"]}]
        for row in rows:
            a = textwrap.wrap(row["signal"], left) or [""]
            b = textwrap.wrap(row["data"], right) or [""]
            for index in range(max(len(a), len(b))):
                lines.append(f"| {a[index] if index < len(a) else '':<{left}} | {b[index] if index < len(b) else '':<{right}} |")
        lines += [""]
        if section["chart"]:
            maximum = max(item["value"] for item in section["chart"])
            for item in section["chart"]:
                bar = "#" * max(0, round(item["value"] / maximum * 18))
                lines.append(f"{compact(item['label'], 30):<30} {bar:<18} {item['display']}")
            lines += [""]
        lines += textwrap.wrap(section["conclusion"], width) + [""]
    lines += [labels["overall"], "-" * len(labels["overall"])] + textwrap.wrap(document["summary"], width) + [""]
    if document["products"]:
        lines += [labels["ideas"], "-" * len(labels["ideas"])]
        for index, item in enumerate(document["products"], 1):
            proposed = " (" + labels["proposed"] + ")" if item["untested"] else ""
            lines += textwrap.wrap(f"{index}. {item['channel']}{proposed} -> {item['need']} -> {item['title']}. {item['description']}", width) + [""]
    for attribution in document["attributions"]:
        lines += textwrap.wrap(attribution, width) + [""]
    return "\n".join(lines)
