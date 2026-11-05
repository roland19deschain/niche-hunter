# TikTok search provider v1 — TokConnect MCP

This route combines client-managed API-key or OAuth access and tool calls with a deterministic, offline normalizer. It supports search topics, topic detail/related topics, and TikTok autocomplete. Videos, comments, ads, Shop sales, demographic analysis, and historical-series growth are outside this adapter version. They must not be silently substituted for search evidence.

Public supplier schemas were reviewed on November 4, 2026; Claude Code authentication and plugin tool naming were rechecked on November 5. Authenticated responses, account entitlements, metric accuracy and free-credit charging still need a real-account check. Documentation examples and synthetic tests are not live integration proof.

## One-time setup

1. Inspect existing connections first. The plugin bundles `tokconnect` at `https://mcp.tokconnect.com/mcp`; reuse a working connection rather than adding a duplicate. Prefer an already configured `niche-hunter-tokconnect` API-key connection over an unauthenticated bundled entry. Standalone skill installation does not install plugin-level MCP configuration.
2. For an owner-supplied API key, use [the key setup reference](access.md). The recipient does not need their own TokConnect account or the owner's browser login. Enter keys only in a native credential field or the local helper's hidden terminal prompt, never in chat. Verify shared allowance through a non-research facility or nonsecret owner confirmation. Do not require a key recipient to open the owner's account page.
3. If the caller chooses OAuth instead, explain that TokConnect is an independent third-party service with its own account and credits. Reuse their prepared account. Use the client's browser sign-in and consent; never request passwords/cookies in chat or select paid billing. OAuth discovery advertises issuer `https://app.tokconnect.com`, dynamic client registration, PKCE S256, and scope `mcp`. Prefer automatic discovery; no shared OAuth client ID/secret is shipped. Let the client store and refresh tokens. Check actual free allowance rather than assuming an advertised [pricing offer](https://app.tokconnect.com/pricing).
4. For that OAuth route only: in Codex inspect the server name in the MCP list/settings and use its sign-in action. The CLI supports `codex mcp login SERVER_NAME` for a configured server; use the actual registered name, not a guessed plugin namespace. In Claude Code select the plugin's TokConnect server in `/mcp` and authenticate, or use `claude mcp login SERVER_NAME` with its listed name. Claude's documented plugin server name is `plugin:niche-hunter:tokconnect`. Regular Chat/Work/Cowork connector installation is a separate client surface; do not promise it is configured by a Code/CLI plugin installation. Do not run OAuth login for an already configured API-key connection.
5. If using only the standalone skill and choosing OAuth, offer an explicit manual MCP configuration: `codex mcp add tokconnect --url https://mcp.tokconnect.com/mcp` or `claude mcp add --transport http tokconnect https://mcp.tokconnect.com/mcp`, then the client's sign-in flow. Explain configuration scope and reuse existing registrations. Do not perform this as part of an ordinary research run. The key setup command is the alternative for a supplied key.
6. Once data is available through the caller's authorized connection or supplied capture, process and store it locally as requested. Do not require a terms-of-use link, a `storage_permitted` flag or a separate legal confirmation. Optional supplied rights metadata can be retained as provenance; never invent it or use its absence as a collection/export gate.
7. Inspect the actual tool catalog/input/output schemas and verify the available **free** balance and charging before data calls. If quota cannot be verified, stop with an explicit gap; do not guess 50 remaining credits. A setup check may propose one tiny autocomplete call after connection/free-budget checks and an explicit research request. Count it in any associated run budget and do not silently repeat it during research.

### Claude Code first run

Use the installed plugin in the caller's working project. Confirm its version with `claude plugin list`; after installation/update, start a new session or apply `/reload-plugins` as the client directs. A repository-local `/niche-hunter` skill alone does not load the plugin's MCP server. If the caller received an API key, follow [key setup](access.md) instead of the account sign-in steps below; the same readiness and research steps then apply.

