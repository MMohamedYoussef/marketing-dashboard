"""Render a shareable static PNG of the dashboard from the checked-in CSV."""

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).parent / ".cache" / "matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter, MaxNLocator
import pandas as pd

from marketing import channel_performance, summarize, validate_dataset


ROOT = Path(__file__).parent
frame = pd.read_csv(ROOT / "data" / "campaigns.csv")
validate_dataset(frame)
metrics = summarize(frame)
channels = channel_performance(frame)
daily = frame.groupby("date", as_index=False)[["spend_usd", "revenue_usd"]].sum()

background, panel, text, muted, grid = "#0c1422", "#17283d", "#f5f9ff", "#9fb4c8", "#29415d"
teal, orange, blue = "#34d3bd", "#f6af63", "#86a9ff"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
fig = plt.figure(figsize=(17, 9.2), facecolor=background)
fig.text(0.05, 0.94, "CAMPAIGN PULSE", color=text, fontsize=27, weight="bold")
fig.text(0.05, 0.907, "Synthetic campaign performance  |  01 Jan – 30 Apr 2026", color=muted, fontsize=12)

cards = [
    ("REVENUE", f"${metrics['revenue_usd']:,.0f}"),
    ("AD SPEND", f"${metrics['spend_usd']:,.0f}"),
    ("CONVERSIONS", f"{metrics['conversions']:,}"),
    ("ROAS", f"{metrics['roas']:.2f}×"),
    ("CAC", f"${metrics['cac_usd']:.2f}"),
]
for index, (label, value) in enumerate(cards):
    x = 0.05 + index * 0.185
    fig.add_artist(FancyBboxPatch((x, 0.75), 0.17, 0.125, boxstyle="round,pad=0.009,rounding_size=0.016", transform=fig.transFigure, facecolor=panel, edgecolor=grid, linewidth=1))
    fig.text(x + 0.014, 0.841, label, color=muted, fontsize=10, weight="bold")
    fig.text(x + 0.014, 0.787, value, color=text, fontsize=23, weight="bold")

ax_trend = fig.add_axes((0.065, 0.38, 0.54, 0.31), facecolor=panel)
ax_trend.plot(pd.to_datetime(daily["date"]), daily["revenue_usd"], color=teal, linewidth=2.5, label="Revenue")
ax_trend.plot(pd.to_datetime(daily["date"]), daily["spend_usd"], color=orange, linewidth=2.3, label="Spend")
ax_trend.set_title("Revenue and spend over time", loc="left", color=text, weight="bold", pad=20)
ax_trend.legend(facecolor=panel, labelcolor=text, edgecolor=grid, ncol=2)
ax_trend.tick_params(colors=muted)
ax_trend.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
ax_trend.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax_trend.grid(axis="y", color=grid, alpha=0.7)
for spine in ax_trend.spines.values():
    spine.set_visible(False)

ax_channels = fig.add_axes((0.67, 0.38, 0.27, 0.31), facecolor=panel)
labels = channels["channel"].tolist()
positions = list(range(len(labels)))
ax_channels.barh([x - 0.18 for x in positions], channels["revenue_usd"], height=0.34, color=teal, label="Revenue")
ax_channels.barh([x + 0.18 for x in positions], channels["spend_usd"], height=0.34, color=orange, label="Spend")
ax_channels.set_yticks(positions, labels)
ax_channels.invert_yaxis()
ax_channels.set_title("Channel returns", loc="left", color=text, weight="bold", pad=20)
ax_channels.legend(facecolor=panel, labelcolor=text, edgecolor=grid, ncol=2)
ax_channels.tick_params(colors=muted)
ax_channels.xaxis.set_major_locator(MaxNLocator(nbins=4))
ax_channels.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"${value / 1000:.0f}k"))
ax_channels.grid(axis="x", color=grid, alpha=0.7)
for spine in ax_channels.spines.values():
    spine.set_visible(False)

ax_table = fig.add_axes((0.065, 0.11, 0.875, 0.20), facecolor=panel)
ax_table.axis("off")
ax_table.set_title("Channel scorecard", loc="left", color=text, weight="bold", pad=18)
headers = ["CHANNEL", "SPEND", "REVENUE", "CONVERSIONS", "ROAS", "CAC"]
values = [[r.channel, f"${r.spend_usd:,.0f}", f"${r.revenue_usd:,.0f}", f"{r.conversions:,}", f"{r.roas:.2f}×", f"${r.cac_usd:.2f}"] for r in channels.itertuples()]
table = ax_table.table(cellText=values, colLabels=headers, bbox=[0, 0, 1, 0.88], cellLoc="left", colLoc="left")
table.auto_set_font_size(False)
table.set_fontsize(10)
for (row, _), cell in table.get_celld().items():
    cell.set_edgecolor(grid)
    cell.set_facecolor(panel if row % 2 == 0 else background)
    cell.get_text().set_color(muted if row == 0 else text)
    if row == 0:
        cell.get_text().set_weight("bold")

fig.text(0.05, 0.035, "Synthetic data  •  ROAS = revenue / spend  •  CAC = spend / conversions", color=muted, fontsize=10)
assets = ROOT / "assets"
assets.mkdir(exist_ok=True)
fig.savefig(assets / "dashboard-preview.png", dpi=140, facecolor=background)
plt.close(fig)
with (assets / "metrics.json").open("w", encoding="utf-8") as handle:
    json.dump(metrics, handle, indent=2)
print(f"Wrote {assets / 'dashboard-preview.png'} and metrics.json")
