# Niche Hunter data handling

Niche Hunter is a local skill/plugin and Python helper. It does not operate a hosted analytics backend or maintain a central database of users' research.

- The calling AI client processes research requests and tool responses under that client's policies and settings.
- Selecting ChatGPT/OpenAI Signals lets the helper download a fixed public data release from OpenAI. This is aggregate published data, not access to private ChatGPT conversations.
- Selecting TikTok with an authorized connection sends research keywords, topic IDs, and tool parameters to the third-party TokConnect service. TokConnect and its authentication provider process those requests under their applicable policies. Review those policies and consent screens before connecting. Do not include confidential product or customer information in search terms.
- OAuth credentials are handled by the AI client's connection facilities. The skill and Python scripts do not read passwords, cookies, or access tokens. No provider account or shared key is included in the plugin.
- Reports, JSON results, and permitted captures are written to the caller's chosen local paths, outside the plugin cache. They may contain search phrases and source summaries. The calling agent may read those artifacts to perform analysis; they are not automatically uploaded to a Niche Hunter server.
- Local artifacts are not deleted automatically. The caller controls their storage, sharing, and removal and must follow source-specific retention and reuse terms. Research directories are ignored by this repository's Git configuration; review exports before sharing or committing them elsewhere.

TokConnect connection and account information: [connection documentation](https://tokconnect.com/connect/), [account application](https://app.tokconnect.com/). Public availability of data does not by itself grant redistribution rights. If applicable use/storage permissions cannot be established, the skill reports that limitation instead of exporting data.
