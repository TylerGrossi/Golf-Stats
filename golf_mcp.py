from mcp.server.fastmcp import FastMCP
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os, tempfile
from scipy import stats as scipy_stats

# ── Server config ─────────────────────────────────────────────────────────────
_http_host = os.environ.get("FASTMCP_HOST") or (
    "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
)
_http_port = int(os.environ.get("PORT", os.environ.get("FASTMCP_PORT", "8000")))
mcp = FastMCP("Golf Analytics", host=_http_host, port=_http_port)

BASE = os.environ.get(
    "GOLF_DATA_DIR",
    os.path.join(os.path.expanduser("~"), "Desktop", "Tyler", "OneDrive", "Projects", "Golf Stats")
)

# ── Load all data ─────────────────────────────────────────────────────────────
xl          = pd.ExcelFile(os.path.join(BASE, "Golf Stats Multiple Users.xlsx"))
rounds_df   = xl.parse("Golf Scores")
handicap_df = xl.parse("Handicap")
range_df    = xl.parse("Range Stats")
raps_df     = xl.parse("Rapsodo Course Stats")
putt_log    = xl.parse("Putt Log")

sg_df       = pd.read_excel(os.path.join(BASE, "strokes_gained_summary.xlsx"), sheet_name="Round Summary")
recs_df     = pd.read_excel(os.path.join(BASE, "golf_recommendations.xlsx"),   sheet_name="Sheet1")
club_ranges = pd.read_excel(os.path.join(BASE, "club_ranges.xlsx"),            sheet_name="Sheet1")
club_sel    = pd.read_excel(os.path.join(BASE, "club_selector.xlsx"),          sheet_name="Sheet1")
clutch_df   = pd.read_excel(os.path.join(BASE, "clutch_score_analysis.xlsx"),  sheet_name="Sheet1")

# ── Clean dates ───────────────────────────────────────────────────────────────
for df in [rounds_df, handicap_df, sg_df, clutch_df, range_df, putt_log]:
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

# ── Tyler slices ──────────────────────────────────────────────────────────────
tyler        = rounds_df[rounds_df["Golfer"] == "Tyler"].copy().sort_values("Date")
tyler_hcap   = handicap_df[handicap_df["Golfer"] == "Tyler"].copy().sort_values("Date")
tyler_sg     = sg_df[sg_df["Golfer"] == "Tyler"].copy().sort_values("Date")
tyler_clutch = clutch_df[clutch_df["Golfer"] == "Tyler"].copy().sort_values("Date")
tyler_range  = range_df[range_df["Golfer"] == "Tyler"].copy().sort_values("Date")
tyler_putts  = putt_log[putt_log["Golfer"] == "Tyler"].copy().sort_values("Date")
tyler_raps   = raps_df[raps_df["Golfer"] == "Tyler"].copy()

CLUB_ORDER    = ["lw - 30","lw - 50","lw","sw","gw","pw","9i","8i","7i","6i","5i","4i","3h","3w","d"]
TRACKMAN_COLS = ["Carry Distance","Total Distance","Ball Speed","Launch Angle",
                 "Club Speed","Smash Factor","Apex","Side Carry","Descent Angle"]

# ── Chart helpers ─────────────────────────────────────────────────────────────
CHART_DIR = tempfile.mkdtemp()

def save_chart(fig, name):
    path = os.path.join(CHART_DIR, f"{name}.png")
    fig.savefig(path, dpi=130, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)
    return path

def style_ax(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor("#16213e")
    ax.tick_params(colors="#cccccc", labelsize=9)
    ax.xaxis.label.set_color("#cccccc")
    ax.yaxis.label.set_color("#cccccc")
    ax.title.set_color("#ffffff")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444466")
    if title:  ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    if xlabel: ax.set_xlabel(xlabel, fontsize=9)
    if ylabel: ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(True, color="#2a2a4a", linewidth=0.6, linestyle="--")


# ══════════════════════════════════════════════════════════════════════════════
# SCORING
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_scoring_trends(last_n_rounds: int = 10) -> str:
    """Get Tyler's recent scoring trends and averages."""
    recent = tyler.tail(last_n_rounds)
    rows = recent[["Date","Course","Score","Over Par"]].copy()
    rows["Date"] = rows["Date"].dt.strftime("%Y-%m-%d")
    return (
        f"Last {last_n_rounds} rounds — Avg: {recent['Score'].mean():.1f}, "
        f"Best: {recent['Score'].min()}, Worst: {recent['Score'].max()}\n\n"
        + rows.to_string(index=False)
    )


@mcp.tool()
def chart_scoring_trend(last_n_rounds: int = 20) -> str:
    """Generate a chart of Tyler's score trend over recent rounds."""
    df = tyler.tail(last_n_rounds).copy()
    fig, ax = plt.subplots(figsize=(10, 4), facecolor="#1a1a2e")
    style_ax(ax, title=f"Tyler's Score Trend (Last {last_n_rounds} Rounds)",
             xlabel="Date", ylabel="Score")
    ax.plot(df["Date"], df["Score"], color="#4fc3f7", linewidth=2,
            marker="o", markersize=5, markerfacecolor="#ffffff")
    z = np.polyfit(range(len(df)), df["Score"], 1)
    ax.plot(df["Date"], np.poly1d(z)(range(len(df))), "--",
            color="#ff7043", linewidth=1.5, label="Trend")
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    plt.xticks(rotation=30)
    return f"Chart saved to: {save_chart(fig, 'score_trend')}"


@mcp.tool()
def get_scoring_distribution() -> str:
    """
    Breakdown of Tyler's score distribution: birdie rate, par rate, bogey rate,
    double bogey+ rate, and how scoring has shifted across calendar years.
    """
    df = tyler.dropna(subset=["Birdies","Pars","Bogeys","Double Bogeys"]).copy()
    df["Year"] = df["Date"].dt.year
    total_holes = len(df) * 18
    lines = ["Scoring distribution (all rounds):\n"]
    for col in ["Birdies","Pars","Bogeys","Double Bogeys"]:
        total = df[col].sum()
        pct = total / total_holes * 100
        lines.append(f"  {col:<16} {int(total):>5} total  ({pct:.1f}% of holes)")
    lines.append("\nBy year:")
    for year, grp in df.groupby("Year"):
        n = len(grp)
        avg = grp["Score"].mean()
        bird_rate = grp["Birdies"].sum() / (n * 18) * 100
        dbl_rate  = grp["Double Bogeys"].sum() / (n * 18) * 100
        lines.append(f"  {year}  n={n:<3}  avg={avg:.1f}  birdie%={bird_rate:.1f}  dbl_bogey%={dbl_rate:.1f}")
    return "\n".join(lines)


@mcp.tool()
def get_rolling_scoring_average(window: int = 5) -> str:
    """
    Rolling N-round scoring average to reveal momentum and true skill trend,
    filtering out one-off outlier rounds.
    """
    df = tyler.dropna(subset=["Score"]).copy()
    df["Rolling_Avg"] = df["Score"].rolling(window, min_periods=1).mean()
    lines = [f"Rolling {window}-round scoring average:\n",
             f"  Current rolling avg:  {df['Rolling_Avg'].iloc[-1]:.1f}",
             f"  Season low (rolling): {df['Rolling_Avg'].min():.1f}",
             f"  Slope:                {np.polyfit(range(len(df)), df['Rolling_Avg'], 1)[0]:+.2f} strokes/round\n",
             "\nRecent:"]
    for _, row in df.tail(10).iterrows():
        lines.append(f"  {row['Date'].strftime('%Y-%m-%d')}  {row['Course']:<35}  {int(row['Score'])}  (rolling avg: {row['Rolling_Avg']:.1f})")
    return "\n".join(lines)


@mcp.tool()
def get_scoring_by_season() -> str:
    """
    Break down Tyler's scoring by season (spring/summer/fall/winter)
    and year-over-year to identify patterns.
    """
    df = tyler.dropna(subset=["Score"]).copy()
    df["Month"] = df["Date"].dt.month
    df["Year"]  = df["Date"].dt.year
    def season(m):
        if m in [3,4,5]:    return "spring"
        elif m in [6,7,8]:  return "summer"
        elif m in [9,10,11]:return "fall"
        else:               return "winter"
    df["Season"] = df["Month"].apply(season)
    lines = ["Scoring by season:\n"]
    for s, grp in df.groupby("Season"):
        lines.append(f"  {s.capitalize():<8}  n={len(grp)}  avg={grp['Score'].mean():.1f}  best={grp['Score'].min()}  worst={grp['Score'].max()}")
    lines.append("\nBy year:\n")
    for yr, grp in df.groupby("Year"):
        lines.append(f"  {yr}  n={len(grp)}  avg={grp['Score'].mean():.1f}  best={grp['Score'].min()}  worst={grp['Score'].max()}")
    return "\n".join(lines)


@mcp.tool()
def get_handicap_trend() -> str:
    """Get Tyler's handicap differentials over time."""
    df = tyler_hcap[["Date","Course","Differential"]].copy()
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    avg20 = tyler_hcap.tail(20)["Differential"].mean()
    return f"Estimated handicap index (avg of last 20): {avg20:.1f}\n\n" + df.to_string(index=False)


@mcp.tool()
def chart_handicap_trend() -> str:
    """Generate a chart of Tyler's handicap differential over time."""
    df = tyler_hcap.dropna(subset=["Differential"]).copy()
    rolling = df["Differential"].rolling(5, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(10, 4), facecolor="#1a1a2e")
    style_ax(ax, title="Tyler's Handicap Differential Trend", xlabel="Date", ylabel="Differential")
    ax.scatter(df["Date"], df["Differential"], color="#80deea", s=30, alpha=0.7, label="Each round")
    ax.plot(df["Date"], rolling, color="#ffb74d", linewidth=2, label="5-round rolling avg")
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.xticks(rotation=30)
    return f"Chart saved to: {save_chart(fig, 'handicap_trend')}"


@mcp.tool()
def get_front_vs_back_splits() -> str:
    """Compare Tyler's front 9 vs back 9 scoring."""
    df = tyler.dropna(subset=["Front 9","Back 9"])
    return (
        f"Front 9 avg: {df['Front 9'].mean():.1f}\n"
        f"Back 9 avg:  {df['Back 9'].mean():.1f}\n"
        f"Front better: {(df['Front 9'] < df['Back 9']).sum()} rounds\n"
        f"Back better:  {(df['Back 9'] < df['Front 9']).sum()} rounds"
    )


# ══════════════════════════════════════════════════════════════════════════════
# RANGE — TRACKMAN SHOT DATA
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_range_stats_summary(club: str = "") -> str:
    """
    Get shot stats from Tyler's Trackman range sessions.
    Pass a club (e.g. 'd', '7i', 'pw', 'sw', 'lw') or leave blank for all clubs.
    Returns carry distance, ball speed, launch angle, smash factor, club speed stats.
    """
    df = tyler_range.copy()
    if club:
        df = df[df["Club Type"].str.lower() == club.lower()]
        if df.empty:
            return f"No data for '{club}'. Available: {tyler_range['Club Type'].unique().tolist()}"
    avail = [c for c in TRACKMAN_COLS if c in df.columns]
    summary = df.groupby("Club Type")[avail].agg(["mean","std","min","max","count"]).round(2)
    lines = [f"Range Stats — {'  ' + club.upper() if club else 'All Clubs'}:\n"]
    for col in avail:
        sub = summary[col].dropna(how="all")
        lines.append(f"\n{col}:")
        for club_name, row in sub.iterrows():
            lines.append(
                f"  {club_name:<8}  avg={row['mean']:.1f}  std={row['std']:.1f}  "
                f"min={row['min']:.1f}  max={row['max']:.1f}  n={int(row['count'])}"
            )
    return "\n".join(lines)


@mcp.tool()
def get_range_stats_percentiles(club: str) -> str:
    """
    Full percentile breakdown (P10, P25, P50, P75, P90) for all Trackman metrics
    for a specific club. More informative than avg/std — shows the true distribution
    of carry, smash factor, ball speed, launch angle, etc.
    """
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].copy()
    if df.empty:
        return f"No data for '{club}'. Available: {tyler_range['Club Type'].unique().tolist()}"
    avail = [c for c in TRACKMAN_COLS if c in df.columns]
    pcts = [10, 25, 50, 75, 90]
    lines = [f"Percentile breakdown — {club.upper()} ({len(df)} shots):\n",
             f"{'Metric':<20} {'P10':>7} {'P25 (Q1)':>10} {'P50 (med)':>11} {'P75 (Q3)':>10} {'P90':>7} {'Mean':>8} {'Std':>7}"]
    lines.append("-" * 80)
    for col in avail:
        vals = df[col].dropna()
        if len(vals) < 3:
            continue
        ps = np.percentile(vals, pcts)
        lines.append(
            f"  {col:<18} {ps[0]:>7.1f} {ps[1]:>10.1f} {ps[2]:>11.1f} {ps[3]:>10.1f} {ps[4]:>7.1f} {vals.mean():>8.2f} {vals.std():>7.2f}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_smash_factor_deep(club: str) -> str:
    """
    Deep smash factor analysis for a single club: percentiles, Q3 (peak contact),
    session-by-session Q3 trend, and gap to tour/elite benchmarks.
    Q3 estimated as avg + 0.6745*std per session (normal approximation).
    Club options: d, 3w, 3h, 5i, 6i, 7i, 8i, 9i, pw, gw, sw, lw
    """
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].dropna(subset=["Smash Factor"]).copy()
    if df.empty:
        return f"No smash factor data for '{club}'."
    sf   = df["Smash Factor"]
    pcts = np.percentile(sf, [10, 25, 50, 75, 90])
    benchmarks = {
        "d":  (1.44,1.48),"3w":(1.42,1.45),"3h":(1.40,1.43),
        "5i": (1.38,1.41),"6i":(1.37,1.40),"7i":(1.36,1.39),
        "8i": (1.34,1.37),"9i":(1.32,1.35),"pw":(1.28,1.32),
        "gw": (1.24,1.28),"sw":(1.20,1.24),"lw":(1.18,1.22),
    }
    tour_avg, elite = benchmarks.get(club.lower(), (1.30, 1.35))
    session = df.groupby("Date")["Smash Factor"].agg(["mean","std","count"]).dropna(subset=["std"])
    session["Q3"] = session["mean"] + 0.6745 * session["std"]
    session.index = session.index.strftime("%Y-%m-%d")
    career_q3 = (session["Q3"] * session["count"]).sum() / session["count"].sum()
    peak_q3   = session["Q3"].nlargest(3).mean()
    lines = [
        f"Smash Factor Analysis — {club.upper()} ({len(sf)} shots)\n",
        f"Percentiles:",
        f"  P10={pcts[0]:.3f}  P25={pcts[1]:.3f}  Median={pcts[2]:.3f}  P75={pcts[3]:.3f}  P90={pcts[4]:.3f}",
        f"\nContact quality (Q3 = top-25% contact per session):",
        f"  Career Q3 avg:             {career_q3:.3f}",
        f"  Peak Q3 avg (top 3 sessions): {peak_q3:.3f}",
        f"  Tour avg benchmark:        {tour_avg:.2f}",
        f"  Elite benchmark:           {elite:.2f}",
        f"  Gap to tour avg:           {career_q3 - tour_avg:+.3f}",
        f"  Gap to elite:              {career_q3 - elite:+.3f}",
        f"\nSession Q3 (most recent first):",
        f"  {'Date':<12} {'Avg SF':>8} {'Std':>7} {'Q3':>8} {'n':>5}"
    ]
    lines.append("  " + "-" * 42)
    for date, row in session.sort_index(ascending=False).iterrows():
        lines.append(f"  {date:<12} {row['mean']:>8.3f} {row['std']:>7.3f} {row['Q3']:>8.3f} {int(row['count']):>5}")
    return "\n".join(lines)


