# Changelog

## [Unreleased]

- Use release tags without a leading `v`; align the release workflow, package names, source links and install/rollback examples. Existing 0.1.0 and 0.2.0 tags retain their source commits under the new names.

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
