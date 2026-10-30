# NicheHunter

## Project status

- As of October 31, 2026, the repository contains `README.md`, `avatar.png`, `LICENSE` (MIT), an Xcode/Swift `.gitignore`, this file, and the canonical development plan. There is no source code, skill, integrations, tests, or run commands yet.
- The technology stack, runtime, and execution method have not been selected. The `.gitignore` template does not mean this project is an iOS app.
- Canonical project context and handoff: [docs/development-plan.md](./docs/development-plan.md). It consolidates the earlier design and access investigations, distinguishing dated observations, documented capabilities, supplier claims, and open decisions. Start with its handoff snapshot and next-agent checklist.
- The user selected a free pilot and has no provider accounts or credentials yet. The current request defines the authorized work; the plan itself does not authorize account creation, service integrations, advertising experiments, paid purchases, or regular data collection.

## Goal

Create a reusable process/skill for market research before selecting and developing small iOS or web products. Follow the Distribution First principle:

`Channel + audience → problems and desires → demand and competitor validation → economic hypothesis → minimal experiment → MVP`.

Research should produce testable, narrowly scoped product hypotheses with primary sources, suitable acquisition channels, and a validation plan. Support exploration through existing search demand and through discovery/content, using paid and organic channels. The work is not limited to OutLoud.

Distinguish topic popularity, actual need, willingness to pay, distribution viability, and validated product economics. Publicly available signals help select hypotheses; profitability and product-market fit require real tests.

## Implementation direction

This is a proposed design, not existing modules:

`research orchestrator → source adapters → observations → topic clustering → trend analyzer → problem extractor → opportunity generator → report`.

- The first iteration targets Reddit, TikTok, and ChatGPT through OpenAI Signals. Follow [the development plan](./docs/development-plan.md), add adapters in stages as access is validated, and explicitly report unavailable sources and actual coverage.
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

- Main artifacts: `report.md` and `results.json`; CSV and links to permitted raw snapshots when needed.
- The report includes run parameters, actual coverage, limitations, trends (`emerging`, `sustained`, `declining`, `spike-only`), metrics/baseline, primary sources, user problems, and alternatives.
- For each product hypothesis, specify the audience, narrow task, value proposition, channel, monetization, minimal MVP, risks, and a measurable experiment with success/stop criteria. The initial research MVP should produce 3–5 hypotheses.

## Working in the repository

- Communicate and write project explanations in Russian; preserve technical identifiers in their original form.
- Maintain [docs/development-plan.md](./docs/development-plan.md) in English, including all future updates. Its provider roadmap describes future candidates separately from the MVP.
- Make small changes scoped to the current task while preserving others' work. As implementation is added, update the actual structure and run/verification commands here.
- Run shell commands through `rtk`; rules: `/Users/AlexeyRoik/.codex/RTK.md`.
- Do not run Xcode builds or SwiftPM package builds unless the user explicitly requests them.
- There are currently no build or test commands. Once code is added, verify deterministic aggregation, deduplication, date boundaries, rolling windows, and incomplete/unavailable sources; do not present fixtures as live integration verification.

Before the first implementation, determine an accessible source and its coverage, the runtime/execution format, secret storage, and permitted snapshots. Choose the technology stack based on these conditions.
