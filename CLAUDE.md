# Golf Stats — agent orientation

Personal golf performance analytics for **Tyler** (with comparison golfers Rich and Ryan).
Three surfaces over one Excel-based dataset: a Jupyter notebook that computes derived
metrics, an MCP server that exposes ~60 analysis tools to Claude, and a Power BI dashboard.

There is no application, no test suite, and no build. "Running the project" means either
executing notebook cells or starting the MCP server.

## Layout

```
paths.py                    Single source of truth for data locations — import it, never hardcode
golf_mcp.py                 MCP server (SDK v2), 54 tools
notebooks/
  Golf Analytics.ipynb      Builds everything in data/derived/
data/
  raw/Golf Stats.xlsx       The one hand-maintained input. Everything derives from it
  derived/                  Notebook output — regenerate, don't hand-edit
dashboards/                 Power BI (.pbix), opened manually
docs/                       DATA_DICTIONARY.md + images
archive/                    Retired inputs, read by nothing in the live pipeline
```

**`data/raw/Golf Stats.xlsx` is the single source of truth.** The MCP server, the notebook,
and Power BI all trace back to it. Anything in `archive/` is retired — don't reintroduce it.

## The pipeline

```
data/raw/Golf Stats.xlsx        ← hand-maintained source of truth
      │
      ├─ notebooks/Golf Analytics.ipynb   (run top to bottom)
      │        ↓
      │   data/derived/strokes_gained_summary.xlsx
      │   data/derived/round_profiles.xlsx
      │   data/derived/clutch_score_analysis.xlsx
      │   data/derived/club_ranges.xlsx
      │   data/derived/club_selector.xlsx
      │   data/derived/golf_recommendations.xlsx
      │        ↓
      └─ golf_mcp.py  → ~60 tools Claude can call
```

`dashboards/Golf Dashboard 2.0.pbix` reads six of these files independently, via absolute
paths stored in the file (Power BI → Data source settings → Change Source):
`Golf Stats.xlsx`, `strokes_gained_summary.xlsx`, `round_profiles.xlsx`,
`clutch_score_analysis.xlsx`, `club_ranges.xlsx`, `golf_recommendations.xlsx`.
It does **not** use `club_selector.xlsx` — that file feeds the MCP server only.

### Paths

`paths.py` exports a constant per file (`GOLF_STATS`, `STROKES_GAINED`, `CLUB_RANGES`, …) as
`pathlib.Path` objects resolved relative to the repo root. **Use these — never write a bare
filename literal.** `golf_mcp.py` does `import paths`; the notebook's first cell walks up from
the working directory to find the repo root, adds it to `sys.path`, and imports the constants
by name.

`GOLF_DATA_DIR` overrides the data root. Note the semantics changed in the restructure: it now
points at a directory containing `raw/` and `derived/`, not at a flat directory of workbooks.

### Notebook cell order matters

Cells are not independent. Sections run top to bottom; `idx` is the 0-based cell index in the
`.ipynb` JSON, for when you need to edit a specific cell programmatically.

| Section heading | idx | Reads | Writes |
|---|---|---|---|
| *(path bootstrap)* | 0 | — | — |
| Feature Importances | 2, 3 | `DATA_CSV` *(archived)* | *(nothing — exploratory RF classifier / regressor)* |
| Shots Gained | 5 | `GOLF_STATS` | `STROKES_GAINED` |
| Round Profiling | 7 | `GOLF_STATS` | `ROUND_PROFILES` |
| Clutch Score | 9 | `GOLF_STATS` | `CLUTCH_SCORES` |
| Club Recommendations | 11 | `GOLF_STATS` | `CLUB_SELECTOR` |
| Club Recommendations | 12 | `GOLF_STATS` | `CLUB_RANGES` |
| Golf Recommendations | 14 | `GOLF_STATS`, `CLUB_RANGES` | `RECOMMENDATIONS` |

**Cell 0 must run first** (nothing else resolves without it), and the `CLUB_RANGES` cell must
run **before** Golf Recommendations. Every other section reads only `GOLF_STATS`, so order is
otherwise free; running top to bottom satisfies everything. After adding rounds, run the whole
notebook, then restart the MCP server (it loads all data once at import).