@mcp.tool()
def get_range_session_dates() -> str:
    """List all of Tyler's range session dates and which clubs were hit each session."""
    df = tyler_range.copy()
    df["Date_str"] = df["Date"].dt.strftime("%Y-%m-%d")
    sessions = df.groupby("Date_str")["Club Type"].apply(lambda x: ", ".join(sorted(x.unique())))
    shots = df.groupby("Date_str").size()
    result = pd.DataFrame({"Clubs Hit": sessions, "Total Shots": shots})
    return f"Range sessions ({len(result)} total):\n\n" + result.to_string()


@mcp.tool()
def compare_range_sessions(club: str, stat: str = "Carry Distance") -> str:
    """
    Compare Tyler's stats for a club across different range session dates.
    stat options: Carry Distance, Ball Speed, Smash Factor, Launch Angle, Club Speed, Side Carry
    """
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].dropna(subset=[stat]).copy()
    if df.empty:
        return f"No data for {club}."
    session = df.groupby("Date")[stat].agg(["mean","std","count"]).round(2)
    session.index = session.index.strftime("%Y-%m-%d")
    session.columns = [f"Avg {stat}", "Std Dev", "Shots"]
    return f"{club.upper()} — {stat} by session:\n\n" + session.to_string()


@mcp.tool()
def get_session_comparison(date1: str, date2: str = "") -> str:
    """
    Compare two specific range sessions head-to-head across all clubs and key metrics.
    date1 format: YYYY-MM-DD. Leave date2 blank to compare vs all other sessions combined.
    """
    df = tyler_range.copy()
    df["Date_str"] = df["Date"].dt.strftime("%Y-%m-%d")
    s1 = df[df["Date_str"] == date1]
    if s1.empty:
        return f"No session for {date1}. Available: {sorted(df['Date_str'].unique())}"
    s2 = df[df["Date_str"] != date1] if not date2 else df[df["Date_str"] == date2]
    label2 = date2 if date2 else "all other sessions"
    metrics = [m for m in ["Carry Distance","Ball Speed","Smash Factor","Side Carry"] if m in df.columns]
    lines = [f"Session comparison: {date1} vs {label2}\n",
             f"{'Club':<8}" + "".join(f"  {m[:12]:>14}" for m in metrics)]
    lines.append("-" * (8 + 16 * len(metrics)))
    for club_name in sorted(s1["Club Type"].unique()):
        c1 = s1[s1["Club Type"] == club_name]
        c2 = s2[s2["Club Type"] == club_name]
        if c2.empty: continue
        row_parts = [f"{club_name:<8}"]
        for m in metrics:
            v1, v2 = c1[m].mean(), c2[m].mean()
            delta = v1 - v2
            row_parts.append(f"  {v1:>6.2f} ({'+' if delta>=0 else ''}{delta:.2f})")
        lines.append("".join(row_parts))
    return "\n".join(lines)


@mcp.tool()
def get_peak_session_stats(club: str = "", top_n: int = 3) -> str:
    """
    Find Tyler's top N range sessions ranked by Q3 smash factor and carry distance.
    Useful for identifying what a great session looks like.
    Leave club blank to rank across all clubs.
    """
    df = tyler_range.dropna(subset=["Smash Factor","Carry Distance"]).copy()
    if club:
        df = df[df["Club Type"].str.lower() == club.lower()]
    session = df.groupby(["Date","Club Type"]).agg(
        avg_carry=("Carry Distance","mean"),
        avg_sf=("Smash Factor","mean"),
        std_sf=("Smash Factor","std"),
        avg_ball_speed=("Ball Speed","mean"),
        n=("Smash Factor","count")
    ).reset_index()
    session["Q3_sf"] = session["avg_sf"] + 0.6745 * session["std_sf"].fillna(0)
    session["Date_str"] = session["Date"].dt.strftime("%Y-%m-%d")
    lines = [f"Top {top_n} sessions by Q3 smash" + (f" — {club.upper()}" if club else " (all clubs)") + ":\n",
             f"{'Date':<12} {'Club':<8} {'Q3 SF':>8} {'Avg SF':>8} {'Avg Carry':>10} {'Ball Spd':>9} {'n':>4}"]
    lines.append("-" * 60)
    for _, row in session.nlargest(top_n, "Q3_sf").iterrows():
        lines.append(f"  {row['Date_str']:<12} {row['Club Type']:<8} {row['Q3_sf']:>8.3f} {row['avg_sf']:>8.3f} "
                     f"{row['avg_carry']:>10.1f} {row['avg_ball_speed']:>9.1f} {int(row['n']):>4}")
    lines.append(f"\nTop {top_n} sessions by carry" + (f" — {club.upper()}" if club else "") + ":\n")
    lines.append(f"{'Date':<12} {'Club':<8} {'Avg Carry':>10} {'Q3 SF':>8} {'n':>4}")
    lines.append("-" * 46)
    for _, row in session.nlargest(top_n, "avg_carry").iterrows():
        lines.append(f"  {row['Date_str']:<12} {row['Club Type']:<8} {row['avg_carry']:>10.1f} "
                     f"{row['Q3_sf']:>8.3f} {int(row['n']):>4}")
    return "\n".join(lines)


@mcp.tool()
def get_carry_percentiles_all_clubs() -> str:
    """
    Carry distance percentiles (P25, P50, P75, P90) for every club in the bag.
    More useful than avg+std for course management — P25 is your safe/conservative
    carry, P90 is your flush ceiling.
    """
    df = tyler_range.dropna(subset=["Carry Distance"]).copy()
    present = [c for c in CLUB_ORDER if c in df["Club Type"].values]
    lines = ["Carry distance percentiles (yards) — all clubs:\n",
             f"{'Club':<10} {'P25 (safe)':>11} {'P50 (median)':>13} {'P75':>6} {'P90 (flush)':>12} {'Max':>6} {'n':>4}"]
    lines.append("-" * 68)
    for c in present:
        vals = df[df["Club Type"] == c]["Carry Distance"].dropna()
        ps = np.percentile(vals, [25, 50, 75, 90])
        lines.append(f"  {c:<10} {ps[0]:>11.1f} {ps[1]:>13.1f} {ps[2]:>6.1f} {ps[3]:>12.1f} {vals.max():>6.1f} {len(vals):>4}")
    lines.append("\nUse P25 for safe layups / hazard clearances. P90 for max distance estimates.")
    return "\n".join(lines)


@mcp.tool()
def get_dispersion_analysis(club: str = "") -> str:
    """
    Full dispersion (accuracy) analysis: side carry mean, std, left/right bias,
    and % of shots within 10 / 20 / 30 ft of center.
    Leave club blank to rank all clubs by dispersion tightness.
    """
    df = tyler_range.dropna(subset=["Side Carry"]).copy()
    if club:
        df = df[df["Club Type"].str.lower() == club.lower()]
        if df.empty:
            return f"No data for '{club}'."
    present = [c for c in CLUB_ORDER if c in df["Club Type"].values]
    lines = ["Dispersion analysis (Side Carry, feet):\n",
             f"{'Club':<10} {'Avg Miss':>9} {'Std':>6} {'Bias':>7} {'±10ft':>7} {'±20ft':>7} {'±30ft':>7} {'n':>5}"]
    lines.append("-" * 66)
    for c in (present if not club else [club.lower()]):
        vals = df[df["Club Type"] == c]["Side Carry"].dropna()
        if len(vals) < 3: continue
        avg_miss = vals.abs().mean()
        std_val  = vals.std()
        bias_dir = "R" if vals.mean() > 0 else "L"
        bias_amt = abs(vals.mean())
        p10 = (vals.abs() <= 10).mean() * 100
        p20 = (vals.abs() <= 20).mean() * 100
        p30 = (vals.abs() <= 30).mean() * 100
        lines.append(f"  {c:<10} {avg_miss:>9.1f} {std_val:>6.1f} {bias_dir}{bias_amt:>5.1f} "
                     f"{p10:>6.0f}% {p20:>6.0f}% {p30:>6.0f}% {len(vals):>5}")
    return "\n".join(lines)


@mcp.tool()
def get_stat_trend_regression(club: str, stat: str = "Smash Factor") -> str:
    """
    Linear regression of a Trackman stat over time for a specific club.
    Returns slope, R-squared, p-value, and whether the trend is statistically significant.
    Use this to confirm whether improvement or decline is real vs noise.
    stat options: Carry Distance, Ball Speed, Smash Factor, Launch Angle, Club Speed, Side Carry
    """
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].dropna(subset=["Date", stat]).copy()
    if df.empty:
        return f"No data for {club}/{stat}."
    session = df.groupby("Date")[stat].mean().reset_index()
    if len(session) < 4:
        return f"Need at least 4 sessions for regression. Only {len(session)} found for {club}."
    x = np.arange(len(session))
    y = session[stat].values
    slope, intercept, r, p, se = scipy_stats.linregress(x, y)
    direction = "improving" if slope > 0 else "declining"
    sig = "significant" if p < 0.05 else "not significant"
    lines = [
        f"Regression: {club.upper()} — {stat}\n",
        f"  Slope:       {slope:+.4f} per session",
        f"  R-squared:   {r**2:.3f}  ({r**2*100:.1f}% of variance explained)",
        f"  p-value:     {p:.4f}  ({sig} at alpha=0.05)",
        f"  Direction:   {direction}",
        f"  First session avg: {y[0]:.3f}  ({session['Date'].iloc[0].strftime('%Y-%m-%d')})",
        f"  Last session avg:  {y[-1]:.3f}  ({session['Date'].iloc[-1].strftime('%Y-%m-%d')})",
        f"  Net change:        {y[-1]-y[0]:+.3f}",
    ]
    if p < 0.05:
        lines.append(f"\nTrend is statistically significant — the change is likely real.")
    else:
        lines.append(f"\nTrend is NOT statistically significant across {len(session)} sessions — may be noise.")
    return "\n".join(lines)


