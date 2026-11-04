# TikTok search provider v1 — TokConnect MCP

This route combines client-managed OAuth and tool calls with a deterministic, offline normalizer. It supports search topics, topic detail/related topics, and TikTok autocomplete. Videos, comments, ads, Shop sales, demographic analysis, and historical-series growth are outside this adapter version. They must not be silently substituted for search evidence.

Public supplier schemas were reviewed on November 4, 2026. Authenticated responses, account entitlements, metric accuracy and free-credit charging still need a real-account check. Documentation examples and synthetic tests are not live integration proof.

## One-time setup

1. Inspect existing connections first. The plugin bundles `tokconnect` at `https://mcp.tokconnect.com/mcp`; reuse a working connection rather than adding a duplicate. Standalone skill installation does not install plugin-level MCP configuration.
2. Explain that TokConnect is an independent third-party service with its own account and shared credits. The current [pricing page](https://app.tokconnect.com/pricing) advertises Free with 50 initial credits, no card, and MCP. This is an offer, not the caller's verified balance. Account creation and consent happen in the user's browser; never request passwords, cookies or keys in chat. Do not select paid billing.
3. Use the client's connection/authentication UI to sign in to the bundled server and approve access. OAuth discovery advertises issuer `https://app.tokconnect.com`, dynamic client registration, PKCE S256, and scope `mcp`. Prefer automatic discovery; no shared OAuth client ID/secret is shipped. Let the client store and refresh tokens.
4. Codex: inspect the server name in the MCP list/settings and use its sign-in action. The CLI supports `codex mcp login SERVER_NAME` for a configured server; use the actual registered name, not a guessed plugin namespace. Claude Code: select the plugin's TokConnect server in `/mcp` and authenticate, or use `claude mcp login SERVER_NAME` with its listed name. Claude's documented plugin server name is `plugin:niche-hunter:tokconnect`. Regular Chat/Work/Cowork connector installation is a separate client surface; do not promise it is configured by a Code/CLI plugin installation.
5. If using only the standalone skill, offer an explicit manual MCP configuration: `codex mcp add tokconnect --url https://mcp.tokconnect.com/mcp` or `claude mcp add --transport http tokconnect https://mcp.tokconnect.com/mcp`, then the client's sign-in flow. Explain configuration scope and reuse existing registrations. Do not perform this as part of an ordinary research run.
6. Verify allowed research/storage use in the account's applicable terms or authorization. Record a specific public reference and basis. Public marketing pages and OAuth consent alone do not establish data reuse/retention rights. If unresolved, report `usage_terms_unconfirmed`; do not export research data.
7. Inspect the actual tool catalog/input/output schemas and verify the available **free** balance and charging before data calls. If quota cannot be verified, stop with an explicit gap; do not guess 50 remaining credits. A setup check may propose one tiny autocomplete call after those checks. Count it in any associated run budget and do not silently repeat it during research.

References: [supplier Codex guide](https://tokconnect.com/connect/codex/), [supplier Claude Code guide](https://tokconnect.com/connect/claude-code/), [demand schema](https://tokconnect.com/docs/api/demand/). Current client documentation takes precedence over supplier UI descriptions.

## Bounded research

- Only collect if `tiktok` is selected and a permitted connection is authorized. Keep authentication failures, denied access, unknown rights, exhausted credits, and unsupported methods explicit. No retries on auth, credit, entitlement, or schema errors; honor rate limits. No paid REST fallback, scraping, proxies, account sharing, or automatic upgrade.
- Verify current live schemas for these supported tool/method pairs: `demand_find_topics` (`search`, `feed`, `trending`), `demand_topic` (`detail`, `related`), and `demand_keywords` (`tiktok`). Names are documented routing leads; clients add namespaces. If the schema differs, stop this adapter and report the mismatch rather than inventing a response.
- For a topic, use its relevant query/seed and inspect returned topics for relevance. For a broad survey, use feed/trending and a bounded selection of catalog seeds; disclose categories not sampled. Reserve calls for promising topic details and contradiction checks instead of consuming every credit on pagination. Total calls across all providers stay within the run cap and confirmed free allowance, including failures/checks/baselines; each result page uses allowance.
- Pass documented `limit`/`cursor` arguments within caps. Follow `hasMore` and `next` (or the documented wrapper's `next_cursor`) only while budget remains. Cursors come from the tool, never fabricated. Record incomplete pagination.
- Compact topic lists contain `topics[]` with `queryId`, `queryText`, `searchVolume`, `popularity`, `videoCount`, optional `category`/`trend7d`. Detail uses `topic`; autocomplete uses `suggestions[].text`. The normalizer accepts bare compact objects, `data` wrappers, MCP `structuredContent`, a single JSON text content block, or JSON-RPC `result` wrappers.
- `queryText` does not prove a literal typed search. The adapter keeps CSI topics `unknown`; small volume alone never promotes them to `typed_search`. Autocomplete becomes `recommended_keyword`, with no search volume attached. Metrics remain `provider_claim_unverified` even after a successful call.
- `searchVolume` is the supplier's claimed seven-day topic popularity. Do not call it precise searches for a phrase. `trend7d` is preserved as undated supplier readings in provenance; do not sum it or infer independent daily counts/growth. Popularity index and matched-video counts have separate meanings.
- A 14-day/custom request cannot extend the supplier's metric window. Preserve a verified actual window if supplied; otherwise use unknown boundaries and explain the claimed seven-day metric/snapshot. Never derive measurement dates or freshness from retrieval time. The v1 adapter deliberately leaves region/language filters unsupported; record those gaps even if a tool accepts similarly named arguments.

## Capture and normalize

The calling agent writes a bounded local capture from **permitted** tool results. Keep only the needed compact fields and avoid account/profile details, authors, headers, keys, and cookies. Do not persist supplier exports if rights are unresolved. Capture files stay outside plugin caches and Git, under the run's working files, subject to source retention terms.

Capture shape (`schema_version: "0.1.0"`):

| Field | Meaning |
| --- | --- |
| `external_calls`, `new_paid_spending_usd` | Actual total external attempts/checks for this source, 0–10; new paid spend must be 0 |
| `free_credits_before` | Verified integer free balance before these calls; conservatively reserve at least one credit per external attempt/check |
| `rights` | Same explicit permitted-storage object as the import contract; never set true automatically |
| `topic` | Caller topic or null; if set, require `topic_relevance_checked: true` and per-call `selected_ids` after semantic review |
| `actual_window` | Optional verified source scope; omit to retain unknown boundaries, not the requested window |
| `calls` | At most 10 captured calls, each containing the fields below |

Each call has `tool`, exact `arguments` including `method`, actual offset-aware `retrieved_at`, and `response`. Optional `measurement_window` supplies verified search-popularity bounds; omit for unknown. Optional `selected_ids` retains only reviewed entities from that response. Topic IDs are `queryId`; autocomplete IDs are `keyword:` plus the first 24 hex characters of SHA-256 of the stripped, case-folded text. For an unscoped run selection can be omitted. An explicit empty selection retains no rows. Do not mark unrelated feed results as topic-specific.

For HTTP errors, supply the actual `http_status` instead of a response body: 401 → `auth_required`; 402/429 → `rate_limited`; 403 → `not_supported`; other errors → `unavailable`. A protocol/tool error without a reliable code becomes `unavailable`, not guessed authentication or an empty successful search. Partial successful calls remain usable; the report discloses failed calls. Schema-invalid captures fail normalization without producing an import: keep other sources working and supply a failure envelope instead.

For missing access before any calls, write a failure capture with `schema_version`, `status` (`unconfigured`, `auth_required`, `usage_terms_unconfirmed`, or another documented failure), `external_calls: 0`, `new_paid_spending_usd: 0`, `calls: []`. No credentials or invented credit balance are needed. The normalizer creates the corresponding import failure envelope.

Run the adapter, then the existing collector, using a fresh output path/directory and all original run parameters:

```bash
python3 skills/niche-hunter/scripts/tiktok.py \
  --input .nichehunter/tiktok-capture.json --out .nichehunter/tiktok-import.json
python3 skills/niche-hunter/scripts/research.py collect \
  --providers tiktok --import-file .nichehunter/tiktok-import.json \
  --out .nichehunter/runs/example
```

The adapter never networks or reads secrets. It retains at most 100 unique observations, uses stable source IDs, selects the most recently retrieved topic snapshot (last capture wins on equal retrieval times), preserves missing metrics as null with reasons, and records safe tool receipts/undated trend readings. The helper performs final source-ID deduplication, filter/coverage reporting, and evidence-ID assignment. Then use the normal analysis/finalization workflow; search topics and recommendations alone do not force product hypotheses.
