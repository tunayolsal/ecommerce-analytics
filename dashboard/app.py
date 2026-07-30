"""Olist E-Commerce Analytics — dashboard entry point (Milestone 4)."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from utils import (
    CATEGORICAL,
    fmt_currency,
    fmt_currency_short,
    fmt_int,
    kpi_row,
    load_mart,
    page_header,
    style_fig,
)

st.set_page_config(
    page_title="Olist E-Commerce Analytics",
    page_icon=":bar_chart:",
    layout="wide",
)

page_header(
    "Olist E-Commerce Analytics",
    "A Brazilian e-commerce marketplace — sales, customer segments, delivery, and payments, "
    "built entirely from pre-aggregated parquet marts (no live database needed).",
)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
summary = load_mart("summary_kpis").iloc[0]

kpi_row(
    [
        ("Total Revenue", fmt_currency_short(summary["total_revenue"])),
        ("Total Orders", fmt_int(summary["total_orders"])),
        ("Avg. Order Value", fmt_currency(summary["avg_order_value"])),
        ("Avg. Review Score", f"{summary['avg_review_score']:.2f} / 5"),
    ]
)

st.divider()

# ---------------------------------------------------------------------------
# Monthly revenue trend
# ---------------------------------------------------------------------------
st.subheader("Monthly Revenue Trend")

mrt = load_mart("monthly_revenue_trend").sort_values("order_purchase_month")
# drop the partial first/last months with near-zero volume for a cleaner line
mrt = mrt[mrt["order_count"] >= 5]

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=mrt["order_purchase_month"],
        y=mrt["total_revenue"],
        mode="lines",
        line=dict(color=CATEGORICAL[0], width=2, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(42,120,214,0.08)",
        name="Revenue",
        hovertemplate="%{x}<br>R$ %{y:,.0f}<extra></extra>",
    )
)
fig.update_layout(height=380, yaxis_title="Revenue (R$)", xaxis_title="Month", showlegend=False)
fig = style_fig(fig)
st.plotly_chart(fig, use_container_width=True)

st.info(
    "**So what?** Revenue grew rapidly through 2017-2018 as Olist scaled onto the marketplace, "
    "then flattened in 2018 — use the Sales Overview page to break this down by category and state."
)

st.divider()

st.markdown(
    """
    ### About this project

    This dashboard analyzes ~100k orders from the [Olist Brazilian E-Commerce dataset](
    https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), covering revenue trends,
    RFM customer segmentation, cohort retention, delivery performance, and payment behavior.
    Built with DuckDB (ETL/analysis), Streamlit, and Plotly.

    **GitHub:** `https://github.com/tunayolsal/ecommerce-analytics`

    Use the sidebar to navigate between pages: **Sales Overview**, **Customer Segments**,
    **Delivery and Reviews**, and **Payments**.
    """
)
