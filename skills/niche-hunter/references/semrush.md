# Optional Semrush search validation

Use Keyword Overview for one market per lookup. Agree on the country database with the caller and use the same market when comparing sources.

| Use | Evidence to look for |
| --- | --- |
| Google SEO | Estimated monthly volume, intent, keyword difficulty and SERP features when available |
| Google Search Ads | Estimated CPC and paid competition for the same phrases |
| Google Trends | Compare recent interest with longer-term Semrush seasonality for the same phrases. Keep both sources' metrics and coverage separate. |
| Reddit, TikTok, YouTube, OpenAI Signals, App Store, and Meta Ad Library | Use relevant topics, user language, product categories or offers as seeds for Google Search validation. Keep the starting source and Google Search evidence independently attributed. |

In **Product Hunt**, test whether people search for a solution and whether SEO or paid search offers a plausible acquisition route. In **Trend Hunt**, describe the current snapshot and available monthly history or seasonality. Semrush's monthly search volume is an estimate averaged across twelve months. Preserve that meaning and the returned snapshot month. Use Google Trends or another compatible source for shorter-term interest. Keyword difficulty and CPC are estimates. A campaign is needed to measure acquisition cost. Keep Prompt Research and platform-native search analytics outside this workflow. [Keyword data and methodology](https://www.semrush.com/kb/257-keyword-overview) · [Search volume](https://www.semrush.com/kb/683-what-is-search-volume-in-semrush)

## Access by client

Reuse authorized access in the current client. Follow the caller's preferred route. If both routes are authorized and there is no preference, propose the callable official connector. Use only one route per lookup. When neither route is ready, offer the relevant setup or the free manual check. Semrush is optional. For a Semrush-only request, keep other providers out of scope.

| Client | Official Semrush MCP | Private v4 SEO API key |
| --- | --- | --- |
| ChatGPT macOS app in Codex mode and Codex CLI | Add the official remote MCP server in local Codex settings and sign in with OAuth when Semrush permits access from this client. Both surfaces share the local MCP settings on the same host. | Use the local helper below from either surface. |
| Claude Code CLI | Add the official remote MCP server and authenticate via `/mcp`. | Use the same local helper below. |
| Claude Desktop with Niche Hunter MCPB | **Customize → Connectors → Semrush**, then sign in. | **Settings → Desktop app → Extensions → Niche Hunter**. Enter **Semrush API key** and enable **Semrush extension access approved** if your Semrush terms cover use in Claude. Check `optional_checks.semrush` in `niche_hunter_status` and confirm `niche_hunter_semrush_keyword` is callable. Use the extension tool for lookups. |

Official MCP requires an eligible subscription. Direct access requires a v4 SEO API key with permission and units, typically SEO Business plus a units package. Use the key only when your Semrush terms allow this integration and AI processing in the intended client. Enter secrets in the extension settings or your own terminal. Never paste them into chat. [Semrush MCP access](https://developer.semrush.com/api/v4/introduction/semrush-mcp/) · [Direct API access](https://developer.semrush.com/api/v4/get-started/api-access/) · [Semrush terms](https://www.semrush.com/company/legal/terms-of-service/)

In Codex on macOS, open **Settings → MCP servers → Add server**, choose Streamable HTTP and enter the Semrush URL shown below. Save, restart and use **Authenticate** if required. For CLI setup, choose the command for your client. In Codex CLI, complete browser authorization when prompted, or run `codex mcp login semrush` if needed. In Claude Code, select Semrush in `/mcp` and authenticate. Open a new session if the tools are still missing. [Codex MCP setup](https://developers.openai.com/codex/mcp) · [Semrush MCP setup](https://developer.semrush.com/api/v4/introduction/semrush-mcp/)

```bash
codex mcp add semrush --url https://mcp.semrush.com/v2/mcp
claude mcp add --transport http --scope user semrush https://mcp.semrush.com/v2/mcp
```

For a local Codex or Claude Code API-key setup, run the first command yourself from the skill directory. The prompt hides the key and writes an owner-only file outside the workspace. All three local surfaces can reuse it under the same OS user. `--replace` rotates the local key and `--remove` clears it. The agent can run `status` and the approved lookup. Status checks settings without using units. Use these commands only when the skill directory is available on the current local host.

```bash
python3 scripts/semrush.py setup
python3 scripts/semrush.py status
python3 scripts/semrush.py keyword --keyword "KEYWORD" --country COUNTRY_CODE
```

## Lookup and presentation

1. Confirm one keyword, one country, one access route and the use of the plan's existing units. Allocate attempts before collection. A direct lookup uses one attempt and is listed at 20 units. Plan MCP discovery, schema inspection and execution within the shared attempt ceiling. If the plan leaves insufficient attempts, offer a separate follow-up or the browser check. Never buy or top up units. [Keyword Metrics v4](https://developer.semrush.com/api/v4/seo/keyword-reports/)
2. With an official connector, inspect the callable tools, use `keyword_research` to discover the current one-keyword overview report and use its advertised schema for execution. Prefer Keyword Metrics if offered. Semrush also documents the legacy `phrase_this` report. Use the provider's reported units or the published price for that exact report. For direct API, call the local helper or the extension tool with the same keyword and country. If an authorized route fails, report the status and offer another route or skip before spending again. [Official keyword workflow](https://www.semrush.com/mcp/prompt-library/skills/keyword-research?view=skills)
3. Present one concise Semrush Google Search table in the conversation. Include the keyword, country, snapshot month, estimated monthly volume, search intent, keyword difficulty, CPC in USD, paid competition on a 0–100 scale, and the relative trend when supplied. Add SERP features if relevant. Mark unavailable fields as unknown. The direct helper and extension already convert CPC from cents. For legacy MCP output use the report schema. For `phrase_this`, CPC is in dollars, competition and the relative trend are on a 0–1 scale, and intent codes 0–3 stand for commercial, informational, navigational and transactional. Scale the indices to 0–100 when that schema confirms the scale. A returned month takes precedence over the requested or retrieval date. Report an unknown month if absent. Keep Semrush data and derived claims in the conversation, out of the saved JSON, Markdown and PDF inputs. [Field conversion reference](https://developer.semrush.com/api/v4/seo/semrush-api-v4-seo-migration-guide/)
4. For a free manual check, share up to ten prioritized phrases, the selected country and fields, and link to [Keyword Overview](https://www.semrush.com/analytics/keywordoverview/). The ten daily requests are shared across eligible web tools. The caller checks these phrases in the browser. Keep this a handoff and avoid requesting dashboard exports, screenshots or metric values in chat. [Free usage limits](https://www.semrush.com/blog/free-seo-tools/)
