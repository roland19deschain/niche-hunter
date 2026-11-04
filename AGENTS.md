# NicheHunter

## Project status

- Current release version: 0.2.1 (November 5, 2026), a shared plugin with root `plugin.json`, Claude compatibility metadata, and GitHub-backed marketplaces for both clients. The one canonical skill stays at `skills/niche-hunter/`; project links support contributor use. Native package discovery and client validation are separate from authenticated research; see the release handoff in the development plan for publication evidence.
- Runtime: Python 3.10+ standard library with IANA time-zone data. The helper collects public OpenAI Signals, validates permitted normalized Reddit/TikTok imports, handles dates and source-ID deduplication, and renders reports with calling-agent analysis. Version 0.2.0 adds bundled TokConnect MCP declarations, explicit setup, and `scripts/tiktok.py` for offline normalization of caller-collected TikTok search responses. Version 0.2.1 accepts client-namespaced tool names and adds Claude Code first-run readiness guidance. No authenticated Reddit/TikTok connection has been validated. The `.gitignore` template does not mean this project is an iOS app.
- Canonical project context and handoff: [docs/development-plan.md](./docs/development-plan.md). It consolidates the earlier design and access investigations, distinguishing dated observations, documented capabilities, supplier claims, and open decisions. Start with its handoff snapshot and next-agent checklist.
- The user selected a free pilot and has prepared a TokConnect account for Claude Code onboarding. The plugin is installed in Claude Code; the tested OAuth login failed with `client_uri: Invalid URL` before browser consent. Client authorization, free allowance, permitted storage and live response validation remain pending; no Reddit account/access is configured. The current request defines the authorized work; the plan itself does not authorize account creation, service integrations, advertising experiments, paid purchases, or regular data collection.

## Goal

Create a reusable process/skill for discovering niches for small digital products and refining existing products. The primary decision is `distribution channel → reachable market/audience and need → product or product change`. Follow the Distribution First principle:

`Channel + audience → problems and desires → demand and competitor validation → economic hypothesis → minimal experiment → MVP`.

Research should produce testable, narrowly scoped product hypotheses with primary sources, suitable acquisition channels, and a validation plan. Support exploration through existing search demand and through discovery/content, using paid and organic channels. The caller selects the target product and audience.

Distinguish topic popularity, actual need, willingness to pay, distribution viability, and validated product economics. Publicly available signals help select hypotheses; profitability and product-market fit require real tests.

## Implementation direction

The shared skill and helper implement the collection/reporting slice; semantic analysis is performed by the calling agent. The broader design is:

`research orchestrator → source adapters → observations → topic clustering → trend analyzer → problem extractor → opportunity generator → report`.

- The first iteration targets Reddit, TikTok, and ChatGPT through OpenAI Signals. Follow [the development plan](./docs/development-plan.md), add adapters in stages as access is validated, and explicitly report unavailable sources and actual coverage. The TikTok v1 search route uses client-managed TokConnect tools and `skills/niche-hunter/scripts/tiktok.py`; see the skill's `references/tiktok.md`. Python never reads provider tokens or calls TikTok endpoints. Keep both client connection manifests credential-free and synchronized in endpoint/transport semantics.
- Explicitly describe each adapter's capabilities: authorization, API/import, fields and units, geography, historical depth, pagination, limits, and permitted storage.
- Separate original observations and permitted raw snapshots from derived metrics and LLM conclusions. Preserve run parameters and provenance for reproducibility.
- A skill, CLI, MCP, and continuously running collector are different execution methods; choose based on the task rather than assuming a background process exists.

## Data reliability

- Link every material claim to evidence: source, URL/ID, original text or summary, publication time, metric observation time and retrieval time, extraction method, quality, and limitations.
- Distinguish `observed fact`, `estimate`, `inference`, `hypothesis`, and `test needed`. Clearly label demonstration fixtures and synthetic scenarios.
- Store missing metrics as `null`/`unknown` with a reason. Explicitly label source unavailability (`unconfigured`, `auth_required`, `not_supported`, `rate_limited`, `unavailable`); reflect incomplete collection in coverage.
- Compare only compatible measurements. A popularity index, views, engagement, and search volume have different meanings.
- Deduplicate records, reposts, and cross-posts; account for spam, small samples, seasonality, platform biases, and isolated viral spikes. High confidence requires independent observations.
- Do not replace unknown values with averages in rankings. Store score, confidence, evidence count, and missing data separately; ranking weights are a configurable hypothesis.
- Do not infer actual CPA/CAC/ROAS/LTV from likes, views, cheap clicks, or the presence of competitor ads. Label economic scenarios as assumptions with explicit funnel stages, costs, and time periods.

## Dates and coverage

- Parameterize sources, topics/categories, region, language, dates, time zone, limits, and baseline. Do not assign geography unless the source supports it.
- Use an explicit `[start_at, end_at)` interval and UTC normalization while preserving the source time zone. For TikTok, the default reference window is the last seven complete calendar days in the selected time zone.
- Show the requested window separately from actual coverage, gaps, and sampling limitations. For comparison, choose a comparable preceding, non-overlapping interval of the same duration.
- Current counters on old content do not reconstruct historical values. History requires an available time series or saved observations.
- Do not sum overlapping rolling windows or present them as daily volumes. Show absolute and relative growth; a zero or small baseline requires separate handling.

