# Niche Hunter — first-version development plan

Date: **October 31, 2026**. Discussion time zone: `Europe/Minsk`.

**Document language: English. Keep all future updates to this plan in English.**

Status: access options have been researched and a **free pilot** has been selected. The user confirmed that no source accounts or access credentials are available yet; the current stage is information gathering. The skill, installation, account creation, and authorization setup have not been implemented. Purchasing subscriptions is outside this stage.

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

Project context: [context.md](../context.md). Previous access research: [source-access.md](./source-access.md). These are reference materials; availability, pricing, and schemas below have their own verification date.

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

Examples of intended interaction, **not working commands in the current repository**:

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

[source-access.md](./source-access.md) describes:

- Discovery: current trending and recommended search phrases, without search volumes for a selected week.
- Search Ads Keyword Ideas: monthly search-volume ranges and related metrics.
- Discovery Hashtags: content trends with supported windows, including seven days.

This research confirmed account requirements and Keyword Planner availability restrictions. Test actual responses and API windows after obtaining access; findings from the previous research do not replace a live test.

Official programmatic access may require a TikTok for Business account, an advertiser account, a developer application, approved permissions, and account-owner authorization. Search recommendations require the relevant Discovery permission. Requirements vary by endpoint.

Keyword Planner is available for supported advertiser-account countries; otherwise allowlisting may be necessary. The user's time zone alone does not determine availability.

**A separate current per-call API price has not been confirmed.** Do not label this as guaranteed free, ready-to-use access. Using planning tools also does not mean the pilot needs to launch advertising.

Sources: [Keyword Planner and eligible countries](https://ads.tiktok.com/resources/help/article/about-the-keyword-planner-tool-in-tiktok-as-manager?lang=en), [API for Business authorization](https://business-api.tiktok.com/gateway/docs/index?doc_id=1738373141733378), [schema links in source-access.md](./source-access.md).

### 3.4. Reddit: official and licensed access

**The main uncertainty in the current source set is sustainable, permitted access to Reddit data.**

The official migration schedule was checked again:

- **October 31, 2026:** new public Data API access requests stop being accepted.
- **January 12, 2027:** access removal begins for apps that have not registered or responded to Reddit.
- **March 2027:** remaining public access ends under this transition.

Do not base a long-term MVP on the assumption that a new OAuth client can be obtained freely and used with the previous public API. Devvit is not an established replacement for external data export; suitability and permissions for our use case require separate verification.

Commercial use requires agreement with Reddit and a contract. A public fixed price for suitable access has not been confirmed. Do not automatically extend the public API shutdown to every licensed commercial agreement.

Paying a third-party service does not itself establish permission for the required collection. Before choosing a supplier, verify its rights, available fields, permitted analysis and export, history, and the price of API access specifically.

Sources: [official migration schedule](https://www.reddit.com/r/redditdev/comments/1wubcvf/moving_data_api_apps_to_the_developer_platform/), [commercial access terms](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data), [migration guide](https://developers.reddit.com/docs/guides/migrate/public-api).

### 3.5. Reddit: Arctic Shift

**A technically accessible free candidate; permission for commercial use has not been established.**

- The public API supports community, time, and content filters; text search has parameter-combination restrictions.
- Research needs a category-based community catalog; do not promise exhaustive global discovery of all needs.
- The limited metadata probe did not require an account.
- The author describes the service as free, with dynamic rate limits and no availability guarantee.
- Archive metrics are not current Reddit counters; documentation describes fetching updated metrics after approximately 36 hours.
- The reviewed documentation did not establish sufficient licensing terms for our commercial use case. HTTP 200 does not resolve that question.
- Future reliability after Reddit API changes is also unconfirmed.

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

## 5. Corrections to previous research

Before implementation, update [source-access.md](./source-access.md), retaining the distinction between observation, documentation, and supplier claims:

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

- [x] Read the project context and `source-access.md`.
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

- Create the canonical `skills/niche-hunter/` folder with `SKILL.md` and only necessary `scripts/` and `references/`.
- Enable discovery in Codex and Claude Code without duplicating source files, for example through supported links from skill directories.
- Define shared provider, normalized observation, and coverage contracts.
- Implement providers, dates/duration, topic, time zone, and limit inputs.
- Connect OpenAI Signals and the validated TikTok path.
- Connect Reddit only with suitable confirmed access; otherwise return an explicit status for the selected provider.
- Choose runtime and integration details based on validated connections. Keep shared logic independent of a single LLM supplier's SDK.

### Stage 2 — analysis and concise reporting

- Add deduplication, topic grouping, comparable time-window analysis, and problem extraction.
- Separate facts, supplier estimates, interpretations, and product hypotheses.
- Produce evidence-backed results and a minimal validation plan, rather than promises of profitability or low CAC.
- Add caching and explicit free-quota limits.

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
