# Golf Stats

Personal golf performance analytics. Round-by-round scoring, hole-level strokes gained,
launch-monitor club data, and club-fitting analysis — served to Claude through an MCP server
and visualized in Power BI.

## Layout

```
paths.py                       Data file locations — import these, don't hardcode paths
golf_mcp.py                    MCP server: ~60 tools for stats, charts, and fitting reports
notebooks/Golf Analytics.ipynb Computes strokes gained, clustering, clutch scores, club gapping
data/raw/Golf Stats.xlsx       Single source of truth, maintained by hand in Excel
data/derived/                  Notebook output — regenerated, not hand-edited
dashboards/                    Power BI dashboard
docs/                          Data dictionary and images
archive/                       Retired inputs, kept for reference only
```

## Setup

```powershell
pip install -r requirements.txt
```

## Refreshing after new rounds

1. Add rounds to `data/raw/Golf Stats.xlsx` (`Golf Scores` and `Hole Log` sheets).
2. Run `notebooks/Golf Analytics.ipynb` top to bottom — the first cell resolves paths, and
   later sections depend on files earlier ones write.
3. Restart the MCP server — it loads all data once at import.

## Running the MCP server

```powershell
python golf_mcp.py
```

Binds `127.0.0.1:8000`. `PORT`, `FASTMCP_HOST`, and `FASTMCP_PORT` control the HTTP binding;
`GOLF_DATA_DIR` points the data root somewhere other than `./data`.

## Documentation

- [CLAUDE.md](CLAUDE.md) — architecture, pipeline dependencies, conventions, and known issues
- [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) — every sheet and column

Both are written for AI agents working in this repo, but they're the fastest orientation for
a human too. **Read the known-issues section of `CLAUDE.md` before trusting any number** —
strokes gained uses invented constants rather than tour baselines, so the totals are not
comparable to published strokes-gained figures.

## Power BI

`dashboards/Golf Dashboard 2.0.pbix` stores absolute paths to six files (`Golf Stats.xlsx`
plus five in `data/derived/`). After the move they need re-pointing via
**Data source settings → Change Source**.
