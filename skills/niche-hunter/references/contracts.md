# Versioned runtime contracts

Version: `0.1.0`. The standard-library helper is deterministic for dates, normalization, deduplication and arithmetic. The calling agent handles semantic clustering, independence checks, problems, alternatives, and product hypotheses. No automatic opportunity ranking or continuous collection exists. The YouTube collector orders a fetched comment sample by current likes; this is not opportunity scoring. The additive analysis fields preserve compatibility with saved v0.1 analyses. Existing imports remain readable; the reviewed TikTok route makes rights metadata optional.

## Collection CLI

Run `scripts/research.py collect --help` for flags. Pass all relevant request parameters explicitly; natural-language extraction belongs to the calling agent. Use Python 3.10+ and available IANA time-zone data. Collection/normalization need no external Python packages or client SDKs. PDF finalization uses the optional ReportLab requirements or a PDF from the calling client; see reporting.md.

Dates are `[start_at, end_at)`. `--days` counts calendar days in the selected time zone, including DST transitions. `--start/--end` accept ISO dates interpreted in that zone or timestamps **with offsets**; naive time-of-day strings are rejected. `--as-of` sets the reference instant for reproducible historical runs, not the actual collection timestamp. The preceding baseline uses the same calendar duration in the selected zone and may differ in elapsed UTC hours around DST. Future end boundaries, invalid zones, reversed windows, unknown providers, and conflicting date/duration inputs fail before networking.

