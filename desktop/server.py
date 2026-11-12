"""Local Claude Desktop MCP tools for Niche Hunter."""

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal
from urllib.parse import quote, quote_plus

import anyio
import certifi
import httpx
from jsonschema import Draft202012Validator
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from mcp.types import ToolAnnotations
from referencing import Registry

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/niche-hunter/scripts"))

import research
import tiktok
import youtube
from public_sources import collect_public
from report_pdf import pdf_bytes


ENV_KEYS = {
    "tokconnect": "NICHE_HUNTER_TOKCONNECT_KEY",
    "youtube_api_key": "NICHE_HUNTER_YOUTUBE_KEY",
    "serpapi_api_key": "NICHE_HUNTER_SERPAPI_KEY",
}
PROVIDER_QUOTAS = {"tiktok": ("tokconnect_credits",),
                   "youtube": ("serpapi_searches", "youtube_search_calls", "youtube_comment_units")}
MANIFEST = Path(__file__).resolve().with_name("manifest.json")
DESKTOP_MANIFEST = json.loads(MANIFEST.read_text(encoding="utf-8"))
QUOTA_SETTINGS = {name: DESKTOP_MANIFEST["user_config"][f"{name}_per_run"]
                  for names in PROVIDER_QUOTAS.values() for name in names}
QUOTA_DEFAULTS = {name: config["default"] for name, config in QUOTA_SETTINGS.items()}
QUOTA_CAPS = {name: config["max"] for name, config in QUOTA_SETTINGS.items()}
TOKCONNECT_URL = "https://mcp.tokconnect.com/mcp"
TOKCONNECT_TOOL = "demand_find_topics"
RUN_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def now():
    return datetime.now(research.UTC)


def injected_keys():
    # Keep provider keys out of the process environment after reading them.
    keys = {}
    for name, variable in ENV_KEYS.items():
        value = os.environ.pop(variable, "").strip()
        if re.fullmatch(r"[A-Za-z0-9._~+/-]{8,500}=*", value):
            keys[name] = value
    return keys


def injected_limits():
    limits = {}
    for name, maximum in QUOTA_CAPS.items():
        value = os.environ.pop(f"NICHE_HUNTER_{name.upper()}_PER_RUN", "").strip()
        if not value:
            limits[name] = QUOTA_DEFAULTS[name]
        else:
            limits[name] = int(value) if re.fullmatch(r"[0-9]", value) and int(value) <= maximum else 0
    return limits


def plan_calls(providers, imported, limits, imported_attempts=0, trends_csv=False, region=None):
    live = set(providers) - set(imported)
    plan = dict.fromkeys(QUOTA_CAPS, 0)
    plan["imported_attempts"] = imported_attempts
    plan["signals_downloads"] = 2 if "chatgpt" in live else 0
    plan.update(research.public_request_plan(live, trends_csv=trends_csv, region=region))
    remaining = 10 - sum(plan.values())
    if "tiktok" in live:
        plan["tokconnect_credits"] = limits["tokconnect_credits"]
        remaining -= plan["tokconnect_credits"]
    if "youtube" in live and remaining >= 3:
        for name in PROVIDER_QUOTAS["youtube"]:
            plan[name] = limits[name]
        plan["youtube_comment_units"] = min(plan["youtube_comment_units"], remaining - 2)
    return plan


def check_size(value):
    data = json.dumps(value, allow_nan=False).encode()
    research.require(len(data) <= research.MAX_BYTES, "Research input exceeds 10 MiB")
    return data


