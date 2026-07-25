# Data dictionary

Every workbook, sheet, and non-obvious column. See [../CLAUDE.md](../CLAUDE.md) for how these
files flow into each other.

Shared conventions:

- **`Golfer`** — `Tyler` (the subject), `Rich`, or `Ryan` (comparison only). Filter on this first.
- **`Date`** — round date; a `(Golfer, Date, Course)` triple identifies a round.
- **`Tees`** — tee set played (`White`, `Blue`, `Gold`, …). Changes yardage/rating/slope, so it
  is part of the key wherever course difficulty matters.
- **`Hole 1` … `Hole 18`** — wide per-hole layout. Several sheets repeat this shape with
  different payloads (score, putts, fairway flag, GIR flag, yardage, stroke index).
- **Club identifiers** are lowercase: `lw - 30`, `lw - 50`, `lw`, `sw`, `gw`, `pw`, `9i`, `8i`,
  `7i`, `6i`, `5i`, `4i`, `3h`, `3w`, `d`.

---

## Source workbooks

### `data/raw/Golf Stats.xlsx` — source of truth

Hand-maintained in Excel. Through 2026-07-19, 84 rounds. **The single source of truth** —
the notebook, the MCP server, and Power BI all trace back to this file.

#### `Golf Scores` — one row per round

| Column | Meaning |
|---|---|
| `Score` | Total strokes |
| `Over Par` | `Score` − `Par` |
| `Played With` | Free-text playing partners |
| `Par` / `Yardage` | Course par and yardage for the tees played |
| `Front 9` / `Back 9` | Nine-hole subtotals |
| `Eagles`…`Double Bogeys` | Hole-result counts (double bogey **or worse** falls in `Double Bogeys`) |
| `Holes Played` | 9 or 18 — filter on this before comparing round scores |
| `Putts` / `Fairways` / `Greens` | Round totals (counts, not percentages) |

#### `Handicap` — one row per posted score

| Column | Meaning |
|---|---|
| `Rating` / `Slope` | USGA course rating and slope for the tees played |
| `Differential` | `(Score − Rating) × 113 / Slope` — the handicap differential |

#### `Hole Log` — one row per hole played ⭐

The most granular sheet and the input to strokes gained.

| Column | Meaning |
|---|---|
| `Short Course` | Abbreviated course name (join key in places) |
| `Score` | **Round** total, repeated on every hole row |
| `Holes` | 9 or 18 for the round |
| `Hole` | Hole number 1–18 |
| `Handicap` | Hole **stroke index** (1 = hardest), not the golfer's handicap |
| `Hole Score` | Strokes on this hole |
| `Score vs Par` | `Hole Score` − `Par` |
| `Type` | Hole result label (birdie / par / bogey / …) |
| `Putts` | Putts on this hole |
| `Fairways` | 1 = fairway hit, 0 = missed. Par 3s are typically 0 — exclude `Par == 3` before computing fairway % |
| `GIR` | 1 = green in regulation, 0 = not |

#### `Golf Log` — round scorecard, wide

`Hole 1`…`Hole 18` hold per-hole strokes. Also `Par 3 Avg` / `Par 4 Avg` / `Par 5 Avg` —
scoring average by par type for that round.

#### `Putt Log` / `Fairway Log` / `GIR Log` — wide per-hole splits

Same shape, different payload. `Putt Log` carries a duplicate `Putts2` column (`Putts` is the
round total, `Putts2` a restatement — prefer `Putts`). `Fairway Log` adds `Fairway %`,
`GIR Log` adds `GIR %`.

#### `Course Stats` / `Course Yardages` / `Course Handicaps` — course reference

One row per `(Course, Tees)`. `Course Stats` carries `Yardage`, `Rating`, `Slope`, `Par` plus
per-hole **par**; `Course Yardages` per-hole **yardage**; `Course Handicaps` per-hole
**stroke index**.

#### `Range Stats` — launch monitor, one row per shot

Practice-range captures. Keyed by `Club Type` (the club identifier) with `Club Brand` /
`Club Model` describing the equipment.

| Column | Meaning |
|---|---|
| `Carry Distance` / `Total Distance` | Yards to landing / to rest |
| `Ball Speed` / `Club Speed` | mph |
| `Smash Factor` | `Ball Speed / Club Speed` — strike efficiency (~1.50 driver ceiling) |
| `Launch Angle` / `Launch Direction` | Vertical launch° / horizontal start° (− left, + right) |
| `Apex` | Peak height, yards |
| `Side Carry` | Lateral offset at landing, yards (− left, + right) — dispersion metric |
| `Descent Angle` | Landing angle° — drives stopping power |
| `Attack Angle` | Club path vertical° at impact (− down, + up) |
| `Club Path` | Horizontal path° at impact |
| `Spin Rate` / `Spin Axis` | rpm / tilt° (− draw, + fade) |
| `Club Data Est Type` | Whether club-side data was measured or estimated by the monitor |

#### `Rapsodo Course Stats`

Same columns as `Range Stats` but captured **on course** — keyed by `Course` instead of `Date`.

---

### `archive/data.csv` — Bethpage Blue fragment (retired)

36 rows (18 holes × White/Blue tees), one course only. **Archived** — consumed by the
exploratory "Feature Importances" notebook section and nothing else. Columns are aggregates **across every play of that hole**:

| Column | Meaning |
|---|---|
| `TP` | Times played |
| `+/-` | Cumulative strokes over par across those plays |
| `Putts` | Average putts per play |
| `Fairs` / `Fair%` | Fairways hit (count) and `Fairs / TP` |
| `GIR` / `GIR%` | Greens hit (count) and `GIR / TP` |