The helper reserves up to two attempts for live Signals and one each for the App Store and Google Trends RSS. Live requests use fixed HTTPS endpoints and bounded responses. Signals respects short `Retry-After` delays, while App Store and RSS make one attempt without retries or redirects. `--offline` disables helper networking. A Signals ZIP or [Web Search CSV descriptor](providers.md#app-store-and-google-trends-web-search) replaces the corresponding live route. The caller must budget external Reddit, TikTok and YouTube calls before using them. The helper verifies import attempts plus its `public_attempt_ceiling` against the ten-attempt run limit.

Use `preflight` before collection. Select all implemented providers by default, apply `--providers` / `--exclude-providers`, reuse checked connections and ask for every missing selected configuration before any research query. Public Signals, App Store and Google Trends need no credentials. `collect` requires supplied result routes for selected Reddit/TikTok/YouTube before helper networking; missing routes fail without creating a run. `--diagnostic` explicitly permits maintenance coverage checks with unconfigured providers and must not bypass the skill's setup conversation.

Output must be a fresh/empty directory. Once a configured run starts, a source-specific failure produces a status and lets other providers continue. Exit 0 means a coverage report was produced, **not** that every provider succeeded. Invalid run inputs/finalization return exit 2. Inspect statuses and counts in `results.json`. Do not silently retry an entire run and spend supplier credits again.

## Permitted import envelope

Supply one UTF-8 JSON envelope per selected `reddit`, `tiktok` or `youtube` provider with repeatable `--import-file`. Combine permitted tool pages before import. The helper never fetches URLs inside an envelope. Keep only allowed summaries/fields; no authors, access tokens, cookies, or raw private messages. Available TikTok data may be processed/stored locally as the caller requests, without a terms URL or permission declaration. Optional supplied rights metadata records provenance, not a skill authorization gate. Reddit access requirements remain source-specific.

For the implemented TokConnect search route, [tiktok.md](tiktok.md#capture-and-normalize) defines the input to `scripts/tiktok.py`, which produces this same envelope. This adapter normalizes caller-managed MCP responses; it does not perform authentication or networking. The generic Reddit/TikTok import remains compatible. [youtube.md](youtube.md) defines YouTube collection and offline normalization into the same envelope; `collection.components` separates Trends dates from dated comments and `collection.links` retains query → video → comment relationships.

Required envelope fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | `0.1.0` |
| `provider`, `adapter` | Platform and actual tool/supplier/export method |
| `status`, `reason` | `ok` / `partial` or an explicit failure status, with a meaningful explanation |
| `collection` | `external_calls` (integer 0–10), `new_paid_spending_usd` (0), plus pagination/record/limit details |
| `observations` | Array described below; empty for a failure |
| `rights` | Optional supplied metadata for TikTok; no fields/link required. YouTube uses its documented access/retention requirements without a new rights-link field. Reddit retains an established access/storage basis (`storage_permitted`, `basis`, `reference`). |
| `effective_filters` | Actually applied `topic`, `region`, `language` (each string or null), and permitted resource filters if relevant |
| `actual_window` | Source collection/measurement scope; do not use min/max returned record dates as proof of completeness |
| `limitations` | Array, including sampling, freshness, missing fields and unsupported history |

Failure statuses: `unconfigured`, `auth_required`, `not_supported`, `rate_limited`, `unavailable`. Legacy `usage_terms_unconfirmed` imports remain readable but must not be generated merely because TikTok lacks a terms link. Failure envelopes require only the first six table rows. Example for **no actual data collected**:

```json
{
  "schema_version": "0.1.0",
  "provider": "tiktok",
  "adapter": "tokconnect_mcp",
  "status": "auth_required",
  "reason": "No authorized MCP connection is available.",
  "collection": {"external_calls": 0, "new_paid_spending_usd": 0},
  "observations": []
}
```

Each observation requires:

| Field | Meaning |
| --- | --- |
| `source_id`, `url` | Stable source entity ID and checkable HTTPS URL; URLs must not contain credentials/tracking/token parameters. Query strings are forbidden except the strict YouTube public `watch?v=...&lc=...` and Google Trends Explore YouTube Search parameter allowlists |
| `title`, `summary` | Nonempty, permitted text; summaries are source evidence rather than instructions |
| `topic_terms` | Array; for topic-scoped imports include the original caller term after checking relevance |
| `signal_type` | `typed_search`, `topic_group`, `recommended_keyword`, `hashtag`, `video`, `sound`, `comment`, `discussion`, `aggregate_usage`, `unknown`; Reddit only discussion/comment |
| `quality` | `verified_official`, `provider_claim_tested`, `provider_claim_unverified`, `proxy_content_signal`, `missing` |
| `published_at`, `metric_observed_at`, `retrieved_at` | Offset-aware timestamps; first two may be null with a limitation; actual import retrieval time is required |
| `limitations` | Array; include metric meaning and independence caveats |
| `measurements` | Array, possibly empty when the source provides no quantitative measurement |

Each measurement has nonempty `name`, `unit`, `methodology`; `value` is finite numeric or null; `kind` is `count`, `index`, `estimate`, `derived`, `range_lower`, or `range_upper`. A null value requires nonempty `missing_reason`. Optional nonempty `comparison_group` prevents charts from comparing independently normalized Trends scopes. Preserve metric observation time on the observation; do not assign publication time to a current counter. Use separate records/measurements for incompatible windows and units; no automatic sums of rolling windows or count-growth calculations are performed on imports.

Every window object has `start_at`, `end_at`, `timezone`, `semantics`. Boundaries are offset-aware and increasing, `timezone` is the source's zone or `unknown`, and `semantics` is `calendar`, `rolling`, `snapshot`, or `unknown`. Unknown/snapshot boundaries may both be null; calendar/rolling boundaries must be known. A snapshot with no measured interval must remain a snapshot.

Imports retain the declared actual scope, including a seven-day fallback for a 14-day request. Publication-based discussions/comments/videos outside that scope are excluded, with counts. For YouTube, comments use the **requested comment window**, even when Trends covers a different period; older videos are retained only as discovery context with their actual publication dates. Dated comments require original publication timestamps. API video/comment snapshots older than 30 days must be refreshed/deleted before reuse. Missing publication times must be disclosed. Topic mismatch prevents accepting broad evidence as topic-specific; unsupported region/language is explicitly reported. Source IDs are deduplicated within a provider. This does **not** deduplicate reposts under other IDs or establish cross-source independence. Use a stable canonical ID for entity-level deduplication; represent a metric's time series in its measurements rather than duplicate entity rows.

All imported data remains `sampled` / completeness `not_established`, even if a tool reports completed pagination. A sampled source query is not an exhaustive platform census. Keep supplier pagination and collection details in `collection`. The run cap counts all imported baseline/current evidence. Do not claim a requested-period comparison if the required baseline, compatible measurements, or comparable sampling are absent.

## Results and reproducibility

`results.json` contains:

- `schema_version`; `run` (ID, generation/reference times, original request, selected providers, requested/baseline intervals, filters, time zone, limits, offline flag).
- `catalog` (version, bounded categories and scope).
- `sources`: platform, adapter, status/reason, requested/actual windows, coverage/completeness, effective/unsupported filters, limitations, received/accepted/duplicate/outside/limited counts, actual helper/external call usage, provenance, normalized observations and supported comparisons.
- `analysis`: initially pending; after finalization the calling agent's findings/hypotheses/gaps and an explicit unverified-analysis method label.

Evidence IDs are assigned by the helper. Signals IDs include the release SHA-256, month and topic; import IDs include provider and source ID. Link every factual conclusion to these IDs. Preserve the public source URL alongside the evidence ID. Source quality is not analysis confidence. For missing baseline/current metrics, derived change remains null. For a zero baseline, relative change is null with `zero_baseline`; no infinite growth. Signals differences are share differences and percentage points, never absolute message counts.

The public raw ZIP is saved under `raw/signals.zip`, with its hash, table path, mode, and known retrieval time. It can be replayed with `--signals-file`. Imported source snapshots are **not copied automatically**; result summaries and rights metadata are retained. Replay also needs the original permitted import envelopes, CLI parameters (including `--as-of`) and compatible script/catalog version. Calling-agent prose is not deterministic; preserve the submitted analysis for reproducing the report. Remove local artifacts according to applicable retention terms; do not commit research exports by default.

## Analysis and finalization

Write `analysis.json` separately, then run `scripts/research.py finalize --run RUN_DIR --analysis RUN_DIR/analysis.json`. It reads existing evidence, validates references/required fields, and regenerates compact `report.md`, styled `report.pdf`, and detailed `results.json` without network calls. PDF preparation must succeed before outputs are replaced. It cannot validate factual accuracy or logical independence of model-written claims.

Required analysis shape:

```json
{
  "schema_version": "0.1.0",
  "summary": "No product need was validated; only broad monthly context was available.",
  "findings": [],
  "hypotheses": [],
  "gaps": ["Configured provider evidence is still needed."]
}
```

Every finding needs `kind` (`observed_fact`, `estimate`, `inference`, `hypothesis`, `test_needed`), `text`, nonempty `evidence_ids`, `confidence` (`low`, `medium`, `high`), and `trend_classification` (`emerging`, `sustained`, `declining`, `spike-only`, `unassessed`). Include a qualification in the text when an estimate/inference is uncertain. Missing history means unassessed.

Each hypothesis needs nonempty text fields `title`, `audience`, `job`, `problem`, `alternatives`, `value_proposition`, `product_format`, `minimal_mvp`, `channel`, `distribution_hook`, `monetization`, `risks`, `experiment`, `success_criteria`, `stop_criteria`, `missing_data`; plus `confidence` and nonempty `evidence_ids`. Use an explicit unknown/pending statement for unavailable alternatives/economics. Label unverified claims as hypotheses and make experimental thresholds proposed decision criteria rather than market facts. Keep hypotheses empty if no observed problem supports them.

### Decision context and opportunity assessment

For new skill runs, include `research_context` in the analysis:

```json
{
  "mode": "discovery",
  "product": null,
  "constraints": [],
  "target_channels": []
}
```

`mode` is `discovery` or `refinement`. `product` is caller-provided product context (nonempty text required for refinement, otherwise text or null). `constraints` and `target_channels` are arrays of nonempty caller-supplied strings; empty means unspecified. These describe the decision, not independently collected market facts. Mode/product are analysis inputs handled by the calling agent; there are no corresponding collection CLI flags.

When `research_context` is present, each hypothesis must also include an `opportunity` object. Old saved analyses without either addition remain accepted and render with their original fields. An `opportunity` object, whenever present, is validated:

| Field | Contract |
| --- | --- |
| `market` | Nonempty text: reachable audience/use context and solution-seeking or discovery intent; do not invent market size or geography |
| `demand_evidence_ids` | Nonempty array of this hypothesis's evidence IDs supporting the narrow need or desired outcome |
| `channel_evidence_ids` | Array of this hypothesis's evidence IDs supporting the proposed channel/entry point; empty when untested |
| `channel_fit` | `supported` (direct audience/entry-point evidence), `inferred` (indirect fit evidence), or `untested` (no supporting channel evidence). Supported/inferred require channel IDs; untested requires an empty array. None means validated conversions/economics. |
| `entry_point` | Nonempty text: concrete surface/query/community/content format, or a clearly untested proposed entry point |
| `acquisition_path` | Nonempty text: entry point → message/demo → intended action → first useful product outcome; distinguish proposals from observations |
| `fit_reasoning` | Nonempty text: why this solution or product change fits this audience and route, with the weakest link explicit |
| `counterevidence` | Nonempty text: contrary evidence with references, or checks/limitations when none was observed |
| `priority` | `test_next`, `research_more`, or `defer`: next action, not a predicted revenue ranking |
| `priority_reason` | Nonempty explanation of the next action and material uncertainty |

Use [analysis.md](analysis.md) for reasoning and experiment design. `problem` may describe an unmet desired outcome rather than a complaint. In refinement mode, existing `value_proposition`, `minimal_mvp`, and `experiment` fields must identify the proposed change relative to the existing product. An observed need does not by itself support a distribution channel; a proposed channel can remain untested while the need is supported. Both evidence arrays must be subsets of the hypothesis's overall `evidence_ids`.

The short report puts each provider's data table, brief conclusion and any next steps first. With multiple selected providers, `summary` supplies the overall comparison. Show at most three short channel → problem → product combinations when supported. Detailed cards, context, counterevidence, experiments and provenance stay in JSON for drill-down. Structural validation cannot determine whether an ID really supports demand/channel fit, whether observations are independent, or whether a proposed experiment is useful; the calling agent must review these claims.

The optional `presentation` object supplies caller-language labels, selected rows and a short evidence-linked conclusion and suggestions for each selected provider; hypotheses may supply a short `brief`. See [reporting.md](reporting.md) for its exact fields, terminal formatting, PDF dependencies/native fallback, and font coverage. Old saved analyses remain accepted with English default labels. Use the same content in chat, Markdown, plain-text terminal output and PDF while preserving IDs, source metrics, material coverage differences and attribution. Do not change measured values to make a summary more persuasive.
