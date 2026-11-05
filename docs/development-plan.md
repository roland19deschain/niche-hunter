# Niche Hunter — first-version development plan

Updated: **November 6, 2026**. Source investigations below retain their original verification dates.

**Document language: English. Keep all future updates to this plan in English.**

Status: **0.3.0 is published** (section 23), incorporating the accepted November 6 preflight/compact-export revision (section 22) and shared report palette. Release 0.2.1 remains published (section 21). 0.2.0 is published (original publication in section 19; bare-tag migration in section 20). It sharpens channel → market/need → product reasoning and existing-product refinement (section 17), and adds the first TokConnect MCP/search adapter (section 18). The Python standard-library helper collects public OpenAI Signals, accepts permitted normalized imports, and finalizes evidence-linked reports. The user authorized the new release and stable-branch synchronization on November 4. The **free pilot** remains in force; the user now has a TokConnect account for Claude Code onboarding, but this project has not validated its authorization, entitlements or data access. Authenticated Reddit/TikTok collection and interactive research quality remain incomplete. Purchasing subscriptions is outside scope.

## 0. Handoff snapshot — read first

This is the canonical project context and implementation plan. Earlier design notes and access investigations have been consolidated here; their historical versions remain in Git. An agent should be able to resume without the original chat, screenshots, meeting notes, or deleted documents.

| Area | Current working state as of November 6, 2026 |
| --- | --- |
| Repository | Work and test in `develop`; promote tested releases to stable `master`. Inspect staged/unstaged changes before editing. Do not automatically synchronize unfinished development work. |
| Implemented artifacts | Canonical `skills/niche-hunter/`: shared `SKILL.md`, references/catalog, Python helper, and Codex UI metadata. Project `.agents/skills/niche-hunter` and `.claude/skills/niche-hunter` symlink to it. Version 0.2.0 adds TikTok client MCP declarations, setup instructions and offline search-response normalization; authenticated operation is still unverified. |
| Runtime | Python 3.10+ standard library and IANA time-zone data for collection; ReportLab/bundled fonts or a client PDF exporter for the reviewed PDF feature; manual skill invocation with calling-agent analysis. No additional LLM API, continuously running collector, scheduler, hosted backend, or cloud storage. |
| Analytical decision | Version 0.2.0: discovery/refinement modes, channel → reachable market/need → product combinations, separate demand/channel evidence, acquisition paths, counterevidence, and qualitative next actions. See section 17; the 0.1.0 runtime is unchanged. |
| Accounts and credentials | The user has prepared a TokConnect account for Claude Code onboarding. Live authorization, free balance and permitted storage remain unverified. No Reddit, TikTok for Business or licensed-monitoring access is configured. No credentials are committed. |
| OpenAI Signals | Live v0.1 helper download and offline replay verified. One global monthly topic-share table is supported, with release hashing, permitted ZIP snapshot, adjacent-month comparisons, explicit monthly fallback and unsupported narrow-topic handling. |
| TikTok | First search route included in 0.2.0 through client-managed TokConnect MCP and `scripts/tiktok.py`. November 4 public schemas/pricing and OAuth discovery checked; account setup was pending then; the user confirms a prepared account on November 5. No authorized data response, permitted-storage confirmation or metric-accuracy validation. See sections 18 and 21. |
| Reddit | Bounded Arctic Shift metadata retrieval verified. Suitable commercial access, completeness, and future reliability remain unresolved. |
| Budget and scope | Free pilot only. Implementation is authorized; this document does not itself authorize account creation, paid purchases, advertising, deployment, or scheduled collection. Defaults: 100 normalized observations/provider, 10 external calls/run subject to confirmed free balance, at most two public Signals HTTP attempts. |
| Distribution | Public `0.3.0` is published at commit `5ced0aa34b68c66fc867e39f4af0615db5da71c3`, with verified ZIP/checksum and installed/enabled Codex and Claude Code updates. The downloaded runtime produced Markdown/PDF exports with bundled fonts and the shared palette. Develop/master CI and the Release workflow passed. Release tags omit the prefix; earlier tags/commits are preserved. Provider account access and real research remain separate checks. See section 23 and `docs/releasing.md`. |

Resume by reading this snapshot and the current requirements in section 22, then source-specific constraints in section 3, implementation contracts in section 12, and the next-action checklist in section 14. Treat dated probes as historical observations, not a current access guarantee. Recheck changing schemas, prices, terms, and permissions when implementing an adapter.

## 1. Goal and agreed decisions

Niche Hunter helps identify needs and niches for websites, web applications, mobile and desktop applications, and other small digital products, or refine an existing product in a selected domain. The primary decision is **distribution channel → reachable market (audience, intent, unmet need) → potential product or product change → experiment**. Research should explain this combination from observations rather than append a generic channel name to a product idea.

Agreed decisions:

- User-facing name: **Niche Hunter**. Technical name: `niche-hunter`.
- Maintain one skill for **Codex and Claude Code**, with a shared `SKILL.md`, references, and helper scripts. Separate client settings and authorization from research logic.
- The MVP includes three providers: **Reddit, TikTok, and ChatGPT**. The concrete ChatGPT data source is **OpenAI Signals**.
- When providers are not specified, consider every registered MVP provider. The caller may select one or several.
- The default period is the **last seven complete calendar days** in the selected time zone. An explicit period in the request takes precedence.
- Without a topic, survey every category in the supported resource catalog. When a topic is supplied, scope research to it.
- If a source cannot support the requested period, use an available comparable interval or its latest available snapshot and clearly explain the difference. One unavailable source must not stop the others.
- Return a concise, informative result: key signals, sources, product opportunities, and limitations. Full technical data must not overwhelm the chat response.
- The current-stage budget is **$0 for new subscriptions and paid top-ups**. Advertising spend, paid plans, and launching ads are not planned.

### Product context and research boundaries

The skill serves product builders and marketers researching small digital products. Initial scoping focused on new-product discovery; the November 4 clarification also includes research to refine a caller-specified existing product. Record the caller's relevant product, audience, distribution constraints, and experiment budget for each run. This plan does not select a specific product or commercial partner or establish provider accounts, advertising budgets, or permission to contact anyone.

Follow **Distribution First**: `channel + audience → observed problem/desire → demand and competitor checks → economic hypothesis → minimal experiment → MVP → payments/retention evidence`.

Distinguish five separate questions: whether a topic is growing, whether a recurring user need exists, whether people will pay, whether an acquisition channel is viable, and whether the product achieves profitable retention/scaling. Public observations can support hypotheses; they cannot establish all five.

Support both intent-led discovery, where people already seek a solution, and content-led discovery, where a demonstration creates interest. Prefer a narrow job-to-be-done with a testable value proposition over a broad fashionable category. Check frequency, audience size, alternatives, service cost, monetization, and distribution rather than treating a viral topic as a product opportunity automatically.

Availability and pricing claims below carry their own verification dates. Hypotheses, fixtures, and illustrative calculations are not collected market evidence.

## 2. Provider selection

A provider in the caller interface is a platform. A platform may have several access adapters:

| Provider | Potential adapters | Research role |
| --- | --- | --- |
| `reddit` | Permitted official or licensed access; Arctic Shift as a separate candidate | Needs, questions, complaints, alternatives, and discussion trends |
| `tiktok` | TokConnect MCP; official Business APIs and tools when access is available | Search topics, recommendations, content trends, and interest in product demonstrations |
| `chatgpt` | Public OpenAI Signals CSV files | Aggregate trends in ChatGPT usage categories and user tasks |

TokConnect is an access method for TikTok, rather than a fourth platform provider. Selecting `tiktok` should not require the caller to know the underlying supplier.

Selection rules:

1. No provider filter means `reddit`, `tiktok`, `chatgpt`, and future registered providers included in the supported default set.
2. An explicit selection limits both collection and reporting to those platforms. Selecting only Reddit must not trigger TikTok or OpenAI Signals requests.
3. An unconfigured or unavailable selected provider remains in the status table with its reason; do not silently omit it.
4. If the only selected provider is unavailable, return a clear availability result without automatically switching platforms.
5. An unknown provider name requires clarification and a list of supported options; it does not automatically create an adapter.
6. Adding a platform extends the capability and source registry while preserving common selection, date-window, and reporting logic.

Examples of skill requests (filesystem discovery is configured; fresh-session discovery and behavior still need validation in both clients):

```text
/niche-hunter
/niche-hunter only TikTok for the last 14 days
/niche-hunter Reddit and ChatGPT, topic: horoscopes
```

Explicit invocation is expected to use `$niche-hunter` in Codex and `/niche-hunter` in Claude Code. Extract parameters from ordinary language; a separate command language is not required.

## 3. Availability and cost

### 3.1. ChatGPT: OpenAI Signals

**Suitable for the free MVP as aggregate context.**

- CSV files are public and require neither a ChatGPT account nor an API key.
- Data is licensed under **CC BY 4.0**, requiring attribution.
- Published aggregates cover usage categories, message shares, intent, and other breakdowns. They do not contain original conversations, prompt text, or user search logs.
- The verified current release was updated on October 26, 2026, and covers July 2024 through September 2026. The principal time resolution is monthly; some breakdowns are quarterly.
- This dataset cannot provide seven-day trends for narrow queries such as "tomorrow's horoscope."
- For a weekly request, show the latest available monthly snapshot as supplementary context, with its actual dates and publication lag.
- If a caller's topic is not represented at the required granularity, state that limitation. Do not assign growth to a narrow topic based on a broader category.

**Data cost: $0.** Reading these files does not require a separate paid OpenAI API. The calling agent's model can interpret them under its usual plan.

