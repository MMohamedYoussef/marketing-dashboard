"""Run with: streamlit run app.py"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from marketing import channel_performance, filter_campaigns, summarize, validate_dataset


st.set_page_config(page_title="Campaign Pulse", page_icon="📊", layout="wide")
st.markdown("""
<style>
  .stApp { background: #0c1422; color: #e8f0f8; }
  [data-testid="stSidebar"] { background: #142236; }
  .block-container { max-width: 1450px; padding-top: 2rem; }
  h1, h2, h3 { color: #f5f9ff; }
  [data-testid="stMetric"] { background: #17283d; padding: 1rem 1.25rem; border: 1px solid #29415d; border-radius: 14px; }
  [data-testid="stMetricLabel"] { color: #9fb4c8; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_campaigns() -> pd.DataFrame:
    path = Path(__file__).parent / "data" / "campaigns.csv"
    frame = pd.read_csv(path)
    validate_dataset(frame)
    return frame


def money(value: float | None) -> str:
    return "—" if value is None else f"${value:,.2f}"


def ratio(value: float | None) -> str:
    return "—" if value is None else f"{value:,.2f}×"


st.caption("PORTFOLIO / SYNTHETIC CAMPAIGN ANALYTICS")
st.title("Campaign Pulse")
st.write("Explore channel efficiency, acquisition cost and revenue movement across generated campaigns.")

try:
    campaigns = load_campaigns()
except (FileNotFoundError, ValueError) as error:
    st.error(f"Campaign data unavailable: {error}. Run `python marketing.py` to generate it.")
    st.stop()

min_day = pd.to_datetime(campaigns["date"]).min().date()
max_day = pd.to_datetime(campaigns["date"]).max().date()
with st.sidebar:
    st.header("Filters")
    start_day = st.date_input("From", min_day, min_value=min_day, max_value=max_day)
    end_day = st.date_input("Through", max_day, min_value=min_day, max_value=max_day)
    selected_channels = st.multiselect("Channels", sorted(campaigns["channel"].unique()), default=sorted(campaigns["channel"].unique()))
    st.caption("All records are synthetic. Revenue is attributed to the same campaign day for this demo.")

if start_day > end_day:
    st.warning("The start date must be on or before the end date.")
    st.stop()

filtered = filter_campaigns(campaigns, start_day, end_day, selected_channels)
if filtered.empty:
    st.info("No campaign rows match these filters.")
    st.stop()

summary = summarize(filtered)
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Revenue", money(summary["revenue_usd"]))
col2.metric("Ad spend", money(summary["spend_usd"]))
col3.metric("Conversions", f"{summary['conversions']:,}")
col4.metric("ROAS", ratio(summary["roas"]))
col5.metric("CAC", money(summary["cac_usd"]))

palette = {"Revenue": "#34d3bd", "Spend": "#f6af63", "Search": "#34d3bd", "Social": "#86a9ff", "Email": "#f6af63", "Display": "#ed88bf"}
daily = filtered.groupby("date", as_index=False)[["spend_usd", "revenue_usd", "conversions"]].sum()
daily = daily.rename(columns={"spend_usd": "Spend", "revenue_usd": "Revenue"})
trend = daily.melt(id_vars="date", value_vars=["Revenue", "Spend"], var_name="Metric", value_name="USD")
fig_trend = px.line(trend, x="date", y="USD", color="Metric", color_discrete_map=palette, title="Revenue and spend over time")
fig_trend.update_traces(line_width=2.8)
fig_trend.update_layout(template="plotly_dark", paper_bgcolor="#17283d", plot_bgcolor="#17283d", legend_title_text="", margin=dict(l=20, r=20, t=55, b=20), height=380)
fig_trend.update_xaxes(title_text="", showgrid=False)
fig_trend.update_yaxes(title_text="USD", gridcolor="#29415d")

channels = channel_performance(filtered)
channel_long = channels.rename(columns={"spend_usd": "Spend", "revenue_usd": "Revenue"}).melt(id_vars="channel", value_vars=["Spend", "Revenue"], var_name="Metric", value_name="USD")
fig_channels = px.bar(channel_long, x="channel", y="USD", color="Metric", barmode="group", color_discrete_map=palette, title="Spend versus revenue by channel")
fig_channels.update_layout(template="plotly_dark", paper_bgcolor="#17283d", plot_bgcolor="#17283d", legend_title_text="", margin=dict(l=20, r=20, t=55, b=20), height=380)
fig_channels.update_xaxes(title_text="", showgrid=False)
fig_channels.update_yaxes(title_text="USD", gridcolor="#29415d")

left, right = st.columns([1.6, 1])
with left:
    st.plotly_chart(fig_trend, use_container_width=True)
with right:
    st.plotly_chart(fig_channels, use_container_width=True)

left, right = st.columns([1.6, 1])
with left:
    st.subheader("Channel scorecard")
    scorecard = channels[["channel", "spend_usd", "revenue_usd", "conversions", "roas", "cac_usd"]].rename(columns={
        "channel": "Channel", "spend_usd": "Spend ($)", "revenue_usd": "Revenue ($)",
        "conversions": "Conversions", "roas": "ROAS", "cac_usd": "CAC ($)",
    })
    st.dataframe(scorecard.style.format({"Spend ($)": "{:,.2f}", "Revenue ($)": "{:,.2f}", "ROAS": "{:.2f}×", "CAC ($)": "{:,.2f}"}), use_container_width=True, hide_index=True)
with right:
    st.subheader("Funnel quality")
    st.metric("Click-through rate", f"{summary['ctr']:.2%}" if summary["ctr"] is not None else "—")
    st.metric("Click-to-conversion rate", f"{summary['conversion_rate']:.2%}" if summary["conversion_rate"] is not None else "—")
    st.caption("Ratios use summed numerators and denominators, not an average of row percentages.")

with st.expander("Metric definitions and assumptions"):
    st.markdown("""
- **ROAS** = attributed revenue / advertising spend.
- **CAC** = advertising spend / conversions. Each conversion is treated as one newly acquired customer in this synthetic model.
- **CTR** = clicks / impressions; **conversion rate** = conversions / clicks.
- A zero denominator is undefined and appears as an em dash. Revenue excludes refunds, tax and organic sales.
""")
