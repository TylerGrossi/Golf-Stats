from mcp.server.fastmcp import FastMCP
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os, tempfile

mcp = FastMCP("Golf Analytics")

BASE = os.environ.get(
    "GOLF_DATA_DIR",
    os.path.join(os.path.expanduser("~"), "Desktop", "Tyler", "OneDrive", "Projects", "Golf Stats")
)

# ── Load all data ─────────────────────────────────────────────────────────────
xl = pd.ExcelFile(os.path.join(BASE, "Golf Stats Multiple Users.xlsx"))
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

# ── Chart helpers ─────────────────────────────────────────────────────────────
CHART_DIR = tempfile.mkdtemp()

def save_chart(fig, name: str) -> str:
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


# ═══════════════════════════════════════════════════════════════════════════════
# SCORING
# ═══════════════════════════════════════════════════════════════════════════════

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
    style_ax(ax, title="Tyler's Handicap Differential Trend",
             xlabel="Date", ylabel="Differential")
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


# ═══════════════════════════════════════════════════════════════════════════════
# RANGE STATS — SHOT-LEVEL TRACKMAN DATA
# ═══════════════════════════════════════════════════════════════════════════════

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

    numeric_cols = ["Carry Distance","Total Distance","Ball Speed","Launch Angle",
                    "Club Speed","Smash Factor","Apex","Side Carry","Descent Angle"]
    avail = [c for c in numeric_cols if c in df.columns]
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
def get_club_consistency(club: str) -> str:
    """
    Analyze how consistent Tyler is with a specific club.
    Looks at carry distance spread, smash factor, and side carry (accuracy).
    """
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
        f"  Range:     {carry.min():.0f} – {carry.max():.0f} yds",
        f"\nAccuracy (Side Carry):",
        f"  Avg miss:  {side.abs().mean():.1f} yds",
        f"  Miss bias: {'Right' if side.mean() > 0 else 'Left'} ({abs(side.mean()):.1f} yds avg)",
    ]
    if not smash.empty:
        lines += [
            f"\nSmash Factor:",
            f"  Average:  {smash.mean():.3f}  (driver ideal ~1.48, irons ~1.38)",
            f"  Best:     {smash.max():.3f}",
        ]
    if "Launch Angle" in df.columns:
        la = df["Launch Angle"].dropna()
        lines.append(f"\nLaunch Angle: avg {la.mean():.1f}°  ({la.min():.1f}° – {la.max():.1f}°)")
    if "Club Speed" in df.columns:
        cs = df["Club Speed"].dropna()
        lines.append(f"Club Speed:   avg {cs.mean():.1f} mph  ({cs.min():.1f} – {cs.max():.1f})")
    return "\n".join(lines)


@mcp.tool()
def chart_club_carry_distribution(club: str) -> str:
    """
    Generate a histogram of carry distance for a specific club.
    Shows how tight or spread Tyler's distances are.
    """
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
    ax.axvline(carry.mean() - carry.std(), color="#ef5350", linewidth=1.2, linestyle=":",
               label=f"±1 SD: {carry.mean()-carry.std():.0f}–{carry.mean()+carry.std():.0f}")
    ax.axvline(carry.mean() + carry.std(), color="#ef5350", linewidth=1.2, linestyle=":")
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    return f"Chart saved to: {save_chart(fig, f'carry_dist_{club}')}"


@mcp.tool()
def chart_club_stats_over_time(club: str, stat: str = "Carry Distance") -> str:
    """
    Chart how a club stat has changed across range sessions over time.
    stat options: 'Carry Distance', 'Ball Speed', 'Smash Factor', 'Launch Angle',
                  'Club Speed', 'Side Carry', 'Apex', 'Descent Angle'
    """
    valid = ["Carry Distance","Ball Speed","Smash Factor","Launch Angle",
             "Club Speed","Side Carry","Apex","Descent Angle"]
    if stat not in valid:
        return f"Invalid stat. Choose from: {valid}"
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].dropna(subset=["Date", stat]).copy()
    if df.empty:
        return f"No data for {club}/{stat}."
    session = df.groupby("Date")[stat].mean().reset_index()

    fig, ax = plt.subplots(figsize=(10, 4), facecolor="#1a1a2e")
    style_ax(ax, title=f"{club.upper()} — {stat} Over Time", xlabel="Date", ylabel=stat)
    ax.plot(session["Date"], session[stat], color="#4fc3f7", linewidth=2,
            marker="o", markersize=6, markerfacecolor="#ffffff")
    if len(session) >= 3:
        z = np.polyfit(range(len(session)), session[stat], 1)
        direction = "improving ↑" if z[0] > 0 else "declining ↓"
        ax.plot(session["Date"], np.poly1d(z)(range(len(session))), "--",
                color="#ff7043", linewidth=1.5, label=f"Trend ({direction})")
        ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d '%y"))
    plt.xticks(rotation=30)
    return f"Chart saved to: {save_chart(fig, f'{club}_{stat.replace(chr(32), chr(95))}_trend')}"