Note the Club Recommendations cell that writes `CLUB_RANGES` ends with an `input()` prompt, so
"run all" will block there waiting on stdin.

Feature Importances is exploratory only — it writes nothing, reads an archived one-course
CSV, and can be skipped.

## Known issues — read before trusting any number

1. **Strokes gained is heuristic, not tour-baseline.** The Shots Gained cell assigns SG_OTT as
   a flat ±0.15 on fairway hit/miss and SG_Approach as ±0.3/−0.2 on GIR, with SG_ARG as the
   leftover residual. These are invented constants, not PGA Tour expected-strokes tables.
   Treat SG values as an internal consistency index, not a figure comparable to published
   strokes-gained numbers. This is why `get_strokes_gained_summary` reports large negative
   totals (≈ −19 over 10 rounds) — the baseline is not a real scratch golfer.

2. **Round profile ratings are relative, not absolute.** Each area is z-scored against that
   golfer's *own* history, so `On` means "good for you," not "good." Cross-golfer comparison
   of ratings is meaningless — compare the raw `Fairway%` / `GIR%` / `UpDown%` / `TotalPutts`
   columns instead. Ryan has only 9 rounds behind his baseline (`BaselineRounds` records this),
   so his ratings move a lot as rounds are added.

3. **Everything in `archive/` is retired**, kept for reference only: `Golf Stats Multiple
   Users.xlsx` (superseded by `Golf Stats.xlsx`), `clutch_scores_advanced.xlsx` and
   `profiled_rounds_clustered.xlsx` (single-golfer predecessors, no `Golfer` column), and
   `data.csv` (a Bethpage-Blue-only fragment, 36 rows, read only by the exploratory
   Feature Importances cells). Don't wire new work to any of them.

## golf_mcp.py

Single ~2,050-line module built on **MCP Python SDK v2** (`mcp.server.mcpserver.MCPServer`),
which implements spec revision `2026-07-28`. Sections are marked by `── banner ──` comments,
in this order:

- **Server config.** `MCPServer` takes no host/port — transport is chosen in the entrypoint at
  the bottom. `BearerAuthMiddleware` lives here too: raw ASGI, not `BaseHTTPMiddleware`, which
  would buffer the response body and break the Streamable HTTP stream.
- **Load all data / Tyler slices.** All workbooks are read at *import time* into module
  globals, then filtered to `Golfer == "Tyler"` into `tyler`, `tyler_sg`, `tyler_clutch`,
  `tyler_range`, `tyler_putts`, `tyler_hcap`, `tyler_raps`. Data changes require a restart.
- **Chart helpers.** `render_chart()` renders a figure to an inline base64 PNG at `CHART_DPI`.
  `style_ax()` applies the dark theme (`#1a1a2e` figure, `#16213e` axes). `chart_tool`
  registers a chart tool and serializes it on `_PYPLOT_LOCK` — see the notes below.
- **Tools**, grouped by banner comment: scoring, handicap, range/launch-monitor stats, club
  gapping, strokes gained, putting, course breakdowns, clutch, charts, ball-flight simulation,
  and club fitting.
- **Entrypoint.** `/health` route, `build_http_app()`, and the stdio/HTTP switch.

Conventions to match when adding a tool:

- Decorate with `@mcp.tool(structured_output=False)`, return `str`, and give it a docstring —
  the docstring is what Claude sees when choosing tools. **The `structured_output=False` is
  load-bearing**: v2 auto-derives an output schema from the `-> str` annotation and then sends
  the return value twice, once as text content and once as an identical `structuredContent`
  blob. Drop the flag only when giving a tool a *real* schema worth the second copy.
- Return pandas frames via `.to_string(index=False)`, not `.to_markdown()` or raw repr.
- Chart tools use `@chart_tool` (not `@mcp.tool`), annotate `-> Image`, and `return
  render_chart(fig)` — which renders to an inline base64 PNG. **Never return a file path**:
  that only worked when the client shared a disk with the server, and breaks the moment the
  server is remote. To send a chart *and* text, return a list (`[render_chart(fig), info]`),
  which the SDK flattens into separate content blocks.
