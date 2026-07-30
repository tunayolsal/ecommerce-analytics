"""Sales Overview — category, geography, and monthly order trends."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import CATEGORICAL, SEQUENTIAL_BLUE, load_mart, page_header, style_fig

st.set_page_config(page_title="Sales Overview | Olist Analytics", page_icon=":bar_chart:", layout="wide")

page_header("Sales Overview", "Where revenue comes from — by product category, state, and month.")

# ---------------------------------------------------------------------------
# Top-15 categories by revenue
# ---------------------------------------------------------------------------
st.subheader("Top 15 Product Categories by Revenue")

cat = load_mart("revenue_by_category").sort_values("total_revenue", ascending=True)

fig_cat = go.Figure()
fig_cat.add_trace(
    go.Bar(
        x=cat["total_revenue"],
        y=cat["category"],
        orientation="h",
        marker=dict(color=CATEGORICAL[0]),
        hovertemplate="%{y}<br>R$ %{x:,.0f}<extra></extra>",
    )
)
fig_cat.update_layout(height=520, xaxis_title="Revenue (R$)", yaxis_title="")
fig_cat = style_fig(fig_cat)
st.plotly_chart(fig_cat, use_container_width=True)

top_cat = cat.iloc[-1]
st.info(
    f"**So what?** *{top_cat['category'].replace('_', ' ').title()}* is the single biggest revenue "
    f"driver at R$ {top_cat['total_revenue']:,.0f}. Revenue is fairly spread across the top 15 "
    "categories rather than concentrated in one or two — a broad catalog strategy, not a hero-SKU one."
)

st.divider()

# ---------------------------------------------------------------------------
# Revenue by state
# ---------------------------------------------------------------------------
st.subheader("Revenue by Customer State")

state = load_mart("revenue_by_state").sort_values("total_revenue", ascending=False)

tab_map, tab_bar = st.tabs(["Map", "Bar chart"])

with tab_map:
    try:
        fig_map = px.choropleth(
            state,
            geojson="https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson",
            featureidkey="properties.sigla",
            locations="customer_state",
            color="total_revenue",
            color_continuous_scale=SEQUENTIAL_BLUE,
            scope="south america",
            labels={"total_revenue": "Revenue (R$)"},
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0))
        fig_map = style_fig(fig_map)
        st.plotly_chart(fig_map, use_container_width=True)
    except Exception as exc:  # pragma: no cover - network-dependent fallback
        st.warning(f"Map unavailable ({exc}); showing bar chart instead.")
        state_sorted = state.sort_values("total_revenue", ascending=True).tail(15)
        fig_state = go.Figure(
            go.Bar(
                x=state_sorted["total_revenue"],
                y=state_sorted["customer_state"],
                orientation="h",
                marker=dict(color=CATEGORICAL[0]),
            )
        )
        fig_state = style_fig(fig_state)
        st.plotly_chart(fig_state, use_container_width=True)

with tab_bar:
    state_sorted = state.sort_values("total_revenue", ascending=True).tail(15)
    fig_state = go.Figure(
        go.Bar(
            x=state_sorted["total_revenue"],
            y=state_sorted["customer_state"],
            orientation="h",
            marker=dict(color=CATEGORICAL[0]),
            hovertemplate="%{y}<br>R$ %{x:,.0f}<extra></extra>",
        )
    )
    fig_state.update_layout(height=480, xaxis_title="Revenue (R$)", yaxis_title="")
    fig_state = style_fig(fig_state)
    st.plotly_chart(fig_state, use_container_width=True)

top_state = state.iloc[0]
st.info(
    f"**So what?** {top_state['customer_state']} alone accounts for R$ {top_state['total_revenue']:,.0f} "
    f"({top_state['order_count']:,} orders) — customer demand is heavily concentrated in Brazil's "
    "southeast, which should drive logistics and marketing prioritization."
)

st.divider()

# ---------------------------------------------------------------------------
# Monthly orders / AOV
# ---------------------------------------------------------------------------
st.subheader("Monthly Orders and Average Order Value")

mrt = load_mart("monthly_revenue_trend").sort_values("order_purchase_month")
mrt = mrt[mrt["order_count"] >= 5]

col1, col2 = st.columns(2)
with col1:
    fig_orders = go.Figure(
        go.Bar(
            x=mrt["order_purchase_month"],
            y=mrt["order_count"],
            marker=dict(color=CATEGORICAL[2]),
            hovertemplate="%{x}<br>%{y:,} orders<extra></extra>",
        )
    )
    fig_orders.update_layout(height=360, title="Orders per Month", xaxis_title="Month", yaxis_title="Orders")
    fig_orders = style_fig(fig_orders)
    st.plotly_chart(fig_orders, use_container_width=True)

with col2:
    fig_aov = go.Figure(
        go.Scatter(
            x=mrt["order_purchase_month"],
            y=mrt["avg_order_value"],
            mode="lines+markers",
            line=dict(color=CATEGORICAL[1], width=2),
            marker=dict(size=6),
            hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>",
        )
    )
    fig_aov.update_layout(height=360, title="Average Order Value per Month", xaxis_title="Month", yaxis_title="AOV (R$)")
    fig_aov = style_fig(fig_aov)
    st.plotly_chart(fig_aov, use_container_width=True)

st.info(
    "**So what?** Order volume climbed steadily as the marketplace grew, while average order value "
    "stayed roughly flat around R$ 150-180 — growth has come from more customers, not bigger baskets."
)