async def collect_tokconnect(key, topic, limit):
    arguments = {"method": "search" if topic else "trending", "limit": min(20, limit)}
    if topic:
        arguments["keyword"] = topic
    capture = {"schema_version": research.VERSION, "external_calls": 0,
               "new_paid_spending_usd": 0, "calls": []}

    async def request():
        headers = {"Authorization": "Bearer " + key}
        async with httpx.AsyncClient(headers=headers, timeout=20, follow_redirects=False,
                                     trust_env=False) as client:
            async with streamable_http_client(TOKCONNECT_URL, http_client=client) as (read, write, _):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=25)) as session:
                    await session.initialize()
                    tools = (await session.list_tools()).tools
                    tool = next((item for item in tools if item.name == TOKCONNECT_TOOL), None)
                    if tool is None:
                        capture["status"] = "not_supported"
                        return
                    Draft202012Validator(tool.inputSchema, registry=Registry()).validate(arguments)
                    capture["external_calls"] = 1
                    response = await session.call_tool(TOKCONNECT_TOOL, arguments)
                    body = response.model_dump(mode="json", by_alias=True, exclude_none=True)
                    check_size(body)
                    capture["calls"].append({"tool": TOKCONNECT_TOOL, "arguments": arguments,
                                             "retrieved_at": research.iso(now()), "response": body})

    try:
        await asyncio.wait_for(request(), timeout=35)
    except Exception as error:
        if capture["calls"]:
            return capture
        # MCP/anyio can wrap transport errors in exception groups.
        pending = [error]
        status = "unavailable"
        while pending:
            item = pending.pop()
            pending.extend(getattr(item, "exceptions", ()))
            if isinstance(item, httpx.HTTPStatusError):
                status = tiktok.ERRORS.get(item.response.status_code, "unavailable")
                break
        capture["status"] = status
    return capture