@mcp.tool()
def chart_all_clubs_carry_comparison() -> str:
    """
    Box plot comparing carry distance distributions across all clubs.
    Best way to see the full bag picture and identify distance gaps.
    """
    df = tyler_range.dropna(subset=["Carry Distance"]).copy()
    club_order = ["lw - 30","lw - 50","lw","sw","gw","pw","9i","8i","7i","6i","5i","4i","3h","3w","d"]
    present = [c for c in club_order if c in df["Club Type"].values]
    data = [df[df["Club Type"] == c]["Carry Distance"].values for c in present]

    fig, ax = plt.subplots(figsize=(14, 5), facecolor="#1a1a2e")
    style_ax(ax, title="Full Bag Carry Distance Comparison (Trackman Range Data)",
             xlabel="Club", ylabel="Carry Distance (yds)")
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
def chart_smash_factor_by_club() -> str:
    """
    Chart smash factor (energy efficiency) by club vs ideal benchmarks.
    Driver ideal ~1.48, irons ~1.38. Higher = more efficient strike.
    """
    df = tyler_range.dropna(subset=["Smash Factor"]).copy()
    summary = df.groupby("Club Type")["Smash Factor"].mean().reset_index()
    club_order = ["lw - 30","lw - 50","lw","sw","gw","pw","9i","8i","7i","6i","5i","4i","3h","3w","d"]
    summary["order"] = summary["Club Type"].map({c: i for i, c in enumerate(club_order)})
    summary = summary.sort_values("order").dropna(subset=["order"])

    fig, ax = plt.subplots(figsize=(12, 4), facecolor="#1a1a2e")
    style_ax(ax, title="Avg Smash Factor by Club vs Ideal", xlabel="Club", ylabel="Smash Factor")
    bars = ax.bar(summary["Club Type"], summary["Smash Factor"],
                  color="#4fc3f7", edgecolor="#1a1a2e", alpha=0.85)
    ax.axhline(1.48, color="#ff7043", linewidth=1.5, linestyle="--", label="Driver ideal (1.48)")
    ax.axhline(1.38, color="#ffb74d", linewidth=1.5, linestyle="--", label="Iron ideal (1.38)")
    for bar, val in zip(bars, summary["Smash Factor"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{val:.2f}", ha="center", va="bottom", color="#cccccc", fontsize=8)
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    return f"Chart saved to: {save_chart(fig, 'smash_factor')}"


@mcp.tool()
def chart_launch_angle_by_club() -> str:
    """
    Chart Tyler's avg launch angle per club vs ideal benchmarks.
    Helps identify clubs launching too low or too high.
    """
    ideals = {"d":13,"3w":14,"3h":16,"4i":17,"5i":19,"6i":21,
              "7i":23,"8i":25,"9i":27,"pw":29,"gw":32,"sw":35,"lw":38}
    df = tyler_range.dropna(subset=["Launch Angle"]).copy()
    summary = df.groupby("Club Type")["Launch Angle"].mean().reset_index()
    club_order = list(ideals.keys())
    summary["order"] = summary["Club Type"].map({c: i for i, c in enumerate(club_order)})
    summary = summary.sort_values("order").dropna(subset=["order"])
    summary["Ideal"] = summary["Club Type"].map(ideals)

    fig, ax = plt.subplots(figsize=(12, 4), facecolor="#1a1a2e")
    style_ax(ax, title="Avg Launch Angle by Club vs Ideal", xlabel="Club", ylabel="Launch Angle (°)")
    x = np.arange(len(summary))
    ax.bar(x - 0.2, summary["Launch Angle"], 0.4, label="Tyler's avg", color="#4fc3f7", alpha=0.85)
    ax.bar(x + 0.2, summary["Ideal"], 0.4, label="Ideal benchmark", color="#ff7043", alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(summary["Club Type"])
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    return f"Chart saved to: {save_chart(fig, 'launch_angle')}"


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
    stat options: 'Carry Distance', 'Ball Speed', 'Smash Factor', 'Launch Angle', 'Club Speed', 'Side Carry'
    """
    df = tyler_range[tyler_range["Club Type"].str.lower() == club.lower()].dropna(subset=[stat]).copy()
    if df.empty:
        return f"No data for {club}."
    session = df.groupby("Date")[stat].agg(["mean","std","count"]).round(2)
    session.index = session.index.strftime("%Y-%m-%d")
    session.columns = [f"Avg {stat}", "Std Dev", "Shots"]
    return f"{club.upper()} — {stat} by session:\n\n" + session.to_string()


@mcp.tool()
def chart_distance_gaps() -> str:
    """Visual chart of Tyler's full bag distance coverage with error bars showing spread."""
    rs = tyler_range.groupby("Club Type")["Carry Distance"].agg(["mean","std"]).reset_index()
    rs.columns = ["Club","Avg","Std"]
    club_order = ["lw - 30","lw - 50","lw","sw","gw","pw","9i","8i","7i","6i","5i","4i","3h","3w","d"]
    rs["order"] = rs["Club"].map({c: i for i, c in enumerate(club_order)})
    rs = rs.sort_values("order").dropna(subset=["order"])

    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#1a1a2e")
    style_ax(ax, title="Full Bag Distance Coverage (Trackman Data)",
             xlabel="Club", ylabel="Carry Distance (yds)")
    x = np.arange(len(rs))
    ax.bar(x, rs["Avg"], color="#4fc3f7", alpha=0.8, label="Avg carry")
    ax.errorbar(x, rs["Avg"], yerr=rs["Std"], fmt="none",
                color="#ffb74d", capsize=5, linewidth=2, label="±1 SD")
    for xi, (_, row) in zip(x, rs.iterrows()):
        ax.text(xi, row["Avg"] + row["Std"] + 2, f'{row["Avg"]:.0f}',
                ha="center", va="bottom", color="#eeeeee", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(rs["Club"])
    ax.legend(facecolor="#16213e", labelcolor="#cccccc")
    return f"Chart saved to: {save_chart(fig, 'distance_gaps')}"


@mcp.tool()
def get_club_distance_gaps() -> str:
    """Identify distance gaps or overlaps in Tyler's bag using Trackman data."""
    rs = tyler_range.groupby("Club Type")["Carry Distance"].agg(["mean","std"]).reset_index()
    rs.columns = ["Club","Avg","Std"]
    rs["Low"]  = rs["Avg"] - rs["Std"]
    rs["High"] = rs["Avg"] + rs["Std"]
    club_order = ["lw - 30","lw - 50","lw","sw","gw","pw","9i","8i","7i","6i","5i","4i","3h","3w","d"]
    rs["order"] = rs["Club"].map({c: i for i, c in enumerate(club_order)})
    rs = rs.sort_values("order").dropna(subset=["order"]).reset_index(drop=True)

    lines = ["Distance gap analysis (Trackman):\n",
             f"{'Club':<8} {'Avg':>6} {'±1SD Range':>16} {'Gap to Next':>14}"]
    lines.append("-" * 50)
    for i, row in rs.iterrows():
        if i < len(rs) - 1:
            nxt = rs.iloc[i + 1]
            gap = nxt["Low"] - row["High"]
            gap_str = f"{gap:+.0f} yds"
            flag = "  ⚠️ GAP" if gap > 5 else ("  🔴 OVERLAP" if gap < -10 else "")
        else:
            gap_str, flag = "—", ""
        lines.append(f"{row['Club']:<8} {row['Avg']:>6.1f} {row['Low']:>6.0f}–{row['High']:<8.0f} {gap_str}{flag}")
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
    for club_name, diff in closest.items():
        lines.append(f"  {club_name.upper():<6}  avg carry {rs_avgs[club_name]:.1f} yds  (diff: {diff:+.1f})")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# STROKES GAINED
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_strokes_gained_summary(last_n_rounds: int = 10) -> str:
    """Get Tyler's strokes gained breakdown. Negative = worse than scratch golfer."""
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
    cats = ["SG_OTT","SG_Approach","SG_ARG","SG_Putting"]
    labels = ["Off Tee","Approach","Around Green","Putting"]
    vals = [recent[c].mean() for c in cats]
    min_v, max_v = min(vals) - 0.5, max(vals) + 0.5
    norm = [(v - min_v) / (max_v - min_v) for v in vals]
    norm += norm[:1]
    angles = np.linspace(0, 2 * np.pi, len(cats), endpoint=False).tolist()
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


# ═══════════════════════════════════════════════════════════════════════════════
# COURSE, CLUTCH & HEAD-TO-HEAD
# ═══════════════════════════════════════════════════════════════════════════════

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)