# Golf Dashboard 2.0 — report map

Reference for the Power BI report at `dashboards/Golf Dashboard 2.0.pbip`. Written after
converting the `.pbix` to PBIP (source-controlled folder format) and renaming all page
folders to readable names. Use this to locate pages/visuals before making changes.

> Editing rule: close Power BI Desktop before editing any file under
> `Golf Dashboard 2.0.Report/`, then reopen the `.pbip`. Desktop locks the files while open.

## Project layout (in `dashboards/`)

```
Golf Dashboard 2.0.pbip                    entry point (open this in Desktop)
Golf Dashboard 2.0.Report/                 the report — pages, visuals, bookmarks, theme
  definition.pbir                          binds report -> ../Golf Dashboard 2.0.SemanticModel
  definition/
    report.json                            theme + custom-visual registrations
    pages/pages.json                       page order + active page
    pages/pgNNName/page.json               one folder per page (renamed, see table)
    pages/pgNNName/visuals/<guid>/visual.json   one folder per visual (still GUID-named)
    bookmarks/                             6 bookmarks (all target pg02Overview)
Golf Dashboard 2.0.SemanticModel/          the data model — tables, measures, relationships
Golf Dashboard 2.0.pbix                    OLD single-file copy, now redundant with the PBIP
```

The report and the model are **separate artifacts**. Report changes (pages, visuals,
layout, formatting) are files under `.Report/`. Data changes (tables, columns, measures,
relationships) are TMDL files under `.SemanticModel/` and are normally edited in Desktop.

## Pages (21)

Only **pg01GolfDashboard** is visible; it's the navigation hub (buttons + shapes + text,
no charts). Every other page is `HiddenInViewMode` and reached by clicking a nav button on
the hub. Page folders were renamed from GUIDs to the names below; the old GUID is kept here
for cross-reference with anything outside this repo.

| Folder | Display name | Old GUID | Canvas | Visuals | Notable data-viz |
|--------|--------------|----------|--------|---------|------------------|
| pg01GolfDashboard | Golf Dashboard *(landing/nav)* | 601f7bece1c8de7406a3 | 1280×720 | 18 | nav only (buttons/shapes) |
| pg02Overview | Overview Dashboard | 142843785b67c53328e9 | 1550×800 | 34 | 3 gauge, 2 line, column, pie, donut, 5 card |
| pg03Round | Round Dashboard | b17e67da00a7850ea6ce | 1550×800 | 35 | box-and-whisker, clustered bar, column, table, 9 card |
| pg04Hole | Hole Dashboard | e60a0eb6551858cb005a | 1550×800 | 36 | column, line, 3 table, 7 card |
| pg05Putt | Putt Dashboard | 57aa99cb631e52ab6a81 | 1550×800 | 38 | 2 line, 4 table, 7 card |
| pg06Fairways | Fairways Dashboard | 8f507aaf6db849b539e2 | 1550×800 | 44 | 2 line, 3 table, 12 card |
| pg07GIR | GIR Dashboard | 2014a2eedd6b4143def5 | 1550×800 | 41 | column, line, 4 table, 8 card |
| pg08OnCourseTool | On Course Tool | 542e286b2bcde8c5786c | 1550×800 | 48 | 24 KPI cards, table |
| pg09RangeStats | Range Stats | 68a6e94557f9f775caa0 | 1550×800 | 46 | 2 column, gauge, pivot table, table, 10 card |
| pg10OnlineRoundStats | Online Round Stats | 34ebac066e00e1c91746 | 1550×800 | 38 | 3 column, gauge, table, 10 card |
| pg11Course | Course Dashboard | fc5b0b6a8b0dfc6f0bd9 | 1550×800 | 39 | column, line, 4 table, 7 card |
| pg12Splits | Golf Splits | eacd161a1bc9006be015 | 1550×800 | 26 | 2 KPI cards |
| pg13SmashFactor | Smash Factor | ec3657f638226b951146 | 1280×720 | 7 | column |
| pg14BallsHit | Balls Hit | 70cab94ba2c6024c7dd4 | 1280×720 | 7 | column |
| pg15LaunchAngle | Launch Angle | ed38a772dd13e727ff01 | 1280×720 | 12 | line |
| pg16LaunchDirection | Launch Direction | 562eb557abd431ae5c2f | 1280×720 | 12 | line |
| pg17Apex | Apex | 60510cd393485e9af00f | 1280×720 | 12 | line |
| pg18DescentAngle | Descent Angle | 6ff3adc81e3e0640b459 | 1280×720 | 12 | line |
| pg19ClubSpeed | Club Speed | 1d064a0f818d01487dcf | 1280×720 | 12 | line |
| pg20BallSpeed | Ball Speed | 483cfeacb7ea72222af4 | 1280×720 | 12 | line |
| pg21DispersionMap | Dispersion Map | e9860fbeab5861527b51 | 1280×720 | 12 | scatter |

Two page groups by canvas size: the **scoring/on-course** pages are 1550×800 (pg02–pg12,
plus pg09/pg10), and the **launch-monitor** single-metric pages are 1280×720 (pg13–pg21).

