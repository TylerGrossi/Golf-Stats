"""Single source of truth for data file locations.

Both `golf_mcp.py` and `notebooks/Golf Analytics.ipynb` import this, so paths are
resolved relative to the repo rather than hardcoded to any one machine.

Usage:

    from paths import RAW, DERIVED, GOLF_STATS
    df = pd.read_excel(GOLF_STATS, sheet_name="Hole Log")

Set the ``GOLF_DATA_DIR`` environment variable to point at a different data root
(a directory containing ``raw/`` and ``derived/``); otherwise ``<repo>/data`` is used.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DATA = Path(os.environ.get("GOLF_DATA_DIR", ROOT / "data"))
RAW = DATA / "raw"
DERIVED = DATA / "derived"
ARCHIVE = ROOT / "archive"

# ── Raw (hand-maintained) ─────────────────────────────────────────────────────
GOLF_STATS = RAW / "Golf Stats.xlsx"

# ── Archived ──────────────────────────────────────────────────────────────────
# Retired inputs. Nothing in the live pipeline reads these; DATA_CSV is kept only so
# the notebook's exploratory "Feature Importances" section still runs.
DATA_CSV = ARCHIVE / "data.csv"

# ── Derived (written by the notebook) ─────────────────────────────────────────
STROKES_GAINED = DERIVED / "strokes_gained_summary.xlsx"
ROUND_PROFILES = DERIVED / "round_profiles.xlsx"
CLUTCH_SCORES = DERIVED / "clutch_score_analysis.xlsx"
CLUB_RANGES = DERIVED / "club_ranges.xlsx"
CLUB_SELECTOR = DERIVED / "club_selector.xlsx"
RECOMMENDATIONS = DERIVED / "golf_recommendations.xlsx"


def find_root(start: Path | None = None) -> Path:
    """Locate the repo root by walking up from `start` (default: cwd).

    Lets the notebook bootstrap itself regardless of the working directory Jupyter
    was launched from.
    """
    start = (start or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / "paths.py").exists():
            return candidate
    raise FileNotFoundError(f"Could not find repo root (no paths.py) above {start}")
