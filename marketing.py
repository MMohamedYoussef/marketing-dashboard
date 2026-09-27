"""Deterministic campaign data and audited metric calculations."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd


REQUIRED = ["date", "channel", "campaign", "impressions", "clicks", "conversions", "spend_usd", "revenue_usd"]
CHANNELS = {
    "Search": (6000, 0.055, 0.055, 1.30, 89),
    "Social": (9200, 0.023, 0.030, 0.78, 74),
    "Email": (3900, 0.080, 0.065, 0.78, 82),
    "Display": (12500, 0.010, 0.018, 0.44, 70),
}


def generate_dataset(days: int = 120, seed: int = 20260927) -> pd.DataFrame:
    """Create one row per date, channel and campaign with a fixed random seed."""
    if days < 1:
        raise ValueError("days must be positive")
    rng = random.Random(seed)
    records = []
    start = date(2026, 1, 1)
    for offset in range(days):
        day = start + timedelta(days=offset)
        weekend = 0.75 if day.weekday() >= 5 else 1.0
        for channel, (base, ctr, cvr, cpc, order_value) in CHANNELS.items():
            for campaign in ("Core", "Growth"):
                lift = 1.13 if campaign == "Core" else 0.88
                impressions = round(base * weekend * lift * rng.uniform(0.82, 1.18))
                clicks = min(impressions, round(impressions * ctr * rng.uniform(0.73, 1.28)))
                conversions = min(clicks, round(clicks * cvr * rng.uniform(0.70, 1.35)))
                spend = round(clicks * cpc * rng.uniform(0.87, 1.12), 2)
                revenue = round(conversions * order_value * rng.uniform(0.84, 1.22), 2)
                records.append({
                    "date": day.isoformat(), "channel": channel, "campaign": campaign,
                    "impressions": impressions, "clicks": clicks, "conversions": conversions,
                    "spend_usd": spend, "revenue_usd": revenue,
                })
    result = pd.DataFrame.from_records(records, columns=REQUIRED)
    validate_dataset(result)
    return result


def validate_dataset(frame: pd.DataFrame) -> None:
    """Reject invalid grain, missing values and impossible funnel counts."""
    missing = set(REQUIRED) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    if frame[REQUIRED].isna().any().any():
        raise ValueError("Missing values in required columns")
    if frame[["date", "channel", "campaign"]].astype(str).eq("").any().any():
        raise ValueError("Empty date, channel or campaign")
    pd.to_datetime(frame["date"], format="%Y-%m-%d", errors="raise")
    if frame.duplicated(["date", "channel", "campaign"]).any():
        raise ValueError("Duplicate campaign grain")
    numeric = frame[["impressions", "clicks", "conversions", "spend_usd", "revenue_usd"]].apply(pd.to_numeric, errors="raise")
    if numeric.lt(0).any().any():
        raise ValueError("Negative values are not allowed")
    for column in ("impressions", "clicks", "conversions"):
        if (numeric[column] % 1 != 0).any():
            raise ValueError(f"{column} must be an integer")
    if (numeric["clicks"] > numeric["impressions"]).any():
        raise ValueError("clicks exceed impressions")
    if (numeric["conversions"] > numeric["clicks"]).any():
        raise ValueError("conversions exceed clicks")


def filter_campaigns(frame: pd.DataFrame, start: date, end: date, channels: list[str]) -> pd.DataFrame:
    """Apply inclusive dates and selected channels to the campaign grain."""
    if start > end:
        raise ValueError("start must be on or before end")
    dates = pd.to_datetime(frame["date"], format="%Y-%m-%d").dt.date
    return frame.loc[dates.between(start, end) & frame["channel"].isin(channels)].copy()


def _ratio(numerator: float, denominator: float) -> float | None:
    return float(numerator / denominator) if denominator else None


def summarize(frame: pd.DataFrame) -> dict[str, float | int | None]:
    """Compute weighted KPIs from aggregate numerators and denominators."""
    totals = frame[["impressions", "clicks", "conversions", "spend_usd", "revenue_usd"]].sum()
    impressions, clicks, conversions = (int(totals[key]) for key in ("impressions", "clicks", "conversions"))
    spend, revenue = (float(totals[key]) for key in ("spend_usd", "revenue_usd"))
    return {
        "impressions": impressions, "clicks": clicks, "conversions": conversions,
        "spend_usd": spend, "revenue_usd": revenue,
        "roas": _ratio(revenue, spend),
        "cac_usd": _ratio(spend, conversions),
        "ctr": _ratio(clicks, impressions),
        "conversion_rate": _ratio(conversions, clicks),
    }


def channel_performance(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate rows first, then calculate ratios for each channel."""
    columns = ["channel", "impressions", "clicks", "conversions", "spend_usd", "revenue_usd", "roas", "cac_usd"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    grouped = frame.groupby("channel", as_index=False)[["impressions", "clicks", "conversions", "spend_usd", "revenue_usd"]].sum()
    grouped["roas"] = grouped.apply(lambda row: _ratio(row["revenue_usd"], row["spend_usd"]), axis=1)
    grouped["cac_usd"] = grouped.apply(lambda row: _ratio(row["spend_usd"], row["conversions"]), axis=1)
    return grouped[columns].sort_values("revenue_usd", ascending=False).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic marketing campaigns")
    parser.add_argument("--days", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20260927)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data" / "campaigns.csv")
    arguments = parser.parse_args()
    data = generate_dataset(arguments.days, arguments.seed)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(arguments.output, index=False)
    print(f"Wrote {len(data)} campaign-days to {arguments.output}")


if __name__ == "__main__":
    main()