### Why the pages are hidden + how navigation works

The hub (pg01) holds action buttons whose navigation action stores the **target page name as
a literal** (`"Value": "'pg02Overview'"`). Every non-hub page also carries a set of nav
buttons back to the others. Because navigation is by page *name*, renaming a page means
updating every button reference — which was done in the same pass as the folder rename, so
navigation is intact. If you add a page and want it reachable, add a button with a
`pageNavigation` action pointing at the new page name.

## Visual inventory (whole report, ~570 visuals)

| Type | Count | Notes |
|------|-------|-------|
| slicer | 189 | mostly hidden per-page filter slicers (Golfer = Tyler, date, course) |
| actionButton | 132 | page navigation |
| card | 75 | classic single-value cards |
| cardVisual | 26 | new-style KPI cards (24 on pg08 On Course Tool) |
| textbox | 22 | titles/labels |
| tableEx | 22 | detail tables |
| shape | 17 | decorative/background |
| lineChart | 15 | trends |
| columnChart | 12 | |
| gauge | 5 | handicap / summary gauges |
| scatterChart / pivotTable / pieChart / donutChart / clusteredBarChart | 1 each | |
| BoxandWhisker (custom) | 1 | pg03Round |

Visual folders are **still GUID-named** (intentionally — you rarely navigate them by hand).
To find a specific visual, open the page in Desktop, or grep the page's `visuals/` folder for
the field/measure it uses.

### Custom (imported) visuals — registered in `report.json`
- Box-and-Whisker (MAQ)
- Radar chart
- Deneb (custom Vega/Vega-Lite)
- A chiclet-style slicer (`PBI_CV_…`)
- `BoxWhiskerChart1455…`

### Theme
Custom theme `Innovate8211295494590508.json` layered over Microsoft base `CY24SU10`.
A background image `Fairway8444562480098291.PNG` is registered as a report resource.

## Data model (`.SemanticModel`)

Bound to the report via `definition.pbir` (`byPath` → `../Golf Dashboard 2.0.SemanticModel`).

### Tables that matter
- **Fact/log tables:** `Golf Log`, `Hole Log`, `Putt Log`, `Fairway Log` (+ `Fairway Log by Hole`),
  `GIR Log` (+ `GIR Log by Hole`), `Golf Log by Hole`, `Putt Log by Hole`, `Golf Scores`
- **Launch-monitor:** `Range Stats`, `Rapsodo Course Stats`
- **Derived (from the notebook pipeline):** `strokes_gained_summary`, `clutch_score_analysis`,
  `club_ranges`, `Recommendations`, `clustered_rounds`
- **Dimension/lookup:** `Course Table`, `Course Stats`, `Date Table`, `Hole Table`,
  `Round Table`, `ClubLookup`, `Handicap`, `PerformanceMetrics`
- **Chart-helper (shaped for a specific visual):** `ApexGraph`, `LaunchAngleGraph`,
  `LaunchDirectionGraph`, `ClubDescentFlight`

### Measures (41, across 7 tables)
- **Golf Log (13):** Birdie / Par / Bogey / Eagle Count, `Double Bogey+ Count t`, Shots Over Par,
  Shots Under Par, Over Par by Hole, Times Played, Sum Over Par by Hole, Unique Course Count,
  Average Front 9 Score, Average Back 9 Score
- **Hole Log (13):** GIR Average Display, Fairway Average Display, Scrambling %, Hit/Left/Right/
  Long/Short %, GIR Hit/Left/Right/Long/Short %
- **Putt Log (4):** One / Two / Three Putt Count, Hole Outs
- **Fairway Log (5):** MissLeft%, MissRight%, MissShort%, MissLong%, HitCenter%
- **Course Stats (3):** Hole Score vs Par, Hole Par (Fixed), Over Par on each Hole
- **Handicap (2):** Handicap Index, Handicap Index Total
- **Range Stats (1):** Average Launch Angle

## Known structural notes / cleanup opportunities
1. **Auto date/time clutter:** ~20 `LocalDateTable_*` and `DateTableTemplate_*` tables are
   auto-generated by Power BI's auto date/time. They're noise. Remove them in Desktop via
   Options → Data Load → uncheck "Auto date/time" (cannot be safely deleted by editing files).
2. **Redundant `.pbix`:** `Golf Dashboard 2.0.pbix` is the pre-PBIP single-file copy. Safe to
   archive/delete once you've confirmed the PBIP opens correctly, to avoid editing the wrong one.
3. **Visual folders remain GUIDs** — by choice. Revisit only if you start editing visual JSON
   by hand often.

## Relationship to the rest of the repo
This report reads its own `.SemanticModel`, which imports from the same Excel outputs described
in the root `CLAUDE.md`: `data/raw/Golf Stats.xlsx` plus the notebook-derived workbooks
(`strokes_gained_summary`, `clutch_score_analysis`, `club_ranges`, `Recommendations`,
`round_profiles`). The MCP server (`golf_mcp.py`) consumes the same derived files independently.