class DesktopResearch:
    def __init__(self, keys, root, limits=None):
        self.keys = keys
        self.root = root
        self.extension_version = DESKTOP_MANIFEST["version"]
        self.limits = {name: (limits or {}).get(name, default) for name, default in QUOTA_DEFAULTS.items()}

    def check_content(self, value):
        data = check_size(value)
        for key in self.keys.values():
            if any(candidate.encode() in data for candidate in {key, quote(key, safe=""), quote_plus(key)}):
                raise ValueError("Provider credentials are accepted only through the extension settings")

    def status(self, providers, imported=(), region=None, google_trends_csv_supplied=False):
        selected = research.selected_providers(providers)
        checks = []
        for provider in selected:
            missing = []
            if provider in imported:
                route = "normalized_import"
            elif provider == "chatgpt":
                route = "public_openai_signals"
            elif provider == "google_trends" and google_trends_csv_supplied:
                route = "google_trends_web_csv"
            elif provider in research.PUBLIC_ROUTES:
                route = research.PUBLIC_ROUTES[provider]
            elif provider == "tiktok":
                route = "tokconnect_mcp"
                if "tokconnect" not in self.keys:
                    missing.append("TokConnect API key")
            elif provider == "youtube":
                route = "serpapi_and_youtube_data"
                if "youtube_api_key" not in self.keys:
                    missing.append("YouTube Data API v3 key")
                if "serpapi_api_key" not in self.keys:
                    missing.append("SerpApi API key")
            else:
                route = "normalized_import"
                missing.append("permitted Reddit import")
            if provider not in imported:
                missing.extend(name + " per-run limit" for name in PROVIDER_QUOTAS.get(provider, ())
                               if self.limits[name] == 0)
            checks.append({"provider": provider, "ready": not missing, "route": route, "missing": missing})
        return {"ready": all(item["ready"] for item in checks), "providers": checks,
                "extension_version": self.extension_version, "owner_limits": dict(self.limits),
                "limit_defaults": dict(QUOTA_DEFAULTS),
                "maximum_planned_attempts": plan_calls(selected, imported, self.limits, region=region,
                                                       trends_csv=google_trends_csv_supplied),
                "checks": "Configuration and per-run limits only. Provider balances are not checked here.",
                "report_directory": str(self.root)}

    async def collect(self, providers, days, start, end, timezone, topic, region, language,
                      free_tokconnect_credits, free_serpapi_searches, youtube_search_calls,
                      youtube_comment_units, max_records, imports, youtube_seed=None, google_trends_csv=None,
                      app_store_region=None, app_store_topic=None, google_trends_region=None, hunt_mode="product_hunt"):
        self.check_content([providers, start, end, timezone, topic, region, language, imports, youtube_seed,
                            google_trends_csv, app_store_region, app_store_topic, google_trends_region, hunt_mode])
        research.require(1 <= max_records <= 100, "Use 1 to 100 records per provider")
        research.require(topic is None or 0 < len(topic.strip()) <= 100, "Use a topic of at most 100 characters")
        args = SimpleNamespace(providers=providers, exclude_providers=None, days=days, start=start, end=end,
                               timezone=timezone, topic=topic, region=region, language=language,
                               max_records=max_records, request=None, offline=False, signals_file=None,
                               app_store_region=app_store_region, app_store_topic=app_store_topic,
                               google_trends_region=google_trends_region, hunt_mode=hunt_mode)
        run = research.parameters(args, now())
        research.require(google_trends_csv is None or "google_trends" in run["providers"],
                         "Use google_trends_csv only with the Google Trends provider")
        sources = {}
        for payload in imports:
            provider = payload.get("provider")
            research.require(provider in run["providers"] and provider not in sources,
                             "Supply at most one import per selected provider")
            source = research.collect_import(payload, run, max_records)
            research.require(source["status"] in {"ok", "partial"},
                             "Supply a usable import matching the requested topic")
            sources[provider] = source
        status = self.status(providers, sources, app_store_region or region, google_trends_csv is not None)
        if not status["ready"]:
            return {"error": "Configure every selected provider before collection.", **status}

        live_tiktok = "tiktok" in run["providers"] and "tiktok" not in sources
        live_youtube = "youtube" in run["providers"] and "youtube" not in sources
        imported_attempts = sum(source["usage"]["external_calls"] for source in sources.values())
        overrides = {"tokconnect_credits": free_tokconnect_credits, "serpapi_searches": free_serpapi_searches,
                     "youtube_search_calls": youtube_search_calls, "youtube_comment_units": youtube_comment_units}
        research.require(all(value is None or type(value) is int and value >= 0 for value in overrides.values()),
                         "Use a nonnegative whole number for an explicit per-run override")
        available = {name: limit if overrides[name] is None else min(limit, overrides[name])
                     for name, limit in self.limits.items()}
        if live_tiktok:
            research.require(available["tokconnect_credits"] > 0, "Use a TikTok import or exclude TikTok when its limit is zero")
        if live_youtube:
            research.require(all(available[name] > 0 for name in PROVIDER_QUOTAS["youtube"]),
                             "Use a YouTube import or exclude YouTube when one of its limits is zero")
        planned = plan_calls(run["providers"], sources, available, imported_attempts,
                             trends_csv=google_trends_csv is not None, region=app_store_region or region)
        research.require(sum(planned.values()) <= 10, "The selected routes exceed the 10-attempt run budget")
        if youtube_seed is not None:
            research.require(live_youtube and not run["topic"], "Use youtube_seed only with live YouTube and no topic")
            youtube_seed = youtube_seed.strip()
            research.require(0 < len(youtube_seed) <= 100 and "," not in youtube_seed,
                             "Use a single YouTube Trends seed of at most 100 characters")
        if live_youtube:
            research.require(planned["youtube_comment_units"] >= 1,
                             "Leave at least three attempts for YouTube Trends, videos and comments")
            youtube_calls = 2 + planned["youtube_comment_units"]
            research.require(not run["topic"] or "," not in run["topic"], "Use a single YouTube Trends term")
            youtube.trends_window(run["requested_window"], now())

        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        out = self.root / run["id"]
        out.mkdir(mode=0o700)
        actual = dict.fromkeys(planned, 0)
        actual["imported_attempts"] = imported_attempts
        for provider in run["providers"]:
            if provider in sources:
                continue
            source = research.source_result(provider, run)
            try:
                if provider == "chatgpt":
                    source = await asyncio.to_thread(research.collect_signals, run, args, out, source)
                elif provider in research.PUBLIC_ROUTES:
                    source = await asyncio.to_thread(collect_public, run, source, google_trends_csv)
                    actual[provider + "_requests"] = source["usage"]["helper_http_attempts"]
                elif provider == "tiktok":
                    capture = await collect_tokconnect(self.keys["tokconnect"], run["topic"], max_records)
                    source["usage"]["external_calls"] = capture["external_calls"]
                    actual["tokconnect_credits"] = capture["external_calls"]
                    self.check_content(capture)
                    payload = tiktok.normalize(capture, desktop_credit_limit=planned["tokconnect_credits"])
                    run["generated_at"] = research.iso(now())
                    source = research.collect_import(payload, {**run, "topic": None}, max_records, source)
                    source["provenance"]["mode"] = "live_desktop_collection"
                    if run["topic"] and source["observations"]:
                        source["topic_review_pending"] = True
                    if source["status"] == "auth_required":
                        source["reason"] = "TokConnect rejected the extension key. Check it in Claude Desktop settings."
                elif provider == "youtube":
                    options = SimpleNamespace(max_calls=youtube_calls, max_queries=1, max_videos=2,
                                              free_trends_calls=planned["serpapi_searches"], max_trends_calls=1,
                                              trends_file=None, seed=[youtube_seed] if youtube_seed else None,
                                              select_query=None, pages_per_video=1)
                    network = youtube.Network(self.keys, youtube_calls, planned["serpapi_searches"])
                    try:
                        capture = await asyncio.to_thread(youtube.collect_capture, run, options, self.keys, network)
                    finally:
                        source["usage"]["external_calls"] = network.used
                        actual["serpapi_searches"] = sum(call["service"] == "serpapi" for call in network.calls)
                        actual["youtube_search_calls"] = sum(call["method"] == "search" for call in network.calls)
                        actual["youtube_comment_units"] = network.used - actual["serpapi_searches"] - actual["youtube_search_calls"]
                    self.check_content(capture)
                    capture["collection"].pop("free_trends_calls_confirmed", None)
                    payload = youtube.normalize(capture, maximum=max_records)
                    run["generated_at"] = research.iso(now())
                    source = research.collect_import(payload, run, max_records, source)
                    source["provenance"]["mode"] = "live_desktop_collection"
                self.check_content(source)
            except Exception:
                failed = research.source_result(provider, run, source.get("adapter"))
                failed.update(status="unavailable", usage=source["usage"],
                              reason="Provider connection, response or local processing failed; inspect access and coverage.")
                source = failed
            sources[provider] = source

        if "chatgpt" in sources:
            actual["signals_downloads"] = sources["chatgpt"]["usage"]["helper_http_attempts"]
        run["extension_version"] = self.extension_version
        run["desktop_budget"] = {"planned_attempts": planned, "actual_attempts": actual}
        if live_tiktok or live_youtube:
            run["desktop_budget"]["limit_source"] = "extension_settings"
            run["desktop_budget"]["requested_overrides"] = {name: value for name, value in overrides.items()
                                                               if value is not None}
        result = {"schema_version": research.VERSION, "run": run,
                  "catalog": {"version": research.CATALOG["version"],
                              "categories": [item["id"] for item in research.CATALOG["categories"]],
                              "scope": research.CATALOG["scope"]},
                  "sources": [sources[provider] for provider in run["providers"]],
                  "analysis": {"status": "pending", "findings": [], "hypotheses": [],
                               "gaps": ["Calling-agent analysis pending."]}}
        self.check_content(result)
        with (out / "results.json").open("x", encoding="utf-8") as pending:
            json.dump(result, pending, ensure_ascii=False, indent=2, allow_nan=False)
        return result

    def finalize(self, run_id, analysis, tiktok_evidence_ids):
        self.check_content([run_id, analysis, tiktok_evidence_ids])
        research.require(RUN_ID.fullmatch(run_id), "Use a run ID returned by niche_hunter_collect")
        out = self.root / run_id
        result_path = out / "results.json"
        research.require(not out.is_symlink() and not result_path.is_symlink(), "Invalid run directory")
        result = research.load_json(result_path)
        research.require(result["run"]["id"] == run_id, "Run ID does not match the stored result")
        for source in result["sources"]:
            if not source.pop("topic_review_pending", False):
                continue
            known = {row["id"] for row in source["observations"]}
            research.require(tiktok_evidence_ids is not None and set(tiktok_evidence_ids) <= known,
                             "Supply only reviewed TikTok evidence IDs, or an empty list")
            selected = set(tiktok_evidence_ids)
            source["observations"] = [row for row in source["observations"] if row["id"] in selected]
            topic = result["run"]["topic"]
            source["effective_filters"]["topic"] = topic
            for row in source["observations"]:
                row["topic_terms"] = [topic]
            source["counts"]["accepted"] = len(selected)
            collection = source["provenance"]["collection"]
            for call in collection["calls"]:
                call["retained"] = len(selected)
            kept = {row["source_id"] for row in source["observations"]}
            collection["supplier_trend_readings"] = [row for row in collection["supplier_trend_readings"]
                                                      if row["source_id"] in kept]
            if not selected:
                source["reason"] = "No sampled TikTok candidates passed topical review."
        result["analysis"] = research.validate_analysis(analysis, result)
        document = research.build_report(result)
        pdf = pdf_bytes(document)
        for name in ("report.md.tmp", "report.pdf.tmp", "results.json.tmp"):
            research.require(not (out / name).exists() and not (out / name).is_symlink(), "Run has a staged output")
        research.save_run(out, result, pdf)
        return {"directory": str(out), "files": {name: str(out / name)
                for name in ("report.md", "report.pdf", "results.json")},
                "markdown": (out / "report.md").read_text(encoding="utf-8")}