@mcp.tool()
def compare_clubs_head_to_head(club1: str, club2: str, stat: str = "Carry Distance") -> str:
    """
    Statistical t-test comparison between two clubs for a given stat.
    Also returns Cohen's d effect size.
    stat options: Carry Distance, Ball Speed, Smash Factor, Launch Angle, Club Speed, Side Carry
    """
    df = tyler_range.copy()
    a = df[df["Club Type"].str.lower() == club1.lower()][stat].dropna()
    b = df[df["Club Type"].str.lower() == club2.lower()][stat].dropna()
    if len(a) < 3 or len(b) < 3:
        return f"Insufficient data. {club1}: {len(a)} shots, {club2}: {len(b)} shots."
    t, p = scipy_stats.ttest_ind(a, b, equal_var=False)
    cohens_d = (a.mean() - b.mean()) / np.sqrt((a.std()**2 + b.std()**2) / 2)
    lines = [
        f"Head-to-head: {club1.upper()} vs {club2.upper()} — {stat}\n",
        f"  {club1.upper():<8}  avg={a.mean():.2f}  std={a.std():.2f}  n={len(a)}",
        f"  {club2.upper():<8}  avg={b.mean():.2f}  std={b.std():.2f}  n={len(b)}",
        f"\n  Difference:   {a.mean()-b.mean():+.2f}",
        f"  t-statistic:  {t:.3f}",
        f"  p-value:      {p:.4f}",
        f"  Cohen's d:    {cohens_d:.2f}  ({'large' if abs(cohens_d)>0.8 else 'medium' if abs(cohens_d)>0.5 else 'small'} effect)",
        f"  Significant:  {'Yes (p < 0.05)' if p < 0.05 else 'No (p >= 0.05)'}",
    ]
    return "\n".join(lines)


@mcp.tool()
def get_launch_efficiency_report() -> str:
    """
    For every club, actual vs ideal launch angle and smash factor gap to tour benchmarks.
    Flags clubs launching too high, too low, or with poor contact efficiency.
    """
    ideals_la  = {"d":13,"3w":14,"3h":16,"4i":17,"5i":19,"6i":21,
                  "7i":23,"8i":25,"9i":27,"pw":29,"gw":32,"sw":35,"lw":38}
    ideals_sf  = {"d":1.48,"3w":1.45,"3h":1.43,"4i":1.41,"5i":1.40,
                  "6i":1.39,"7i":1.38,"8i":1.36,"9i":1.34,"pw":1.30,
                  "gw":1.27,"sw":1.24,"lw":1.22}
    df = tyler_range.dropna(subset=["Launch Angle","Smash Factor"]).copy()
    present = [c for c in ideals_la if c in df["Club Type"].values]
    lines = ["Launch efficiency report:\n",
             f"{'Club':<7} {'Actual LA':>10} {'Ideal LA':>9} {'LA Delta':>9} {'Actual SF':>10} {'Ideal SF':>9} {'SF Delta':>9}"]
    lines.append("-" * 68)
    for c in present:
        sub = df[df["Club Type"] == c]
        avg_la = sub["Launch Angle"].mean()
        avg_sf = sub["Smash Factor"].mean()
        la_d = avg_la - ideals_la[c]
        sf_d = avg_sf - ideals_sf[c]
        la_flag = " high" if la_d > 3 else (" low" if la_d < -3 else " ok")
        lines.append(f"  {c:<7} {avg_la:>10.1f} {ideals_la[c]:>8}  {la_d:>+8.1f} {la_flag:<6}"
                     f"{avg_sf:>10.3f} {ideals_sf[c]:>9.2f} {sf_d:>+9.3f}")
    return "\n".join(lines)


@mcp.tool()
def get_club_consistency(club: str) -> str:
    """Analyze how consistent Tyler is with a specific club."""
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].copy()
    if df.empty:
        return f"No data for '{club}'. Available: {tyler_range['Club Type'].unique().tolist()}"
    carry = df["Carry Distance"].dropna()
    side  = df["Side Carry"].dropna()
    smash = df["Smash Factor"].dropna()
    cv = (carry.std() / carry.mean() * 100) if carry.mean() > 0 else 0
    lines = [
        f"Consistency Report — {club.upper()} ({len(df)} shots)\n",
        f"Carry Distance:",
        f"  Average:   {carry.mean():.1f} yds",
        f"  Std Dev:   {carry.std():.1f} yds  (lower = more consistent)",
        f"  Variation: {cv:.1f}%  (tour avg ~5-7%)",
        f"  Range:     {carry.min():.0f} - {carry.max():.0f} yds",
        f"\nAccuracy (Side Carry):",
        f"  Avg miss:  {side.abs().mean():.1f} yds",
        f"  Miss bias: {'Right' if side.mean() > 0 else 'Left'} ({abs(side.mean()):.1f} yds avg)",
    ]
    if not smash.empty:
        lines += [f"\nSmash Factor:",
                  f"  Average:  {smash.mean():.3f}",
                  f"  Best:     {smash.max():.3f}"]
    if "Launch Angle" in df.columns:
        la = df["Launch Angle"].dropna()
        lines.append(f"\nLaunch Angle: avg {la.mean():.1f} deg  ({la.min():.1f} - {la.max():.1f})")
    if "Club Speed" in df.columns:
        cs = df["Club Speed"].dropna()
        lines.append(f"Club Speed:   avg {cs.mean():.1f} mph  ({cs.min():.1f} - {cs.max():.1f})")
    return "\n".join(lines)


@mcp.tool()
def get_club_distance_gaps() -> str:
    """Identify distance gaps or overlaps in Tyler's bag using Trackman data."""
    rs = tyler_range.groupby("Club Type")["Carry Distance"].agg(["mean","std"]).reset_index()
    rs.columns = ["Club","Avg","Std"]
    rs["Low"]  = rs["Avg"] - rs["Std"]
    rs["High"] = rs["Avg"] + rs["Std"]
    rs["order"] = rs["Club"].map({c: i for i, c in enumerate(CLUB_ORDER)})
    rs = rs.sort_values("order").dropna(subset=["order"]).reset_index(drop=True)
    lines = ["Distance gap analysis (Trackman):\n",
             f"{'Club':<8} {'Avg':>6} {'+-1SD Range':>16} {'Gap to Next':>14}"]
    lines.append("-" * 50)
    for i, row in rs.iterrows():
        if i < len(rs) - 1:
            nxt = rs.iloc[i + 1]
            gap = nxt["Low"] - row["High"]
            gap_str = f"{gap:+.0f} yds"
            flag = "  GAP" if gap > 5 else ("  OVERLAP" if gap < -10 else "")
        else:
            gap_str, flag = "--", ""
        lines.append(f"{row['Club']:<8} {row['Avg']:>6.1f} {row['Low']:>6.0f}-{row['High']:<8.0f} {gap_str}{flag}")
    return "\n".join(lines)


@mcp.tool()
def get_club_for_distance(distance: int) -> str:
    """Recommend the best club for a given target carry distance in yards."""
    sel = club_sel.copy()
    sel["BinMin"] = sel["DistanceBin"].str.split("-").str[0].astype(int)
    sel["BinMax"] = sel["DistanceBin"].str.split("-").str[1].astype(int)
    match = sel[(sel["BinMin"] <= distance) & (sel["BinMax"] >= distance)]
    rs_avgs = tyler_range.groupby("Club Type")["Carry Distance"].mean()
    closest = (rs_avgs - distance).abs().nsmallest(3)
    lines = [f"Club recommendation for {distance} yards carry:\n"]
    if not match.empty:
        r = match.iloc[0]
        lines += [f"Best match (shot history): {r['Club'].upper()}",
                  f"  Top-25% carry: {r['Top25Carry']} yds  |  {r['ShotCount']} shots recorded\n"]
    lines.append("From Trackman session averages (closest clubs):")
    for cname, diff in closest.items():
        lines.append(f"  {cname.upper():<6}  avg carry {rs_avgs[cname]:.1f} yds  (diff: {diff:+.1f})")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# STROKES GAINED
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_strokes_gained_summary(last_n_rounds: int = 10) -> str:
    """Get Tyler's strokes gained breakdown vs scratch golfer."""
    recent = tyler_sg.tail(last_n_rounds)
    avgs = recent[["SG_Total","SG_T2G","SG_OTT","SG_Approach","SG_ARG","SG_Putting"]].mean()
    labels = {"SG_Total":"Total","SG_Putting":"Putting","SG_T2G":"Tee-to-Green",
              "SG_OTT":"Off the Tee","SG_Approach":"Approach","SG_ARG":"Around the Green"}
    lines = [f"Strokes Gained (last {last_n_rounds} rounds vs scratch):"]
    for col, label in labels.items():
        lines.append(f"  {label:<22} {avgs[col]:+.2f}")
    lines.append(f"\nBiggest weakness: {labels[min(labels, key=lambda c: avgs[c])]} ({min(avgs.values()):+.2f})")
    return "\n".join(lines)


@mcp.tool()
def get_strokes_gained_by_round() -> str:
    """Full round-by-round strokes gained table — every round, every SG category."""
    df = tyler_sg.copy()
    cols = ["Date","Course","SG_Total","SG_OTT","SG_Approach","SG_ARG","SG_Putting"]
    avail = [c for c in cols if c in df.columns]
    df2 = df[avail].copy()
    df2["Date"] = df2["Date"].dt.strftime("%Y-%m-%d")
    return df2.to_string(index=False)


@mcp.tool()
def get_strokes_gained_rolling(window: int = 5) -> str:
    """
    Rolling N-round strokes gained averages to reveal momentum in each SG category.
    Identifies if recent SG trends differ from career baseline.
    """
    df = tyler_sg.copy()
    sg_cols = ["SG_OTT","SG_Approach","SG_ARG","SG_Putting","SG_Total"]
    avail = [c for c in sg_cols if c in df.columns]
    for col in avail:
        df[f"Roll_{col}"] = df[col].rolling(window, min_periods=1).mean()
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    lines = [f"Rolling {window}-round SG averages:\n",
             f"{'Date':<12} {'OTT':>7} {'App':>7} {'ARG':>7} {'Putt':>7} {'Total':>8}"]
    lines.append("-" * 50)
    for _, row in df.tail(10).iterrows():
        lines.append(
            f"  {row['Date']:<12} {row.get('Roll_SG_OTT',float('nan')):>+7.2f} "
            f"{row.get('Roll_SG_Approach',float('nan')):>+7.2f} "
            f"{row.get('Roll_SG_ARG',float('nan')):>+7.2f} "
            f"{row.get('Roll_SG_Putting',float('nan')):>+7.2f} "
            f"{row.get('Roll_SG_Total',float('nan')):>+8.2f}"
        )
    return "\n".join(lines)


