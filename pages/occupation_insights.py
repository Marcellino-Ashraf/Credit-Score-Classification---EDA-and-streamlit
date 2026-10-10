import streamlit as st

from utils import charts, theme
from utils.components import Kpi, card, chart_card, data_table, empty_state, fmt_currency, fmt_pct, \
    insight_callout, kpi_row, page_header, section_header, sidebar_filters
from utils.data import chi_square_p, describe_p, load_cleaned, score_mix, score_shares

page_header("Occupation Insights", "Does the job of a customer change their credit score, income or debt?",
            "briefcase")

df = sidebar_filters(load_cleaned(), key="occ")
if df.empty:
    empty_state()
    st.stop()

# One summary row per occupation
by_occ = df.groupby("Occupation").agg(
    customers=("Customer_ID", "nunique"),
    income=("Annual_Income", "median"),
    debt=("Outstanding_Debt", "median"),
    delay=("Delay_from_due_date", "median"),
)
mix = score_mix(df, "Occupation")
by_occ = by_occ.join(mix).sort_values("Poor", ascending=False)
overall = score_shares(df)

# ── Score mix per occupation ──────────────────────────────
section_header("Credit score mix per occupation", "bars-progress",
               f"Sorted by % Poor. Chi-square test: {describe_p(chi_square_p(df, 'Occupation'))}.")
chart_card(charts.score_stacked_bar(by_occ[theme.SCORE_ORDER], "Occupation"),
           "Share of Poor / Standard / Good by occupation", icon="chart-bar", key="occ-mix",
           caption="Each bar sums to 100%. Bars of similar length mean the job alone says little about the score.")

c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(charts.bar(by_occ.reset_index(), "Occupation", "income", "currency", "Occupation",
                          "Median annual income (USD)"),
               "Median annual income by occupation", icon="sack-dollar", key="occ-income",
               caption="Median, so a few very high earners do not distort the bar.")
with c2:
    chart_card(charts.bar(by_occ.reset_index(), "Occupation", "debt", "currency", "Occupation",
                          "Median outstanding debt (USD)", color=theme.ACCENT),
               "Median outstanding debt by occupation", icon="file-invoice-dollar", key="occ-debt",
               caption="Debt is what the customer still owes; more debt usually goes with a worse score.")

# ── One occupation in focus ───────────────────────────────
section_header("Focus on one occupation", "user-tie", "Compare a single job with all customers.")
focus = st.selectbox("Occupation", by_occ.index.tolist(), key="occ_focus")
row = by_occ.loc[focus]
kpi_row([
    Kpi("Customers", f"{row['customers']:,}", "users"),
    # Differences as plain captions: a green "up" arrow on a rising Poor share would read as good news.
    Kpi("Poor score", fmt_pct(row["Poor"]), "triangle-exclamation",
        delta_caption=f"{row['Poor'] - overall['Poor']:+.1f} pts vs all customers"),
    Kpi("Good score", fmt_pct(row["Good"]), "circle-check",
        delta_caption=f"{row['Good'] - overall['Good']:+.1f} pts vs all customers"),
    Kpi("Median income", fmt_currency(round(row["income"])), "sack-dollar"),
    Kpi("Median days late", f"{row['delay']:.0f} days", "clock"),
])

focus_df = df[df["Occupation"] == focus]
c1, c2 = st.columns(2, gap="medium")
with c1:
    trend = score_mix(focus_df, "Month").reset_index()
    chart_card(charts.score_lines(trend, "Month", "Month"), f"{focus}: credit score mix by month",
               icon="chart-line", key="occ-trend")
with c2:
    behaviour = score_mix(focus_df, "Payment_Behaviour").sort_values("Poor", ascending=False)
    chart_card(charts.score_stacked_bar(behaviour, "Payment behaviour"),
               f"{focus}: score mix by payment behaviour", icon="credit-card", key="occ-behaviour")

with card("Occupation summary table", icon="table", key="occ-table"):
    table = by_occ.reset_index().rename(columns={
        "customers": "Customers", "income": "Median income", "debt": "Median debt",
        "delay": "Median days late", "Poor": "% Poor", "Standard": "% Standard", "Good": "% Good"})
    data_table(table, formats={"Customers": "count", "Median income": "currency", "Median debt": "currency",
                               "Median days late": "number", "% Poor": "percent", "% Standard": "percent",
                               "% Good": "percent"})

spread = by_occ["Poor"].max() - by_occ["Poor"].min()
insight_callout([
    f"{by_occ.index[0]} has the highest Poor share ({fmt_pct(by_occ['Poor'].iloc[0])}) and "
    f"{by_occ.index[-1]} the lowest ({fmt_pct(by_occ['Poor'].iloc[-1])}): a gap of {spread:.1f} points.",
    f"The highest median income is {by_occ['income'].idxmax()} ({fmt_currency(round(by_occ['income'].max()))}), "
    f"the lowest {by_occ['income'].idxmin()} ({fmt_currency(round(by_occ['income'].min()))}).",
    "Occupation differences are small next to payment behaviour, debt and credit history "
    "(see Credit Score Drivers).",
])
