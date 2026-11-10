# From observations to channel and product opportunities

Use after collection, before writing `analysis.json`. The calling agent performs this reasoning; the helper validates structure and references, not market fit.

## Frame the decision

- **Discovery:** find a narrow product that could serve an identifiable audience through a concrete distribution route.
- **Refinement:** use caller-provided product context to evaluate positioning, a workflow, a feature, or acquisition. Explain the proposed change relative to that product, expected user benefit, and how to test it. Do not replace the caller's product with an unrelated idea unless asked.
- Preserve caller constraints such as channel, format, budget, or audience. Distinguish supplied product facts from market observations and untested assumptions. Ask about a missing constraint only when it prevents a useful decision.

## Extract needs before proposing solutions

Group evidence by **audience + situation + job or desired outcome**, not merely matching keywords. Retain source IDs, actual windows, independent support, and conflicting observations. Look for repeated tasks, costly workarounds, dissatisfaction, requests for tools, or a desired result a small product can deliver.

Separate attention/entertainment, solution-seeking intent, a recurring need, and payment evidence. A desired outcome can support a hypothesis without an explicit complaint. A stable need can be useful without a rising trend. Monthly broad categories alone cannot identify a narrow job or its reachable audience.

Inspect alternatives named in the permitted evidence: what users already do, where it falls short, and why a new solution or change could be preferred. Unknown competitor coverage remains unknown. Do not invent a competitive gap from the absence of a competitor in the sample.

## Construct the combination

For each promising need, reason through:

`specific channel surface → reachable audience and intent → unmet task → solution/value → first product use`.

The **market** is the reachable segment and use context, not a made-up market-size number. State geography/language only when supported; otherwise leave them unknown. Different intents or acquisition routes may justify different product configurations, but do not multiply the same idea into near-duplicate cards.

| Route | Questions that change the product/test |
| --- | --- |
| Search intent | What query or task leads to the product, what is expected at the landing point, and how quickly can it deliver the answer? A discussion about a task does not establish search volume. |
| Content discovery | What visible result or demonstration earns attention from the relevant audience, and why would someone leave the feed to use the product? Views alone do not establish this transition. |
| Community | Which relevant community contains the audience, and is there a permitted, useful way to introduce a solution? A complaint does not grant promotional access. |
| Other caller-selected route | What is the entry point, reachable buyer/user, and path to first value? If unmeasured, keep the route untested. |

Providers and distribution channels are separate axes. TikTok evidence may concern search, organic video, or ads; do not transfer results between them. Reddit evidence can reveal a problem for a product whose search acquisition is still untested. OpenAI Signals provides aggregate context, not private prompts, audience targeting, or an established ChatGPT acquisition route.

For YouTube, inspect the exact Trends seed/window/region and query → video → comment links. Search interest may support an entry query, and independently repeated comments may support a need; a tutorial view or a liked question does not establish external-product acquisition. Treat old videos as context, current likes as snapshots, and unfetched comments as unknown. Do not rank products by Trends index or comment likes.

Describe comment-quality concerns in observable terms. Cite the records showing repeated wording, recurring promotional links, or vague praise without a described task. Explain how the pattern limits confidence in the need. Attribute comments to automation only with direct evidence of authorship.

Write the acquisition path explicitly: entry point → message/demo → intended action → first useful outcome. Explain why the proposed format and minimal MVP suit both the task and the channel. Identify friction such as installation, trust, data entry, demonstration difficulty, or channel access. Show where evidence ends and the hypothesis begins.

For refinement, name the relevant existing behavior/positioning, proposed change, and expected effect. Preserve this connection in `value_proposition`, `minimal_mvp`, and `experiment`; do not turn every feature suggestion into a separate new product.

## Challenge and prioritize

Use the hypothesis's `opportunity` block to distinguish **need evidence** from **channel evidence**. `supported` channel fit means the sample supports audience/entry-point fit, not validated acquisition or profitable economics. `inferred` means an indirect fit argument; `untested` means the route has no supporting observation. A need may be supported while the proposed route is untested.

Challenge the combination with contrary observations, satisfactory existing solutions, audience mismatch, promotional concentration, one-off use, or a reason users may not take the proposed action. If none were observed, say what was checked and that the bounded sample does not establish their absence.

Choose a qualitative next action, with a reason:

- `test_next`: enough need/fit support to justify a small experiment, with remaining assumptions explicit.
- `research_more`: a material missing link makes a product/channel test premature; name the smallest evidence check.
- `defer`: contrary evidence, poor fit, or a blocker makes this a lower priority under the caller's constraints.

Order by the justified next action and evidence strength, not raw engagement or a fabricated composite score. Confidence describes support, not likely revenue. High confidence requires independent corroboration, not multiple records from one campaign/dataset. Explain independence in the narrative when it matters; any reported count needs a defensible counting basis.

## Test the weakest link

Identify the riskiest link: existence of the need, ability to reach the audience, response to the message, first value, or willingness to pay. Propose the smallest test of that link. Name the audience/route, action, metric and denominator, time/sample boundary, and proposed success/stop rule. In refinement mode, compare the proposed change with current behavior where feasible.

A demonstration test can evaluate qualified interest; it does not establish payment or retention. Economic assumptions must name funnel stages and costs. Tests remain proposals, not authorization to publish, contact users, run ads, or spend money.

Keep the shortlist evidence-dependent. If only aggregate context or unavailable sources remain, return findings, explicit gaps, and the next collection check with no product hypotheses. A full report with no supported opportunity is a valid outcome.

## Short presentation, retained reasoning

Analyze the evidence deeply, then separate it from the initial deliverable. Follow [reporting.md](reporting.md): provider table/chart, short conclusion and up to two useful next steps. With multiple providers, compare the available evidence and explain which channel/need/product combination to validate first, if any. Keep detailed reasoning and experiments in JSON, with a one- or two-sentence `brief` for each displayed idea. Include material uncertainty where it changes interpretation; expand on request.