- `@chart_tool` also holds `_PYPLOT_LOCK` for the whole tool body. v2 runs sync tool functions
  on worker threads, and pyplot's current-figure state (`plt.subplots`, `plt.xticks`) is
  process-global, so concurrent chart calls would otherwise draw into each other's figures.
  Non-chart tools are pure pandas and need no lock.
- Club identifiers are lowercase and follow `CLUB_ORDER`
  (`lw - 30`, `lw - 50`, `lw`, `sw`, `gw`, `pw`, `9i`…`4i`, `3h`, `3w`, `d`).
- Read from the `tyler_*` slices, not the raw frames, unless the tool is explicitly a
  multi-golfer comparison (see `compare_with_partner`).

### Running it

The server needs the repo venv — the global 3.14 install still has SDK v1, which has no
`mcp.server.mcpserver` and fails at import. `.mcp.json` already points at `.venv`.

```powershell
.venv\Scripts\python.exe -X utf8 golf_mcp.py       # stdio (local Claude clients)
$env:PORT=8000; .venv\Scripts\python.exe golf_mcp.py   # Streamable HTTP, 0.0.0.0:8000
```

Setting `PORT` (or `MCP_PORT`) switches the transport to Streamable HTTP; `PORT` alone also
flips the bind address to `0.0.0.0` for container hosts. `MCP_HOST` overrides the address.
HTTP mode runs `stateless_http=True` — without it the server rejects every request with
"Missing session ID", and with it any instance can serve any request, which is what makes
the server deployable behind a load balancer or on serverless.

HTTP mode also **refuses to start without `MCP_AUTH_TOKEN`**, because it publishes all 54
tools to anyone who can reach the port. Requests must carry `Authorization: Bearer <token>`;
`/health` is deliberately exempt so a failing host check reads differently from a bad token.
The token must never go in the URL — the spec forbids credentials in query strings.

### Deploying it

`Dockerfile` + `fly.toml` deploy to Fly.io. The dataset is under 1 MB and committed, so it is
baked into the image — no volume, no database. The tradeoff: **re-running the notebook means
redeploying**, otherwise the deployed server keeps serving the data from its last build.

```powershell
fly launch --no-deploy --copy-config            # claims the app name, keeps fly.toml
fly secrets set MCP_AUTH_TOKEN=$(python -c "import secrets;print(secrets.token_urlsafe(32))")
fly deploy                                      # builds remotely; local Docker not required
```

Then add `https://<app>.fly.dev/mcp` in Claude → Settings → Connectors → Add custom connector,
with the token as an `Authorization: Bearer <token>` header. That URL works from web, desktop,
and mobile. Anthropic reaches the server from its own IP ranges, so it must stay publicly
routable — a private network or VPN will not connect.

Measured facts worth not re-deriving: image is ~780 MB, resident memory is 170 MB idle and
194 MB peak across the heaviest charts, hence `memory = "512mb"` in `fly.toml`. `CHART_DPI`
(default 110) trades chart payload size against sharpness; charts run 40–300 KB raw and travel
base64-encoded, which costs a third more again.

## Data

Column-by-column reference for every sheet: [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

Quick orientation — `Golf Stats.xlsx` holds 12 sheets. `Golf Scores` (one row per round) and
`Hole Log` (one row per hole, the basis for strokes gained) are the two that matter most.
`Range Stats` is launch-monitor data keyed by `Club Type`.

## Conventions

- Dates are coerced with `pd.to_datetime(..., errors="coerce")` on load; expect NaT rather
  than exceptions on bad rows.
- The `Golfer` column is the primary filter everywhere. `Tyler` is the subject; `Rich` and
  `Ryan` exist for comparison only.
- `data/derived/` files are build artifacts but **are committed** — they're what the MCP server
  and Power BI consume, and neither runs the notebook. Regenerate and commit together.
- Excel files are binary: git can't diff or merge them. Don't edit one while another process
  has it open, and never resolve a conflict on them by hand.
