# Changelog

## [Unreleased]

## [0.11.0] - 2026-11-12

- Use built-in per-run limits for Claude Desktop. Blank settings use the defaults, saved overrides remain in effect, and ordinary runs skip numeric quota questions.

## [0.10.0] - 2026-11-12

- Use the bundled PDF exporter for the Claude Desktop companion. Guide users to the extension settings when its tools are missing.

## [0.9.0] - 2026-11-12

- Add credential-free App Store competitor snapshots and Google Trends Web Search via Trending Now RSS or a related-queries CSV.
- Confirm the selected public source scopes on every skill run. Tier 1 uses separate US and UK App Store snapshots and US Google Trends RSS. Allow individual provider overrides.

## [0.8.0] - 2026-11-11

- Add up to two short next steps per provider. For runs with multiple providers, compare the available evidence and identify which channel and product to validate first when the evidence supports a preference.
- Show month-to-month Signals changes in percentage points and chart comparable changes around zero. Display requested periods as local calendar dates or local times for partial days.
- Ground comments about evidence quality in cited, observable patterns.

## [0.6.2] - 2026-11-11

- Avoid positional argument substitution in the skill's spending instruction and validate the shared skill at packaging time.
- Expose the running Desktop extension version and attempt plan. Apply owner-configured per-run caps and caller-reported available allowances before live collection, and record attempted usage by service.
- Support a caller-selected Trends seed in broad Desktop YouTube runs. Show seed and sample coverage, prioritize cited evidence, and label hypotheses that require more research in compact exports.

## [0.6.1] - 2026-11-11

Fixes from the first live Desktop YouTube run.

- Keep PDF export working when quoted source text contains emoji. Recognized emoji sequences with missing glyphs are omitted from the PDF, and uncovered arrows become ASCII (`->`). Other missing symbols still raise an explicit error listing their code points. Markdown and JSON keep the original text. Chart labels are included in the coverage check.
- Bundle the emoji recognition data in the Desktop extension and declare the dependency for Python PDF export.
- Count the Top and Rising related queries returned in SerpApi call receipts instead of always recording `returned: 0`.

## [0.6.0] - 2026-11-10

Claude Desktop pilot for Apple silicon Macs.

- Add a local MCPB with native sensitive fields for TokConnect, YouTube Data API v3 and SerpApi. The companion skill ZIP guides first-run setup and uses the local tools for preflight, collection and Markdown/PDF export.
- Check the exact provider selection and confirmed allowance before collection. ChatGPT uses public Signals, and Reddit uses permitted imports. Save reports to the Mac for access in Finder.
- Publish the Desktop MCPB and companion skill ZIP alongside the shared plugin archive. Verification uses synthetic data; native Claude Desktop installation and authenticated provider runs are pilot acceptance checks.