@mcp.tool()
def chart_strokes_gained_trend() -> str:
    """Chart how Tyler's strokes gained categories have changed over time."""
    df = tyler_sg.copy()
    sg_cols = {"SG_Putting":"Putting","SG_OTT":"Off Tee","SG_Approach":"Approach","SG_ARG":"ARG"}
    colors = ["#4fc3f7","#ffb74d","#a5d6a7","#ef9a9a"]
    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#1a1a2e")
    style_ax(ax, title="Strokes Gained Trends Over Time", xlabel="Date", ylabel="SG per Round")
    for (col, label), color in zip(sg_cols.items(), colors):
        ax.plot(df["Date"], df[col], marker="o", markersize=4, linewidth=1.5,
                label=label, color=color, alpha=0.85)
    ax.axhline(0, color="#555577", linewidth=1, linestyle="--")
    ax.legend(facecolor="#16213e", labelcolor="#cccccc", ncol=2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.xticks(rotation=30)
    return f"Chart saved to: {save_chart(fig, 'sg_trend')}"


@mcp.tool()
def chart_strokes_gained_radar() -> str:
    """Radar chart of Tyler's strokes gained profile across all categories."""
    recent = tyler_sg.tail(10)
    cats   = ["SG_OTT","SG_Approach","SG_ARG","SG_Putting"]
    labels = ["Off Tee","Approach","Around Green","Putting"]
    vals   = [recent[c].mean() for c in cats]
    min_v, max_v = min(vals) - 0.5, max(vals) + 0.5
    norm = [(v - min_v) / (max_v - min_v) for v in vals]
    norm += norm[:1]
    angles = np.linspace(0, 2*np.pi, len(cats), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True), facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.plot(angles, norm, color="#4fc3f7", linewidth=2)
    ax.fill(angles, norm, color="#4fc3f7", alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([f"{l}\n({v:+.2f})" for l, v in zip(labels, vals)],
                       color="#cccccc", size=10)
    ax.set_yticklabels([])
    ax.set_title("SG Profile (last 10 rounds)", color="#ffffff", pad=20, fontsize=12)
    ax.grid(color="#2a2a4a")
    return f"Chart saved to: {save_chart(fig, 'sg_radar')}"


# ══════════════════════════════════════════════════════════════════════════════
# PUTTING
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_putting_analysis() -> str:
    """
    Deep putting analysis: make% by distance band, avg putts per round,
    and putting vs scoring correlation.
    """
    df = tyler_putts.copy()
    lines = ["Putting Analysis:\n"]
    if not df.empty and "Distance" in df.columns and "Made" in df.columns:
        bins = [(0,3),(3,6),(6,10),(10,15),(15,20),(20,30),(30,100)]
        lines.append("Make% by distance:")
        for lo, hi in bins:
            band = df[(df["Distance"] >= lo) & (df["Distance"] < hi)]
            if band.empty: continue
            lines.append(f"  {lo:>3}-{hi:<3} ft   {band['Made'].mean()*100:>5.1f}%   ({len(band)} putts)")
    round_putts = tyler.dropna(subset=["Putts"])
    if not round_putts.empty:
        corr = round_putts[["Putts","Score"]].corr().iloc[0,1]
        lines += [f"\nFrom round data:",
                  f"  Avg putts/round:  {round_putts['Putts'].mean():.1f}",
                  f"  Best round:       {round_putts['Putts'].min():.0f}",
                  f"  Worst round:      {round_putts['Putts'].max():.0f}",
                  f"  Corr with score:  {corr:+.2f}  (explains {corr**2*100:.0f}% of score variance)"]
    return "\n".join(lines)


@mcp.tool()
def get_putting_trends() -> str:
    """
    Putts per round over time with rolling average and trend direction.
    """
    df = tyler.dropna(subset=["Putts","Date"]).copy()
    df["Roll5"] = df["Putts"].rolling(5, min_periods=1).mean()
    slope = np.polyfit(range(len(df)), df["Putts"], 1)[0]
    lines = ["Putting trend (putts per round):\n",
             f"  Career avg: {df['Putts'].mean():.1f}",
             f"  Last 5 rounds avg: {df['Putts'].tail(5).mean():.1f}",
             f"  Trend slope: {slope:+.2f} putts/round ({'improving' if slope < 0 else 'worsening'})\n",
             f"{'Date':<12} {'Course':<35} {'Putts':>6} {'Rolling Avg':>12}"]
    lines.append("-" * 68)
    for _, row in df.tail(15).iterrows():
        lines.append(f"  {row['Date'].strftime('%Y-%m-%d'):<12} {row['Course']:<35} {int(row['Putts']):>6} {row['Roll5']:>12.1f}")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# COURSE & SITUATIONAL
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_course_breakdown(course_name: str = "") -> str:
    """Get Tyler's performance breakdown by course."""
    df = tyler.copy()
    if course_name:
        df = df[df["Course"].str.contains(course_name, case=False)]
    summary = df.groupby("Course").agg(
        Rounds=("Score","count"), Avg=("Score","mean"), Best=("Score","min"),
        Avg_Putts=("Putts","mean"), Avg_FW=("Fairways","mean"), Avg_GIR=("Greens","mean")
    ).round(1)
    return summary.to_string()


@mcp.tool()
def get_course_improvement(course_name: str) -> str:
    """
    Round-by-round history at a specific course with delta vs course average.
    Shows whether Tyler is improving there over time with a trend line.
    """
    df = tyler[tyler["Course"].str.contains(course_name, case=False)].copy()
    if df.empty:
        return f"No rounds found matching '{course_name}'."
    course_avg = df["Score"].mean()
    df["vs_avg"]  = df["Score"] - course_avg
    df["Date_str"] = df["Date"].dt.strftime("%Y-%m-%d")
    lines = [f"Course history — {df['Course'].iloc[0]}\n",
             f"  Course avg: {course_avg:.1f}  ({len(df)} rounds)\n",
             f"{'Date':<12} {'Score':>6} {'vs Avg':>8} {'Putts':>7} {'GIR':>6}"]
    lines.append("-" * 42)
    for _, row in df.iterrows():
        lines.append(
            f"  {row['Date_str']:<12} {int(row['Score']):>6} {row['vs_avg']:>+8.0f} "
            f"{int(row['Putts']) if pd.notna(row.get('Putts')) else '--':>7} "
            f"{int(row['Greens']) if pd.notna(row.get('Greens')) else '--':>6}"
        )
    if len(df) >= 3:
        slope = np.polyfit(range(len(df)), df["Score"], 1)[0]
        lines.append(f"\n  Score trend: {slope:+.2f} strokes/round ({'improving' if slope < 0 else 'worsening'})")
    return "\n".join(lines)


@mcp.tool()
def get_gir_and_fairway_analysis() -> str:
    """
    GIR and fairway hit rates by year, scoring when hitting vs missing GIR,
    and correlation of each with total score.
    """
    df = tyler.dropna(subset=["Greens","Fairways","Score"]).copy()
    df["Year"]    = df["Date"].dt.year
    df["GIR_pct"] = df["Greens"] / 18 * 100
    df["FW_pct"]  = df["Fairways"] / 14 * 100
    hi = df[df["Greens"] >= 6]["Score"].mean()
    lo = df[df["Greens"] < 6]["Score"].mean()
    lines = [
        "GIR and Fairway Analysis:\n",
        f"  Career GIR avg:      {df['GIR_pct'].mean():.1f}%  ({df['Greens'].mean():.1f}/18)",
        f"  Career Fairway avg:  {df['FW_pct'].mean():.1f}%  ({df['Fairways'].mean():.1f}/14)",
        f"  GIR corr with score: {df[['GIR_pct','Score']].corr().iloc[0,1]:+.2f}",
        f"  FW  corr with score: {df[['FW_pct','Score']].corr().iloc[0,1]:+.2f}",
        f"\n  Avg score with >=6 GIR: {hi:.1f}",
        f"  Avg score with  <6 GIR: {lo:.1f}  (delta: {hi-lo:+.1f})",
        "\nBy year:",
    ]
    for yr, grp in df.groupby("Year"):
        lines.append(f"  {yr}  GIR={grp['GIR_pct'].mean():.1f}%  FW={grp['FW_pct'].mean():.1f}%  avg={grp['Score'].mean():.1f}")
    return "\n".join(lines)


@mcp.tool()
def get_hole_recommendations(course_name: str, tees: str = "") -> str:
    """Get hole-by-hole strategy recommendations for a specific course."""
    df = recs_df[recs_df["Course"].str.contains(course_name, case=False)]
    if tees:
        df = df[df["Tees"].str.lower() == tees.lower()]
    if df.empty:
        return "No data. Available courses:\n" + "\n".join(recs_df["Course"].unique())
    cols = ["Hole","Tees","Yardage","Par","Recommendation","Tee Recommendation","Approach Recommendation"]
    return df[cols].to_string(index=False)


@mcp.tool()
def get_clutch_analysis() -> str:
    """Analyze how Tyler finishes rounds vs how he starts."""
    df = tyler_clutch.copy()
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    counts = df["ClutchLabel"].value_counts()
    lines = ["Tyler's finish tendencies:"]
    for label, count in counts.items():
        lines.append(f"  {label:<20} {count} rounds ({count/len(df)*100:.0f}%)")
    lines.append(f"\nAvg trend slope: {df['Score_Trend_Slope'].mean():+.3f}  (negative = improving through round)")
    lines.append("\n" + df[["Date","Course","ClutchLabel","Score_Trend_Slope"]].to_string(index=False))
    return "\n".join(lines)


@mcp.tool()
def get_stat_correlations() -> str:
    """Show which stats correlate most strongly with Tyler's score."""
    df = tyler.dropna(subset=["Putts","Fairways","Greens","Score"])
    corr = df[["Score","Putts","Fairways","Greens","Birdies","Bogeys","Double Bogeys"]].corr()["Score"]
    corr = corr.drop("Score").sort_values(ascending=False)
    lines = ["Correlation with score (positive = raises score = hurts you):"]
    for stat, val in corr.items():
        lines.append(f"  {stat:<20} {val:+.2f}")
    return "\n".join(lines)


@mcp.tool()
def compare_with_partner(partner: str = "Rich") -> str:
    """Compare Tyler head-to-head with a playing partner on shared rounds."""
    p = rounds_df[rounds_df["Golfer"] == partner].copy()
    merged = tyler.merge(p, on=["Date","Course"], suffixes=("_Tyler", f"_{partner}"))
    if merged.empty:
        return f"No shared rounds with {partner}. Partners: {rounds_df['Golfer'].unique().tolist()}"
    rows = merged[["Date","Course","Score_Tyler",f"Score_{partner}"]].copy()
    rows["Date"] = rows["Date"].dt.strftime("%Y-%m-%d")
    return (
        f"Tyler vs {partner} — {len(merged)} rounds\n"
        f"Tyler win rate: {merged['Score_Tyler'].lt(merged[f'Score_{partner}']).mean():.0%}\n"
        f"Avg score diff: {(merged['Score_Tyler'] - merged[f'Score_{partner}']).mean():+.1f}\n\n"
        + rows.to_string(index=False)
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def chart_club_carry_distribution(club: str) -> str:
    """Histogram of carry distance with P25/P75 markers for a specific club."""
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].copy()
    if df.empty:
        return f"No range data for '{club}'."
    carry = df["Carry Distance"].dropna()
    fig, ax = plt.subplots(figsize=(8, 4), facecolor="#1a1a2e")
    style_ax(ax, title=f"{club.upper()} Carry Distribution ({len(carry)} shots)",
             xlabel="Carry Distance (yds)", ylabel="Frequency")
    ax.hist(carry, bins=20, color="#4fc3f7", edgecolor="#1a1a2e", alpha=0.85)
    ax.axvline(carry.mean(), color="#ffb74d", linewidth=2, linestyle="--",
               label=f"Avg: {carry.mean():.1f} yds")
    ax.axvline(np.percentile(carry, 25), color="#a5d6a7", linewidth=1.5, linestyle=":",
               label=f"P25: {np.percentile(carry, 25):.0f} yds")
    ax.axvline(np.percentile(carry, 75), color="#ef9a9a", linewidth=1.5, linestyle=":",
               label=f"P75: {np.percentile(carry, 75):.0f} yds")
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    return f"Chart saved to: {save_chart(fig, f'carry_dist_{club}')}"


@mcp.tool()
def chart_club_stats_over_time(club: str, stat: str = "Carry Distance") -> str:
    """
    Chart how a club stat has changed across range sessions over time, with SD band.
    stat options: Carry Distance, Ball Speed, Smash Factor, Launch Angle,
                  Club Speed, Side Carry, Apex, Descent Angle
    """
    valid = ["Carry Distance","Ball Speed","Smash Factor","Launch Angle",
             "Club Speed","Side Carry","Apex","Descent Angle"]
    if stat not in valid:
        return f"Invalid stat. Choose from: {valid}"
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].dropna(subset=["Date", stat]).copy()
    if df.empty:
        return f"No data for {club}/{stat}."
    session = df.groupby("Date")[stat].agg(["mean","std"]).reset_index()
    fig, ax = plt.subplots(figsize=(10, 4), facecolor="#1a1a2e")
    style_ax(ax, title=f"{club.upper()} -- {stat} Over Time", xlabel="Date", ylabel=stat)
    ax.plot(session["Date"], session["mean"], color="#4fc3f7", linewidth=2,
            marker="o", markersize=6, markerfacecolor="#ffffff")
    ax.fill_between(session["Date"],
                    session["mean"] - session["std"],
                    session["mean"] + session["std"],
                    color="#4fc3f7", alpha=0.15, label="+-1 SD band")
    if len(session) >= 3:
        z = np.polyfit(range(len(session)), session["mean"], 1)
        direction = "improving" if z[0] > 0 else "declining"
        ax.plot(session["Date"], np.poly1d(z)(range(len(session))), "--",
                color="#ff7043", linewidth=1.5, label=f"Trend ({direction})")
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d '%y"))
    plt.xticks(rotation=30)
    return f"Chart saved to: {save_chart(fig, f'{club}_{stat.replace(chr(32), chr(95))}_trend')}"


@mcp.tool()
def chart_smash_factor_by_club() -> str:
    """Chart avg and Q3 smash factor by club vs tour benchmarks."""
    df = tyler_range.dropna(subset=["Smash Factor"]).copy()
    summary = df.groupby("Club Type")["Smash Factor"].agg(["mean","std"]).reset_index()
    summary["Q3"] = summary["mean"] + 0.6745 * summary["std"].fillna(0)
    summary["order"] = summary["Club Type"].map({c: i for i, c in enumerate(CLUB_ORDER)})
    summary = summary.sort_values("order").dropna(subset=["order"])
    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#1a1a2e")
    style_ax(ax, title="Smash Factor by Club -- Avg vs Q3 (peak contact)", xlabel="Club", ylabel="Smash Factor")
    x = np.arange(len(summary))
    ax.bar(x - 0.2, summary["mean"], 0.35, label="Avg SF",         color="#4fc3f7", alpha=0.85, edgecolor="#1a1a2e")
    ax.bar(x + 0.2, summary["Q3"],  0.35, label="Q3 SF (top 25%)", color="#ffb74d", alpha=0.85, edgecolor="#1a1a2e")
    ax.axhline(1.48, color="#ff7043", linewidth=1.5, linestyle="--", label="Driver ideal (1.48)")
    ax.axhline(1.38, color="#a5d6a7", linewidth=1.5, linestyle="--", label="Iron ideal (1.38)")
    for xi, val in zip(x, summary["mean"]):
        ax.text(xi - 0.2, val + 0.003, f"{val:.2f}", ha="center", va="bottom", color="#cccccc", fontsize=7)
    for xi, val in zip(x, summary["Q3"]):
        ax.text(xi + 0.2, val + 0.003, f"{val:.2f}", ha="center", va="bottom", color="#ffb74d", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(summary["Club Type"])
    ax.legend(facecolor="#16213e", labelcolor="#cccccc", ncol=2)
    return f"Chart saved to: {save_chart(fig, 'smash_factor_q3')}"


@mcp.tool()
def chart_all_clubs_carry_comparison() -> str:
    """Box plot comparing carry distance distributions across all clubs."""
    df = tyler_range.dropna(subset=["Carry Distance"]).copy()
    present = [c for c in CLUB_ORDER if c in df["Club Type"].values]
    data = [df[df["Club Type"] == c]["Carry Distance"].values for c in present]
    fig, ax = plt.subplots(figsize=(14, 5), facecolor="#1a1a2e")
    style_ax(ax, title="Full Bag Carry Distance Comparison (Trackman)", xlabel="Club", ylabel="Carry Distance (yds)")
    bp = ax.boxplot(data, labels=present, patch_artist=True,
                    medianprops=dict(color="#ffb74d", linewidth=2))
    colors = plt.cm.cool(np.linspace(0.2, 0.9, len(present)))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
    for element in ["whiskers","caps","fliers"]:
        for item in bp[element]:
            item.set_color("#8888aa")
    plt.xticks(rotation=20)
    return f"Chart saved to: {save_chart(fig, 'full_bag_boxplot')}"


@mcp.tool()
def chart_distance_gaps() -> str:
    """Visual chart of full bag distance coverage with error bars."""
    rs = tyler_range.groupby("Club Type")["Carry Distance"].agg(["mean","std"]).reset_index()
    rs.columns = ["Club","Avg","Std"]
    rs["order"] = rs["Club"].map({c: i for i, c in enumerate(CLUB_ORDER)})
    rs = rs.sort_values("order").dropna(subset=["order"])
    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#1a1a2e")
    style_ax(ax, title="Full Bag Distance Coverage (Trackman Data)", xlabel="Club", ylabel="Carry Distance (yds)")
    x = np.arange(len(rs))
    ax.bar(x, rs["Avg"], color="#4fc3f7", alpha=0.8, label="Avg carry")
    ax.errorbar(x, rs["Avg"], yerr=rs["Std"], fmt="none",
                color="#ffb74d", capsize=5, linewidth=2, label="+-1 SD")
    for xi, (_, row) in zip(x, rs.iterrows()):
        ax.text(xi, row["Avg"] + row["Std"] + 2, f'{row["Avg"]:.0f}',
                ha="center", va="bottom", color="#eeeeee", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(rs["Club"])
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    return f"Chart saved to: {save_chart(fig, 'distance_gaps')}"


@mcp.tool()
def chart_launch_angle_by_club() -> str:
    """Chart Tyler's avg launch angle per club vs ideal benchmarks."""
    ideals = {"d":13,"3w":14,"3h":16,"4i":17,"5i":19,"6i":21,
              "7i":23,"8i":25,"9i":27,"pw":29,"gw":32,"sw":35,"lw":38}
    df = tyler_range.dropna(subset=["Launch Angle"]).copy()
    summary = df.groupby("Club Type")["Launch Angle"].mean().reset_index()
    summary["order"] = summary["Club Type"].map({c: i for i, c in enumerate(ideals.keys())})
    summary = summary.sort_values("order").dropna(subset=["order"])
    summary["Ideal"] = summary["Club Type"].map(ideals)
    fig, ax = plt.subplots(figsize=(12, 4), facecolor="#1a1a2e")
    style_ax(ax, title="Avg Launch Angle by Club vs Ideal", xlabel="Club", ylabel="Launch Angle (deg)")
    x = np.arange(len(summary))
    ax.bar(x - 0.2, summary["Launch Angle"], 0.4, label="Tyler's avg", color="#4fc3f7", alpha=0.85)
    ax.bar(x + 0.2, summary["Ideal"], 0.4, label="Ideal benchmark", color="#ff7043", alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(summary["Club Type"])
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    return f"Chart saved to: {save_chart(fig, 'launch_angle')}"


@mcp.tool()
def chart_dispersion_scatter(club: str) -> str:
    """
    Shot dispersion scatter plot: side carry (x) vs carry distance (y), colored by smash factor.
    Reveals miss patterns — fade/draw bias, thin/fat tendency.
    """
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].dropna(
        subset=["Side Carry","Carry Distance"]).copy()
    if df.empty:
        return f"No data for '{club}'."
    avg_carry = df["Carry Distance"].mean()
    fig, ax = plt.subplots(figsize=(7, 7), facecolor="#1a1a2e")
    style_ax(ax, title=f"{club.upper()} Shot Dispersion Pattern",
             xlabel="Side Carry (ft, right = fade)", ylabel="Carry Distance (yds)")
    sc = ax.scatter(df["Side Carry"], df["Carry Distance"],
                    c=df["Smash Factor"] if "Smash Factor" in df.columns else "#4fc3f7",
                    cmap="cool", alpha=0.7, s=40, edgecolors="#333355", linewidth=0.5)
    ax.axvline(0, color="#555577", linewidth=1, linestyle="--")
    ax.axhline(avg_carry, color="#ffb74d", linewidth=1, linestyle="--",
               label=f"Avg carry: {avg_carry:.0f} yds")
    if "Smash Factor" in df.columns:
        plt.colorbar(sc, ax=ax, label="Smash Factor").ax.yaxis.label.set_color("#cccccc")
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    return f"Chart saved to: {save_chart(fig, f'{club}_dispersion')}"


@mcp.tool()
def chart_club_stats_radar(club: str) -> str:
    """
    Radar chart comparing Tyler's Trackman metrics for one club vs tour benchmarks.
    Carry, ball speed, smash factor, launch angle, club speed as % of ideal.
    Club options with benchmarks: d, 7i, 9i, pw, gw
    """
    benchmarks = {
        "d":  {"Carry Distance":270,"Ball Speed":167,"Smash Factor":1.48,"Launch Angle":13,"Club Speed":113},
        "7i": {"Carry Distance":172,"Ball Speed":120,"Smash Factor":1.38,"Launch Angle":23,"Club Speed":87},
        "9i": {"Carry Distance":145,"Ball Speed":105,"Smash Factor":1.34,"Launch Angle":27,"Club Speed":79},
        "pw": {"Carry Distance":130,"Ball Speed":95, "Smash Factor":1.30,"Launch Angle":29,"Club Speed":73},
        "gw": {"Carry Distance":115,"Ball Speed":88, "Smash Factor":1.27,"Launch Angle":32,"Club Speed":69},
    }
    bench = benchmarks.get(club.lower(), benchmarks["7i"])
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].copy()
    if df.empty:
        return f"No data for '{club}'."
    cats       = [c for c in bench if c in df.columns]
    tyler_vals = [df[c].mean() for c in cats]
    bench_vals = [bench[c] for c in cats]
    norm_t = [t/b for t, b in zip(tyler_vals, bench_vals)]
    norm_b = [1.0] * len(cats)
    norm_t += norm_t[:1]; norm_b += norm_b[:1]
    angles = np.linspace(0, 2*np.pi, len(cats), endpoint=False).tolist()
    angles += angles[:1]
    short = ["Carry","Ball Spd","Smash","Launch","Club Spd"][:len(cats)]
    fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True), facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.plot(angles, norm_b, color="#555577", linewidth=1.5, linestyle="--", label="Tour benchmark")
    ax.fill(angles, norm_b, color="#555577", alpha=0.08)
    ax.plot(angles, norm_t, color="#4fc3f7", linewidth=2, label="Tyler")
    ax.fill(angles, norm_t, color="#4fc3f7", alpha=0.2)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([f"{l}\n({v:.1f})" for l, v in zip(short, tyler_vals)], color="#cccccc", size=9)
    ax.set_yticklabels([])
    ax.set_title(f"{club.upper()} vs Tour Benchmarks", color="#ffffff", pad=20)
    ax.legend(loc="upper right", facecolor="#16213e", labelcolor="#cccccc")
    ax.grid(color="#2a2a4a")
    return f"Chart saved to: {save_chart(fig, f'{club}_radar')}"


# ══════════════════════════════════════════════════════════════════════════════
# BALL FLIGHT & LAUNCH ANGLE VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════════

def _simulate_trajectory(ball_speed_mph: float, launch_deg: float,
                          backspin_rpm: float = 3000, steps: int = 500):
    """
    Physics-based ball flight simulation using aerodynamic model.
    Accounts for drag, lift (backspin), and gravity.
    Returns (x_yards, y_feet) arrays.
    """
    g   = 32.174          # ft/s^2
    rho = 0.0765          # air density lb/ft^3
    m   = 0.1012          # ball mass lb
    r   = 0.0714          # ball radius ft
    A   = np.pi * r**2    # cross-section ft^2

    # Aerodynamic coefficients (empirical golf ball values)
    Cd = 0.23             # drag coefficient
    Cl = 0.21 * (backspin_rpm / 3000) ** 0.4  # lift scales with spin

    v0 = ball_speed_mph * 1.46667  # mph -> ft/s
    ang = np.radians(launch_deg)
    vx, vy = v0 * np.cos(ang), v0 * np.sin(ang)

    dt = 0.01
    x, y = 0.0, 0.0
    xs, ys = [0.0], [0.0]

    for _ in range(int(steps / dt)):
        v   = np.sqrt(vx**2 + vy**2)
        if v < 0.1:
            break
        # Drag force (opposing motion)
        Fd  = 0.5 * rho * v**2 * Cd * A
        ax_drag = -(Fd / m) * (vx / v)
        ay_drag = -(Fd / m) * (vy / v)
        # Lift force (perpendicular to velocity, upward for backspin)
        Fl  = 0.5 * rho * v**2 * Cl * A
        ax_lift = -(Fl / m) * (vy / v)
        ay_lift =  (Fl / m) * (vx / v)

        vx += (ax_drag + ax_lift) * dt
        vy += (ay_drag + ay_lift - g) * dt
        x  += vx * dt
        y  += vy * dt

        if y < 0 and len(xs) > 5:
            break
        xs.append(x)
        ys.append(max(y, 0.0))

    xs_yards = np.array(xs) / 3.0
    return xs_yards, np.array(ys)


@mcp.tool()
def chart_ball_flight_by_club(club: str) -> str:
    """
    Simulate and chart realistic ball flight trajectories for a specific club
    using Tyler's actual Trackman data (ball speed, launch angle, apex, carry).
    Shows avg shot, best shot (P90), and conservative shot (P25) overlaid.
    Club options: d, 3w, 3h, 5i, 6i, 7i, 8i, 9i, pw, gw, sw, lw
    """
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].dropna(
        subset=["Ball Speed", "Launch Angle", "Carry Distance"]).copy()
    if df.empty:
        return f"No data for '{club}'."

    bs_avg  = df["Ball Speed"].mean()
    la_avg  = df["Launch Angle"].mean()
    bs_p90  = np.percentile(df["Ball Speed"], 90)
    la_p90  = np.percentile(df["Launch Angle"], 75)
    bs_p25  = np.percentile(df["Ball Speed"], 25)
    la_p25  = np.percentile(df["Launch Angle"], 40)

    # Backspin estimates by club (rpm)
    spin_map = {"d":2600,"3w":3200,"3h":3800,"4i":4200,"5i":4600,"6i":5000,
                "7i":5400,"8i":5800,"9i":6200,"pw":7000,"gw":7500,"sw":8000,"lw":8500}
    spin = spin_map.get(club.lower(), 5000)

    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#1a1a2e")
    style_ax(ax, title=f"{club.upper()} Ball Flight — Avg / P90 / P25 (Tyler's Trackman data)",
             xlabel="Carry Distance (yards)", ylabel="Height (feet)")

    scenarios = [
        (bs_p90, la_p90, spin * 0.92, "#ffb74d", "P90 flush",    3.0, "--"),
        (bs_avg, la_avg, spin,        "#4fc3f7", "Avg shot",      2.5, "-"),
        (bs_p25, la_p25, spin * 1.08, "#ef9a9a", "P25 mishit",   1.5, ":"),
    ]

    for bs, la, sp, color, label, lw, ls in scenarios:
        xs, ys = _simulate_trajectory(bs, la, sp)
        carry  = xs[-1]
        apex   = ys.max()
        ax.plot(xs, ys, color=color, linewidth=lw, linestyle=ls,
                label=f"{label}  |  {carry:.0f} yds  |  apex {apex:.0f} ft")
        ax.annotate(f"{carry:.0f}", xy=(carry, 1), fontsize=8,
                    color=color, ha="center", va="bottom")

    # Actual apex from Trackman if available
    if "Apex" in df.columns:
        real_apex = df["Apex"].mean()
        ax.axhline(real_apex, color="#555577", linewidth=1, linestyle="--",
                   label=f"Trackman apex avg: {real_apex:.0f} ft")

    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    ax.legend(facecolor="#16213e", labelcolor="#cccccc", fontsize=8)
    return f"Chart saved to: {save_chart(fig, f'{club}_flight_paths')}"