1. Open `/mcp`, select the bundled TokConnect server and authenticate using the existing account. Use the server's listed name; the expected plugin identity is `plugin:niche-hunter:tokconnect`. Current Claude Code also provides `claude mcp login SERVER_NAME`; inspect `claude mcp --help` if an older client lacks it and use `/mcp` instead. Do not add a second manual server when the bundled one is present.
2. Invoke `/niche-hunter:niche-hunter set up TikTok using my existing TokConnect account`. Inspect the live tool catalog; authentication and schema discovery are setup checks, not successful research. Verify free allowance through an available account tool or the caller's account page; do not spend credits merely to discover the starting balance. Ask only for missing nonsecret configuration or budget facts; do not ask for terms links.
3. Return a short readiness table: connection/authentication, supported search tools, verified free allowance/call cost, and remaining action. Use an actual connection/account failure such as `unconfigured` or `auth_required` when blocked. A connected server alone does not make research ready. Never claim that this plugin release has validated the caller's account.
4. After readiness is established and research is requested, use a small TikTok-only prompt such as `/niche-hunter:niche-hunter research product opportunities using only TikTok for the last 7 days`. A topic can be added by the caller. Respect the shared call cap and actual free balance, create fresh run paths, and produce `report.md`, `report.pdf` and detailed `results.json` using the normal workflow. Report the supplier's actual window separately; a later 14-day request must disclose a seven-day or undated fallback.

Tokens remain in this client's credential facility; a login in Codex or another Claude surface does not establish authorization in this Claude Code session. If access is blocked, finish setup with the concrete next action rather than returning a misleading empty research report. If the live response shape differs, retain only permitted diagnostics outside Git and report the schema gap for the adapter.