def make_server(desktop):
    server = FastMCP("Niche Hunter Desktop", log_level="ERROR")

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    def niche_hunter_status(providers: str = ",".join(research.PROVIDERS),
                            imported_providers: list[str] | None = None, region: str | None = None,
                            app_store_region: str | None = None, google_trends_csv_supplied: bool = False) -> dict[str, Any]:
        """Check selected provider configuration without making network requests. List only imports already available."""
        try:
            desktop.check_content([providers, imported_providers, region, app_store_region])
            return desktop.status(providers, imported_providers or [], app_store_region or region, google_trends_csv_supplied)
        except ValueError:
            return {"error": "Use a comma-separated list of implemented providers and no credentials."}

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    async def niche_hunter_collect(providers: str = ",".join(research.PROVIDERS), days: int | None = None,
                                   start: str | None = None, end: str | None = None, timezone: str | None = None,
                                   topic: str | None = None, region: str | None = None, language: str | None = None,
                                   free_tokconnect_credits: int | None = None, free_serpapi_searches: int | None = None,
                                   youtube_search_calls: int | None = None, youtube_comment_units: int | None = None,
                                   max_records: int = 20,
                                   imports: list[dict] | None = None, youtube_seed: str | None = None,
                                   google_trends_csv: dict | None = None, app_store_region: str | None = None,
                                   app_store_topic: str | None = None, google_trends_region: str | None = None,
                                   hunt_mode: Literal["product_hunt", "trend_hunt"] = "product_hunt") -> dict[str, Any]:
        """Collect one run after preflight. Omit limit arguments unless the caller explicitly requests a lower cap."""
        try:
            return await desktop.collect(providers, days, start, end, timezone, topic, region, language,
                                         free_tokconnect_credits, free_serpapi_searches, youtube_search_calls, youtube_comment_units,
                                         max_records, imports or [], youtube_seed, google_trends_csv,
                                         app_store_region, app_store_topic, google_trends_region, hunt_mode)
        except (ValueError, KeyError, TypeError, OSError) as error:
            message = str(error) if isinstance(error, ValueError) else ""
            if not message.startswith(("Use ", "Confirm ", "Leave ", "The selected ", "Supply ",
                                       "Provider credentials ", "Research input ")):
                message = "Check the dates, time zone, provider inputs and output directory."
            return {"error": message}

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def niche_hunter_finalize(run_id: str, analysis: dict,
                              tiktok_evidence_ids: list[str] | None = None) -> dict[str, Any]:
        """Write Markdown and PDF from analysis. For a pending TikTok topic review, pass only relevant evidence IDs."""
        try:
            return desktop.finalize(run_id, analysis, tiktok_evidence_ids)
        except (ValueError, KeyError, TypeError, OSError) as error:
            message = str(error) if isinstance(error, ValueError) else ""
            if not message.startswith(("Use a run ID", "Supply only reviewed ", "Analysis contains ",
                                       "PDF font ", "Provider credentials ")):
                message = "Check the run ID, analysis schema, and local output directory."
            return {"error": message}

    return server


async def run_stdio(server):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8")
    # Pass the original streams so the transport cannot close their shared buffers.
    async with stdio_server(stdin=anyio.wrap_file(sys.stdin), stdout=anyio.wrap_file(sys.stdout)) as (read, write):
        protocol = server._mcp_server
        await protocol.run(read, write, protocol.create_initialization_options())


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    desktop = DesktopResearch(injected_keys(), Path.home() / "Niche Hunter Reports", injected_limits())
    anyio.run(run_stdio, make_server(desktop))