@mcp.tool()
def chart_full_bag_flight_paths() -> str:
    """
    Overlay simulated ball flight trajectories for every club in Tyler's bag
    on a single chart, using avg Trackman data per club.
    Shows the full distance ladder from LW to Driver in one view.
    """
    club_list = ["lw","sw","gw","pw","9i","8i","7i","6i","5i","3h","3w","d"]
    spin_map  = {"d":2600,"3w":3200,"3h":3800,"5i":4600,"6i":5000,"7i":5400,
                 "8i":5800,"9i":6200,"pw":7000,"gw":7500,"sw":8000,"lw":8500}
    colors    = plt.cm.rainbow(np.linspace(0.0, 0.85, len(club_list)))

    fig, ax = plt.subplots(figsize=(14, 6), facecolor="#1a1a2e")
    style_ax(ax, title="Full Bag Ball Flight Trajectories (Tyler's Trackman Averages)",
             xlabel="Carry Distance (yards)", ylabel="Height (feet)")

    plotted = []
    for club_name, color in zip(club_list, colors):
        sub = tyler_range[tyler_range["Club Type"].str.lower() == club_name].dropna(
            subset=["Ball Speed","Launch Angle"])
        if sub.empty:
            continue
        bs = sub["Ball Speed"].mean()
        la = sub["Launch Angle"].mean()
        sp = spin_map.get(club_name, 5000)
        xs, ys = _simulate_trajectory(bs, la, sp)
        carry = xs[-1]
        apex  = ys.max()
        ax.plot(xs, ys, color=color, linewidth=1.8, alpha=0.85)
        ax.text(carry + 1, 1, club_name.upper(), color=color, fontsize=7,
                va="bottom", ha="left")
        plotted.append(f"{club_name.upper()}: {carry:.0f} yds, apex {apex:.0f} ft")

    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)

    # Annotate in legend box
    from matplotlib.lines import Line2D
    legend_lines = [Line2D([0], [0], color=c, linewidth=2)
                    for _, c in zip(club_list[:len(plotted)], colors)]
    ax.legend(legend_lines, [p.split(":")[0] for p in plotted],
              facecolor="#16213e", labelcolor="#cccccc", fontsize=7,
              ncol=2, loc="upper left")

    info = "\n".join(plotted)
    return f"Chart saved to: {save_chart(fig, 'full_bag_flights')}\n\n{info}"