Download both Desktop assets from this release and follow the [installation guide](https://github.com/roland19deschain/niche-hunter/blob/0.6.0/skills/niche-hunter/references/claude-desktop.md).

## [0.5.0] - 2026-11-06

YouTube Search interest and dated-comment provider.

- Add `youtube` to provider selection/preflight/defaults with automatic SerpApi Trends delivery or native Google Trends related-query CSVs, followed by YouTube Data API video/comment sampling.
- Add private, hidden local key setup, bounded zero-new-spending collection, safe attempt accounting, offline normalization and query → video → comment provenance. Keep older videos as discovery context and filter comments by original publication within the requested interval.
- Preserve scope-relative Top indices, source-reported Rising/Breakout and current-like snapshots; rank only the fetched comment sample. Add a compact YouTube section to Markdown, terminal and dark PDF outputs, without cross-scope index charts.
- Reserve Signals attempts in the total run budget; document setup, unsupported coverage, 30-day API-data refresh/deletion and additional-analytics acceptance requirements.

Verification uses synthetic responses and isolated settings; no authenticated Google/SerpApi calls, key setup, allowance or analytics approval is claimed. Research JSON remains 0.1.0.

## [0.4.1] - 2026-11-06

Dark dashboard styling for reports.

- Replace the light report palette with charcoal backgrounds, light primary text, readable gray labels, dark table surfaces, cyan links/highlights and blue/cyan/teal/lime chart series. Paint every PDF page dark, including continuation pages.
- Share semantic theme roles with available native chat charts/artifacts. Reserve green/red for supported comparable changes and keep ordinary Markdown/terminal output portable; host chat backgrounds remain controlled by the client.
- Preserve report content, metric values, source links and layout contracts. Support legacy report-model palette fields through current-theme defaults, and verify text contrast, multipage backgrounds and content preservation.

Limitations: custom chat canvas colors are not controlled by the skill; styled native visuals depend on the client's actual capabilities. No provider, authentication, allowance or spending behavior changes. Research JSON version remains `0.1.0`.

## [0.4.0] - 2026-11-06

Owner-supplied API keys and automatic first-run configuration choices.

- Add owner-supplied TokConnect API-key onboarding without recipient provider accounts: hidden terminal setup, private Codex/Claude Code settings, key rotation/removal and client-specific native connector guidance. Reuse working connections and verify the shared allowance separately; setup makes no network requests and bundles no secrets.
- Make bare skill invocations proactively present all missing-provider setup choices, including browser/API-key options for TokConnect, then resume the requested research once configuration is ready.
- Accept TokConnect autocomplete suggestions as strings as well as objects with `text`, retaining stable deduplication IDs and recommendation-only semantics. Add wrapper and two-call offline import regression coverage.

Limitations: setup writes private client settings and does not verify live authentication, entitlements or credit balances. Codex key setup requires Python 3.11+; Claude Code setup and research support Python 3.10+. Claude native request headers remain a limited beta; ordinary ChatGPT Chat uses its supported OAuth/import routes. No credentials or paid spending are included. Research JSON version remains `0.1.0`.

## [0.3.0] - 2026-11-06

Provider readiness and compact reports for every client.

- Require a configuration preflight for every selected provider, reuse working connections, and apply exclusions before setup or research calls. Add a zero-research-call `preflight` command and an explicit maintenance-only diagnostic mode.
- Remove the TikTok terms-link/permission-declaration prerequisite in the skill, normalizer and import validator; retain optional source metadata without inventing it.
- Replace verbose reports with provider data tables and brief conclusions, an overall summary, and at most three short channel/need/product combinations. Keep detailed analysis and provenance in JSON.
- Generate matching Markdown, plain-text terminal and styled PDF reports from one model, with localized presentation labels, compatible charts, source links, bundled OFL fonts, export hashes and explicit font/dependency failures.
- Apply the shared gold, paper, sage, slate and ink palette to styled PDF reports and native chart guidance.

Limitations: configured provider access and metric accuracy still need live validation. Collection remains standard-library-only; default PDF export uses the declared ReportLab dependency, with native client PDF export as an alternative. Research JSON version remains `0.1.0`.

## [0.2.1] - 2026-11-05

Claude Code first-run readiness and release-tag consistency.

- Accept client-namespaced TokConnect search tool names while retaining the original callable name in provenance and rejecting unsupported tools/methods.
- Document existing-account browser authorization in Claude Code, setup readiness checks, and a small TikTok-only first run. Keep authentication, tool discovery, free allowance and permitted storage separate.
- Clarify client-specific credentials, plugin versus standalone installation, and the 7-day/14-day coverage fallback.
- Use release tags without a leading `v`; align the release workflow, package names, source links and install/rollback examples. Existing 0.1.0 and 0.2.0 tags retain their source commits under the new names.

Limitations: live account access, actual tool responses, charging and metric accuracy still require the caller's authorized Claude Code run. No credentials, paid upgrade or new provider is included; the research JSON schema remains `0.1.0`.

## [0.2.0] - 2026-11-04

TikTok search connection and distribution-first opportunity analysis.

- Make channel → reachable market/need → product combinations the primary research decision, with discovery and existing-product refinement modes.
- Add a focused analysis guide, separate demand/channel evidence, explicit channel-fit status, acquisition paths, counterevidence, and qualitative next actions.
- Extend analysis finalization and reports with decision context and opportunity assessments while preserving saved v0.1 analysis compatibility; place decisions before the evidence appendix.
- Bundle credential-free TokConnect MCP declarations for both clients and reuse the shared skill for explicit connection onboarding.
- Add the first TikTok search adapter: bounded search topics, detail/related topics and autocomplete, MCP response normalization, safe call receipts, and explicit missing/failed/partial coverage. Live authenticated validation is pending.
- Add setup/capture documentation and a privacy disclosure. Reddit access remains unchanged; no accounts, shared credentials, paid REST dependency or background collector are included.
- Add Adjust and AppsFlyer as future benchmark-provider candidates without changing the default MVP provider set.
- Replace maintainer-specific guidance with portable English documentation and generic regional-timezone checks.

Limitations: TikTok requires the caller's TokConnect account, browser authorization, verified free allowance and permitted data storage. Authenticated responses and metric accuracy have not yet been validated. This adapter covers search topics and autocomplete; videos, comments, ads and Shop analytics are not included. OpenAI Signals remains broad monthly context. Research/import/analysis schema version stays `0.1.0`.

## [0.1.0] - 2026-11-02

First public plugin release for Codex and Claude Code.

- One shared Niche Hunter skill, packaged for both clients with GitHub-backed marketplaces.
- Provider selection, topic scoping, seven complete days by default, custom periods, and explicit coverage limitations.
- Public OpenAI Signals collection, permitted normalized Reddit/TikTok imports, and evidence-linked Markdown/JSON reports.
- Stable `master` distribution, version/tag pinning, update and rollback instructions.
- Reproducible plugin ZIP with SHA-256 checksums, CI checks, and tag-triggered GitHub Releases.

Limitations: Signals supplies broad monthly context. No authenticated Reddit/TikTok data connection has been validated; their access, quotas, metric accuracy, and permitted use still need onboarding. Installing or updating the plugin does not provision provider credentials. Automated semantic analysis quality and interactive client behavior are not established by helper tests.