Sources: [Signals individual data](https://openai.com/signals/data/), [CSV downloads and license](https://openai.com/signals/data-download/), [data dictionary](https://cdn.openai.com/signals/data-dictionary.pdf).

### 3.2. TikTok: TokConnect MCP

**A candidate for the free search-signal pilot. Production data has not yet been tested with authorization.**

**November 4 update:** public pricing now advertises REST on every paid plan, rather than the earlier Pro-only finding below. The free MCP direction is unchanged. DCR/PKCE OAuth metadata and documented compact search-response shapes were checked; the connector/normalizer in section 18 ships in 0.2.0. The original table and source investigation retain their historical meaning; they do not establish a current account balance or permission to export data.

The supplier claims access to CSI-like search topics, seven-day metrics, related topics, content signals, and MCP. Its collection method and permitted use of results require validation before routine collection.

Current public prices were checked on the application pricing page and in recent supplier documentation:

| Plan | Monthly billing | Monthly equivalent when billed annually | Advertised programmatic access |
| --- | --- | --- | --- |
| Free | $0; advertised 50 trial credits once | — | MCP |
| Starter | $49 | $34.99 | MCP |
| Growth | $99 | $69.99 | MCP |
| Pro | $199 | $139.99 | MCP and a separate REST API |
| Enterprise | Custom quote | Custom quote | Supplier terms |

Annual equivalents are not monthly subscription prices: Starter, for example, is billed as $419.88 per year. Do not select annual billing during validation.

Recent documentation describes one credit per request and a shared balance across MCP, the research agent, and the API. Older indexed pages still mention 100 free credits and different quotas. Use the recent **50-credit** offer for pilot planning, but verify the actual balance and charging rules in the new account.

The current pricing screen also lists limits on niches and results. Do not assume Starter permits unlimited research across every category or that board limits exactly match MCP limits. Current numerical quotas for paid MCP plans still need clarification.

Pilot decision:

- Use the advertised **Free MCP access**, without purchasing a subscription.
- Connect one account and limit requests. Start with 5–10 topics and selective detail within the confirmed free balance.
- Discover the current tool list and schemas through MCP; do not treat outdated method names in articles as the implementation contract.
- Validate values, dates, geography, freshness, and the distinction between `typed_search` and `topic_group`. Receiving JSON does not establish metric accuracy.
- Where possible, cross-check a sample against TikTok CSI and record exactly what was verified.
- Do not buy REST API access for the MVP: first evaluate the supplier-supported MCP interface inside Codex and Claude Code.

Sources: [current application pricing](https://app.tokconnect.com/pricing), [MCP, REST, and pricing documentation](https://tokconnect.com/guides/tiktok-shop-api-n8n-zapier/), [AI client connections](https://tokconnect.com/connect/), [CSI claims](https://tokconnect.com/guides/creator-search-insights-api/).

### 3.3. TikTok: official tools

Retain these as alternative and supplementary adapters. The user currently has no required accounts or application; authorized responses have not been tested.

The following implementation leads were recorded from official documentation in the October 29–30 investigation. They are **documented findings, not live authorized responses**, and must be checked against the current schema before coding:

| API for Business v1.3 endpoint | Recorded fields and capabilities | Window and important restrictions |
| --- | --- | --- |
| `GET /open_api/v1.3/discovery/trending/search/` | `search_keywords`: up to 20 trending phrases; `business_id`, `is_personalized` | Current snapshot; no documented date, country, or category filter and no search-count field. Default unpersonalized mode should be checked; retain personalization/account context when used. |
| `GET /open_api/v1.3/discovery/trending/search/keyword/` | Up to 20 topic-based recommendations; `query` recorded as at most 255 characters | Current recommendations, not measured weekly search volumes. |
| `GET /open_api/v1.3/tool/search_keyword/keyword_idea/` | `avg_monthly_searches_lower/upper`, `three_month_change`, `year_over_year_change`, `competition`, `estimated_cpc_lower/upper`, `total_search_volume_lower/upper` | Monthly search metrics; prior notes record up to 10 seed terms, English-only input, default `country_codes=US`, and allowlisting restrictions. Verify actual field units and country support. |
| `GET /open_api/v1.3/discovery/trending_list/` | Top-200 hashtags; `rank_position`, `rank_change`, `views`, `posts`, `top_country_list`, `trending_history` | Recorded windows: `1DAY`, `7DAY`, `30DAY`, `120DAY`; `country_code` and `category_name` filters. History reportedly includes daily ranks/views for up to 30 days, with `views_daily=null` below 1,000 views. Validate those semantics. |

Recorded access requirements:

- Search Discovery requires a TikTok-account token with `discovery.search.words`; inspect `/tt_user/token_info/get/` to verify granted scopes. The account identifier must follow the actual OAuth schema, not a guessed advertiser ID.
- The prior documentation review also required Advanced Access or a Verified Business Account; `/business/get/` and `has_advanced_access` were identified as entitlement checks. Confirm the current entitlement route before onboarding.
- Keyword Ideas and hashtag Discovery were recorded as requiring `advertiser_id` and advertiser authorization. A developer application and the appropriate approval process are also needed; specific Discovery review eligibility remains unresolved.
- The official TikTok for Business MCP catalog reviewed on October 30 included `tool_search_keyword_idea_get`; Discovery tools were not found in that review. Enumerate the live catalog instead of assuming either permanent absence or a fixed tool count.

No `14DAY` hashtag window was recorded. A 14-day calculation might be possible from genuine compatible daily history, but only for the returned top-200 selection and days with available values. That is not complete TikTok coverage, and missing daily views must not become zero.

Source exclusions and fallbacks:

- **Research API:** not the commercial MVP route; official eligibility excludes commercial users. Its video date filters do not reveal users' search demand. The earlier review recorded a maximum 30-day video query window; recheck if a separately eligible research use case ever arises.
- **Creator Search Insights:** useful for checking frequently searched topics and content gaps, but no public official CSI export API was established. Availability depends on account/region; some topics are generated groups rather than literal typed phrases.
- **Creative Center / TikTok One Creative Suite:** an October 30 unauthenticated UI check exposed only the top three hashtags. That observation is not a stable API contract; content trends must remain distinct from search volumes.

Keyword Planner is available for supported advertiser-account countries; otherwise allowlisting may be necessary. The user's time zone alone does not determine availability.

**A separate current per-call API price has not been confirmed.** Do not label this as guaranteed free, ready-to-use access. Using planning tools also does not mean the pilot needs to launch advertising.

Sources: [trending keywords](https://business-api.tiktok.com/portal/docs/get-trending-search-keywords/v1.3), [recommended keywords](https://business-api.tiktok.com/portal/docs/get-recommended-search-keywords/v1.3), [Keyword Ideas](https://business-api.tiktok.com/portal/docs/discover-new-keywords/v1.3), [popular hashtags](https://business-api.tiktok.com/portal/docs/get-popular-hashtags/v1.3), [official Business MCP tools](https://business-api.tiktok.com/portal/docs/available-tools-in-tiktok-for-business-mcp-server/v1.3), [account entitlements](https://ads.tiktok.com/help/article/about-tiktok-account-entitlements), [Keyword Planner availability](https://ads.tiktok.com/resources/help/article/about-the-keyword-planner-tool-in-tiktok-as-manager?lang=en), [authorization](https://business-api.tiktok.com/gateway/docs/index?doc_id=1738373141733378), [Research API eligibility](https://developers.tiktok.com/docs/en/research-api-faq), [CSI](https://newsroom.tiktok.com/creator-search-insights?lang=en).

### 3.4. Reddit: official and licensed access

**The main uncertainty in the current source set is sustainable, permitted access to Reddit data.**

The official migration schedule was checked again:

- **October 31, 2026:** new public Data API access requests stop being accepted.
- **November 30, 2026:** registration deadline for the migration bounty program; this is not a new research-data entitlement.
- **January 12, 2027:** access removal begins for apps that have not registered or responded to Reddit.
- **March 2027:** remaining public access ends under this transition.

Do not base a long-term MVP on the assumption that a new OAuth client can be obtained freely and used with the previous public API. Devvit is not an established replacement for external data export; suitability and permissions for our use case require separate verification.

Commercial use requires agreement with Reddit and a contract. A public fixed price for suitable access has not been confirmed. Do not automatically extend the public API shutdown to every licensed commercial agreement.

Paying a third-party service does not itself establish permission for the required collection. Before choosing a supplier, verify its rights, available fields, permitted analysis and export, history, and the price of API access specifically.

Earlier access probes, recorded on **October 30, 2026**, explain why unauthenticated fallbacks are not the baseline:

| Route | Historical observation | Consequence for implementation |
| --- | --- | --- |
| Public `www.reddit.com/search.json` and subreddit `new.json` | HTTP 403; `old.reddit.com/search.json` redirected to login | Do not assume public JSON works or switch hosts to bypass access restrictions. |
| `/search.rss` | HTTP 200, then `x-ratelimit-remaining: 0`; at most 100 results; one `horoscope` query returned 97 items covering about ten hours, without score/comment-count fields | Success did not establish seven-day completeness. RSS is not a dependable long-term collection foundation. |
| Existing approved Data API access | Documentation exposes content search with `t=week` and record timestamps | This searches publications matching our query, not a seven-day log of searches entered by Reddit users. No authorized account was tested. |

Earlier press reports claimed an RSS shutdown on November 13, 2026 and roughly 100 API requests/minute per client. Those are **unverified secondary reports**, not a granted quota or a confirmed API contract. The primary access/migration rules above take precedence. Reddit's UI may surface some recently searched topics, but no official seven-day search-volume feed was established for this project.

Sources: [official migration schedule](https://www.reddit.com/r/redditdev/comments/1wubcvf/moving_data_api_apps_to_the_developer_platform/), [commercial access terms](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data), [migration guide](https://developers.reddit.com/docs/guides/migrate/public-api).

Additional references: [content Search API](https://www.reddit.com/dev/api/#GET_search), [recent search-topic UI](https://support.reddithelp.com/hc/en-us/articles/19696269107348-How-can-I-see-what-s-trending-on-Reddit), [RSS shutdown press report](https://www.socialmediatoday.com/news/reddit-ends-support-for-rss-feeds/831844/). The historical probe descriptions are retained for handoff and were not repeated during document consolidation.

### 3.5. Reddit: Arctic Shift

**A technically accessible free candidate; permission for commercial use has not been established.**

- The public API supports community, time, and content filters; text search has parameter-combination restrictions.
- Research needs a category-based community catalog; do not promise exhaustive global discovery of all needs.
- The limited metadata probe did not require an account.
- The author describes the service as free, with dynamic rate limits and no availability guarantee.
- Archive metrics are not current Reddit counters; documentation describes fetching updated metrics after approximately 36 hours.
- The reviewed documentation did not establish sufficient licensing terms for our commercial use case. HTTP 200 does not resolve that question.
- Future reliability after Reddit API changes is also unconfirmed.

Implementation lead: base URL `https://arctic-shift.photon-reddit.com`, endpoint `/api/posts/search`, with `subreddit`, `after`, `before`, `limit`, `sort`, `fields`, and optional `query` filters. An October 30 `astrology` probe for October 23–30 returned 100 posts dated October 24–29; an unconstrained text `query` without `subreddit` or `author` returned HTTP 400. Date filters are capabilities, not proof that every day or item is archived. Use actual pagination and coverage checks instead of promising arbitrary complete history.

Do not treat Arctic Shift as a guaranteed primary commercial source until these conditions are clarified. Reddit remains in the MVP registry and coverage table even if no permitted adapter is available.

Sources: [project and data provenance](https://github.com/ArthurHeitmann/arctic_shift), [API documentation](https://raw.githubusercontent.com/ArthurHeitmann/arctic_shift/master/api/README.md), [archiving details](https://github.com/ArthurHeitmann/arctic_shift/blob/master/file_content_explanations.md).

## 4. Network checks performed on October 31, 2026

| Check | Observed result | What it establishes |
| --- | --- | --- |
| Public OpenAI Signals ZIP | HTTP 200 without authorization; 2,011,697 bytes; 24 CSV files | Automatic download is possible without an account or API key |
| `share_of_messages_by_topic_month.csv` | 189 rows; columns `month`, `topic`, `share_of_messages`; July 2024–September 2026; seven broad categories | Actual format, monthly resolution, and limited topic granularity |
| Unauthenticated TokConnect MCP | HTTP 401 pointing to OAuth resource metadata | A programmatic client needs authorization; no search data was obtained |
| TokConnect OAuth resource metadata | HTTP 200; authorization server `https://app.tokconnect.com`; scope `mcp`; Bearer header | A standard MCP connection mechanism exists |
| Current TokConnect pricing screen | Read in the browser, including annual prices and Pro API access | Current public pricing, not account-specific quotas |
| Arctic Shift: one `r/productivity` metadata request, October 24–31, 2026 UTC filter, limit 5 | HTTP 200 without authorization; five records; result dates October 30, within the filter | A bounded request works; neither complete weekly coverage nor commercial-use permission |

The Arctic Shift request was limited to IDs, community, timestamps, and counters. Text and authors were not requested. Original user messages were not saved in the repository.

Not verified: authorized TikTok/Reddit responses, the actual balance of a new TokConnect account, supplier search-metric accuracy, archive completeness, or the real cost of surveying the full category catalog. No accounts were created and no subscriptions were purchased.

## 5. Evidence provenance and corrected conclusions

This plan incorporates the October 29 design discussion, October 30 access investigation, and October 31 probes and user decisions. Retain their dates and distinguish `observed fact` (a bounded live check), `documented` (a primary-source capability or rule), `press report` (secondary and unconfirmed), and `provider claim` (a supplier statement). None of these labels alone establishes production readiness.

The following conclusions supersede less precise statements in the earlier material:

1. **Reddit Pro is not a ready source for manually importing others' discussions.** Official help prohibits downloading others' posts, comments, and other displayed information manually or automatically. Exporting owned metrics does not solve our task.
2. For TokConnect, distinguish **MCP** from **REST API**, and current plans from older indexed pages.
3. For Reddit, distinguish retirement of public API access from potential separate commercial agreements.
4. For Arctic Shift, distinguish technical availability, archive completeness, and permitted use.
5. Add OpenAI Signals as a monthly aggregate ChatGPT source, without promising original queries or weekly statistics.

Source for the Reddit Pro restriction: [official Trends help](https://support.reddithelp.com/hc/en-us/articles/47619216411284-Reddit-Pro-Feature-Trends).

## 6. Caller experience

### One-time setup

- OpenAI Signals works without credentials; preserve the source, release version, and attribution.
- For TikTok, first connect Free TokConnect MCP to the chosen client. Select an authentication method actually supported by both client and supplier.
- For Reddit, show the available permitted options and their status. Do not present unavailable OAuth access as a guaranteed one-step installation.
- Store secrets using client facilities or secure local storage, not in the skill, Git, or reports.
- When a connection is missing, explain what needs configuration. Repeated research must not require re-entering still-valid keys or passwords.

### Normal invocation

1. Extract providers, period, topic, and additional constraints from the request.
2. Check selected-source capabilities: authorization, supported windows, available budget, and cache freshness.
3. Collect available data within agreed limits, processing sources independently.
4. Normalize observations, deduplicate them, and preserve provenance.
5. Extract themes, needs, and product opportunities while retaining distinctions between signal types.
6. Return a concise report and machine-readable results with actual coverage and quota consumption.

Simplicity and cost principles:

- Ordinary language should be sufficient for the caller. Hide supplier details, pagination, schemas, and error handling behind adapters.
- For a broad survey, start with inexpensive discovery across the category catalog, then inspect the strongest signals within the remaining budget.
- Set per-run call and record limits after verifying real quotas. Unlimited platform traversal is not the default mode.
- Cache permitted data according to freshness and retention terms. Do not reinterpret an unchanged monthly Signals release as a new weekly publication.
- When free credits run out, stop that adapter and disclose incomplete coverage. Do not automatically upgrade or top up.
- Use the calling agent for interpretation. A separate paid LLM API is not mandatory for the first version; the user's usual Codex/Claude costs still apply.

## 7. Periods, topics, and evidence quality

Preserve the following separately for each signal type:

- Requested start, end, and time zone.
- Actual supplier measurement window and retrieval time.
- Geography, language, entity type, and measurement unit.
- Access method, source, and evidence URL/identifier.
- Limitations, completeness, freshness, and verification level.

Example behavior for a 14-day request:

- Reddit: use the requested interval if the selected permitted adapter actually covers it.
- TikTok: if a particular metric is available only as a rolling seven-day aggregate, show that exact window. Other signals may have their own periods.
- ChatGPT: show the latest available monthly aggregate separately from the 14-day results.

Equal day counts do not make windows equivalent. Rolling seven days may differ from the caller's seven complete calendar days. Do not sum overlapping aggregates or reconstruct historical values from current counters.

Calling something "growing" requires comparable history. Without it, report current popularity or an observed need without inventing a growth rate. Do not combine Signals message shares, TikTok views, and Reddit discussion counts into a single search volume.

"All topics" means the supported category, resource, and query catalog, with explicit limits. For a supplied topic, adapters select relevant categories, communities, and terms; unavailable granularity is reported explicitly.

## 8. Research output

Return in chat:

- Period, topic, and selected providers.
- A compact table of actual coverage and status.
- A small set of useful signals with links, metrics, and limitations.
- Several product hypotheses: need, audience, potential product format, channel, and next experiment.
- Missing data and material unknowns.

Signal and hypothesis counts depend on evidence. Do not fill weak reports with invented ideas to reach a fixed row count. Add a diagram when it improves comparison; concise prose and tables are sufficient for an ordinary run.

Artifacts: a compact `report.md` and `results.json` containing parameters, provenance, limitations, and derived results. Retain original materials only within permitted fields and retention periods.

## 9. Implementation stages

### Stage 0 — finish access validation

- [x] Read and consolidate the original design context and source-access investigation into this plan.
- [x] Add provider selection with "all" as the default.
- [x] Select ChatGPT/OpenAI Signals as the third MVP provider.
- [x] Verify public Signals download and format.
- [x] Check public TokConnect prices, MCP authorization, and the REST distinction.
- [x] Recheck the official Reddit migration schedule.
- [x] Run a bounded Arctic Shift metadata probe.
- [x] Agree on a free pilot and record that no existing access is available.
- [ ] Clarify a permitted Reddit source and Arctic Shift conditions for our use case.
- [ ] Create a Free TokConnect account during a separate onboarding step and verify its actual balance and quotas.
- [ ] Test MCP tools on 5–10 topics, including charging, values, windows, and freshness.
- [ ] Determine whether free access meets pilot requirements and which signals are actually available.

### Stage 1 — shared skill and minimal collection

- [x] Create canonical `skills/niche-hunter/` with instructions, references, scripts, and Codex UI metadata.
- [x] Add project discovery symlinks for Codex and Claude Code without duplicating logic; actual client discovery remains to test.
- [x] Define v0.1 run, observation, coverage, permitted-import, and analysis contracts in `skills/niche-hunter/references/contracts.md`.
- [x] Implement provider selection, duration/custom dates, topic, time zone, region/language filter disclosure, and record limits.
- [x] Implement public OpenAI Signals collection, SHA-256 snapshot provenance, and offline replay.
- [x] Add validated normalized Reddit/TikTok import processing and explicit selected-provider failure statuses.
- [x] Select Python 3.10+ standard library with calling-agent tool orchestration and analysis; no model SDK dependency.
- [ ] Validate an authorized TikTok tool/data path and map its real fields/charging semantics into the contract.
- [ ] Establish suitable Reddit access and map its real fields/history into the contract.

### Stage 2 — analysis and concise reporting

- [x] Implement source-ID deduplication and adjacent-calendar-month Signals share arithmetic. Semantic repost/topic grouping and problems are assigned to the calling agent, not an automated classifier.
- [x] Define findings/hypothesis labels and validate evidence IDs and required analysis fields during offline finalization.
- [x] Generate `report.md` and `results.json`, including source status, actual windows, limitations, provenance and analysis-pending state.
- [x] Preserve public Signals ZIP for replay and bound helper attempts/imported records; instruct the caller to enforce free-credit limits before tool calls.
- [x] Implement the first TikTok search normalization and client-managed MCP setup path; keep live authorization/usefulness acceptance open (section 18).
- [ ] Validate useful multi-source problem extraction and product experiments from real permitted Reddit/TikTok evidence. Broad monthly aggregates alone must not force a hypothesis shortlist.

### Stage 3 — behavioral validation

- Exercise the same scenarios in Codex and Claude Code; format compatibility does not guarantee identical model behavior.
- Check defaults, 14 days, explicit dates, a single provider, and provider combinations.
- Check a topic below Signals' available granularity and an unavailable sole provider.
- Check missing authorization, exhausted credits, partial coverage, delayed data, and unavailable sources.
- Check date boundaries, overlapping windows, zero/small baselines, and duplicates.
- Distinguish demonstration fixtures from real authorized responses.

## 10. Conditions for paid access

No purchases are approved. Revisit payment after free testing establishes:

1. Usefulness and verification level of the signals.
2. Actual call counts for a focused report and a broad survey.
3. Available windows, geography, and completeness limits.
4. Real plan quotas and permitted storage/use.
5. A permitted Reddit path and its price if a contract or third-party supplier is required.

Starter at $49/month is a later evaluation option, not an agreed expense or a confirmed price for the entire system. Total monthly MVP cost cannot yet be fixed: the Reddit path and adequacy of Free TikTok access remain open.

## 11. Future provider coverage and channel mapping

This is a brief feasibility screen of the acquisition channels visible in the supplied screenshot, not a completed integration or pricing audit. The **MVP remains Reddit, TikTok, and ChatGPT**. Future candidates stay outside default collection until their access, fields, cost, and coverage have been validated.

An acquisition channel is not necessarily a separate provider. Google Ads and SEO can share Google Search adapters; Apple Ads and ASO can share App Store adapters; Organic Social spans multiple platforms. Avoid duplicate collection and double-counting when one observation supports several channels.

| Screenshot channel | Provider or adapter to evaluate | Useful evidence and main limitation | Roadmap priority |
| --- | --- | --- | --- |
| Google Search Ads | `google_search`: Google Ads Keyword Planning | Keyword ideas, approximate monthly search volumes, competition, and bid ranges. Requires account/API access; monthly volume is not a seven-day count or measured acquisition cost. | Next after MVP |
| Google SEO | `google_search`: Google Trends and permitted SEO/SERP datasets | Relative interest, seasonality, related demand, and competing pages. The official Trends API is currently an access-limited alpha; consider permitted exports when access is absent. Review licensed SEO suppliers separately. | Next after MVP; shares Google Search infrastructure |
| Apple Ads | `app_store`: authorized Apple Ads APIs | Account-scoped keyword/search-term performance, insights, and suggestions where available. Account authorization is required; owned campaign reports do not provide every competitor's search demand. | Next after MVP, alongside ASO |
| ASO | `app_store`: permitted store metadata and licensed ASO intelligence | Product positioning, pricing, available reviews, and keyword competition. Store metadata access and market-wide keyword intelligence are separate capabilities; validate export rights and any paid supplier. | Next after MVP; shares App Store infrastructure |
| Meta Ads | `meta`: Ad Library and authorized advertising reports | Ad examples, offers, creative angles, and permitted campaign metrics. Validate API eligibility and geographic/ad-category coverage; competitor CAC and ROAS remain unknown without direct evidence. | Following expansion |
| TikTok Ads | Extend `tiktok` with permitted ad-intelligence adapters | Creative demonstrations, offers, and authorized campaign results. Reuse the existing TikTok provider and distinguish ad observations from organic and search signals. | Following expansion of the MVP provider |
| Snapchat Ads | `snapchat`: Ads Gallery API, then authorized Marketing API or Ads MCP | Ad examples and authorized campaign performance. Gallery coverage and access need validation; account reporting is not a platform-wide demand feed. | Later candidate |
| Popunder / Clickunder | A named advertising-network adapter; no concrete provider selected yet | Network-specific inventory, traffic estimates, and eventually results from authorized tests. These are placement formats, not search-demand sources; actual economics require campaign data. | Exploratory; select a network before designing an adapter |
| Organic Social | `youtube` first, plus the existing `tiktok` and future `meta` adapters | Public video discovery and available comments can reveal demonstrations and unmet needs. YouTube offers a documented Data API with date filters; quotas apply. Views are not search volumes or purchases, and each platform needs its own access path. | YouTube next after MVP; other platforms later |
| Reddit / Communities | Existing `reddit`, then individually selected community adapters | Recurring questions, complaints, workarounds, and alternatives. Validate each community's API, permitted use, history, and sampling; a generic unrestricted forum crawler is not assumed. | Reddit in MVP; additional communities later |

Suggested sequence after validating the MVP:

1. **Google Search:** add external search-demand validation for opportunities discovered on social platforms.
2. **App Store / ASO:** check existing mobile solutions, positioning, and account-accessible keyword signals.
3. **YouTube:** add product demonstrations and comments through a documented API.
4. **Meta, additional communities, and TikTok ad intelligence:** add independent problem and distribution evidence where access is confirmed.
5. **Snapchat and a selected popunder/clickunder network:** add when the target audience and a concrete experiment justify the integration.

Future provider names are proposals, not implemented invocation options. Each candidate must pass access and licensing review, a bounded live test, measurement/window validation, quota and price assessment, and usefulness checks before registration in the default provider set. No additional advertising accounts, paid subscriptions, or campaigns are authorized by this roadmap.

Primary references from the brief review:

- [Google Ads historical keyword metrics](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-historical-metrics).
- [Google Trends API alpha and access](https://developers.google.com/search/apis/trends).
- [Apple Ads APIs and account authorization](https://ads.apple.com/maps/apple-ads/help/campaigns/0022-use-apple-ads-platform-api).
- [Meta Ad Library API](https://www.facebook.com/ads/library/api/). Its full current API documentation was not accessible in this pass; leave coverage and eligibility unconfirmed until a focused check.
- [YouTube Data API search](https://developers.google.com/youtube/data/reference/rest/v3/search/list) and [comment threads](https://developers.google.com/youtube/v3/docs/commentThreads/list).
- [Snap Marketing APIs, Ads Gallery, and Ads MCP](https://www.developers.snap.com/marketing-api/home).

### Additional discovery candidates retained from the original design

These are an inventory for later evaluation, not verified integrations or approved expenses:

| Candidate | Potential contribution | Qualification required before use |
| --- | --- | --- |
| Google Ads Transparency Center | Advertiser creatives and positioning | Permitted retrieval and coverage; no inference of competitor unit economics |
| Google Play | Android product descriptions, pricing, updates, and permitted review signals | An appropriate public or licensed access method; no assumption of access to competitors' private developer data |
| Product Hunt | New products, positioning, and early reactions | Current API/export rights and sampling bias |
| G2 / Capterra | B2B complaints, alternatives, and pricing gaps | Permitted access, reuse rights, freshness, and representativeness |
| Semrush / Ahrefs | Keyword intelligence, SEO competitors, and estimated traffic | API-specific price, licensing, limits, and estimation methodology |
| AppMagic / Sensor Tower | Estimated mobile downloads, revenue, and category dynamics | Licensed API/export access and clear labeling of estimates |
| Similarweb | Estimated web traffic and channel mix | Licensed access and methodology; estimates are not owned analytics |
| Adjust | Public industry reports/benchmarks; later, authorized analytics for the caller's apps | Public-report extraction/reuse rights and period/methodology; reporting API requires account access and is not a market-wide feed |
| AppsFlyer | Public Benchmarks and Performance Index; later, authorized analytics for the caller's apps | Validate actual benchmark data availability, stable retrieval and reuse rights; account reporting does not expose arbitrary competitors |

### Adjust and AppsFlyer — future benchmark providers

Feasibility screen on **November 4, 2026**, following the user's request to consider both providers before TikTok implementation. Proposed provider names are `adjust` and `appsflyer`; neither is registered in the current runtime or default provider set. The MVP remains Reddit, TikTok and ChatGPT. Evaluate the public-data route first; owned-app analytics is a separate, optional adapter for existing-product refinement.

| Provider / route | What was verified from primary sources | Research role and limitations |
| --- | --- | --- |
| Adjust public reports | The [Mobile App Trends 2026 page](https://www.adjust.com/resources/ebooks/mobile-app-trends-2026/) exposes selected category/region benchmarks, including installs, sessions and CPI. The edition largely describes 2025 performance. | Category and acquisition context, not individual user requests or weekly niche demand. Keep publication date separate from measurement period. Full reports may require a download form; public visibility does not establish automated redistribution rights. |
| AppsFlyer public benchmarks | The [Benchmarks page](https://www.appsflyer.com/benchmarks/) exposes category/subcategory, country/region and channel controls and describes anonymous aggregate data with volume thresholds. Category pages advertise normalized trends and per-app performance benchmarks; a bounded text retrieval of Utility & Productivity displayed metric controls but no numerical platform series. | Promising channel × category × market context. Numerical extraction, actual historical depth, refresh frequency, available metrics and missing/suppressed cuts still need a bounded verification. No data in this retrieval is not proof of zero demand. |
| AppsFlyer public media rankings | The [Performance Index 2026 page](https://www.appsflyer.com/resources/reports/performance-index/) describes acquisition/remarketing rankings by platform, region and category. This edition changes its quality methodology to quarter-over-quarter ad-spend change instead of retention. | Candidate advertising-channel selection, not proof of profitable CAC/ROAS or product-market fit. Preserve the edition and methodology; do not silently compare scores across changed methods. |
| Adjust owned-app analytics | Official [API overview](https://dev.adjust.com/en/api/) describes Report Service data for the caller's apps; [authentication](https://dev.adjust.com/en/api/rs-api/authentication/) requires a bearer token from the account. | Can support channel/product refinement with authorized first-party measurements. Account permissions, connected data, plan entitlements, quotas and current prices need separate validation. Creating an empty account does not provide market-wide SDK data. |
| AppsFlyer owned-app analytics | Official [aggregate Pull API documentation](https://support.appsflyer.com/hc/en-us/articles/207034346-Pull-API-aggregate-data) requires an admin-retrieved API token, an app ID, and report parameters; provides UA/retargeting reports. | An optional first-party validation source, not an open feed of other apps' events. Confirm account/app permissions, available reports, retention, plan entitlements and limits before integration. |

Implementation direction:

1. After useful MVP source validation, evaluate a bounded public-report/benchmark adapter for each supplier. Preserve report URL/edition, measurement window, platform, geography, category, channel, unit, sample/methodology, and freshness. Keep normalized indices, per-app averages, ranks, and absolute counts distinct.
2. Prefer documented downloads/exports or a permitted manual import until a stable public machine-readable interface and reuse terms are verified. No documented public benchmark API or arbitrary seven-day market-wide dataset was confirmed in this screen. Do not treat website-internal endpoints as a supported public API.
3. Keep benchmark evidence separate from observed user problems and owned-app campaign outcomes. Category averages and media rankings cannot establish the new product's conversion, CAC, LTV or profitability; do not count an embedded third-party dataset as independent corroboration without checking provenance.
4. Add owned-app adapters only when requested and authorized. Each caller supplies access through client facilities; no shared customer tokens, SDK secrets, or provider accounts ship with the skill. Such integrations may support refinement, but are not prerequisites for public-report research.
5. Before activation, verify retrieval, storage/reuse rights, metric/window semantics, missing-data behavior, quotas/pricing, and usefulness to the channel → market → product decision. Report publication-based fallback periods honestly. No accounts, subscriptions, or runtime adapters were created by this investigation.

Affiliate/creator partnerships and B2B partnerships remain possible distribution models. They require an identified partner/source and relevant conversion or sales-cycle evidence; they are not generic data providers with an assumed API.

## 12. Implementation contracts and design requirements

This section retains the design basis. The implemented v0.1 contract and CLI are specified in [the skill's runtime reference](../skills/niche-hunter/references/contracts.md); it is authoritative for actual field names and supported behavior. The minimal stack was selected from the verified public Signals interface: Python 3.10+ standard library, with client tools handling any authorized MCP collection. Broader requirements remain goals until explicitly checked off.

### Inputs and the resource catalog

| Input | Required behavior |
| --- | --- |
| `providers` | Default supported provider set; allow one or several, with the selection rules in section 2 |
| `days` or explicit dates | Default seven complete local days; explicit dates take priority. Normalize internal intervals to `[start_at, end_at)` in UTC and retain the caller's original boundaries. |
| `timezone` | Use an explicit caller value or available caller time zone. If neither exists, use a clearly disclosed UTC fallback; do not silently use the execution host's local zone. |
| `topic` / query terms | Optional; no topic means the supported category catalog. Preserve original terms alongside canonical topics. |
| Region and language | Record separately; defaults for a market/language pilot have not been agreed. Do not infer a user's country from Reddit text, account personalization, or the time zone. |
| Source filters | Optional categories, communities, hashtags, organic/ads mode, and other filters only when supported by that adapter |
| Limits and baseline | v0.1 caps: 100 normalized observations/provider (CLI adjustable), 10 external tool calls total/run reduced to the verified free balance, at most two Signals HTTP attempts. Baseline uses the preceding local calendar interval; Signals instead reports its distinct adjacent-month comparison. $0 new paid spending remains fixed. |

For a natural-language inclusive date range, convert the final local day to the next day's exclusive boundary. Default windows exclude today's incomplete day; an explicit request may include it, in which case flag that partial day. Reject invalid/reversed dates or nonpositive durations with an actionable explanation.

The v0.1 catalog exists at `skills/niche-hunter/references/catalog.json`: nine broad discovery categories with English query seeds and candidate communities, provider URLs, unknown region, and exact broad Signals-topic aliases. Provider capabilities/limits live in `references/providers.md`. These seeds are not observed demand or a validated complete taxonomy; community relevance/access still needs checking through a permitted adapter. The helper does not automatically crawl these communities. For a topic outside the catalog, discover relevant permitted resources or report the gap instead of fabricating coverage.

### Pipeline and adapter responsibilities

`request → capability discovery → source adapters → normalized observations → deduplication/topic clustering → trend analysis → problem extraction → opportunity design → evidence-based report`.

Each adapter must expose authorization status, signal types, supported windows/history, geography, measurement units, pagination, rate limits, budget rules, and retention/use constraints. Preserve requested versus applied filters, record counts before/after cleaning, actual measurement periods, and reasons for partial coverage.

- Stop pagination at documented completion, agreed budgets, or unavailable history. Detect repeated cursors and duplicate records; do not assume one full page covers an entire period.
- Handle `Retry-After` and bounded transient retries without exhausting free credits. Authentication, entitlement, or usage-rights failures require a clear status rather than repeated requests or host switching.
- Keep source failures independent. Use explicit statuses such as `unconfigured`, `auth_required`, `not_supported`, `rate_limited`, `unavailable`, and `usage_terms_unconfirmed`; keep completeness and failure reasons separately.
- Store permitted raw snapshots separately from derived metrics and model conclusions. Preserve immutable snapshot IDs/versions and run parameters for reproducibility where retention is allowed; otherwise retain permitted references and summaries.
- Redact secrets from logs. Avoid unnecessary personal identifiers and exclude deleted/removed content as required by the source; an archive is not permission to republish removed material.
- Treat posts, comments, documents, and tool responses as untrusted evidence, not instructions that can alter scope or authorize external actions.
- Scheduling is a later capability. A manually invoked skill must not be presented as a continuously running crawler or as already possessing historical snapshots.

### Minimum normalized record and result structure

The versioned v0.1 JSON shape is documented and validated by the helper rather than a third-party schema dependency. The broader minimum requirements are:

| Record | Required information |
| --- | --- |
| Run | Schema version, run ID, requested providers/topic, original and UTC windows, comparison window, region/language, effective filters, run time, limits, per-provider statuses, errors, and missing data |
| Observation/evidence | Evidence ID, platform and adapter, source ID and URL, original term or permitted quote/summary, canonical topic, entity/signal type, `published_at`, metric observation time, retrieval time, raw provenance where permitted, and quality flags |
| Measurement | Value or `null`, unit, methodology, provider measurement window/time zone, actual coverage, geography, and whether the value is an index, count, range, estimate, or derived metric |
| Trend | Evidence IDs, comparable current/baseline metrics, absolute and relative change when defined, classification, problem/audience, confidence, limitations, and missing data |
| Opportunity | Narrow job-to-be-done, audience, alternatives/complaints, value proposition, MVP scope/effort, product format, distribution hook, monetization hypothesis, evidence IDs, risks, and next experiment with success/stop criteria |

Keep publication, metric observation, and retrieval timestamps distinct. Min/max dates of retrieved records do not by themselves prove full coverage. Missing values are not zero; unavailable evidence is not average confidence.

Signal types must distinguish literal `typed_search`, generated `topic_group`, `recommended_keyword`, `hashtag`, `video`, `sound`, `comment`, Reddit discussion, and aggregate usage category. Use `content_trends`, `keyword_recommendations`, or `search_volume_range` where those are the actual observations; do not relabel them as weekly search-volume trends.

The original quality vocabulary was `verified_official`, `provider_claim_tested`, `provider_claim_unverified`, `proxy_content_signal`, and `missing`. Preserve source quality separately from confidence and limitations. A successful supplier response proves interface behavior only; record what metric semantics were validated before assigning a tested label.

TokConnect schema leads to check include `queryId`, `queryText`, `searchVolume`, `popularity`, `videoCount`, `trend7d`, `trendScore7d`, and category fields. Its claimed seven-day `searchVolume` is global unless a returned breakdown establishes otherwise. Confirm whether `trend7d` contains independent daily counts or rolling/other readings; array names and a final value matching a seven-day total do not establish daily-count semantics. If literal phrases cannot be distinguished reliably from generated groups, retain an unknown classification and limitation.

## 13. Analytical and product-selection requirements

### Trend analysis and independent evidence

- Compare a requested interval with the preceding non-overlapping interval of equal duration where coverage and methods permit. Additional baseline collection is subject to the same source and budget limits and must be disclosed.
- Track current and previous mentions/interest, absolute difference, and percentage growth only when mathematically and methodologically meaningful. A zero baseline is not infinite growth; a large percentage from a tiny base is weak evidence by itself.
- Where supported, consider unique communities/creators, engagement distribution, momentum across multiple observations, persistence, freshness, novelty, seasonality, spam, and concentration in one viral post.
- Compare sampling effort and coverage between periods. Changing result limits or source availability must not masquerade as market growth.
- Use `emerging`, `sustained`, `declining`, and `spike-only` classifications when evidence supports them; otherwise leave classification unassessed. Numeric thresholds are not finalized.
- Every reported problem needs a checkable source reference. Higher confidence requires independent observations; reposts, cross-posts, or repetitions of one campaign do not become independent corroboration.

For Reddit, collect permitted titles/bodies/comments and relevant counters, preserve links, and minimize author identifiers. Phrases such as "I wish there was," "is there an app for," "any alternatives," "too expensive," and "doesn't work" are useful heuristics, not the only extraction method or proof of willingness to pay.

For TikTok, examine repeated before/after demonstrations, one-click results, clear value propositions, questions such as "what app is this," and complaints about current tools. Separate entertainment, product curiosity, recurring need, and explicit purchase intent. Public engagement is not proof of sales or a representative market sample.

Competitor and demand checks should consider existing products, prices/paywalls, reviews, unmet needs, distribution fit, frequency of use, service/inference costs, and plausible monetization. If Google/store/competitor data is not yet connected, mark that validation as pending instead of implying it happened.

### Ranking and economics

An initial **configurable, unvalidated ranking proposal** from the design notes assigns 25% to supported demand, 25% to distribution potential, 20% to monetization/LTV potential, 15% to unmet need, and 15% to MVP speed/complexity. These are not proven predictive weights or an implemented default. Keep score, confidence, evidence count, and missing data separate; never fill unknown dimensions with average values silently.

Assess blockers such as unavailable data, platform constraints, privacy/IP requirements, excessive service cost, and inability to run a meaningful test. A narrow niche still needs sufficient reachable audience, willingness to pay, and repeatability.

Metric conventions to preserve:

- `CTR = clicks / impressions`; `CPM = spend / impressions × 1,000`; `CPC = spend / clicks`; `CPI = spend / installs`; cost per trial is spend divided by trials.
- CPA must name the action. CAC must define a new paying customer and which costs are included. CVR must name both funnel stages.
- LTV must specify gross/net value, time horizon, store fees, and variable service costs. ROAS is attributed revenue divided by ad spend for an explicit attribution window.
- For an illustrative app funnel, `CAC = CPC / (click-to-install × install-to-trial × trial-to-paid)`. This is a scenario formula, not a market benchmark.
- Use optimistic/base/pessimistic assumptions when observed conversion and revenue data are missing. Consider net LTV minus CAC, payback, retention, and service margin; do not infer them from social engagement.
- B2B opportunities may require a buyer, partnership route, and sales-cycle model rather than an app-install funnel.

### Illustrative opportunity seeds

These are examples for discovery and clearly labeled fixtures, **not validated winning niches** or real collected trends:

| Narrow product direction | Possible channel to investigate | Important validation question |
| --- | --- | --- |
| Scanned PDF, invoice, or bank-statement data to CSV | Search | Specific task demand, accuracy, privacy, and repeat usage |
| Product photography for a narrow seller segment | Meta/TikTok | Demonstrable result, willingness to pay, and generation cost |
| Voice memo to structured notes | Search/App Store | Recurring workflow, alternatives, and competition |
| Room redesign preview | TikTok/Instagram | Creative appeal, result quality, and service margin |
| Resume tailored to a job description | Search | Commercial intent, saturation, and seasonality |
| Screenshot to structured data | Search/App Store | Profession-specific need, accuracy, and frequency |
| Photo of notes to flashcards | TikTok/ASO | Student demand, seasonality, and retention |
| Subtitle translation or reformatting | Search/SEO | Professional workflow, permitted APIs, and payment evidence |

## 14. Next-agent checklist and completion criteria

The initial stack, canonical skill/discovery paths, bounded catalog, versioned contracts, local run layout, and conservative limits are implemented. Provider credentials and authenticated source usefulness remain unresolved. Keep the plan updated as each live validation is completed; do not infer authenticated integration readiness from the completed helper.

The next useful sequence after v0.1 is:

1. Inspect the actual branch/worktree and read `AGENTS.md`; preserve unrelated changes. Use this plan as the current context, with its dated evidence and unresolved access conditions.
2. Apply section 22's current preflight and compact-report contract; it supersedes earlier TikTok terms-link prerequisites and verbose report layouts. Test representative natural-language research in fresh Codex and Claude Code sessions using the packaged skill. Native plugin discovery/install and local synthetic version transitions were checked on November 2; semantic model behavior is still unverified. Avoid duplicate standalone/plugin copies. Record model behavior separately from deterministic helper and artifact tests.
3. Resolve TikTok onboarding and metric validation on the free allocation. User participation may be required for missing setup/consent; inspect the current client rather than treating dated authentication failures as current access state. Record actual tools, quotas, source terms, window semantics, and what was cross-checked.
4. Resolve a permitted Reddit adapter or retain an explicit unavailable/terms-unconfirmed result. Do not hold all useful work indefinitely on Reddit access or silently treat an unresolved source as production-ready.
5. Run the first useful permitted multi-source research and evaluate problem evidence, alternatives, independent corroboration, and the proposed tests. Broader automation/ranking and more granular Signals tables should follow demonstrated need, not expand the initial slice silently.

For the analytical revision included in 0.2.0, exercise both discovery and existing-product refinement using section 17's decision criteria. Do not confuse deterministic contract checks with model behavior or authenticated source validation.

Minimum acceptance criteria:

- Default and explicit provider selection, seven-day/14-day/custom windows, and topic filtering work as described; unselected platforms receive no requests.
- Each selected provider and signal has an honest status, requested/actual window, freshness, limits, and source provenance. A source failure or free-credit exhaustion produces an informative partial result.
- No fabricated numbers, historical series, geography, purchase intent, or exact search phrases inferred from generated topic groups. Unknown or unsupported data remains explicit.
- Significant conclusions and product problems trace to evidence; confidence reflects independent support and limitations. Weak data does not force a full hypothesis shortlist.
- Pagination/deduplication, date boundaries, publication versus observation times, zero baselines, rolling windows, and budget/error paths have meaningful deterministic checks once implemented.
- A compact report and JSON can be reproduced from recorded parameters and permitted snapshots/release versions. Logs expose counts, filters, errors, and coverage reasons without secrets or unnecessary personal data.
- Fixtures and static checks are distinguished from authorized runtime tests, source accuracy verification, and production proof.
- The skill can operate with one available source and declare the rest unavailable. Broader integration readiness remains incomplete until its required access and useful signal types are actually validated.
- The canonical skill is usable in both target agents without duplicated research logic. README and this plan list real setup/run/verification commands only after those commands exist.

## 15. v0.1 implementation handoff

### Files and execution

- `skills/niche-hunter/SKILL.md`: shared workflow, natural-language parameter extraction, selected-source routing, evidence/analysis rules, and concise delivery.
- `references/catalog.json`: versioned bounded discovery seeds; `references/providers.md`: portable access constraints and verified versus unverified source semantics; `references/contracts.md`: concrete import/results/analysis contract and replay rules.
- `scripts/research.py collect`: run validation, calendar date normalization, public Signals collection, permitted normalized imports, provider failure isolation, source-ID deduplication, and initial Markdown/JSON artifacts. No authenticated Reddit/TikTok requests are embedded.
- `scripts/research.py finalize`: validates calling-agent analysis/evidence references and renders existing results without networking or recollecting. It does not verify the factual correctness of model-written conclusions.
- `agents/openai.yaml`: Codex display metadata; shared frontmatter uses only standard name/description fields. Both project client directories symlink to `../../skills/niche-hunter`.
- `tests/test_research.py`: synthetic helper scenarios; no third-party messages, credentials, or real supplier fixtures.

Portability requirement: keep the skill package in English and use neutral examples without personal paths, workstation-specific tooling, regional time-zone examples, country/language presets, or locale-specific topic aliases. Time zone, region and content language are caller/source parameters, not author-specific defaults. UTC remains the disclosed fallback when no caller time zone is available; `seed_language` describes the actual discovery-seed language, not a target-market filter. Time-zone correctness and DST tests remain necessary, separately from user-facing examples.

Repository commands:

```bash
python3 skills/niche-hunter/scripts/research.py collect \
  --out .nichehunter/runs/NEW_RUN
python3 skills/niche-hunter/scripts/research.py collect \
  --providers tiktok,reddit --days 14 --topic horoscopes \
  --out .nichehunter/runs/ANOTHER_NEW_RUN
python3 skills/niche-hunter/scripts/research.py finalize \
  --run RUN_DIR --analysis RUN_DIR/analysis.json
python3 -m unittest discover -s tests -v
```

Run directories must be fresh/empty and are ignored by Git. `collect` leaves semantic analysis pending; the calling agent writes the versioned analysis object and calls `finalize`. A concise, honest result may contain zero product hypotheses when no observed problem is supported. Normalized permitted imports remain subject to their original storage/retention terms. No secrets are handled by the helper; client authentication belongs in the client's secure facilities.

### Verification on November 1, 2026

- Synthetic checks cover seven-day/14-day/custom windows, DST and preceding intervals, invalid inputs, selected/unavailable source isolation, offline replay, monthly context and unsupported topics/filters, deduplication/exclusive boundaries/caps, source failure isolation, zero/missing baseline, preservation of rolling-window semantics, bounded retries, rights metadata, total external-call caps, and offline finalization with rejected invented evidence IDs.
- A bounded **live execution of the new helper** downloaded the public Signals ZIP successfully. It parsed 189 table rows and retained 14 observations (seven categories for September and August 2026) with attribution and a snapshot hash. Reddit and TikTok were reported as `unconfigured`, with zero network calls to them. The public release was separately replayed offline; replay is not a second live provider test.
- The filesystem discovery links resolve to one canonical directory. Current official [Codex](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills) and [Claude Code](https://code.claude.com/docs/en/skills#choose-where-skills-load) documentation supports project discovery and symlinked skills. Fresh-session loading and model behavior are **not yet verified** in either client.
- Authenticated MCP schemas/responses, free credit balance/charging, supplier metric accuracy, source completeness, commercial Reddit rights and permissions, and useful multi-source hypotheses remain unverified. No accounts, purchases, background jobs, ad experiments, or global client configuration were created.

The host skill-creator validator needs PyYAML separately; it is not a runtime dependency of Niche Hunter. Keep validation-tool dependencies in a temporary/tool environment rather than adding them to the research helper.

## 16. Public distribution and release workflow

Agreed November 2, 2026, with tag naming updated November 5: `develop` is for ongoing work and checks; `master` is the stable source for users. Each public release gets an immutable `MAJOR.MINOR.PATCH` tag, a matching GitHub Release, and changelog notes. README contains separate Install for Codex, Install for Claude Code, Update and Rollback sections. Users can follow stable `master` or pin a published tag.

### Implemented packaging

- Root `plugin.json` is the portable plugin identity/version; `.claude-plugin/plugin.json` supplies Claude compatibility metadata. Both expose the single `skills/niche-hunter/` runtime. Plugin invocation is namespaced (`$niche-hunter:niche-hunter` / `/niche-hunter:niche-hunter`); repository-local invocation remains unprefixed.
- `.agents/plugins/marketplace.json` and `.claude-plugin/marketplace.json` resolve source `./` at their own checked-out root. A tag therefore pins the runtime as well as the catalog; no nested remote source silently follows `master`.
- `scripts/release.py check/build/notes` validates product version consistency, a matching changelog/tag, contained runtime files and portable content. It builds a deterministic ZIP with SHA-256 checksums and extracted release notes. Product versions are independent of the `0.1.0` research JSON contract.
- `.github/workflows/ci.yml` tests releases and research helpers on Python 3.10/3.14. `.github/workflows/release.yml` requires the tag commit to be contained in stable `master`, verifies version/notes, reruns tests, builds assets and publishes a GitHub Release. Administrative branch protection/required checks are separate and have not been configured by these files.
- `docs/releasing.md` documents promotion, release verification, failure handling, rollback and return to stable updates. Do not move existing tags or overwrite published assets. Keep reports/imports outside plugin caches; removing a marketplace can clear plugin-managed state.
- Public directory submission is separate from direct GitHub marketplace distribution and has not been performed. No server, background updater, provider-account provisioning or new subscription is introduced. Claude users can enable auto-update for this third-party marketplace; Codex uses the documented explicit marketplace refresh/install path here.

### Verification and limits

- Nineteen deterministic tests pass: the original helper scenarios plus manifest/tag consistency, pinned-root containment, reproducible curated archives, and extracted install/update/rollback runs. Synthetic product versions are fixtures and are never published as actual releases.
- Native Codex CLI `0.166.0-alpha.5.1` and Claude Code CLI `2.1.316` installed the packaged skill from a temporary local marketplace, updated the fixture from `0.1.0` to `0.1.1`, and rolled back to `0.1.0`. Claude enumerated exactly one skill and no MCP/hooks/agents. The temporary Codex registration was removed; Claude verification used a separate temporary configuration directory. No model queries or provider calls were made by those checks.
- Claude's manifest validator passed. An ignored, untracked filesystem metadata file in the working tree is outside the curated ZIP and Git distribution; validate the extracted release package separately from the working folder's directory-listing advice.
- Public verification completed: [develop CI](https://github.com/roland19deschain/niche-hunter/actions/runs/41446006334) passed Python 3.10/3.14 at commit `3dd6a257f9231ffa34a2999e70b682e67469dc17` before promotion; [master CI](https://github.com/roland19deschain/niche-hunter/actions/runs/41446218872) and the [Release workflow](https://github.com/roland19deschain/niche-hunter/actions/runs/41446247406) also succeeded. The annotated tag was published as `v0.1.0` and now has the name `0.1.0` at the same implementation commit (section 20).
- [GitHub Release 0.1.0](https://github.com/roland19deschain/niche-hunter/releases/tag/0.1.0) originally published `niche-hunter-v0.1.0.zip` (2,097,143 bytes) and `SHA256SUMS`. Before the section 20 migration, the downloaded ZIP matched the checksum and local build byte-for-byte: SHA-256 `f7d1dfa07bffd3ac330990118296115def35dba179f64d63e257c07849b168f3`. The downloaded helper ran offline and correctly reported the sole selected Reddit source as unconfigured without calling other platforms.
- Native GitHub checks passed in both clients for stable `master`, explicit marketplace refresh/update, and reinstall from the then-published `v0.1.0` tag (now `0.1.0`). Those actual public sources were tested separately from the local synthetic `0.1.0 → 0.1.1 → 0.1.0` transition. Temporary test registrations were removed; no provider credentials or user research outputs were stored in the plugin.
- This verification record is a documentation-only follow-up after the immutable release tag; it does not change packaged runtime bytes or move the tag. Interactive model research, cloud-surface behavior and authenticated provider access remain separate follow-up work. GitHub branch protection has not been configured; CI/release workflow checks and documented promotion rules are implemented.

## 17. Channel-to-product analysis revision — November 4, 2026

The user clarified the primary outcome before social-provider implementation: collect observations, analyze them deeply, and find defensible **distribution channel → reachable market/need → product** combinations. Support both discovery of new products and improvement of an existing product in a selected domain. This section records the development revision; its 0.2.0 publication is recorded in section 19. It does not authorize provider-account setup or data collection.

### Audit findings and implemented direction

- Distribution First already existed, but a free-text channel/hook did not require explaining channel access, audience intent, or the path to product use. The analysis could therefore append a channel to a trend-based idea without supporting the combination.
- Existing-product refinement had no explicit context/mode. The skill now distinguishes `discovery` from `refinement`, preserves caller constraints, and relates product changes to the existing workflow/positioning rather than proposing unrelated new products.
- Evidence providers and acquisition channels are explicitly separate. A need found on Reddit can inform a product whose search acquisition remains untested. Aggregate Signals data cannot identify a narrow audience or establish an acquisition route.
- `references/analysis.md` guides need clustering, alternatives, concrete channel surfaces, acquisition paths, solution/channel fit, counterevidence, and tests of the weakest link. Stable needs and desired outcomes remain valid; rising trends and explicit complaints are not prerequisites.
- New analyses include `research_context` and a per-hypothesis `opportunity` block: reachable market, separate demand/channel evidence IDs, channel-fit status, entry point, acquisition path, fit reasoning, counterevidence, and a justified next action (`test_next`, `research_more`, `defer`).
- Finalization validates the additive structure and evidence subsets. Supported/inferred channel fit requires channel references; untested fit requires none. This checks declared structure, not whether the reference actually supports the argument. Legacy v0.1 analyses remain accepted; collection/import schema version stays `0.1.0`.
- Reports put coverage, decision context and a channel/market/product shortlist before the evidence appendix. Detailed evidence, source attribution, and limitations are preserved. Skill instructions still allow fewer hypotheses or none when evidence is weak.
- The release allowlist includes the new analysis reference. README, AGENTS, and the changelog describe the revised goal and output. The development revision left immutable `0.1.0` and client caches unchanged; section 19 records its subsequent inclusion in stable 0.2.0.

### Validation and next handoff

Verified on November 4: all **22** helper/release tests passed, including discovery/refinement finalization, preservation of source observations and run parameters, rejected unsupported channel declarations/evidence links, and legacy analysis compatibility. The host skill validator, `scripts/release.py check`, package build into a temporary review directory, and `git diff --check` also passed. The existing HTTP-error fixture emits a non-failing resource-cleanup warning. Synthetic fixtures verify structure and serialization, not supplier access or the model's analytical quality. No provider calls, client-cache updates, commit, stable promotion, or release publication were part of this revision.

Next, validate authorized TikTok and Reddit access as described in section 14. On the first real useful runs, evaluate whether the calling agent can explain every channel → need → product link, distinguish need from channel evidence, account for contrary observations, and propose a measurable test of the riskiest link. Check an existing-product refinement case and a broad/insufficient-evidence case in both clients before treating analytical quality as established.

## 18. TikTok provider v1 — implementation handoff

Implemented on **November 4, 2026**, at the user's request, and included in 0.2.0 (section 19). The user confirmed there is still no TokConnect account; first setup and authenticated data validation remain necessary. This is the first **search** adapter, not a general TikTok crawler or a completed commercial-source validation.

### Execution and package

`shared skill → client-managed TokConnect OAuth/MCP calls → scripts/tiktok.py → normalized import → research.py collect → calling-agent analysis → finalize`.

- Root `mcp.json` declares the public Streamable HTTP endpoint. `.claude-plugin/mcp.json` declares the same endpoint with Claude's `http` transport, referenced explicitly by the Claude manifest. No credentials, shared OAuth client or local server executable are bundled. A standalone skill copy does not inherit plugin MCP configuration.
- `extensions.com.openai.onboardingSkill` reuses the shared research skill's explicit setup route. Normal research reuses existing access or reports its failure; it does not unexpectedly create accounts or launch login. Users sign in through their client/browser, with client-managed credential storage.
- `skills/niche-hunter/references/tiktok.md` defines setup, current tool/method routing, quota/rights checks, the capture contract and normalization commands. `scripts/tiktok.py` is standard-library-only and performs **no network or credential access**.
- V1 accepts compact `demand_find_topics` search/feed/trending, `demand_topic` detail/related, and `demand_keywords` TikTok autocomplete. It unwraps documented MCP/JSON shapes and generates the existing v0.1 import envelope. Videos/comments, Shop/ads, demographics, automatic historical growth and verified regional/language filtering remain outside this version.
- Captures require actual call counts, zero new paid spend, verified free allowance and explicit permitted-storage basis before retaining data. Topic-scoped results require caller-reviewed selection. Failure captures support no-account/auth/rights errors without fabricated credentials or balance.
- The adapter retains at most 100 unique observations and 10 captured calls. Repeated topic snapshots use the most recent retrieval (last capture on equal times); undated trend readings are retained without summing. Missing metrics remain null; zero matched videos remains zero. Source publication/measurement times are unknown unless supported; retrieval time does not invent a seven-day boundary.
- CSI entities remain `unknown` rather than guessed literal typed searches; autocomplete is `recommended_keyword`. Supplier measurements remain `provider_claim_unverified`. Exact source windows are preserved when established; missing dates and unsupported filters produce explicit gaps/partial coverage.
- Safe receipts retain tool/method, selected nonsecret parameters, retrieval time, call status and pagination information. Headers, author fields, raw errors and opaque cursors are not copied into normalized results. HTTP 401, 402/429, 403, other errors, protocol errors and partial successful batches have distinct handling. Unknown response shapes stop this adapter rather than silently appearing as an empty successful search.
- The curated release allowlist and tests include both connection configs, the adapter/reference and `PRIVACY.md`. The privacy document explains local artifacts, client processing, third-party requests and credential handling; its stable GitHub URL is public with 0.2.0. The initial implementation left 0.1.0 and installed caches unchanged; section 19 records the version bump and stable publication. Existing users update through their client marketplaces.

### Source checks and remaining acceptance

Primary references: [demand schemas](https://tokconnect.com/docs/api/demand/), [current pricing](https://app.tokconnect.com/pricing), [supplier Codex setup](https://tokconnect.com/connect/codex/), [supplier Claude Code setup](https://tokconnect.com/connect/claude-code/), [official OpenAI plugin MCP/onboarding packaging](https://developers.openai.com/plugins/build/plugins), and [official Claude plugin MCP support](https://code.claude.com/docs/en/mcp#plugin-provided-mcp-servers).

Verified November 4:

- Public demand schemas and compact examples were reviewed. These are supplier documentation, not authenticated responses from our account. Public pricing advertises Free with 50 initial credits/no card and one credit per lookup; REST is now advertised on every paid plan. Real free balance/charging remains unverified.
- A bounded unauthenticated MCP initialize request returned **401** with the protected-resource metadata challenge. Protected-resource discovery returned issuer `https://app.tokconnect.com` and scope `mcp`; authorization-server discovery advertised DCR, PKCE S256 and authorization/token endpoints. Zero research tool calls and no account registration were made.
- Native Codex local `plugin/read` recognized **one `tokconnect` MCP server, one research skill and that same onboarding skill**, without installing a candidate or changing the user's plugin registrations. This is package discovery, not an authenticated connection or research run.
- Synthetic tests cover MCP wrappers, null versus zero, conservative entity typing, autocomplete, latest-record replacement, retained trend semantics, topic selection, failed/partial calls and usage, rights/free-budget limits, record caps, and adapter → collector processing of a seven-day fallback for a 14-day request. Release tests reject secret-bearing or drifting connection manifests.
- All **33** helper/release tests passed locally. The host skill validator, release consistency check, Python 3.10 syntax parsing, local skill-reference checks and whitespace checks passed. The extracted review ZIP passed Claude's native directory profile with `--strict` and no findings. A packaged no-account smoke check produced `auth_required`, zero observations and zero research-tool calls for the sole selected TikTok provider. These checks do not establish authenticated collection or model research quality.

Before calling TikTok operationally validated:

1. Have the user create/select their Free TokConnect account and authorize it in the chosen client. Verify the actual account's free allowance and charging; do not rely on the advertised starting balance.
2. Establish applicable research/storage/retention rights from the account's terms or supplier authorization. Public documentation did not resolve that basis; the attempted public terms routes did not provide usable terms. Do not set `storage_permitted: true` merely because login works.
3. Inspect live tool schemas and make a minimal authorized call, then a small topic/detail research sample. Validate response wrapping, IDs, pagination, freshness, metric windows, missing values and costs; update the adapter only from observed differences.
4. Cross-check representative metrics/entity types against an authorized primary TikTok view where possible. Successful JSON does not verify search-volume accuracy or literal-query identity.
5. Exercise end-to-end research and setup in both target clients, including expired auth, no credits, topic mismatch, custom dates and the no-useful-need case. Record model behavior separately from deterministic fixtures. Do not implement Reddit or broaden to video/Shop scraping as an implicit fallback.

## 19. 0.2.0 release handoff — November 4, 2026

The user authorized release and synchronization of `develop` and `master`. Both client manifests now use product version **0.2.0**; research/import/analysis schemas remain **0.1.0**. The immutable 0.1.0 release is retained for rollback. The 0.2.0 changelog covers channel-to-product analysis, existing-product refinement, TikTok MCP/search normalization, the Adjust/AppsFlyer future-provider roadmap, and portable English project guidance.

The release packages connection declarations and setup instructions, not provider accounts or shared credentials. TikTok's first adapter is limited to search topics/detail/related topics and autocomplete. Authorized data access, permitted storage, live free allowance, metric accuracy and model research quality remain open acceptance items; publishing the plugin does not complete them.

Original release procedure: validate the exact candidate and deterministic assets, push `develop`, wait for its CI, fast-forward stable `master`, and publish annotated tag `v0.2.0` through the then-current Release workflow. Section 20 records its later rename to `0.2.0`. Verify public notes, ZIP/checksum and source ancestry after publication. At preparation time GitHub Actions reported a partial outage and the preceding develop run remained queued; do not describe queued jobs as passed.

Original publication and verification completed (asset names/checksums below predate the section 20 migration):

- [Develop CI](https://github.com/roland19deschain/niche-hunter/actions/runs/41866681935) passed Python 3.10/3.14 at exact commit `8c35dfbf83a9ad2fe702ef5efe42570020f78dd9` before stable promotion. [Master CI](https://github.com/roland19deschain/niche-hunter/actions/runs/41868333595) and the [Release workflow](https://github.com/roland19deschain/niche-hunter/actions/runs/41868414059) also completed successfully after the queue resumed.
- [GitHub Release 0.2.0](https://github.com/roland19deschain/niche-hunter/releases/tag/0.2.0) is public, neither a draft nor a prerelease. Its immutable annotated tag points to the tested commit. It originally published `niche-hunter-v0.2.0.zip` and `SHA256SUMS`; section 20 records the replacements.
- The downloaded ZIP is **2,147,866 bytes**, with SHA-256 **`4ce723bf13bb02bcc5ec1bd2c731a5dabe3e23528ff7be18bc29e3b0849428f9`**. It matched the published checksum and local deterministic build byte-for-byte. The package contains product version 0.2.0 and schema version 0.1.0.
- All **34** local helper/release tests passed. Native Codex recognized one TokConnect MCP server, the shared skill and its onboarding route in the extracted package; Claude's strict directory validation had no findings. A packaged no-account TikTok run returned `auth_required` with zero observations/calls.
- Native Codex installed the downloaded, verified package using a temporary marketplace name; native Claude Code installed the actual public GitHub `v0.2.0` source (now `0.2.0`) in an isolated configuration. Both reported version 0.2.0. Test registrations were removed and existing user installations were preserved. No model, authenticated research, account registration or paid calls were part of these checks.
- This publication record is a documentation-only follow-up after the immutable tag. It does not change the release's runtime/archive bytes. Keep develop and master synchronized after its CI; the next integration step is user-authorized TokConnect setup and the still-open live acceptance checks in section 18.

## 20. Bare release tags — November 5, 2026

The user explicitly authorized renaming the two existing tags before public adoption and applying the same convention to all future repositories. Release tags now equal the version number exactly, without a leading `v`: `0.1.0`, `0.2.0`, and future `MAJOR.MINOR.PATCH` versions. Product versions and the `0.1.0` JSON contracts are unchanged. The global Codex instructions also record this prefix rule across all technology stacks while preserving each repository's version-number format.

This is a naming migration, not a new feature release. Both new annotated tags retain their original source commits:

| Tag | Preserved source commit |
| --- | --- |
| `0.1.0` | `3dd6a257f9231ffa34a2999e70b682e67469dc17` |
| `0.2.0` | `8c35dfbf83a9ad2fe702ef5efe42570020f78dd9` |

The prefixed tag refs were removed locally and from origin. GitHub Release records retained their IDs and original publication dates; names, tag associations and notes were updated. The ZIP names now omit the prefix, and their packaged README references point to the renamed tags. Every other archive entry is byte-identical to its original published content. New SHA256SUMS files cover these replacement ZIPs; the original hashes in sections 16 and 19 are historical, not current download hashes. The migration backup contains the original Git bundle, release metadata and assets outside the repository.

| Release asset | Bytes | SHA-256 |
| --- | --- | --- |
| `niche-hunter-0.1.0.zip` | 2,097,136 | `3202e27acac2b11c7224da7ca65ebd3d22afa51a861b769e492fc90add8ad8ff` |
| `niche-hunter-0.2.0.zip` | 2,147,857 | `23f87db6160824a0396c2fc27e4246c1cf930160cced834820a8478b456d445c` |

Release tooling now validates an exact bare tag/version match, builds `niche-hunter-VERSION.zip`, and emits source links under `/blob/VERSION/`. The Release workflow listens for numeric version tags and retains its exact version check and stable-ancestry requirement. README install/rollback examples and project guidance use the same convention. All 34 local tests passed, including rejection of prefixed/mismatched tags, deterministic archives, versioned source links, and extracted install/update/rollback behavior. Downloaded migration assets were checked against their new checksums and original runtime entries.

A prior metadata-only branch-history rewrite left equivalent release source trees on separate commit histories. This tag migration preserves the original release commits rather than retargeting them to rewritten equivalents, so the graph may still show a second line. Original CI/native-install evidence remains dated to the original publication; it is not a fresh authenticated provider test. Historical tagged source snapshots still contain their original release scripts and instructions: use current `develop`/`master` tooling for future releases. Publish subsequent corrections under a new version instead of routinely moving published tags or replacing assets.

Next work remains authorized TokConnect account setup and the live acceptance checks in section 18, followed by permitted Reddit access. Tag naming does not provision provider access or change the free-pilot budget.

## 21. Claude Code first-run release 0.2.1 — November 5, 2026

The user authorized setup preparation, a commit and a new release, and will run the skill in Claude Code using an already prepared TokConnect account. This supersedes the earlier no-account state. Credentials and consent remain in the calling client's facilities; no login details or research data belong in Git. The free-pilot budget and unresolved source rights/metric validation remain unchanged.

Version 0.2.1 adds a concrete Claude Code setup/readiness workflow and first TikTok-only research prompt. It separates authentication, supported tool discovery, verified free allowance/call cost, and permitted-storage basis. Existing accounts and bundled connections are reused. Setup alone does not spend research credits, fabricate a remaining balance, or claim successful collection. A later seven-day/14-day run reports actual supplier coverage.

The normalizer now accepts supported short tool names and client-callable MCP namespaces, including Claude's documented `mcp__plugin_niche-hunter_tokconnect__demand_find_topics` and Codex's `mcp__tokconnect__demand_find_topics`. It retains the canonical route and original callable name in safe provenance. Unsupported tools/methods remain rejected; data semantics and JSON schema version `0.1.0` are unchanged. This closes a first-run import gap identified by comparing the original short-name-only validator with the client's documented tool naming.

November 5 checks: current Claude documentation and installed CLI 2.1.316 both provide `claude mcp login NAME`; `/mcp` remains the interactive authorization route. Plugin names/tool namespaces and the existing HTTP transport were reviewed against official client documentation. The bundled endpoint remains credential-free and client-managed. Source documentation/schema checks do not prove authenticated account access.

Release 0.2.1 includes the previously committed bare-tag tooling/docs changes. Both manifests use `0.2.1`; the annotated tag and GitHub Release are `0.2.1`. Publication followed the exact-commit CI → stable promotion → tag procedure in `docs/releasing.md`. The user's Claude Code live acceptance run remains pending and must be reported separately from synthetic tests or package validation.

Pre-publication validation completed: all **35** helper/release tests passed, including namespace normalization with preserved observations/provenance and rejection of unsupported routes. The host skill-creator validator, release `check/build --tag 0.2.1`, Python 3.10 grammar parsing and whitespace checks passed. The extracted runtime ZIP passed Claude Code's strict directory profile without findings. In an isolated configuration, native Claude Code 2.1.316 installed product version 0.2.1 and resolved `plugin:niche-hunter:tokconnect` to the bundled HTTP endpoint with status **Needs authentication**, as expected without credentials. Temporary registrations were removed and the user's client configuration was not changed. These checks made no authenticated research or paid calls.

Publication verified:

- [Develop CI](https://github.com/roland19deschain/niche-hunter/actions/runs/42032300477) passed Python 3.10/3.14 at exact commit `f93ea8bf2bb002992a298e17dcc5673d1ef18aee` before promotion. [Master CI](https://github.com/roland19deschain/niche-hunter/actions/runs/42032402708) and the [Release workflow](https://github.com/roland19deschain/niche-hunter/actions/runs/42032445339) also succeeded.
- [GitHub Release 0.2.1](https://github.com/roland19deschain/niche-hunter/releases/tag/0.2.1) is public, not a draft/prerelease, and retains that source commit. It contains `niche-hunter-0.2.1.zip` (**2,153,663 bytes**) and `SHA256SUMS`. The downloaded ZIP matched its checksum and the local deterministic build byte-for-byte: SHA-256 **`ccaa11f99b84db03e3cf88a8526244885763149d993dbf9ac3a78ce911e4fc87`**. Manifest versions and versioned README links in the downloaded ZIP were checked.
- Native Claude Code installed the actual public `#0.2.1` source in an isolated configuration and resolved the bundled server as **Needs authentication**. Temporary registrations were removed. The plugin was then installed and enabled at user scope from stable `master` for the requested first run; it reported version 0.2.1. No keys or account data were added to plugin files.

Observed authentication blocker:

- A normal noninteractive shell cannot complete this CLI's browser authentication; its documented login flow requires an interactive terminal. An interactive retry with the actual bundled server failed before opening browser consent: `SDK auth failed`, validation path `client_uri`, `Invalid URL` / `URL must be parseable`. Authorization was not completed; no research tool/data call or paid spend occurred. Do not describe the installed plugin as an authenticated TikTok integration.
- Public protected-resource discovery still advertised issuer `https://app.tokconnect.com` and scope `mcp`. A separate unauthenticated request to the authorization-server metadata URL returned 403. Neither observation establishes the cause of the CLI validation failure. Similar optional-URL response validation is reported in [Anthropic issue 13685](https://github.com/anthropics/claude-code/issues/13685), but that is not proof of TokConnect's root cause. Do not weaken validation, proxy around access controls, or modify installed client binaries.
- The supplier documents a personal MCP-key connection as an alternative in its [Claude Code guide](https://tokconnect.com/connect/claude-code/). The user has not yet checked whether a key is available. Verify its account entitlement and free allowance before choosing that route; enter a key only through private client configuration, never chat, shell history, Git or plugin manifests. Reuse one working connection and avoid duplicate active servers. OAuth or key access, usage/storage rights and useful metric semantics remain acceptance work.

This follow-up records publication and the observed setup blocker; it does not move tag 0.2.1 or replace its assets.

Next acceptance steps:

1. Install/update 0.2.1 in Claude Code and authenticate the listed bundled TokConnect server using the prepared account. Confirm the actual supported tools, free allocation and permitted research/storage basis.
2. Run one small TikTok-only research after readiness is established. Inspect the live response schema, costs, freshness and measurement windows; fix only observed incompatibilities. Save permitted diagnostics and reports outside Git.
3. Verify default seven-day and explicit 14-day fallback reporting, then evaluate channel → reachable need → product reasoning in discovery and refinement modes.
4. Resolve a permitted Reddit adapter and run useful multi-source research. Provider expansion and paid services remain outside this release.

## 22. Provider preflight and compact exports — November 6, 2026 (review)

The original November 6 request was implementation for review only; no commit or release was made during that step. The user subsequently accepted the changes and authorized release plus branch synchronization in section 23. The review used product version 0.2.1; the release candidate now uses 0.3.0. This section supersedes earlier operational instructions requiring a TikTok terms URL or permission declaration and earlier report layouts with detailed product cards/evidence appendices. Historical source checks and release evidence above retain their original dates and meaning.

Current behavior:

- Resolve all implemented providers by default, then explicit only-lists/exclusions. Inspect existing connections for every selected provider, list configuration readiness and explicitly request missing setup in one batch before any research query. Reuse working connections. Public Signals needs no credentials. Unknown providers require scope resolution; future roadmap entries are not implemented adapters. A blocked provider is omitted only if the caller explicitly excludes it. Runtime failures after successful setup can still produce partial coverage.
- `research.py preflight` performs no research calls and reports selected routes plus PDF capability. Checked client routes are declared by the calling agent, not authenticated by Python. `--exclude-providers` is applied before configuration/collection. Normal `collect` rejects missing Reddit/TikTok result inputs before helper HTTP or output creation; an explicit `--diagnostic` mode remains for maintenance coverage tests.
- Available TikTok data can be processed/stored locally at the caller's direction. Neither the normalizer nor the TikTok import validator requires `rights`, `storage_permitted`, `basis` or a terms URL. Supplied metadata is optional provenance, not an invented permission or a processing gate. Existing authentication, actual call counts, no-new-paid-spend budget, source/measurement validation and secret handling remain. Reddit access requirements are unchanged. Legacy failure records remain readable; do not generate a new TikTok terms failure merely because a link is absent.
- Short report order: each selected provider's compact linked data table/optional compatible chart and one short channel/need conclusion; then overall situation; then zero to three best channel/market → problem/desire → product/change combinations with at most two short solution sentences. Deep analysis and provenance remain in JSON. No mandatory hypothesis quota, long product cards, gap lists or evidence appendix in the initial answer. Essential coverage differences are retained in a short line rather than hidden.
- `reporting.py` creates one report model used for Markdown, terminal text and PDF. Additive analysis `presentation` fields supply caller-language labels, selected observation IDs and per-provider conclusions; `brief` supplies short solution descriptions. References must belong to the selected provider; chart measurements need compatible names, units and windows. Unknown metrics are not zero. Provider evidence and a distribution channel remain distinct, especially for broad Signals context.
- `report_pdf.py` uses ReportLab and bundled unmodified Noto Sans fonts with their OFL license. The renderer has no network/browser/system-font dependency. The font choice does not set a market or language; custom TrueType fonts/native export cover other scripts. Unsupported glyphs fail explicitly. The native client route uses an already rendered equivalent PDF, which the calling agent must visually check.
- Finalization prepares matching `report.md`, `report.pdf` and detailed `results.json` without recollection, records export hashes and preserves earlier artifacts when validation/rendering fails. `report --format text` prints plain-text tables/ASCII charts for CLI use. Desktop callers use readable native tables/charts/artifact tools where actually available and attach both report files.

Dependencies and verification:

- Collection/normalization remain standard-library-only. Default PDF finalization requires `python3 -m pip install -r skills/niche-hunter/requirements-pdf.txt` in the chosen environment; test PDF extraction additionally uses `pypdf`. CI/Release workflows install those test/export dependencies before running the suite. The release allowlist includes both report modules, the reporting reference, requirements and licensed font assets. No version/tag change is part of this review.
- Synthetic tests cover missing-config rejection before network/artifacts, checked-route reuse, exclusions, unknown-provider rejection, TikTok processing without permission metadata, concise report order, evidence-reference validation, same-value text/PDF output, compatible charts, PDF links and glyph/export failures. These do not establish live source access or model behavior in either application. A clearly labeled synthetic preview is kept under ignored local runs for visual review, not as market evidence.

Review verification completed locally:

- **51** tests passed in the Python 3.14 review environment, including PDF text/links, Unicode glyphs, native-PDF import, artifact preservation, provider scope/preflight and compatibility checks. Python 3.10 grammar parsing passed; no new remote CI run was started for this uncommitted work.
- The host skill-creator validator, release consistency check, curated archive build, English-text scan and whitespace check passed. The extracted review package passed Claude Code's strict directory validation. No candidate was installed into the user's clients.
- The two-page synthetic report was rendered to page images and both pages inspected. Provider tables/charts/conclusions stay together; chart values match tables, source links are retained and no clipping/overlap was observed. Markdown and plain-text previews contain the same signals, conclusions and brief idea. Artifacts remain under ignored local review runs; no live provider research or paid calls were made.

The user accepted this revision and requested the additional palette change and release in section 23. Recheck live connection/budget state only for a subsequently authorized research run.

## 23. Release 0.3.0 — November 6, 2026

The user accepted section 22's implementation and authorized a commit, publication of a new version, and synchronization of `develop`/`master`. Before release, styled reports must use the supplied five-color palette: gold `#DCC48E`, paper `#EAEFD3`, sage `#B3C0A4`, slate `#505168`, ink `#27233A`. The shared report model records these values for PDF and available native-client styling. Portable Markdown/terminal output keeps the same content without unsupported color markup.

The PDF uses an eggshell page background, dark ink text, slate table headers with light paper text, alternating sage/paper rows, slate bars and gold idea highlights. The header accent and footer use the same palette. Color changes do not alter reported measurements or conclusions. Current runtime/example content stays English and portable; the calling agent can supply the report language through presentation fields.

Both product manifests use **0.3.0**. The annotated release tag and GitHub Release must be **0.3.0**, with no prefix. Research JSON version remains **0.1.0**; the renderer/configuration additions preserve existing saved inputs, and TikTok permission metadata is now optional. No new provider, shared credential, paid service or authenticated research run is included in this release. Provider access, source metrics and semantic model quality remain separate acceptance work.

Prepare/test the exact candidate, verify the recolored synthetic PDF visually, build/validate its curated archive, push `develop` and wait for CI on that commit. Promote it to stable `master`, push the tag, then verify the Release workflow, actual public ZIP/checksum and client installation. Record completed publication evidence here after those checks. Historical review checks in section 22 retain their original scope.

Pre-publication validation completed: all **51** tests passed locally on Python 3.14; Python 3.10 grammar parsing, portable English-content checks, the host skill validator, release consistency/build and whitespace checks passed. The extracted candidate passed Claude Code's strict directory validation without findings. Both pages of the recolored synthetic PDF were inspected; all five requested palette colors were also verified in its PDF drawing operations. These checks do not establish live provider access or real market demand.

Publication and distribution verified:

- [Develop CI](https://github.com/roland19deschain/niche-hunter/actions/runs/42206264082) passed Python 3.10/3.14 on exact commit `5ced0aa34b68c66fc867e39f4af0615db5da71c3` before promotion. [Master CI](https://github.com/roland19deschain/niche-hunter/actions/runs/42206390606) and the [Release workflow](https://github.com/roland19deschain/niche-hunter/actions/runs/42206406709) also succeeded.
- [GitHub Release 0.3.0](https://github.com/roland19deschain/niche-hunter/releases/tag/0.3.0) is public, neither draft nor prerelease, and its annotated tag points to the tested implementation commit. Published assets are `niche-hunter-0.3.0.zip` (**3,343,334 bytes**) and `SHA256SUMS`. The downloaded ZIP matches its checksum and the local deterministic build byte-for-byte: SHA-256 **`d1e762bf9f33461b9e4a43a21f2fb45e828c7cc12647bf4b6e2db55492d6c0c1`**. The package includes the PDF requirements, both licensed fonts and their OFL notice, and source links use `/blob/0.3.0/`.
- The downloaded runtime finalized the synthetic review analysis into a complete two-page PDF and matching Markdown using its own bundled fonts and shared palette. This was an offline export check, not collection or a market recommendation.
- Native Claude Code installed the public `#0.3.0` source in an isolated configuration and resolved its bundled TokConnect server as **Needs authentication** without account credentials. Temporary registrations were removed. That isolated status does not establish the state of a user's authenticated connection.
- Existing stable marketplace installations in both Codex and Claude Code were refreshed and updated to **0.3.0**, reported installed/enabled, and every shared runtime/metadata file was checked byte-for-byte against the source. Client credentials and provider authorization were not changed; no research/paid calls were made. Start a new chat/session to load refreshed instructions.

This documentation-only follow-up records successful publication; it does not move tag 0.3.0 or replace its assets. Keep develop/master synchronized after its CI. Next work is a caller-authorized real research run that uses preflight and reviews concise report usefulness, actual source coverage and account access.
