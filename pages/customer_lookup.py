import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import theme
from utils.components import Kpi, card, chart_card, data_table, fmt_currency, kpi_row, page_header, \
    section_header
from utils.data import label, load_cleaned, median_by_score

page_header("Customer Lookup", "One customer's 8 months: how their credit score and finances changed.",
            "user")

df = load_cleaned()

# Customers whose score changed are the most interesting, so they are listed first.
changes = df.groupby("Customer_ID")["Credit_Score"].nunique()
customers = changes.sort_values(ascending=False, kind="stable").index.tolist()
customer = st.selectbox("Customer ID", customers, key="lookup_customer",
                        help="Type to search. Customers whose credit score changed are listed first.")

cust = df[df["Customer_ID"] == customer].sort_values("Month")
last = cust.iloc[-1]

kpi_row([
    Kpi("Occupation", str(last["Occupation"]).replace("_", " "), "briefcase"),
    Kpi("Age", f"{last['Age']}", "cake-candles"),
    Kpi("Annual income", fmt_currency(round(last["Annual_Income"])), "sack-dollar"),
    Kpi("Latest score", str(last["Credit_Score"]), "gauge", delta_caption=f"in {last['Month']}"),
    Kpi("Months on record", f"{len(cust)}", "calendar"),
])

# Score timeline: Poor=0, Standard=1, Good=2 so the line goes up when the score improves
section_header("Credit score over time", "chart-line")
levels = {s: i for i, s in enumerate(theme.SCORE_ORDER)}
fig = go.Figure(go.Scatter(
    x=cust["Month"].astype(str), y=cust["Credit_Score"].map(levels).astype(int), mode="lines+markers",
    line=dict(color=theme.MUTED, width=2, shape="hv"),
    marker=dict(size=14, color=[theme.SCORE_COLORS[s] for s in cust["Credit_Score"]]),
    text=cust["Credit_Score"].astype(str), hovertemplate="<b>%{x}</b><br>Score: %{text}<extra></extra>",
))
fig.update_layout(height=280, showlegend=False, xaxis=dict(title_text="Month", showgrid=False, type="category"),
                  yaxis=dict(title_text="Credit score", tickvals=[0, 1, 2], ticktext=theme.SCORE_ORDER,
                             range=[-0.4, 2.4]))
chart_card(fig, "Monthly credit score", icon="gauge", key="lookup-timeline",
           caption="Green = Good, amber = Standard, red = Poor.")

# Compare with the typical customer of each score
section_header("How this customer compares", "scale-balanced",
               "Latest month of this customer next to the median customer of each credit score.")
compare_cols = ["Outstanding_Debt", "Interest_Rate", "Delay_from_due_date", "Num_of_Delayed_Payment",
                "Num_Credit_Card", "Num_Bank_Accounts", "Num_of_Loan", "Credit_History_Age_months"]
medians = median_by_score(df, compare_cols).T
table = pd.DataFrame({
    "Variable": [label(c) for c in compare_cols],
    "This customer": [float(last[c]) for c in compare_cols],
    "Median Poor": medians["Poor"].values,
    "Median Standard": medians["Standard"].values,
    "Median Good": medians["Good"].values,
})
with card("Customer vs score medians", icon="table", key="lookup-compare",
          caption="Values closer to the Good column point to a healthier credit profile."):
    data_table(table.round(2), formats={c: "number" for c in table.columns[1:]})

section_header("Monthly records", "table-list")
with card("All months for this customer", icon="database", key="lookup-records"):
    show = ["Month", "Credit_Score", "Credit_Mix", "Payment_of_Min_Amount", "Outstanding_Debt",
            "Delay_from_due_date", "Num_of_Delayed_Payment", "Monthly_Balance"]
    data_table(cust[show].rename(columns=label), formats={label("Outstanding_Debt"): "currency",
                                                         label("Monthly_Balance"): "currency"})
