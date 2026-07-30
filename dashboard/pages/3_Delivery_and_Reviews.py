"""Delivery and Reviews — on-time performance and its link to satisfaction."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go
import streamlit as st

from utils import CATEGORICAL, STATUS_CRITICAL, STATUS_GOOD, load_mart, page_header, style_fig

st.set_page_config(page_title="Delivery and Reviews | Olist Analytics", page_icon=":truck:", layout="wide")

page_header("Delivery and Reviews", "Does a late delivery hurt customer satisfaction? Yes — dramatically.")

rate = load_mart("delivery_rate_overall").set_index("delivery_status")
review = load_mart("review_score_by_delivery").set_index("delivery_status")

on_time_pct = rate.loc["on_time", "pct_of_orders"]
late_pct = rate.loc["late", "pct_of_orders"]
avg_score_on_time = review.loc["on_time", "avg_review_score"]
avg_score_late = review.loc["late", "avg_review_score"]
bad_on_time = review.loc["on_time", "pct_bad_reviews"]
bad_late = review.loc["late", "pct_bad_reviews"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("On-Time Delivery Rate", f"{on_time_pct:.1f}%")
col2.metric("Late Delivery Rate", f"{late_pct:.1f}%")
col3.metric("Avg Review (On-Time)", f"{avg_score_on_time:.2f} / 5")
col4.metric("Avg Review (Late)", f"{avg_score_late:.2f} / 5", delta=f"{avg_score_late - avg_score_on_time:.2f}", delta_color="inverse")

st.divider()

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("On-Time vs. Late Delivery")
    fig_rate = go.Figure(
        go.Bar(
            x=rate.index,
            y=rate["pct_of_orders"],
            marker=dict(color=[STATUS_GOOD, STATUS_CRITICAL]),
            text=[f"{v:.1f}%" for v in rate["pct_of_orders"]],
            textposition="outside",
            hovertemplate="%{x}<br>%{y:.1f}%%<extra></extra>",
        )
    )
    fig_rate.update_layout(height=380, yaxis_title="% of Orders", xaxis_title="")
    fig_rate = style_fig(fig_rate)
    st.plotly_chart(fig_rate, use_container_width=True)

with col_b:
    st.subheader("Review Score: Late vs. On-Time")
    fig_review = go.Figure()
    fig_review.add_trace(
        go.Bar(
            x=review.index,
            y=review["avg_review_score"],
            name="Avg review score",
            marker=dict(color=[STATUS_GOOD, STATUS_CRITICAL]),
            text=[f"{v:.2f}" for v in review["avg_review_score"]],
            textposition="outside",
            hovertemplate="%{x}<br>Avg score: %{y:.2f}<extra></extra>",
        )
    )
    fig_review.update_layout(height=380, yaxis_title="Avg Review Score (1-5)", xaxis_title="", yaxis_range=[0, 5])
    fig_review = style_fig(fig_review)
    st.plotly_chart(fig_review, use_container_width=True)

st.info(
    f"**So what?** Late deliveries devastate satisfaction: average review score drops from "
    f"{avg_score_on_time:.2f}/5 (on-time) to {avg_score_late:.2f}/5 (late), and the share of "
    f"bad reviews (score <= 2) jumps from {bad_on_time:.0f}% to {bad_late:.0f}%. With "
    f"{late_pct:.1f}% of orders arriving late, on-time delivery is the single highest-leverage "
    "lever for improving customer satisfaction."
)

st.divider()

# ---------------------------------------------------------------------------
# Delay by state
# ---------------------------------------------------------------------------
st.subheader("Delivery Delay by State")

by_state = load_mart("delivery_delay_by_state").sort_values("late_pct", ascending=True)

fig_state = go.Figure(
    go.Bar(
        x=by_state["late_pct"],
        y=by_state["customer_state"],
        orientation="h",
        marker=dict(color=CATEGORICAL[1]),
        hovertemplate="%{y}<br>Late: %{x:.1f}%%<extra></extra>",
    )
)
fig_state.update_layout(height=650, xaxis_title="% Late Deliveries", yaxis_title="")
fig_state = style_fig(fig_state)
st.plotly_chart(fig_state, use_container_width=True)

worst_state = by_state.iloc[-1]
best_state = by_state.iloc[0]
st.info(
    f"**So what?** {worst_state['customer_state']} has the worst on-time performance "
    f"({worst_state['late_pct']:.1f}% late), while {best_state['customer_state']} has the best "
    f"({best_state['late_pct']:.1f}% late) — likely reflecting distance from Olist's southeastern "
    "fulfillment hubs. Logistics investment in higher-delay states would directly protect review scores."
)
