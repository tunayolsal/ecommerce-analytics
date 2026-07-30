"""Payments — payment method mix, installment behavior, and category patterns."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go
import streamlit as st

from utils import CATEGORICAL, load_mart, page_header, style_fig

st.set_page_config(page_title="Payments | Olist Analytics", page_icon=":credit_card:", layout="wide")

page_header("Payments", "How customers pay: method mix, installment plans, and category behavior.")

# ---------------------------------------------------------------------------
# Payment type mix
# ---------------------------------------------------------------------------
st.subheader("Payment Type Mix")

mix = load_mart("payment_type_mix").sort_values("total_revenue", ascending=False)

col1, col2 = st.columns(2)
with col1:
    fig_pie = go.Figure(
        go.Pie(
            labels=mix["payment_type"],
            values=mix["total_revenue"],
            marker=dict(colors=CATEGORICAL),
            hovertemplate="%{label}<br>R$ %{value:,.0f} (%{percent})<extra></extra>",
            hole=0.45,
        )
    )
    fig_pie.update_layout(height=380, title="Share of Revenue")
    fig_pie = style_fig(fig_pie)
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    fig_count = go.Figure(
        go.Bar(
            x=mix["payment_type"],
            y=mix["payment_count"],
            marker=dict(color=CATEGORICAL[0]),
            hovertemplate="%{x}<br>%{y:,} payments<extra></extra>",
        )
    )
    fig_count.update_layout(height=380, title="Number of Payments", yaxis_title="Payments", xaxis_title="")
    fig_count = style_fig(fig_count)
    st.plotly_chart(fig_count, use_container_width=True)

top_method = mix.iloc[0]
st.info(
    f"**So what?** {top_method['payment_type'].replace('_', ' ').title()} dominates, driving "
    f"{top_method['pct_of_revenue']:.1f}% of revenue — payment infrastructure and fraud/risk "
    "investment should prioritize this channel first."
)

st.divider()

# ---------------------------------------------------------------------------
# Installment distribution
# ---------------------------------------------------------------------------
st.subheader("Installment Distribution")

inst = load_mart("installment_distribution").sort_values("payment_installments")
avg_val = load_mart("avg_payment_value_by_installments").sort_values("payment_installments")

col3, col4 = st.columns(2)
with col3:
    fig_inst = go.Figure(
        go.Bar(
            x=inst["payment_installments"],
            y=inst["pct_of_payments"],
            marker=dict(color=CATEGORICAL[2]),
            hovertemplate="%{x} installments<br>%{y:.1f}%% of payments<extra></extra>",
        )
    )
    fig_inst.update_layout(height=380, title="Share of Payments by Installment Count", xaxis_title="Installments", yaxis_title="% of Payments")
    fig_inst = style_fig(fig_inst)
    st.plotly_chart(fig_inst, use_container_width=True)

with col4:
    fig_avgval = go.Figure(
        go.Scatter(
            x=avg_val["payment_installments"],
            y=avg_val["avg_payment_value"],
            mode="lines+markers",
            line=dict(color=CATEGORICAL[3], width=2),
            marker=dict(size=6),
            hovertemplate="%{x} installments<br>R$ %{y:,.2f} avg<extra></extra>",
        )
    )
    fig_avgval.update_layout(height=380, title="Avg Payment Value by Installments (Credit Card)", xaxis_title="Installments", yaxis_title="Avg Payment Value (R$)")
    fig_avgval = style_fig(fig_avgval)
    st.plotly_chart(fig_avgval, use_container_width=True)

one_pay_pct = inst.loc[inst["payment_installments"] == 1, "pct_of_payments"]
one_pay_pct = one_pay_pct.iloc[0] if len(one_pay_pct) else float("nan")
st.info(
    f"**So what?** About {one_pay_pct:.1f}% of payments are paid in full (1 installment), but "
    "higher-installment plans correlate with larger basket sizes — installment financing is "
    "clearly used to unlock bigger purchases, not just spread out small ones."
)

st.divider()

# ---------------------------------------------------------------------------
# Category installment behavior
# ---------------------------------------------------------------------------
st.subheader("Credit-Card Installments by Category")

cc_cat = load_mart("credit_card_installments_by_category").sort_values("avg_installments", ascending=True)

fig_cc = go.Figure(
    go.Bar(
        x=cc_cat["avg_installments"],
        y=cc_cat["category"],
        orientation="h",
        marker=dict(color=CATEGORICAL[6]),
        hovertemplate="%{y}<br>Avg installments: %{x:.2f}<extra></extra>",
    )
)
fig_cc.update_layout(height=550, xaxis_title="Avg Installments", yaxis_title="")
fig_cc = style_fig(fig_cc)
st.plotly_chart(fig_cc, use_container_width=True)

top_cc = cc_cat.iloc[-1]
st.info(
    f"**So what?** *{top_cc['category'].replace('_', ' ').title()}* buyers use the most "
    f"installments on average ({top_cc['avg_installments']:.1f}), consistent with these being "
    "higher-ticket categories where financing matters most — a good target for promotional "
    "no-interest installment campaigns."
)