Official references: [Claude Code remote authentication](https://code.claude.com/docs/en/mcp#authenticate-with-remote-mcp-servers), [plugin-provided MCP servers and tool names](https://code.claude.com/docs/en/mcp#plugin-provided-mcp-servers), and [plugin updates](https://code.claude.com/docs/en/discover-plugins#keep-plugins-updated).

References: [supplier Codex guide](https://tokconnect.com/connect/codex/), [supplier Claude Code guide](https://tokconnect.com/connect/claude-code/), [demand schema](https://tokconnect.com/docs/api/demand/). Current client documentation takes precedence over supplier UI descriptions.

## Bounded research

- Only collect if `tiktok` is selected and a permitted connection is authorized. Keep authentication failures, denied access, exhausted credits, and unsupported methods explicit. No retries on auth, credit, entitlement, or schema errors; honor rate limits. An owner-supplied API key is a supported route; never request the owner's password, cookies or browser session. No paid REST fallback, scraping, proxy deployment or automatic upgrade.
- Verify current live schemas for these supported tool/method pairs: `demand_find_topics` (`search`, `feed`, `trending`), `demand_topic` (`detail`, `related`), and `demand_keywords` (`tiktok`). Names are documented routing leads; clients add namespaces. If the schema differs, stop this adapter and report the mismatch rather than inventing a response.
- For a topic, use its relevant query/seed and inspect returned topics for relevance. For a broad survey, use feed/trending and a bounded selection of catalog seeds; disclose categories not sampled. Reserve calls for promising topic details and contradiction checks instead of consuming every credit on pagination. Total calls across all providers stay within the run cap and confirmed free allowance, including failures/checks/baselines; each result page uses allowance.
- Pass documented `limit`/`cursor` arguments within caps. Follow `hasMore` and `next` (or the documented wrapper's `next_cursor`) only while budget remains. Cursors come from the tool, never fabricated. Record incomplete pagination.
- Compact topic lists contain `topics[]` with `queryId`, `queryText`, `searchVolume`, `popularity`, `videoCount`, optional `category`/`trend7d`. Detail uses `topic`; autocomplete uses `suggestions[]` as strings or objects with `text` (including mixed arrays). The normalizer accepts bare compact objects, `data` wrappers, MCP `structuredContent`, a single JSON text content block, or JSON-RPC `result` wrappers. String/object suggestions share the same stripped, case-folded text IDs; neither implies observed search volume.
- `queryText` does not prove a literal typed search. The adapter keeps CSI topics `unknown`; small volume alone never promotes them to `typed_search`. Autocomplete becomes `recommended_keyword`, with no search volume attached. Metrics remain `provider_claim_unverified` even after a successful call.
- `searchVolume` is the supplier's claimed seven-day topic popularity. Do not call it precise searches for a phrase. `trend7d` is preserved as undated supplier readings in provenance; do not sum it or infer independent daily counts/growth. Popularity index and matched-video counts have separate meanings.
- A 14-day/custom request cannot extend the supplier's metric window. Preserve a verified actual window if supplied; otherwise use unknown boundaries and explain the claimed seven-day metric/snapshot. Never derive measurement dates or freshness from retrieval time. The v1 adapter deliberately leaves region/language filters unsupported; record those gaps even if a tool accepts similarly named arguments.

## Capture and normalize

The calling agent writes a bounded local capture from available authorized tool results or caller-supplied data. Keep only the needed compact fields and avoid account/profile details, authors, headers, keys, and cookies. Do not block caller-directed local processing because a terms URL is missing. Capture files stay outside plugin caches and Git, under the run's working files, subject to source retention terms.

Capture shape (`schema_version: "0.1.0"`):

| Field | Meaning |
| --- | --- |
| `external_calls`, `new_paid_spending_usd` | Actual total external attempts/checks for this source, 0–10; new paid spend must be 0 |
| `free_credits_before` | Verified integer free balance before these calls; conservatively reserve at least one credit per external attempt/check |
| `rights` | Optional supplied provenance; no permission flag, basis or terms link is required for TikTok |
| `topic` | Caller topic or null; if set, require `topic_relevance_checked: true` and per-call `selected_ids` after semantic review |
| `actual_window` | Optional verified source scope; omit to retain unknown boundaries, not the requested window |
| `calls` | At most 10 captured calls, each containing the fields below |

Each call has `tool`, exact `arguments` including `method`, actual offset-aware `retrieved_at`, and `response`. `tool` accepts a supported short name or the client's callable MCP name, such as `mcp__plugin_niche-hunter_tokconnect__demand_find_topics` in Claude Code or `mcp__tokconnect__demand_find_topics` in Codex. The normalizer routes by the supported short name and retains the full callable name in the safe receipt; unknown methods/tools still fail. Optional `measurement_window` supplies verified search-popularity bounds; omit for unknown. Optional `selected_ids` retains only reviewed entities from that response. Topic IDs are `queryId`; autocomplete IDs are `keyword:` plus the first 24 hex characters of SHA-256 of the stripped, case-folded text. For an unscoped run selection can be omitted. An explicit empty selection retains no rows. Do not mark unrelated feed results as topic-specific.

For HTTP errors, supply the actual `http_status` instead of a response body: 401 → `auth_required`; 402/429 → `rate_limited`; 403 → `not_supported`; other errors → `unavailable`. A protocol/tool error without a reliable code becomes `unavailable`, not guessed authentication or an empty successful search. Partial successful calls remain usable; the report discloses failed calls. Schema-invalid captures fail normalization without producing an import: keep other sources working and supply a failure envelope instead.

For missing access before any calls, write a failure capture with `schema_version`, `status` (`unconfigured`, `auth_required`, another documented connection/data failure), `external_calls: 0`, `new_paid_spending_usd: 0`, `calls: []`. No credentials or invented credit balance are needed. The normalizer creates the corresponding import failure envelope.

Run the adapter, then the existing collector, using a fresh output path/directory and all original run parameters:

```bash
python3 skills/niche-hunter/scripts/tiktok.py \
  --input .nichehunter/tiktok-capture.json --out .nichehunter/tiktok-import.json
python3 skills/niche-hunter/scripts/research.py collect \
  --providers tiktok --import-file .nichehunter/tiktok-import.json \
  --out .nichehunter/runs/example
```

The adapter never networks or reads secrets. It retains at most 100 unique observations, uses stable source IDs, selects the most recently retrieved topic snapshot (last capture wins on equal retrieval times), preserves missing metrics as null with reasons, and records safe tool receipts/undated trend readings. The helper performs final source-ID deduplication, filter/coverage reporting, and evidence-ID assignment. Then use the normal analysis/finalization workflow; search topics and recommendations alone do not force product hypotheses.