@mcp.tool()
def chart_launch_angle_vs_distance() -> str:
    """
    Scatter plot of individual shots: launch angle (x) vs carry distance (y),
    colored by ball speed. Shows the sweet spot launch window for each club
    and how sub-optimal angles cost distance.
    """
    df = tyler_range.dropna(subset=["Launch Angle","Carry Distance","Ball Speed"]).copy()
    club_list = ["d","3w","3h","7i","8i","9i","pw","gw"]
    colors    = {"d":"#4fc3f7","3w":"#80deea","3h":"#a5d6a7",
                 "7i":"#ffb74d","8i":"#ef9a9a","9i":"#ce93d8",
                 "pw":"#ff8a65","gw":"#fff176"}

    fig, axes = plt.subplots(2, 4, figsize=(14, 6), facecolor="#1a1a2e")
    fig.suptitle("Launch Angle vs Carry Distance — Shot by Shot", color="#ffffff",
                 fontsize=12, fontweight="bold", y=1.01)

    for ax, club_name in zip(axes.flat, club_list):
        sub = df[df["Club Type"].str.lower() == club_name]
        style_ax(ax, title=club_name.upper())
        if sub.empty:
            ax.text(0.5, 0.5, "no data", ha="center", va="center",
                    transform=ax.transAxes, color="#666688")
            continue
        sc = ax.scatter(sub["Launch Angle"], sub["Carry Distance"],
                        c=sub["Ball Speed"], cmap="cool", alpha=0.65, s=18,
                        edgecolors="none")
        # Optimal LA line
        opt_la = sub.loc[sub["Carry Distance"].idxmax(), "Launch Angle"]
        ax.axvline(sub["Launch Angle"].mean(), color="#ffb74d", linewidth=1,
                   linestyle="--", alpha=0.7)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("Launch Angle (°)", fontsize=7)
        ax.set_ylabel("Carry (yds)", fontsize=7)

    plt.tight_layout()
    return f"Chart saved to: {save_chart(fig, 'launch_vs_distance')}"


@mcp.tool()
def get_launch_angle_report() -> str:
    """
    Textual report of Tyler's launch angle stats vs optimal windows per club.
    Shows avg, std, % of shots in optimal window, and distance cost of under/over-launch.
    Optimal launch windows are based on ball speed and standard TrackMan benchmarks.
    """
    optimal = {
        "d":  (10, 14), "3w": (12, 16), "3h": (14, 18),
        "5i": (16, 20), "6i": (18, 22), "7i": (20, 24),
        "8i": (22, 26), "9i": (24, 28), "pw": (26, 31),
        "gw": (28, 34), "sw": (32, 38), "lw": (34, 42),
    }
    df = tyler_range.dropna(subset=["Launch Angle","Carry Distance"]).copy()
    present = [c for c in optimal if c in df["Club Type"].values]

    lines = [
        "Launch Angle Report — Tyler vs Optimal Windows\n",
        f"{'Club':<6} {'Avg LA':>8} {'Std':>6} {'Opt Window':>12} {'In Window':>11} {'Avg Carry':>10} {'Peak Carry':>11}"
    ]
    lines.append("-" * 68)
    for c in present:
        sub  = df[df["Club Type"] == c]
        la   = sub["Launch Angle"].dropna()
        carry= sub["Carry Distance"].dropna()
        lo, hi = optimal[c]
        in_win = ((la >= lo) & (la <= hi)).mean() * 100
        peak_carry = sub[sub["Launch Angle"].between(lo, hi)]["Carry Distance"].mean()
        lines.append(
            f"  {c:<6} {la.mean():>8.1f}° {la.std():>6.1f}  "
            f"{lo}–{hi}°{' ':>3} {in_win:>9.0f}%  "
            f"{carry.mean():>10.1f}  "
            f"{peak_carry:>10.1f}" if not np.isnan(peak_carry) else
            f"  {c:<6} {la.mean():>8.1f}° {la.std():>6.1f}  {lo}–{hi}°{' ':>3} {in_win:>9.0f}%  {carry.mean():>10.1f}  {'n/a':>10}"
        )
    lines.append("\nPeak Carry = avg carry when launch is within the optimal window.")
    lines.append("In Window  = % of shots landing in the optimal launch angle range.")
    return "\n".join(lines)


@mcp.tool()
def chart_shot_shape_profile(club: str) -> str:
    """
    Combined 2-panel chart for a club:
    - Top panel: simulated flight paths for every individual shot (faded),
      with avg and best overlaid prominently. Shows shot-to-shot variation.
    - Bottom panel: side carry distribution showing draw/fade tendencies.
    Club options: d, 3w, 3h, 6i, 7i, 8i, 9i, pw, gw, lw
    """
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].dropna(
        subset=["Ball Speed","Launch Angle","Side Carry","Carry Distance"]).copy()
    if len(df) < 3:
        return f"Not enough shots for '{club}' (need at least 3)."

    spin_map = {"d":2600,"3w":3200,"3h":3800,"4i":4200,"5i":4600,"6i":5000,
                "7i":5400,"8i":5800,"9i":6200,"pw":7000,"gw":7500,"sw":8000,"lw":8500}
    spin = spin_map.get(club.lower(), 5000)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), facecolor="#1a1a2e",
                                    gridspec_kw={"height_ratios": [2, 1]})
    style_ax(ax1, title=f"{club.upper()} — Individual Shot Trajectories",
             ylabel="Height (feet)")
    style_ax(ax2, xlabel="Side of Target Line (ft, right=fade)",
             ylabel="Shots")

    best_carry = 0
    best_xs, best_ys = None, None

    # Individual shots (max 60 for performance)
    sample = df.sample(min(60, len(df)), random_state=42)
    for _, row in sample.iterrows():
        xs, ys = _simulate_trajectory(row["Ball Speed"], row["Launch Angle"],
                                      spin * (1 + np.random.normal(0, 0.05)))
        ax1.plot(xs, ys, color="#4fc3f7", linewidth=0.6, alpha=0.18)
        if xs[-1] > best_carry:
            best_carry, best_xs, best_ys = xs[-1], xs, ys

    # Avg trajectory
    xs_avg, ys_avg = _simulate_trajectory(df["Ball Speed"].mean(),
                                           df["Launch Angle"].mean(), spin)
    ax1.plot(xs_avg, ys_avg, color="#ffb74d", linewidth=2.5, label=f"Avg: {xs_avg[-1]:.0f} yds")
    if best_xs is not None:
        ax1.plot(best_xs, best_ys, color="#a5d6a7", linewidth=2,
                 linestyle="--", label=f"Best: {best_carry:.0f} yds")

    ax1.set_ylim(bottom=0)
    ax1.set_xlim(left=0)
    ax1.legend(facecolor="#16213e", labelcolor="#cccccc", fontsize=9)
    ax1.tick_params(labelbottom=False)

    # Side carry distribution
    side = df["Side Carry"].dropna()
    ax2.hist(side, bins=25, color="#4fc3f7", edgecolor="#1a1a2e", alpha=0.8)
    ax2.axvline(0,           color="#555577", linewidth=1, linestyle="--")
    ax2.axvline(side.mean(), color="#ffb74d", linewidth=2,
                label=f"Avg bias: {'R' if side.mean()>0 else 'L'} {abs(side.mean()):.1f} ft")
    ax2.legend(facecolor="#16213e", labelcolor="#cccccc", fontsize=8)
    ax2.tick_params(colors="#cccccc", labelsize=8)

    plt.tight_layout()
    return f"Chart saved to: {save_chart(fig, f'{club}_shot_shape')}"


# ══════════════════════════════════════════════════════════════════════════════
# CLUB FITTING ENGINE — OPTIMAL LAUNCH / SPIN MATRIX
# ══════════════════════════════════════════════════════════════════════════════

# TrackMan optimal launch angle and spin (rpm) by ball speed (mph) and
# angle of attack (degrees). Matrix rows = ball speed, cols = AoA.
# Format: {ball_speed_mph: {aoa_deg: (launch_angle, spin_rpm, carry_yards)}}
# Values digitised from the TrackMan optimal launch matrix (driver).
_DRIVER_MATRIX = {
    180: {-10:(3.6,3450,None),-8:(4.9,3250,None),-6:(6.2,3050,None),-4:(7.5,2850,None),
          -2:(9.0,2700,None),  0:(10.4,2550,None), 2:(11.9,2400,None), 4:(13.3,2200,None),
           6:(14.8,2050,None), 8:(16.4,1950,None),10:(17.9,1800,None)},
    170: {-10:(4.3,3500,None),-8:(5.7,3300,None),-6:(6.9,3100,None),-4:(8.2,2900,None),
          -2:(9.6,2750,None),  0:(11.0,2550,None), 2:(12.4,2400,None), 4:(13.9,2200,None),
           6:(15.3,2100,None), 8:(16.8,1950,None),10:(18.2,1800,None)},
    160: {-10:(5.2,3500,None),-8:(6.5,3300,None),-6:(7.7,3100,None),-4:(9.0,2900,None),
          -2:(10.3,2750,None), 0:(11.7,2600,None), 2:(13.0,2400,None), 4:(14.4,2200,None),
           6:(15.9,2100,None), 8:(17.3,1950,None),10:(18.7,1800,None)},
    150: {-10:(6.2,3500,None),-8:(7.4,3350,None),-6:(8.6,3150,None),-4:(9.8,2950,None),
          -2:(11.1,2750,None), 0:(12.4,2600,None), 2:(13.7,2450,None), 4:(15.1,2300,None),
           6:(16.4,2150,None), 8:(17.9,2000,None),10:(19.3,1850,None)},
    140: {-10:(7.3,3500,None),-8:(8.3,3300,None),-6:(9.5,3150,None),-4:(10.7,2950,None),
          -2:(12.0,2800,None), 0:(13.2,2600,None), 2:(14.5,2450,None), 4:(15.8,2300,None),
           6:(17.2,2150,None), 8:(18.5,2000,None),10:(19.9,1850,None)},
    130: {-10:(8.4,3500,None),-8:(9.4,3300,None),-6:(10.6,3150,None),-4:(11.7,2950,None),
          -2:(12.8,2750,None), 0:(14.1,2600,None), 2:(15.3,2450,None), 4:(16.6,2300,None),
           6:(17.9,2150,None), 8:(19.2,2000,None),10:(20.6,1850,None)},
    120: {-10:(9.6,3450,None),-8:(10.6,3250,None),-6:(11.6,3100,None),-4:(12.9,2900,None),
          -2:(13.8,2750,None), 0:(15.0,2600,None), 2:(16.2,2450,None), 4:(17.4,2300,None),
           6:(18.7,2150,None), 8:(19.9,1950,None),10:(21.2,1850,None)},
    110: {-10:(10.9,3400,None),-8:(11.8,3200,None),-6:(12.7,3000,None),-4:(13.9,2700,None),
          -2:(14.9,2700,None), 0:(15.9,2550,None), 2:(17.1,2400,None), 4:(18.2,2250,None),
           6:(19.5,2100,None), 8:(20.7,1950,None),10:(21.9,1850,None)},
    100: {-10:(11.9,3100,None),-8:(12.9,3100,None),-6:(13.9,2950,None),-4:(14.9,2600,None),
          -2:(15.9,2600,None), 0:(16.9,2450,None), 2:(18.0,2300,None), 4:(19.1,2150,None),
           6:(20.3,2050,None), 8:(21.4,1900,None),10:(22.6,1750,None)},
     90: {-10:(12.7,3050,None),-8:(13.9,2950,None),-6:(15.0,2800,None),-4:(15.9,2650,None),
          -2:(16.9,2500,None), 0:(18.0,2350,None), 2:(19.0,2200,None), 4:(20.0,2100,None),
           6:(21.0,1950,None), 8:(22.2,1850,None),10:(23.3,1700,None)},
     80: {-10:(13.8,2800,None),-8:(14.5,2650,None),-6:(15.8,2600,None),-4:(17.8,2450,None),
          -2:(18.8,2350,None), 0:(18.8,2200,None), 2:(19.9,2100,None), 4:(21.8,1950,None),
           6:(22.9,1850,None), 8:(22.9,1800,None),10:(24.0,1600,None)},
}

