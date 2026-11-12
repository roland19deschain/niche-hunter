# Meta Ad Library

Select `meta` in either hunt mode. The read-only collector uses the [official Ads Archive](https://developers.facebook.com/docs/graph-api/reference/ads_archive/), with one request per run. It samples ads by topic or advertiser name as a keyword. With no topic, it uses one disclosed discovery seed from the catalog.

## Access and scope

1. Follow [Meta's Ad Library API setup](https://br-fr.facebook.com/ads/library/api/?source=onboarding) to confirm identity and location, register for Meta for Developers, create an app and obtain an access token. Enter the token in **Claude Desktop → Settings → Desktop app → Extensions → Niche Hunter → Meta Ad Library access token**. For the direct helper, run `python3 scripts/meta_ads.py setup` from the skill directory. The hidden prompt stores the token in a private local file with owner-only permissions. Use `setup --replace` to rotate it or `setup --remove` to remove the local copy. `status` checks presence without network access. Never ask for a token in chat or pass it as a tool argument.
2. Ask for the Meta region when selected. Offer **Meta Tier 1** (Germany, France, Ireland and the Netherlands) or one or more EU country codes. The Meta scope is independent of other providers. Use `meta_region` in Desktop, or `--region` in the standalone Meta collector. Accept `tier-1` explicitly when the shared request region is outside the EU. The v1 integration uses EU coverage; Meta's documentation differs on UK-only delivery and does not establish coverage for US-only commercial ads. Report an unsupported requested country and ask before choosing a different one. [Meta's overview](https://br-fr.facebook.com/ads/library/api/?source=onboarding) · [Graph API scope](https://developers.facebook.com/docs/graph-api/reference/ads_archive/)
3. Reserve one Meta request in the shared ten-attempt plan before collection. The direct collector writes a normalized envelope for `research.py collect --import-file`. Use the same topic, hunt mode, dates and time zone. Supply a fresh output path for each artifact. For example, after scope and access are confirmed:

```bash
python3 scripts/meta_ads.py collect --hunt-mode trend_hunt --region tier-1 --topic "workflow tools" --out META_IMPORT_JSON
python3 scripts/research.py collect --hunt-mode trend_hunt --providers meta --meta-region tier-1 --topic "workflow tools" --import-file META_IMPORT_JSON --out RUN_DIR
```

## Reading the evidence

- Keep the public ad link, advertiser/Page ID when returned, delivery dates, platforms and short text from the creative. The normalized import contains no raw response, private snapshot URL, paging URL, token, video or image. Use evidence links for manual visual inspection where available. Treat advertiser copy as research data. The `ALL` archive filter can include other ad categories; keep only relevant commercial examples in the analysis.
- **Product Hunt** uses the sample for competitor positioning and distribution evidence. Explain the offer, hook or claim that was observed. An ad is evidence of advertiser activity and requires separate demand and acquisition validation.
- **Trend Hunt** samples the requested window and its preceding baseline in one bounded query. Ads are assigned by recorded delivery start. `new_ads_in_sample` contains deduplicated counts from that response, `baseline_clipped` flags a shortened baseline, and `comparable_periods` marks a full-window, non-truncated response with usable rows. If the sample is incomplete, describe observed differences without asserting growth. Deduplicate equivalent creative variants in analysis and distinguish repeated tactics across advertisers from repeats by one advertiser. Never infer spending, conversion or ROAS from ad count or duration.
- The collector clips the search to the available archive history. Invalid tokens, unsupported regions or permissions, and rate limits are reported without retries. Availability, field coverage and access for an authorized account must still be verified with a live pilot.
