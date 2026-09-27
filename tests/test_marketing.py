from datetime import date

import pandas as pd
import pytest

from marketing import channel_performance, filter_campaigns, generate_dataset, summarize, validate_dataset


@pytest.fixture
def campaigns():
    return pd.DataFrame(
        [
            {"date": "2026-09-01", "channel": "Search", "campaign": "A", "impressions": 1000, "clicks": 100, "conversions": 10, "spend_usd": 50, "revenue_usd": 200},
            {"date": "2026-09-01", "channel": "Social", "campaign": "B", "impressions": 2000, "clicks": 200, "conversions": 20, "spend_usd": 100, "revenue_usd": 250},
            {"date": "2026-09-02", "channel": "Search", "campaign": "A", "impressions": 500, "clicks": 50, "conversions": 5, "spend_usd": 0, "revenue_usd": 75},
        ]
    )


def test_summary_uses_ratio_of_totals(campaigns):
    result = summarize(campaigns)
    assert result["spend_usd"] == 150
    assert result["revenue_usd"] == 525
    assert result["conversions"] == 35
    assert result["roas"] == pytest.approx(3.5)
    assert result["cac_usd"] == pytest.approx(150 / 35)
    assert result["ctr"] == pytest.approx(0.1)
    assert result["conversion_rate"] == pytest.approx(0.1)


def test_filters_are_inclusive_and_combine_date_and_channel(campaigns):
    result = filter_campaigns(campaigns, date(2026, 9, 1), date(2026, 9, 1), ["Search"])
    assert len(result) == 1
    assert summarize(result)["revenue_usd"] == 200


def test_channel_performance_aggregates_before_calculating_roas(campaigns):
    result = channel_performance(campaigns).set_index("channel")
    assert result.loc["Search", "roas"] == pytest.approx(5.5)
    assert result.loc["Search", "cac_usd"] == pytest.approx(50 / 15)


def test_zero_denominators_are_undefined():
    empty = pd.DataFrame(columns=["date", "channel", "campaign", "impressions", "clicks", "conversions", "spend_usd", "revenue_usd"])
    result = summarize(empty)
    assert result["roas"] is None
    assert result["cac_usd"] is None
    assert result["ctr"] is None
    assert result["conversion_rate"] is None


def test_validation_rejects_impossible_funnel(campaigns):
    campaigns.loc[0, "conversions"] = 101
    with pytest.raises(ValueError, match="conversions"):
        validate_dataset(campaigns)


def test_generator_is_reproducible_and_has_unique_grain():
    first = generate_dataset(days=14, seed=2026)
    second = generate_dataset(days=14, seed=2026)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 14 * 4 * 2
    assert not first.duplicated(["date", "channel", "campaign"]).any()
    validate_dataset(first)