# Iron optimal windows — (launch_angle_low, launch_angle_high, spin_low, spin_high)
# Based on standard TrackMan fitting benchmarks for each iron
_IRON_OPTIMAL = {
    "3i": (13, 17, 3800, 4600),
    "4i": (14, 18, 4200, 5000),
    "5i": (16, 20, 4600, 5400),
    "6i": (18, 22, 5000, 5800),
    "7i": (20, 24, 5400, 6200),
    "8i": (22, 26, 5800, 6600),
    "9i": (24, 28, 6200, 7000),
    "pw": (26, 31, 6800, 7600),
    "gw": (28, 34, 7200, 8200),
    "sw": (32, 38, 7800, 9000),
    "lw": (34, 42, 8000, 9500),
    "3h": (14, 18, 3600, 4400),
    "3w": (12, 16, 3000, 3800),
}

# Ideal smash factors by club
_IDEAL_SMASH = {
    "d":1.48,"3w":1.45,"3h":1.43,"5i":1.40,"6i":1.39,"7i":1.38,
    "8i":1.36,"9i":1.34,"pw":1.30,"gw":1.27,"sw":1.24,"lw":1.22,
}

def _find_optimal_driver(ball_speed: float, aoa: float = 0.0):
    """Interpolate optimal launch angle and spin for a given driver ball speed and AoA."""
    speeds = sorted(_DRIVER_MATRIX.keys())
    aoas   = [-10,-8,-6,-4,-2,0,2,4,6,8,10]

    # Clamp to matrix bounds
    bs_clamped  = max(min(ball_speed, 180), 80)
    aoa_clamped = max(min(aoa, 10), -10)

    # Find bracketing speeds
    lo_s = max([s for s in speeds if s <= bs_clamped], default=speeds[0])
    hi_s = min([s for s in speeds if s >= bs_clamped], default=speeds[-1])

    # Find bracketing AoAs
    lo_a = max([a for a in aoas if a <= aoa_clamped], default=aoas[0])
    hi_a = min([a for a in aoas if a >= aoa_clamped], default=aoas[-1])

    def get_val(spd, ao):
        return _DRIVER_MATRIX[spd][ao]

    if lo_s == hi_s and lo_a == hi_a:
        la, sp, _ = get_val(lo_s, lo_a)
        return la, sp

    # Bilinear interpolation
    if lo_s == hi_s:
        v1 = get_val(lo_s, lo_a)
        v2 = get_val(lo_s, hi_a)
        t  = (aoa_clamped - lo_a) / (hi_a - lo_a) if hi_a != lo_a else 0
        return v1[0] + t*(v2[0]-v1[0]), int(v1[1] + t*(v2[1]-v1[1]))

    if lo_a == hi_a:
        v1 = get_val(lo_s, lo_a)
        v2 = get_val(hi_s, lo_a)
        t  = (bs_clamped - lo_s) / (hi_s - lo_s) if hi_s != lo_s else 0
        return v1[0] + t*(v2[0]-v1[0]), int(v1[1] + t*(v2[1]-v1[1]))

    t_s = (bs_clamped - lo_s) / (hi_s - lo_s)
    t_a = (aoa_clamped - lo_a) / (hi_a - lo_a)
    v00 = get_val(lo_s, lo_a); v10 = get_val(hi_s, lo_a)
    v01 = get_val(lo_s, hi_a); v11 = get_val(hi_s, hi_a)
    la = (v00[0]*(1-t_s)*(1-t_a) + v10[0]*t_s*(1-t_a) +
          v01[0]*(1-t_s)*t_a     + v11[0]*t_s*t_a)
    sp = (v00[1]*(1-t_s)*(1-t_a) + v10[1]*t_s*(1-t_a) +
          v01[1]*(1-t_s)*t_a     + v11[1]*t_s*t_a)
    return round(la, 1), int(sp)


def _fitting_verdict(actual_la, optimal_la, la_tol=1.5,
                     actual_spin=None, optimal_spin=None, spin_tol=300,
                     actual_sf=None, ideal_sf=None, sf_tol=0.03,
                     actual_cv=None):
    """Return (grade, issues, recommendations) fitter-style verdict."""
    issues = []
    recs   = []

    la_delta = actual_la - optimal_la
    if abs(la_delta) <= la_tol:
        la_grade = "A"
    elif abs(la_delta) <= la_tol * 2:
        la_grade = "B"
        if la_delta > 0:
            issues.append(f"Launch angle {la_delta:+.1f}° above optimal — slightly balloon-y")
            recs.append("Weaken grip slightly or move ball back in stance")
        else:
            issues.append(f"Launch angle {la_delta:+.1f}° below optimal — too low/penetrating")
            recs.append("Strengthen loft, tee higher (driver), or move ball forward")
    else:
        la_grade = "C" if abs(la_delta) <= la_tol * 4 else "D"
        if la_delta > 0:
            issues.append(f"Launch angle {la_delta:+.1f}° too high — losing distance to ballooning")
            recs.append("Consider more negative loft or stronger shaft to reduce spin")
        else:
            issues.append(f"Launch angle {la_delta:+.1f}° too low — ball not getting airborne enough")
            recs.append("Higher loft, shaft with more flex, or adjusted setup position")

    spin_grade = "A"
    if actual_spin is not None and optimal_spin is not None:
        spin_delta = actual_spin - optimal_spin
        if abs(spin_delta) <= spin_tol:
            spin_grade = "A"
        elif abs(spin_delta) <= spin_tol * 2:
            spin_grade = "B"
            if spin_delta > 0:
                issues.append(f"Spin {spin_delta:+.0f} rpm above optimal — slightly high spin")
                recs.append("Lower spin shaft or adjust attack angle")
            else:
                issues.append(f"Spin {spin_delta:+.0f} rpm below optimal — low spin, may lose carry")
                recs.append("Higher spin shaft profile or softer flex")
        else:
            spin_grade = "D"
            if spin_delta > 0:
                issues.append(f"Spin {spin_delta:+.0f} rpm too high — significant balloon trajectory")
                recs.append("PRIORITY: Lower spin shaft, check dynamic loft at impact")
            else:
                issues.append(f"Spin {spin_delta:+.0f} rpm too low — ball dropping out of sky")
                recs.append("PRIORITY: Higher loft, check AoA and ball position")

    sf_grade = "A"
    if actual_sf is not None and ideal_sf is not None:
        sf_delta = actual_sf - ideal_sf
        if sf_delta >= -sf_tol:
            sf_grade = "A"
        elif sf_delta >= -sf_tol * 2.5:
            sf_grade = "B"
            issues.append(f"Smash factor {actual_sf:.3f} vs ideal {ideal_sf:.2f} — some off-centre contact")
            recs.append("Check grip pressure and tempo; consider face insert or larger sweet spot")
        else:
            sf_grade = "C"
            issues.append(f"Smash factor {actual_sf:.3f} well below {ideal_sf:.2f} — frequent mishits")
            recs.append("Club fitting priority: shaft flex/weight, face insert, lie angle check")

    cv_grade = "A"
    if actual_cv is not None:
        if actual_cv <= 6:
            cv_grade = "A"
        elif actual_cv <= 9:
            cv_grade = "B"
            issues.append(f"Distance variation {actual_cv:.1f}% — slightly inconsistent contact")
        else:
            cv_grade = "C"
            issues.append(f"Distance variation {actual_cv:.1f}% — high spread, suggest shaft weight/flex eval")
            recs.append("Shaft fitting: weight/profile affects consistency more than loft")

    grades = [la_grade, spin_grade, sf_grade, cv_grade]
    order  = ["A","B","C","D"]
    overall = sorted(grades, key=lambda g: order.index(g))[-1]
    return overall, grades, issues, recs


