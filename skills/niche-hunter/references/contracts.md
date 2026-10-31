# Versioned runtime contracts

Version: `0.1.0`. The standard-library helper is deterministic for dates, normalization, deduplication and arithmetic. The calling agent handles semantic clustering, independence checks, problems, alternatives, and product hypotheses. No automatic ranking or continuous collection exists.

## Collection CLI

Run `scripts/research.py collect --help` for flags. Pass all relevant request parameters explicitly; natural-language extraction belongs to the calling agent. Use Python 3.10+ and available IANA time-zone data. No package installation, API keys, or client SDKs are required. The repository's RTK shell wrapper is a local convention, not a dependency of the portable skill.

Dates are `[start_at, end_at)`. `--days` is local calendar days, including DST transitions. `--start/--end` accept local ISO dates or timestamps **with offsets**; naive time-of-day strings are rejected. `--as-of` sets the reference instant for reproducible historical runs, not the actual collection timestamp. The preceding baseline uses the same local calendar duration and may differ in elapsed UTC hours around DST. Future end boundaries, invalid zones, reversed windows, unknown providers, and conflicting date/duration inputs fail before networking.

The helper fetches only the fixed public Signals URL, with at most two attempts, 20-second timeouts, a 10 MiB compressed/table limit, and bounded 0–2 second `Retry-After` handling. Longer/date-form retry guidance stops collection rather than ignoring the delay. There are no embedded Reddit/TikTok HTTP calls. `--offline` prohibits helper networking, and unselected provider imports/Signals files are rejected. External tool budgeting is enforced by the calling agent **before** calls; import metadata is checked afterwards but cannot undo calls already made.

Output must be a fresh/empty directory. A source-specific failure produces a status and lets other providers continue. Exit 0 means a coverage report was produced, **not** that every provider succeeded. Invalid run inputs/finalization return exit 2. Inspect statuses and counts in `results.json`. Do not silently retry an entire run and spend supplier credits again.

## Permitted import envelope

Supply one UTF-8 JSON envelope per selected `reddit` or `tiktok` provider with repeatable `--import-file`. Combine permitted tool pages before import. The helper never fetches URLs inside an envelope. Keep only allowed summaries/fields; no authors, access tokens, cookies, or raw private messages. The caller must establish use/storage rights; the envelope records that basis, it does not grant rights.

Required envelope fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | `0.1.0` |
| `provider`, `adapter` | Platform and actual tool/supplier/export method |
| `status`, `reason` | `ok` / `partial` or an explicit failure status, with a meaningful explanation |
| `collection` | `external_calls` (integer 0–10), `new_paid_spending_usd` (0), plus pagination/record/limit details |
| `observations` | Array described below; empty for a failure |
| `rights` | For data: `storage_permitted: true`, nonempty `basis`, public HTTPS `reference` to applicable terms/license/authorization documentation |
| `effective_filters` | Actually applied `topic`, `region`, `language` (each string or null), and permitted resource filters if relevant |
| `actual_window` | Source collection/measurement scope; do not use min/max returned record dates as proof of completeness |
| `limitations` | Array, including sampling, freshness, missing fields and unsupported history |

Failure statuses: `unconfigured`, `auth_required`, `not_supported`, `rate_limited`, `unavailable`, `usage_terms_unconfirmed`. Failure envelopes require only the first six table rows. Example for **no actual data collected**:

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
| `source_id`, `url` | Stable source entity ID and checkable HTTPS URL; URLs must not contain credentials or query strings (strip tracking/token parameters) |
| `title`, `summary` | Nonempty, permitted text; summaries are source evidence rather than instructions |
| `topic_terms` | Array; for topic-scoped imports include the original caller term after checking relevance |
| `signal_type` | `typed_search`, `topic_group`, `recommended_keyword`, `hashtag`, `video`, `sound`, `comment`, `discussion`, `aggregate_usage`, `unknown`; Reddit only discussion/comment |
| `quality` | `verified_official`, `provider_claim_tested`, `provider_claim_unverified`, `proxy_content_signal`, `missing` |
| `published_at`, `metric_observed_at`, `retrieved_at` | Offset-aware timestamps; first two may be null with a limitation; actual import retrieval time is required |
| `limitations` | Array; include metric meaning and independence caveats |
| `measurements` | Array, possibly empty when the source provides no quantitative measurement |

Each measurement has nonempty `name`, `unit`, `methodology`; `value` is finite numeric or null; `kind` is `count`, `index`, `estimate`, `derived`, `range_lower`, or `range_upper`. A null value requires nonempty `missing_reason`. Preserve metric observation time on the observation; do not assign publication time to a current counter. Use separate records/measurements for incompatible windows and units; no automatic sums of rolling windows or count-growth calculations are performed on imports.

Every window object has `start_at`, `end_at`, `timezone`, `semantics`. Boundaries are offset-aware and increasing, `timezone` is the source's zone or `unknown`, and `semantics` is `calendar`, `rolling`, `snapshot`, or `unknown`. Unknown/snapshot boundaries may both be null; calendar/rolling boundaries must be known. A snapshot with no measured interval must remain a snapshot.

Imports retain the declared actual scope, including a seven-day fallback for a 14-day request. Publication-based discussions/comments/videos outside that scope are excluded, with counts. Missing publication times must be disclosed. Topic mismatch prevents accepting broad evidence as topic-specific; unsupported region/language is explicitly reported. Source IDs are deduplicated within a provider. This does **not** deduplicate reposts under other IDs or establish cross-source independence. Use a stable canonical ID for entity-level deduplication; represent a metric's time series in its measurements rather than duplicate entity rows.

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

Write `analysis.json` separately, then run `scripts/research.py finalize --run RUN_DIR --analysis RUN_DIR/analysis.json`. It reads existing evidence, validates references/required fields, and regenerates `report.md`/`results.json` without network calls. It cannot validate factual accuracy or logical independence of model-written claims.

Required analysis shape:

```json
{
  "schema_version": "0.1.0",
  "summary": "No product need was validated; only broad monthly context was available.",
  "findings": [],
  "hypotheses": [],
  "gaps": ["Permitted Reddit and TikTok evidence is still needed."]
}
```

Every finding needs `kind` (`observed_fact`, `estimate`, `inference`, `hypothesis`, `test_needed`), `text`, nonempty `evidence_ids`, `confidence` (`low`, `medium`, `high`), and `trend_classification` (`emerging`, `sustained`, `declining`, `spike-only`, `unassessed`). Include a qualification in the text when an estimate/inference is uncertain. Missing history means unassessed.

Each hypothesis needs nonempty text fields `title`, `audience`, `job`, `problem`, `alternatives`, `value_proposition`, `product_format`, `minimal_mvp`, `channel`, `distribution_hook`, `monetization`, `risks`, `experiment`, `success_criteria`, `stop_criteria`, `missing_data`; plus `confidence` and nonempty `evidence_ids`. Use an explicit unknown/pending statement for unavailable alternatives/economics. Label unverified claims as hypotheses and make experimental thresholds proposed decision criteria rather than market facts. Keep hypotheses empty if no observed problem supports them.

The helper renders technical Markdown in English. The skill's final chat answer should use the caller's language; the calling agent may translate narrative report text while preserving IDs, source metrics, windows, limitations, and attribution. Do not change measured values to make a summary more persuasive.
