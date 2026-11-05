# Provider routes — v0.1

TikTok public schemas/OAuth/pricing rechecked November 4, 2026; other access findings date to October 31–November 1. Recheck current terms and schemas when using a route. This file is portable with the skill; repository development history lives in `docs/development-plan.md` and is not required at runtime.

## ChatGPT / OpenAI Signals

Implemented helper route: public HTTPS ZIP, no account/key or separate model API, $0 data download. Only `share_of_messages_by_topic_month.csv` is parsed in v0.1. Other release tables are not yet supported. The release is CC BY 4.0: retain OpenAI Signals attribution, source URL, and identify derived calculations.

- [Download and license](https://openai.com/signals/data-download/), [dictionary](https://cdn.openai.com/signals/data-dictionary.pdf), [ZIP](https://cdn.openai.com/signals/data-download-csv.zip).
- A row is `P(topic | month)`: differentially private weighted share in `[0,1]`, not absolute messages, unique people, searches, or private prompts. Months are UTC month-start labels. Display share differences as percentage points; relative share change is a separate measure.
- Choose the latest **complete month ending no later than the requested end**, and the preceding calendar month if present for the same category. Never prorate monthly data into a weekly count. The comparison is month-on-month; a weekly requested baseline remains unavailable.
- This table is global, without a language filter. Requested region/language filters are explicitly unsupported. Narrow topics must match a catalog alias exactly; otherwise return `not_supported` for topic granularity rather than map a narrow request to an unrelated broad category and invent topic-specific demand.
- November 1 live check: 24 CSVs in ZIP, 189 rows in the selected table, July 2024–September 2026. Do not hardcode these as future counts/date limits. Consumer individual accounts exclude enterprise/Codex in that release; preserve methodology and version limitations.
- Successful retrieval establishes source/format, not a proven user problem or willingness to pay. Publication time is unknown unless supplied by the release; HTTP retrieval time is not publication time. A local file's mtime is not source retrieval time.
- The run saves the public ZIP and SHA-256. `--signals-file ... --offline` replays it, with original retrieval time unknown and current processing time recorded separately. Run artifacts are local and ignored by Git.

## TikTok

Implemented first route: bundled TokConnect MCP connection plus `scripts/tiktok.py`, an offline search-response normalizer. Follow [tiktok.md](tiktok.md) for setup, supported methods, bounded collection, and the capture contract. A plugin declaration is not an authorized account: the caller still signs in and verifies the actual free allowance. No authenticated response has been validated in this project yet.

**TokConnect:** [connections](https://tokconnect.com/connect/), MCP `https://mcp.tokconnect.com/mcp`, [pricing](https://app.tokconnect.com/pricing), [supplier demand schema](https://tokconnect.com/docs/api/demand/). Public OAuth metadata advertises DCR/PKCE and `mcp` scope. November 4 pricing advertises 50 initial free credits, one credit per lookup, MCP on Free, and REST on every paid plan (a change from the earlier Pro-only REST finding). Actual account balance, charging and metric accuracy remain unverified. Do not purchase REST access or start a paid plan. Onboarding/consent is an explicit setup action when needed.

Before collecting, complete the selected-provider configuration check and inspect live tools and account access. Do not require a terms link or storage declaration to process available TikTok data locally. If authorized, use at most the smaller of the free balance or remaining 10-call run budget. Record actual calls even on failure. Do not retry authentication, entitlement, or credit failures. Honor `Retry-After`; stop instead of waiting beyond the run budget. Export only permitted summaries/fields into the import contract.

The adapter maps publicly documented compact `topics`/`topic` fields (`queryId`, `queryText`, `searchVolume`, `popularity`, `videoCount`, `trend7d`, category) and autocomplete `suggestions[].text`. Live schemas must still match before calls. Claimed `searchVolume` is seven-day topic popularity; it is not independently verified literal-query volume. CSI entity type remains `unknown` without proof; autocomplete is `recommended_keyword`. Keep `provider_claim_unverified` even after HTTP success. Undated `trend7d` readings remain provenance, not additive daily counts or a computed growth rate. Missing bounds are unknown, not inferred from retrieval time.

**Official alternatives:** [Business Discovery](https://business-api.tiktok.com/portal/docs/get-trending-search-keywords/v1.3), [Keyword Ideas](https://business-api.tiktok.com/portal/docs/discover-new-keywords/v1.3), [hashtags](https://business-api.tiktok.com/portal/docs/get-popular-hashtags/v1.3). Require current app/account consent, scopes and entitlements. Trending search phrases/recommendations are snapshots without confirmed historical query counts. Keyword Ideas provides monthly ranges. Hashtags have separate windows/ranks/views; a 14-day request does not create a `14DAY` option. Do not label any of these as seven-day typed-search volumes.

[Research API eligibility](https://developers.tiktok.com/docs/en/research-api-faq) excludes commercial users. CSI/Creative Center UI access does not establish a public export API. No UI scraping or host switching is the default fallback.

## Reddit

No embedded Reddit crawler or tokens. Use an already permitted official/licensed tool or a clearly licensed export. Content search finds publications matching **our** terms; it is not a log of users' search queries. Preserve publication dates separately from current counters.

- [Access rules](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data), [migration](https://developers.reddit.com/docs/guides/migrate/public-api), [search schema](https://www.reddit.com/dev/api/#GET_search). Commercial rights and usable current access must be established; do not assume a newly created free OAuth app is available.
- Public JSON was blocked in prior checks; RSS was capped and incomplete. Do not switch hosts, use proxies, or scrape around access failures.
- [Reddit Pro Trends](https://support.reddithelp.com/hc/en-us/articles/47619216411284-Reddit-Pro-Feature-Trends) does not authorize downloading others' posts/comments manually or automatically. A browser screenshot is not a permitted bulk export.
- [Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift) is a technically accessible archive candidate, with incomplete coverage and stale counters. Commercial-use permission was not established. It is **disabled as an automatic route**; a prior 200 response is insufficient.

Once suitable access is established, sample relevant catalog communities and queries with publication filters and bounded pagination. Include recurring questions/workarounds/alternatives and permitted comments; minimize author data. Record received/retained counts, time gaps, community selection, cursor completion, and limits. Preserve current counter observation time; never infer historical engagement from it. One viral thread or repost cluster is weak evidence of growth. Use `discussion` or `comment`, not `typed_search`.

## Status handling

Before normal research, configure every selected provider or have the caller explicitly exclude it. `preflight` reports missing configuration without research calls; normal `collect` rejects missing result routes before any helper HTTP request. An explicit `--diagnostic` run may produce `unconfigured` statuses for maintenance checks. Imported failure envelopes may specify `auth_required`, `not_supported`, `rate_limited`, `unavailable`, with a reason and no observations. `usage_terms_unconfirmed` remains accepted only for replaying legacy failure records, not as a new TikTok terms gate. Tool/schema access alone does not mean data was collected. No selected provider disappears silently, and selecting only an unavailable provider must make zero calls to other platforms.
