# Provider access and owner-supplied API keys

Read this reference for API-key setup or when a caller has received a provider key from its owner. The implemented key route is **TikTok through TokConnect**. For Reddit, use the separate [approved OAuth setup](reddit.md#access). Public OpenAI Signals needs no key. Reuse an already working connection and never require the recipient to create a TokConnect account or log into the owner's account just to use a supplied valid key.

## First-run choice

If access is missing, offer the caller a choice of **owner-supplied API key**, their own TokConnect browser sign-in, or an existing supported import. This also applies during preflight after a bare skill invocation; no explicit setup request or prior mention of an API key is required to present the choices. Batch missing-provider choices with the normal configuration check, then wait for the caller's selection. Ask only which route/client they use; never ask them to paste a key into the conversation. Choosing a route authorizes its configuration, not buying credits. A research request alone does not authorize silently rewriting client settings; a setup-only request does not authorize research. After successful onboarding, resume an already requested research run with its original parameters.

Keep key entry outside the model's conversation and tools. The user enters it personally into a native credential field or the helper's hidden terminal prompt. Do not start the secret prompt through an agent-controlled PTY, relay keystrokes, request a screenshot of its value, or supply the key through command arguments, standard input, an environment dump or a generated document. Show only commands without secrets. Do not read the saved credential back to check setup.

## Codex and Claude Code: one terminal command

From a source checkout or extracted runtime package, run the matching command **in your own terminal**. For an installed skill, substitute the actual skill path without copying it out of a versioned cache or editing that cache. Close the target client before updating its settings.

```bash
python3 skills/niche-hunter/scripts/setup_access.py --client codex
python3 skills/niche-hunter/scripts/setup_access.py --client claude-code
```

Choose one command for the client you use. Codex setup requires **Python 3.11+** for safe standard-library TOML parsing; Claude Code setup and the research helper support Python 3.10+. No setup dependency or provider account registration is installed.

The command prompts once with input hidden, then writes the reserved `niche-hunter-tokconnect` remote connection to that client's private user configuration. It uses `https://mcp.tokconnect.com/mcp` and `Authorization: Bearer …`. Codex uses `http_headers` in its user `config.toml`; Claude Code uses `mcpServers` in its user `.claude.json`. The helper honors `CODEX_HOME` / `CLAUDE_CONFIG_DIR`, refuses plugin/Git locations and symlinked configuration files, preserves unrelated settings and uses atomic writes with owner-only POSIX permissions. Keys are **plaintext in these private files**, not encrypted or invisible to local code. No secret is bundled, printed, placed in process arguments or saved in a research artifact. Setup sends no network requests and does not authenticate or inspect a balance.

Restart the client and keep the Niche Hunter skill enabled. Use the `niche-hunter-tokconnect` connection for TikTok. Claude Code's current documented endpoint precedence prefers manually configured servers over an equivalent bundled plugin server. If a client still displays an unauthenticated bundled TokConnect duplicate, disable only that duplicate in its MCP settings; do not disable the research skill, repeatedly authorize both routes, or assume every client deduplicates by URL. Project/managed settings may override user settings; resolve that conflict in the client's MCP panel before research.

The helper refuses an existing reserved entry by default, so ordinary subsequent runs do not prompt for the key again. If another manually configured connection already uses the endpoint, reuse/update it in the client rather than creating a second one. To rotate a helper-managed key, repeat the command with `--replace`; to remove that connection from this client, use `--remove`. These actions affect only the reserved entry. Removal does not revoke the provider key or remove other OAuth connections. The owner rotates/revokes the upstream key through TokConnect; distribute replacements outside chat and repeat setup in each affected client. Plugin updates keep these user settings separate from package files.

## Claude.app: native connector field

In the Claude application's custom connector settings, add the TokConnect MCP URL, select **No sign-in**, and add a request header named `Authorization`. Enter `Bearer ` followed by the supplied key directly into that credential field, then save and enable the connector. Do not put the key into the server URL, OAuth client-secret field or a chat message. Claude stores the header as a connector credential; its cloud infrastructure sends remote-connector requests, so this is not local-only credential storage.

**Request headers is a limited beta.** If the field is absent, this direct-key route is not available on that Claude surface. Offer supported Codex/Claude Code setup or a separate account OAuth route; do not claim the Python command configures Claude Chat/Cowork. A Team/Enterprise owner can configure an organization connector with a shared credential where supported; all members then have that credential's service access.

## ChatGPT Chat versus Codex

The helper configures **Codex**, including compatible local desktop hosts, not every chat mode in a ChatGPT application. Current OpenAI remote-plugin documentation specifies OAuth and does not support an arbitrary provider API key as a custom ChatGPT MCP credential. Do not ask for a key in ChatGPT Chat or treat an OAuth client secret as that key. Use an existing supported TokConnect OAuth connection, the Codex key route, or an import. Do not create an anonymous proxy or a new Niche Hunter backend as an implicit fallback.

## Readiness and shared allowance

The balance-check workflow here applies to caller-managed collection. For the packaged Claude Desktop extension, use [its per-run limits](claude-desktop.md) and report quota errors from the provider.

After configuration, inspect client connection status and the supported tool catalog without printing headers. Saving a key proves only that settings were written; HTTP success, tool access, available credits and useful data remain distinct checks. Do not perform a research call just to verify installation. Reuse this connection in later preflight checks; request setup again only if missing, invalid or expired.

A recipient need not access the owner's account page. Verify the current shared allowance using an available non-research account facility or a nonsecret, current confirmation from the owner, including the authorized per-run cap. Do not assume an advertised initial balance, a separate allowance per recipient, or that key sharing grants paid-spending permission. Concurrent users consume the same provider pool. The default free pilot, $0 new purchases/top-ups and ten-call run cap remain; an unverified balance is a budget gap, not a reason to request the owner's password or login. Existing import contracts retain `free_credits_before`; do not relabel paid credits as free or widen spending implicitly.

On an authentication, entitlement or exhausted-credit failure, stop this provider's calls. Ask for nonsecret corrective action or direct the user to replace the key outside chat. Do not print the rejected key, repeatedly retry it or fall back to the owner's browser session. Other selected-provider preflight and actual-coverage rules still apply.

## YouTube collector keys

YouTube has a separate local setup, not a TokConnect connection. Read [youtube.md](youtube.md#choose-a-route-during-first-run-preflight): offer the Google YouTube API key plus optional SerpApi key route, or Google key plus native Trends CSV. The user runs `scripts/youtube.py setup` (or `setup --csv-only`) personally; input is hidden, settings are private and no network calls are made. `youtube.py status` prints presence only. Do not send keys into chat, invoke hidden entry through an agent-controlled terminal, or inspect the credential file. Existing supported normalized imports need no new authentication. Native cloud chats without local Python need a supported tool/export route or explicit exclusion.

## Sources and verification boundary

Reviewed November 6, 2026: [TokConnect key setup](https://tokconnect.com/connect/claude-code/), [Codex HTTP MCP settings](https://learn.chatgpt.com/docs/extend/mcp#streamable-http-servers), [Claude Code remote servers and scopes](https://code.claude.com/docs/en/mcp), [Claude native request headers](https://claude.com/docs/connectors/custom/add-unlisted#authenticate-with-request-headers), [OpenAI plugin authentication](https://developers.openai.com/plugins/build/auth#client-identification).

The owner selected direct key distribution and accepts its shared-access tradeoff. No team/subkey entitlement, supplier redistribution permission, real token, authenticated response, free balance or cross-client UI availability is established by this implementation or synthetic tests. Do not add a documentation-link or legal-confirmation gate to caller-directed local TikTok processing.
