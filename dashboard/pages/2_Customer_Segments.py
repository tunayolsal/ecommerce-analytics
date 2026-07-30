"""Customer Segments — RFM segmentation and cohort retention."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import CATEGORICAL, load_mart, page_header, style_fig

st.set_page_config(page_title="Customer Segments | Olist Analytics", page_icon=":busts_in_silhouette:", layout="wide")

page_header("Customer Segments", "RFM (Recency, Frequency, Monetary) segmentation and repeat-purchase cohorts.")

# ---------------------------------------------------------------------------
# RFM segment summary
# ---------------------------------------------------------------------------
st.subheader("RFM Segments")

seg = load_mart("rfm_segment_summary").sort_values("total_revenue", ascending=False)

fig_tree = px.treemap(
    seg,
    path=[px.Constant("All customers"), "segment"],
    values="customer_count",
    color="segment",
    color_discrete_sequence=CATEGORICAL,
    custom_data=["total_revenue", "avg_revenue_per_customer"],
)
fig_tree.update_traces(
    hovertemplate="<b>%{label}</b><br>Customers: %{value:,}<br>Revenue: R$ %{customdata[0]:,.0f}<br>Avg/customer: R$ %{customdata[1]:,.2f}<extra></extra>",
    textinfo="label+value",
)
fig_tree.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0))
fig_tree = style_fig(fig_tree)
st.plotly_chart(fig_tree, use_container_width=True)

st.markdown("**Segment definitions**")
seg_defs = {
    "Champions": "Bought recently, buy often, spend the most",
    "Loyal Customers": "Buy regularly with good recency/frequency",
    "New Customers": "Bought recently but low frequency so far",
    "Big Spenders": "Spend a lot, decent recency, low frequency",
    "At Risk": "Used to buy often, haven't purchased recently",
    "Cant Lose Them": "High spend historically, gone quiet",
    "Hibernating": "Low recency, frequency, and monetary — inactive",
    "Needs Attention": "Below-average across the board",
}
seg_table = seg.copy()
seg_table["definition"] = seg_table["segment"].map(seg_defs).fillna("")
st.dataframe(
    seg_table[["segment", "definition", "customer_count", "total_revenue", "avg_revenue_per_customer"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "segment": "Segment",
        "definition": "Definition",
        "customer_count": st.column_config.NumberColumn("Customers", format="%d"),
        "total_revenue": st.column_config.NumberColumn("Total Revenue (R$)", format="%.2f"),
        "avg_revenue_per_customer": st.column_config.NumberColumn("Avg Revenue/Customer (R$)", format="%.2f"),
    },
)

top_seg = seg.iloc[0]
st.info(
    f"**So what?** *{top_seg['segment']}* generates the most revenue "
    f"(R$ {top_seg['total_revenue']:,.0f} from {top_seg['customer_count']:,} customers) — "
    "since Olist customers rarely repeat-purchase (see the cohort matrix below), retention "
    "campaigns targeting 'At Risk' and 'Cant Lose Them' segments have the highest leverage."
)

st.divider()

# ---------------------------------------------------------------------------
# Cohort retention heatmap
# ---------------------------------------------------------------------------
st.subheader("Cohort Retention")

cohort = load_mart("cohort_retention_matrix").copy()
cohort["cohort_month"] = cohort["cohort_month"].astype(str)

pivot = cohort.pivot(index="cohort_month", columns="months_since_first", values="retention_pct").sort_index()
# limit to first 12 month offsets for readability
pivot = pivot[[c for c in pivot.columns if c <= 11]]

fig_heat = px.imshow(
    pivot,
    color_continuous_scale=[
        "#fcfcfb", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b",
    ],
    labels=dict(x="Months Since First Purchase", y="Acquisition Cohort", color="Retention %"),
    aspect="auto",
)
fig_heat.update_traces(hovertemplate="Cohort: %{y}<br>Month %{x}<br>Retention: %{z}%<extra></extra>")
fig_heat.update_layout(height=520)
fig_heat = style_fig(fig_heat)
st.plotly_chart(fig_heat, use_container_width=True)

month0 = cohort[cohort["months_since_first"] == 0]
month1 = cohort[cohort["months_since_first"] == 1]
avg_m1_retention = month1["retention_pct"].mean() if len(month1) else float("nan")
st.info(
    f"**So what?** Retention falls off a cliff after month 0 — average month-1 retention is only "
    f"about {avg_m1_retention:.1f}%. Olist customers are overwhelmingly one-time buyers, which "
    "explains why the RFM 'Loyal Customers' / 'Champions' segments are small relative to the base "
    "and why acquisition (not retention) has driven most of the growth seen on the Sales Overview page."
)