## Source-specific considerations

- Reddit: look for recurring problems, workarounds, requests for solutions, and shortcomings of alternatives. One popular thread does not establish market growth; keyword heuristics do not replace analysis.
- TikTok: distinguish search queries, recommended keywords, topic groups, hashtags, videos, sounds, and comments. `typed_search` and `topic_group` are not interchangeable.
- The development plan records TikTok Business Discovery, Creator Search Insights, TokConnect, Creative Center, and Research API findings. Verify their current capabilities and access requirements before integration.
- The availability of trending keywords or video search does not establish access to historical user search volumes. When those data are absent, label the result as `content_trends` or `keyword_recommendations`.
- Treat third-party provider metrics as provider claims until the schema, sample responses, units, freshness, and coverage have been verified and compared against the primary source. Record data quality, confidence, and limitations.

## Source access

- Before integration, verify current official documentation, scopes, pricing, limits, geography, and terms of use/storage. A UI link does not prove an API exists.
- Use permitted APIs, tools, or manual CSV/JSON import. Respect authorization and platform restrictions; when access is unavailable, explicitly state the reason and an available verification method.
- Do not store secrets in the repository or logs. Minimize personal data and copying of others' content; account for deletion and permitted retention periods.

## Expected research output

- Main artifacts: `report.md` and `results.json`; analysis input `analysis.json`, public Signals ZIP under the run's `raw/`, and optional permitted normalized imports. Local runs belong in ignored `.nichehunter/runs/`; do not commit third-party exports by default.
- The report includes run parameters, actual coverage, limitations, trends (`emerging`, `sustained`, `declining`, `spike-only`), metrics/baseline, primary sources, user problems, and alternatives.
- For each product hypothesis, specify the audience, narrow task, value proposition, concrete channel entry point and acquisition path, monetization, minimal MVP, risks, and a measurable experiment with success/stop criteria. Keep demand evidence separate from channel evidence, label channel fit, and explain counterevidence and the next action. In refinement mode, connect recommendations to the caller's existing product. Aim for 3–5 hypotheses when supported; fewer or none is valid.

## Working in the repository

- Write committed documentation, skill content, code, and examples in English. Match the caller's language in conversation and generated research reports; preserve technical identifiers in their original form.
- Maintain [docs/development-plan.md](./docs/development-plan.md) in English, including all future updates. Its provider roadmap describes future candidates separately from the MVP.
- Keep the portable skill package in English with neutral examples: no personal paths, workstation tools, regional time-zone examples, fixed country/language presets, or locale-specific topic aliases. Time zone, region, and requested language remain configurable inputs; UTC is the disclosed time-zone fallback. Seed-language metadata describes the catalog, not a default target market.
- Make small changes scoped to the current task while preserving others' work. As implementation is added, update the actual structure and run/verification commands here.
- Work in `develop`. Promote a tested commit to stable `master` for release; do not synchronize unfinished work automatically. Keep plugin versions in both client manifests equal, record changes in `CHANGELOG.md`, and tag releases as `MAJOR.MINOR.PATCH`. Follow [docs/releasing.md](./docs/releasing.md). Release versions are independent of the research JSON schema version.
- Repository commands use standard Python and Git tooling. Apply any additional shell policy from the calling environment without requiring a maintainer-specific tool or configuration file.
- Do not run Xcode builds or SwiftPM package builds unless the user explicitly requests them.
- Verify with `python3 -m unittest discover -s tests -v`. Collect with `python3 skills/niche-hunter/scripts/research.py collect --out .nichehunter/runs/NEW_RUN`. Finalize calling-agent analysis with `python3 skills/niche-hunter/scripts/research.py finalize --run RUN_DIR --analysis RUN_DIR/analysis.json`. Use a fresh output directory. See the skill's references for the v0.1 import/analysis contracts.
- Tests use synthetic fixtures; do not present them as authenticated integration or metric-accuracy verification. The helper uses no external Python packages. The host skill-creator validator separately requires PyYAML in its own environment.
- TikTok capture normalization: `python3 skills/niche-hunter/scripts/tiktok.py --input CAPTURE_JSON --out NEW_IMPORT_JSON`, then pass that file to `research.py collect --import-file`. Rights, verified free allowance, actual retrieval/measurement times, and semantic topic selection belong to the caller; normalization does not establish permission or metric accuracy. No-account/unknown-rights failures are supported without fabricated credentials.
- Release checks: `python3 scripts/release.py check` and `python3 scripts/release.py build --out dist`. CI tests Python 3.10/3.14; tag-triggered Release checks the tag/version and stable ancestry, reruns tests, then publishes GitHub notes/ZIP/checksums. Branch protection is a separate GitHub setting. Verify actual publication and downloaded assets, not just a successful tag push.

Next integration work must establish permitted source access, metric/window semantics and free quotas. Keep credentials in client facilities; the helper never reads them. Follow the development plan's updated handoff checklist and preserve historical evidence dates.
