# Compact reporting and exports

The short report is the same decision-facing content in chat, Markdown, terminal text and PDF. Detailed observations, windows, provenance, confidence and product reasoning remain in `results.json` and the submitted `analysis.json`.

## Visual palette

Use the report model's shared dark `theme` for PDF and supported native visuals:

| Role | Color | Use |
| --- | --- | --- |
| `background` | `#1D1E20` | Full page and chart/artifact background |
| `surface` / `surface_alt` | `#191C1E` / `#24282B` | Dark panels, alternating rows, table headers and idea highlights |
| `border` | `#3A4145` | Subtle separators and chart tracks |
| `text` / `muted` | `#F3F5F7` / `#A3ABB0` | Primary values/body text and secondary labels |
| `accent` / `cyan` | `#01A4FE` / `#5FCCE9` | Primary chart series, links and highlight rules |
| `teal` / `lime` | `#22C6AB` / `#B6D46A` | Additional categorical chart series |
| `positive` / `negative` | `#28D59C` / `#F27870` | Verified comparable changes only |

The PDF paints every page dark, uses light text on dark tables, cyan source links, blue/cyan/teal/lime bar series and dark idea highlights with a cyan edge. Keep labels readable and all text contrast clear. A green/red delta requires actual comparable change data with its sign stated in text; do not invent change badges or imply a favorable result from popularity alone. Add no decorative KPI, donut or growth data just to imitate a dashboard. Content, measurements and the compact report order stay the same.

In ChatGPT/Claude desktop clients, style available chart/artifact panels with this palette and a dark background when their renderer allows it. Normal Markdown inherits the host application's theme: the skill cannot set the chat window's background or force text colors. Use readable native tables/text and attach the styled PDF when custom visuals are unavailable. Do not emit unsupported HTML/CSS or ANSI escapes, request changes to the user's app theme, or promise a dark chat canvas. Markdown and terminal output remain portable and contain the same values.

## Structure

For every selected provider, in selected order:

1. Provider heading and a short coverage line only if the actual interval differs or is unknown.
2. A compact table of observed signals and values, normally at most six rows. Link the signal to its source. Keep units and essential qualifiers, including supplier estimates and monthly shares.
3. An optional chart for measurements with the same name, unit, window and optional comparison group. Never chart missing values as zero or compare shares with counts. No reconstructed historical growth.
4. One or two sentences about the observed situation and relevant distribution route. A source providing broad context is not automatically an acquisition channel.

After all providers, add one short overall conclusion. Add up to three product ideas only when supported: `channel / reachable market -> problem or desire -> product or change`, with at most two brief sentences explaining the solution. Do not add detailed product cards, experiments, monetization plans, confidence tables, gap lists or an evidence appendix to this initial report. Keep material uncertainty in the short conclusion; expand details on request.

Use the caller's language. Technical IDs and metric values remain unchanged. Target roughly 300–500 words; a small evidence set may justify much less. Unavailable sources do not get invented data. No supported ideas means no product-ideas section.

## Calling-agent presentation fields

The analysis contract accepts an additive `presentation` object:

- `title`: optional short report title.
- `labels`: optional translations of the report's label keys. Supported keys are `signal`, `data`, `overall`, `ideas`, `requested`, `coverage`, `unknown`, `pending`, `end_exclusive`, `proposed`, `supplier_popularity`, `matched_videos`, `share`, `trends_index`, `trends_growth`, `trends_breakout`, `likes_snapshot`, `comments_window`, `no_comments`. Defaults are English; they do not set the target market or requested language.
- `providers`: one object per selected provider, with `provider`, a short `conclusion` (at most 420 characters), and `evidence_ids` from that provider. Existing observations require nonempty references. An unavailable source can have no references and a short explanation instead.
- Each provider may include `row_ids`, one to six distinct observation IDs from that provider, ordered by usefulness. Otherwise the helper selects a bounded sample; Signals defaults to its current comparison month, excluding baseline rows from the short table. YouTube defaults to query/comment rows, leaving old video context in JSON. Its coverage line distinguishes differing Trends dates from the requested comment interval and explicitly notes missing dated comments.

Each hypothesis may include `brief`: up to 400 characters with one or two short sentences. It is the solution description in the compact report. `channel`, `problem` and `title` supply the combination. Existing detailed hypothesis fields stay in JSON and are not printed as product cards. The caller orders the best supported ideas; deferred items are omitted and at most three are displayed. An untested acquisition route is labeled proposed.

Presentation references are validated against collected evidence. Structural checks do not establish semantic support, channel access or profitable economics. The calling agent must check these before finalizing.

## Markdown, apps and terminal

`report.md` contains the portable short report with Markdown tables, source links and optional ASCII chart blocks. Present the same content directly in the chat. In graphical clients, use their available readable table, chart and artifact features; replace an ASCII chart with its equivalent native visual when supported, without changing values. Do not require a particular proprietary tool or assume app-only markup works in a terminal.

For terminal output:

```bash
python3 skills/niche-hunter/scripts/research.py report --run RUN_DIR --format text
```

This prints plain-text tables and ASCII charts, with the same signals, conclusions and product ideas. `--format markdown` prints the Markdown version. `report --analysis ANALYSIS_JSON` validates and previews a proposed analysis without collecting or replacing the stored run.

## PDF export

Configure PDF capability during preflight. The bundled renderer uses ReportLab, included Noto Sans fonts and no remote assets. Collection/normalization still use the Python standard library. Install the exporter in the chosen environment if absent:

```bash
python3 -m pip install -r SKILL_DIR/requirements-pdf.txt
```

Use an existing suitable environment or a local environment rather than changing the client's global Python implicitly. The calling agent resolves `SKILL_DIR` from the installed skill location. No browser, system font, operating-system print driver or network service is required by this renderer.

```bash
python3 skills/niche-hunter/scripts/research.py finalize \
  --run RUN_DIR --analysis RUN_DIR/analysis.json
```

This creates `report.md`, styled `report.pdf` and detailed `results.json`. The PDF uses the same report model, with colored tables, compatible bar charts, clickable source links and page numbers. Export hashes are recorded in JSON. Rendering/validation failures preserve previous artifacts instead of reporting success with no PDF.

The default fonts provide broad text coverage but not every writing system. If needed, pass `--font-regular FONT_TTF --font-bold FONT_TTF` with suitable TrueType fonts or use a native client exporter. Missing glyphs fail explicitly rather than producing unreadable boxes. Fonts are licensed separately under the included OFL; no font choice sets a region or market.

For an available native client PDF exporter, first preview the validated report with `report --analysis`, render that same content locally, and then pass `finalize --pdf-file NATIVE_PDF` with the same analysis. This copies the completed PDF alongside its Markdown counterpart; it does not convert an arbitrary file or verify that a separately authored PDF preserved the report. The calling agent must inspect content equivalence and rendering. Never attach an older or unrelated PDF as the new run's output.

Before delivery, visually inspect all PDF pages for clipped/overlapping text, broken glyphs, split headings, table breaks, chart scales and legibility. Check numbers and source links against the Markdown. Attach both `report.md` and `report.pdf`; keep full JSON available for requested drill-down. Do not mark collection-only drafts as the final analyzed report.