`Fair%` and `GIR%` are **strings with a `%` suffix** — strip and divide before use.

---

## Derived workbooks

Regenerated by `notebooks/Golf Analytics.ipynb`. Do not hand-edit. Reference them in code via
the constants in `paths.py`, never by filename literal.

### `data/derived/strokes_gained_summary.xlsx` — notebook section "Shots Gained"

⚠️ SG values use invented constants, not tour baselines — see known issue #2 in
[../CLAUDE.md](../CLAUDE.md).

**`Round Summary`** — one row per round: `SG_Total`, `SG_T2G` (tee to green), `SG_OTT`
(off the tee), `SG_Approach`, `SG_ARG` (around the green), `SG_Putting`.

**`Hole Detail`** — `Hole Log` plus the per-hole SG derivation:

| Column | Meaning |
|---|---|
| `Expected_Score` | Baseline strokes for the hole, from course rating and par |
| `SG_Total` | `Expected_Score` − `Hole Score` |
| `Expected_Putts` | Baseline putts, conditioned on GIR |
| `SG_Putting` | `Expected_Putts` − `Putts` |
| `SG_T2G` | `SG_Total` − `SG_Putting` |
| `SG_OTT` | ±0.15 on `is_fwy`, par 4/5 only (0 on par 3s) |
| `SG_Approach` | Par 3: all of `SG_T2G`. Par 4/5: +0.3 if `is_gir` else −0.2 |
| `SG_ARG` | Residual: `SG_T2G` − `SG_OTT` − `SG_Approach` |
| `is_gir` / `is_fwy` | Boolean forms of `GIR` / `Fairways` |
| `Course_Par` | Course total par (distinct from the hole's `Par`) |

### `data/derived/round_profiles.xlsx` — notebook section "Round Profiling"

One row per **18-hole** round, rating four areas of the game independently. Replaced the old
KMeans `clustered_rounds.xlsx`, whose `Cluster` ids drifted against hand-typed labels.

| Column | Meaning |
|---|---|
| `Fairway%` | Fairways hit ÷ tracked par 4/5 tee shots. Denominator is per-round, not assumed to be 14 |
| `GIR%` | Greens hit ÷ tracked holes |
| `UpDown%` | (Missed green **and** 1 putt) ÷ missed greens |
| `TotalPutts` | Putts for the round |
| `FwyOpps` / `GIRopps` / `UpDownOpps` | Denominators above — the sample behind each rate |
| `z_Driving` / `z_Irons` / `z_Wedges` / `z_Putting` | Standard deviations from **that golfer's own** mean. Putting is sign-flipped, so positive always means played well |
| `Driving` / `Irons` / `Wedges` / `Putting` | `On` / `Normal` / `Off` at \|z\| > 0.5 (`ON_OFF_SIGMA` in the cell) |
| `BestArea` / `WorstArea` | Highest and lowest z that round |
| `BaselineRounds` | Rounds behind this golfer's baseline — low counts make ratings twitchy |

Handling of the `Fairways` / `GIR` arrow codes:

- Only `'1'` counts as a hit; every arrow is a miss.
- **`NC` ("no chance") counts as a driving miss** — it means the drive left no shot at the
  green — and as a missed green for up-and-down purposes, but is excluded from `GIR%` entirely,
  since no iron was ever hit at the green. This overrides `Fairways` even on the 6 holes where
  `NC` coexists with a recorded fairway hit.
- Rounds with fewer than 18 holes are excluded.

`Fairway%` is null when a round has no `Par` data to identify par 4/5 holes (currently one:
Rich, 2023-08-18). The rating columns are null to match rather than guessing.

### `data/derived/clutch_score_analysis.xlsx` — notebook section "Clutch Score"

Late-round performance, one row per round.

| Column | Meaning |
|---|---|
| `Avg_Early_Score_vs_Par` | Mean over-par across the opening holes |
| `Final3_Score_vs_Par` | Over-par across holes 16–18 |
| `ClutchScore_Par` | Early average − closing performance (**positive = finished stronger**) |
| `ClutchScore_Weighted` | Same, weighted toward the final holes |
| `Score_Trend_Slope` | Linear-regression slope of score-vs-par across the round (negative = improving) |
| `ClutchLabel` | Categorical verdict |

### `data/derived/club_ranges.xlsx` — notebook section "Club Recommendations"

One row per club: `Lower`, `Upper` (yards) and `Range` as a display string. Feeds the "Golf Recommendations" section.

### `data/derived/club_selector.xlsx` — notebook section "Club Recommendations"

Distance-to-club lookup: `DistanceBin`, recommended `Club`, `Top25Carry` (75th-percentile
carry, i.e. a good strike rather than an average one), `ShotCount` (sample size — treat low
counts as unreliable).

### `data/derived/golf_recommendations.xlsx` — notebook section "Golf Recommendations"

One row per `(Course, Hole, Tees)`: historical `Putts` / `Fairways` / `GIR` for that hole plus
`Target Distance` and three text fields — `Recommendation`, `Tee Recommendation`,
`Approach Recommendation`.

---

## `archive/` — retired

Kept for reference; nothing in the live pipeline reads them.

| File | Why |
|---|---|
| `Golf Stats Multiple Users.xlsx` | Superseded by `Golf Stats.xlsx`. Identical 12-sheet schema but ends 2026-06-12 / 73 rounds. |
| `clutch_scores_advanced.xlsx` | Single-golfer predecessor of `clutch_score_analysis.xlsx`; no `Golfer` column. |
| `profiled_rounds_clustered.xlsx` | Single-golfer predecessor of the round profiles; no `Golfer` column. |
| `data.csv` | One-course aggregate fragment; see above. |