@mcp.tool()
def get_driver_fitting_report() -> str:
    """
    Full club-fitter style report for Tyler's driver using the TrackMan optimal
    launch and spin matrix. Looks up his actual ball speed and angle of attack,
    finds the optimal launch angle and spin from the matrix, compares to actuals,
    and gives a grade (A-D) with specific fitting recommendations.
    Exactly what a TrackMan fitter would tell you.
    """
    df = tyler_range[tyler_range["Club Type"] == "d"].dropna(
        subset=["Ball Speed","Launch Angle","Smash Factor","Carry Distance"]).copy()
    if df.empty:
        return "No driver data found."

    bs      = df["Ball Speed"].mean()
    la      = df["Launch Angle"].mean()
    sf      = df["Smash Factor"].mean()
    cs      = df["Club Speed"].mean() if "Club Speed" in df.columns else None
    carry   = df["Carry Distance"].mean()
    carry_p = np.percentile(df["Carry Distance"], 75)
    cv      = df["Carry Distance"].std() / df["Carry Distance"].mean() * 100

    # Spin from Trackman if available, else estimate
    if "Spin" in df.columns:
        spin_actual = df["Spin"].dropna().mean()
    else:
        spin_actual = None

    # Assume slightly descending blow typical for amateur (-2 to 0 AoA)
    # Best estimate from launch angle: if LA is low for ball speed, AoA is likely negative
    aoa_est = -2.0 if la < 12 else 0.0 if la < 14 else 2.0
    opt_la, opt_spin = _find_optimal_driver(bs, aoa_est)

    overall, grades, issues, recs = _fitting_verdict(
        la, opt_la,
        actual_spin=spin_actual, optimal_spin=opt_spin,
        actual_sf=sf, ideal_sf=_IDEAL_SMASH["d"],
        actual_cv=cv
    )

    # Distance cost estimate
    la_gap  = abs(la - opt_la)
    dist_cost = la_gap * 1.8  # ~1.8 yds per degree off optimal launch

    lines = [
        "=" * 60,
        "DRIVER FITTING REPORT — Tyler",
        "=" * 60,
        "",
        f"  Ball Speed:      {bs:.1f} mph",
        f"  Club Speed:      {cs:.1f} mph" if cs else "  Club Speed:      n/a",
        f"  Smash Factor:    {sf:.3f}  (ideal {_IDEAL_SMASH['d']:.2f})  [{grades[2]}]",
        f"  Launch Angle:    {la:.1f}°  (optimal {opt_la:.1f}°)  [{grades[0]}]",
        f"  Spin (est AoA {aoa_est:+.0f}°): optimal {opt_spin:,} rpm",
        f"  Avg Carry:       {carry:.1f} yds  (P75: {carry_p:.1f} yds)",
        f"  Consistency CV:  {cv:.1f}%  [{grades[3]}]",
        "",
        f"  OVERALL GRADE:   {overall}",
        f"  Est. distance left on table: ~{dist_cost:.0f} yds from launch angle alone",
        "",
    ]

    if issues:
        lines.append("ISSUES FOUND:")
        for i, iss in enumerate(issues, 1):
            lines.append(f"  {i}. {iss}")
        lines.append("")

    if recs:
        lines.append("FITTER RECOMMENDATIONS:")
        for i, rec in enumerate(recs, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

    if overall == "A":
        lines.append("VERDICT: Driver specs and technique are dialled in. Focus on consistency.")
    elif overall == "B":
        lines.append("VERDICT: Minor adjustments could add 5-15 yards. Not urgent but worth a session.")
    elif overall == "C":
        lines.append("VERDICT: Meaningful distance and consistency gains available. Fitting recommended.")
    else:
        lines.append("VERDICT: Significant mismatch between equipment/technique and optimal. High priority.")

    return "\n".join(lines)


@mcp.tool()
def get_full_bag_fitting_report() -> str:
    """
    Full bag fitting report — every club assessed like a TrackMan fitter would.
    For each club: actual vs optimal launch angle, smash factor grade, distance
    consistency grade, miss bias, and specific recommendations.
    This is the equivalent of a professional club fitting session summary.
    """
    results = []

    for club in ["d","3w","3h","6i","7i","8i","9i","pw","gw","sw","lw"]:
        df = tyler_range[tyler_range["Club Type"].str.lower() == club].dropna(
            subset=["Ball Speed","Launch Angle","Carry Distance","Smash Factor"]).copy()
        if df.empty:
            continue

        bs    = df["Ball Speed"].mean()
        la    = df["Launch Angle"].mean()
        sf    = df["Smash Factor"].mean()
        carry = df["Carry Distance"].mean()
        cv    = df["Carry Distance"].std() / df["Carry Distance"].mean() * 100
        side  = df["Side Carry"].dropna().mean() if "Side Carry" in df.columns else 0
        side_std = df["Side Carry"].dropna().std() if "Side Carry" in df.columns else 0

        if club == "d":
            aoa_est = -2.0 if la < 12 else 0.0 if la < 14 else 2.0
            opt_la, opt_spin = _find_optimal_driver(bs, aoa_est)
        elif club in _IRON_OPTIMAL:
            lo, hi, slo, shi = _IRON_OPTIMAL[club]
            opt_la   = (lo + hi) / 2
            opt_spin = (slo + shi) / 2
        else:
            opt_la, opt_spin = la, None

        overall, grades, issues, recs = _fitting_verdict(
            la, opt_la,
            actual_spin=None, optimal_spin=None,
            actual_sf=sf, ideal_sf=_IDEAL_SMASH.get(club, 1.35),
            actual_cv=cv
        )

        results.append({
            "club": club, "bs": bs, "la": la, "opt_la": opt_la,
            "sf": sf, "ideal_sf": _IDEAL_SMASH.get(club, 1.35),
            "carry": carry, "cv": cv, "side": side, "side_std": side_std,
            "overall": overall, "la_grade": grades[0], "sf_grade": grades[2],
            "cv_grade": grades[3], "issues": issues, "recs": recs
        })

    order = ["A","B","C","D"]
    lines = [
        "=" * 68,
        "FULL BAG FITTING REPORT — Tyler",
        "TrackMan Optimal Launch Matrix Analysis",
        "=" * 68,
        "",
        f"{'Club':<6} {'Ball Spd':>9} {'Act LA':>8} {'Opt LA':>8} {'LA':>4} {'Smash':>7} {'SF':>4} {'CV':>6} {'Overall':>8}",
        "-" * 68,
    ]
    for r in results:
        lines.append(
            f"  {r['club'].upper():<6} {r['bs']:>7.1f}   {r['la']:>7.1f}° {r['opt_la']:>7.1f}°"
            f"  [{r['la_grade']}]  {r['sf']:>6.3f}  [{r['sf_grade']}]  {r['cv']:>5.1f}%  [{r['overall']}]"
        )

    lines += ["", "─" * 68, "DETAILED FINDINGS BY CLUB", "─" * 68]
    for r in results:
        if not r["issues"] and r["overall"] == "A":
            continue
        lines += [
            f"",
            f"  {r['club'].upper()} — Grade {r['overall']}",
            f"  Carry {r['carry']:.1f} yds | Launch {r['la']:.1f}° (optimal {r['opt_la']:.1f}°) | "
            f"Smash {r['sf']:.3f} | Miss bias {'R' if r['side']>0 else 'L'}{abs(r['side']):.1f}ft | "
            f"Dispersion ±{r['side_std']:.1f}ft",
        ]
        for iss in r["issues"]:
            lines.append(f"  ! {iss}")
        for rec in r["recs"]:
            lines.append(f"  → {rec}")

    # Priority summary
    priority = [r for r in results if r["overall"] in ("C","D")]
    ok       = [r for r in results if r["overall"] == "A"]
    lines += ["", "─" * 68, "FITTING PRIORITY SUMMARY", "─" * 68]
    if priority:
        lines.append(f"  HIGH PRIORITY clubs: {', '.join(r['club'].upper() for r in priority)}")
        lines.append("  These show the most distance / consistency gains available.")
    if ok:
        lines.append(f"  DIALLED IN clubs: {', '.join(r['club'].upper() for r in ok)}")
        lines.append("  These are working well — no changes needed.")

    return "\n".join(lines)


@mcp.tool()
def chart_fitting_overview() -> str:
    """
    Visual fitting dashboard: for each club, plots actual launch angle vs
    the optimal window as a colour-coded bar chart, plus a smash factor
    gap chart and a consistency (CV%) chart — all in one figure.
    Green = in spec, amber = minor gap, red = needs attention.
    """
    clubs_to_show = ["d","3w","3h","6i","7i","8i","9i","pw","gw","lw"]

    rows = []
    for club in clubs_to_show:
        df = tyler_range[tyler_range["Club Type"].str.lower() == club].dropna(
            subset=["Launch Angle","Smash Factor","Carry Distance"]).copy()
        if df.empty:
            continue
        la   = df["Launch Angle"].mean()
        sf   = df["Smash Factor"].mean()
        cv   = df["Carry Distance"].std() / df["Carry Distance"].mean() * 100
        if club == "d":
            bs = df["Ball Speed"].mean()
            aoa = -2.0 if la < 12 else 0.0 if la < 14 else 2.0
            opt_la, _ = _find_optimal_driver(bs, aoa)
        elif club in _IRON_OPTIMAL:
            lo, hi, _, _ = _IRON_OPTIMAL[club]
            opt_la = (lo + hi) / 2
        else:
            opt_la = la
        ideal_sf = _IDEAL_SMASH.get(club, 1.35)
        la_gap   = la - opt_la
        sf_gap   = sf - ideal_sf
        rows.append({"club": club.upper(), "la": la, "opt_la": opt_la,
                     "la_gap": la_gap, "sf": sf, "ideal_sf": ideal_sf,
                     "sf_gap": sf_gap, "cv": cv})

    labels    = [r["club"] for r in rows]
    la_gaps   = [r["la_gap"] for r in rows]
    sf_gaps   = [r["sf_gap"] for r in rows]
    cv_vals   = [r["cv"] for r in rows]

    def gap_color(v, tol):
        if abs(v) <= tol:      return "#4caf50"
        elif abs(v) <= tol*2:  return "#ffb74d"
        else:                  return "#ef5350"

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 9), facecolor="#1a1a2e")
    fig.suptitle("Club Fitting Overview — Tyler vs TrackMan Optimal",
                 color="#ffffff", fontsize=13, fontweight="bold")

    x = np.arange(len(labels))

    # ── Panel 1: Launch angle gap ──────────────────────────────────────────
    style_ax(ax1, ylabel="Launch angle gap (°)")
    bar_colors1 = [gap_color(v, 1.5) for v in la_gaps]
    bars1 = ax1.bar(x, la_gaps, color=bar_colors1, edgecolor="#1a1a2e", width=0.6)
    ax1.axhline(0,   color="#ffffff", linewidth=0.8, linestyle="--", alpha=0.4)
    ax1.axhline(+3,  color="#ffb74d", linewidth=0.6, linestyle=":", alpha=0.5)
    ax1.axhline(-3,  color="#ffb74d", linewidth=0.6, linestyle=":", alpha=0.5)
    for bar, val in zip(bars1, la_gaps):
        ax1.text(bar.get_x()+bar.get_width()/2, val + (0.1 if val>=0 else -0.25),
                 f"{val:+.1f}°", ha="center", va="bottom" if val>=0 else "top",
                 color="#cccccc", fontsize=8)
    ax1.set_xticks(x); ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_title("Launch angle: actual minus optimal  (green=in spec, amber=minor, red=fix)",
                  color="#cccccc", fontsize=9, pad=4)

    # ── Panel 2: Smash factor gap ──────────────────────────────────────────
    style_ax(ax2, ylabel="Smash factor gap")
    bar_colors2 = [gap_color(v, 0.025) for v in sf_gaps]
    bars2 = ax2.bar(x, sf_gaps, color=bar_colors2, edgecolor="#1a1a2e", width=0.6)
    ax2.axhline(0, color="#ffffff", linewidth=0.8, linestyle="--", alpha=0.4)
    for bar, val in zip(bars2, sf_gaps):
        ax2.text(bar.get_x()+bar.get_width()/2, val - 0.003,
                 f"{val:+.3f}", ha="center", va="top", color="#cccccc", fontsize=8)
    ax2.set_xticks(x); ax2.set_xticklabels(labels, fontsize=9)
    ax2.set_title("Smash factor: actual minus ideal  (negative = off-centre contact)",
                  color="#cccccc", fontsize=9, pad=4)

    # ── Panel 3: Distance consistency (CV%) ────────────────────────────────
    style_ax(ax3, ylabel="Distance CV %")
    bar_colors3 = [gap_color(v - 6, 1.5) for v in cv_vals]
    bars3 = ax3.bar(x, cv_vals, color=bar_colors3, edgecolor="#1a1a2e", width=0.6)
    ax3.axhline(6, color="#ffb74d", linewidth=1, linestyle="--",
                label="Tour avg ~6%")
    ax3.axhline(9, color="#ef5350", linewidth=0.8, linestyle=":",
                label="Concern threshold 9%")
    for bar, val in zip(bars3, cv_vals):
        ax3.text(bar.get_x()+bar.get_width()/2, val + 0.1,
                 f"{val:.1f}%", ha="center", va="bottom", color="#cccccc", fontsize=8)
    ax3.set_xticks(x); ax3.set_xticklabels(labels, fontsize=9)
    ax3.legend(facecolor="#16213e", labelcolor="#cccccc", fontsize=8)
    ax3.set_title("Distance consistency (CV%) — lower is better",
                  color="#cccccc", fontsize=9, pad=4)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    return f"Chart saved to: {save_chart(fig, 'fitting_overview')}"


@mcp.tool()
def chart_driver_launch_matrix() -> str:
    """
    Render the TrackMan optimal launch/spin matrix as a heatmap with Tyler's
    actual ball speed and estimated angle of attack plotted as a crosshair.
    Shows exactly where on the matrix Tyler sits and how far from optimal.
    """
    df = tyler_range[tyler_range["Club Type"] == "d"].dropna(
        subset=["Ball Speed","Launch Angle"]).copy()
    if df.empty:
        return "No driver data."

    bs_actual = df["Ball Speed"].mean()
    la_actual = df["Launch Angle"].mean()
    aoa_est   = -2.0 if la_actual < 12 else 0.0 if la_actual < 14 else 2.0
    opt_la, opt_spin = _find_optimal_driver(bs_actual, aoa_est)

    speeds = [180,170,160,150,140,130,120,110,100,90,80]
    aoas   = [-10,-8,-6,-4,-2,0,2,4,6,8,10]

    # Build launch angle grid
    la_grid = np.array([[_DRIVER_MATRIX[s][a][0] for a in aoas] for s in speeds])

    fig, ax = plt.subplots(figsize=(12, 7), facecolor="#1a1a2e")
    style_ax(ax, title="TrackMan Driver Optimal Launch Angle Matrix — Tyler's Position",
             xlabel="Angle of Attack (°)", ylabel="Ball Speed (mph)")

    im = ax.imshow(la_grid, aspect="auto", cmap="RdYlGn",
                   extent=[-11, 11, 75, 185], origin="upper", alpha=0.85)
    plt.colorbar(im, ax=ax, label="Optimal Launch Angle (°)").ax.yaxis.label.set_color("#cccccc")

    # Annotate cells with LA values
    for i, spd in enumerate(speeds):
        for j, aoa in enumerate(aoas):
            la_val = _DRIVER_MATRIX[spd][aoa][0]
            ax.text(aoa, spd, f"{la_val:.1f}",
                    ha="center", va="center", fontsize=6.5, color="#1a1a2e", fontweight="bold")

    # Tyler's actual position
    ax.scatter([aoa_est], [bs_actual], color="#ff4444", s=200,
               zorder=5, marker="X", linewidths=2, label=f"Tyler actual: {la_actual:.1f}°")
    ax.scatter([aoa_est], [bs_actual], color="#ff4444", s=500,
               zorder=4, alpha=0.25, marker="o")

    # Optimal position
    ax.annotate(f"Optimal: {opt_la:.1f}°\n(spin ~{opt_spin:,} rpm)",
                xy=(aoa_est, bs_actual),
                xytext=(aoa_est + 3, bs_actual + 10),
                color="#ffb74d", fontsize=9, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#ffb74d"))

    ax.set_xticks(aoas)
    ax.set_xticklabels([f"{a:+d}°" for a in aoas], fontsize=8)
    ax.set_yticks(speeds)
    ax.set_yticklabels([f"{s} mph" for s in speeds], fontsize=8)
    ax.legend(facecolor="#16213e", labelcolor="#cccccc", fontsize=9)

    return f"Chart saved to: {save_chart(fig, 'driver_launch_matrix')}"


if __name__ == "__main__":
    mcp.run()