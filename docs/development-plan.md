# Niche Hunter — first-version development plan

Updated: **November 1, 2026**. Source investigations below retain their original verification dates.

**Document language: English. Keep all future updates to this plan in English.**

Status: **v0.1 of the shared skill is implemented**, with a Python standard-library helper, public OpenAI Signals collection, permitted normalized imports, and evidence-linked report finalization. The user authorized this first implementation on November 1. The **free pilot** remains in force; no source accounts or credentials have been provisioned. Authenticated Reddit/TikTok collection and cross-client behavioral validation remain incomplete. Purchasing subscriptions is outside scope.

## 0. Handoff snapshot — read first

This is the canonical project context and implementation plan. Earlier design notes and access investigations have been consolidated here; their historical versions remain in Git. An agent should be able to resume without the original chat, screenshots, meeting notes, or deleted documents.

| Area | Current state as of November 1, 2026 |
| --- | --- |
| Repository | Work in `develop`; inspect `git status` and both staged and unstaged diffs before editing. Do not assume local branches or remotes are synchronized. |
| Implemented artifacts | Canonical `skills/niche-hunter/`: shared `SKILL.md`, references/catalog, Python helper, and Codex UI metadata. Project `.agents/skills/niche-hunter` and `.claude/skills/niche-hunter` symlink to it. Synthetic behavior tests and actual commands are documented. No authenticated social-source adapter is bundled. |
| Runtime | Python 3.10+ standard library and IANA time-zone data; manual skill invocation with calling-agent analysis. No additional LLM API, continuously running collector, scheduler, hosted backend, or cloud storage. |
| Accounts and credentials | None available for Reddit, TikTok for Business, TokConnect, or licensed monitoring services. No credentials are committed. |
| OpenAI Signals | Live v0.1 helper download and offline replay verified. One global monthly topic-share table is supported, with release hashing, permitted ZIP snapshot, adjacent-month comparisons, explicit monthly fallback and unsupported narrow-topic handling. |
| TikTok | Public documentation, prices, and unauthenticated MCP/OAuth discovery checked. No authorized data response or metric accuracy validation yet. |
| Reddit | Bounded Arctic Shift metadata retrieval verified. Suitable commercial access, completeness, and future reliability remain unresolved. |
| Budget and scope | Free pilot only. Implementation is authorized; this document does not itself authorize account creation, paid purchases, advertising, deployment, or scheduled collection. Defaults: 100 normalized observations/provider, 10 external calls/run subject to confirmed free balance, at most two public Signals HTTP attempts. |

Resume by reading this snapshot, source-specific constraints in section 3, implementation contracts in section 12, and the next-action checklist in section 14. Treat dated probes as historical observations, not a current access guarantee. Recheck changing schemas, prices, terms, and permissions when implementing an adapter.

## 1. Goal and agreed decisions

Niche Hunter helps identify needs and niches for websites, web applications, mobile and desktop applications, and other small digital products. Research should connect observed interest to a specific user task, existing solutions, a distribution channel, and a minimal experiment before development.

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

The user is an experienced iOS developer/technical lead who can ship small applications and web-first products. Earlier discussions with Wowmaking supplied UA and paid-experiment experience, not confirmed accounts, partner integrations, advertising budgets, or authority to contact anyone. This project investigates the next product opportunity; optimizing OutLoud and deciding commercial collaboration terms are outside scope.

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
2. Start fresh local Codex and Claude Code sessions in this repository and test discovery plus representative natural-language requests. Do not install duplicate global copies by default. Use the same canonical skill, portable script, catalog, and v0.1 contracts. Record model behavior separately from deterministic helper tests.
3. Resolve TikTok onboarding and metric validation on the free allocation. User participation is required for account setup/consent; credentials are not currently available. Record actual tools, quotas, source terms, window semantics, and what was cross-checked.
4. Resolve a permitted Reddit adapter or retain an explicit unavailable/terms-unconfirmed result. Do not hold all useful work indefinitely on Reddit access or silently treat an unresolved source as production-ready.
5. Run the first useful permitted multi-source research and evaluate problem evidence, alternatives, independent corroboration, and the proposed tests. Broader automation/ranking and more granular Signals tables should follow demonstrated need, not expand the initial slice silently.

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

Actual repository commands (prefix with `rtk proxy` on this workstation):

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
