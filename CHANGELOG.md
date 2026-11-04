# Changelog

## [Unreleased]

- Make channel → reachable market/need → product combinations the primary research decision, with discovery and existing-product refinement modes.
- Add a focused analysis guide, separate demand/channel evidence, explicit channel-fit status, acquisition paths, counterevidence, and qualitative next actions.
- Extend analysis finalization and reports with decision context and opportunity assessments while preserving saved v0.1 analysis compatibility; place decisions before the evidence appendix.
- Keep provider access unchanged: no authenticated Reddit/TikTok connection is included in these changes.

## [0.1.0] - 2026-11-02

First public plugin release for Codex and Claude Code.

- One shared Niche Hunter skill, packaged for both clients with GitHub-backed marketplaces.
- Provider selection, topic scoping, seven complete days by default, custom periods, and explicit coverage limitations.
- Public OpenAI Signals collection, permitted normalized Reddit/TikTok imports, and evidence-linked Markdown/JSON reports.
- Stable `master` distribution, version/tag pinning, update and rollback instructions.
- Reproducible plugin ZIP with SHA-256 checksums, CI checks, and tag-triggered GitHub Releases.

Limitations: Signals supplies broad monthly context. No authenticated Reddit/TikTok data connection has been validated; their access, quotas, metric accuracy, and permitted use still need onboarding. Installing or updating the plugin does not provision provider credentials. Automated semantic analysis quality and interactive client behavior are not established by helper tests.
