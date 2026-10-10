import pandas as pd
import streamlit as st

from utils import charts
from utils.components import chart_card, empty_state, fmt_currency, fmt_pct, insight_callout, page_header, \
    question, sidebar_filters
from utils.data import chi_square_p, describe_p, kruskal_p, label, load_cleaned, median_by_score, poor_rate, \
    score_mix

page_header("Analysis Questions", "The six questions answered in the notebook, recalculated for the current filters.",
            "circle-question")

df = sidebar_filters(load_cleaned(), key="qa")
if df.empty:
    empty_state()
    st.stop()

# ── Q1 Occupation ─────────────────────────────────────────
question(1, "Does the occupation of a customer affect the credit score?")
occ = score_mix(df, "Occupation").sort_values("Poor", ascending=False)
c1, c2 = st.columns([3, 2], gap="medium")
with c1:
    chart_card(charts.score_stacked_bar(occ, "Occupation"), "Credit score mix per occupation", icon="briefcase",
               key="q1-mix", caption=f"Chi-square test: {describe_p(chi_square_p(df, 'Occupation'))}.")
with c2:
    income = df.groupby("Occupation")["Annual_Income"].median().reset_index()
    chart_card(charts.bar(income, "Occupation", "Annual_Income", "currency", "Occupation",
                          "Median annual income (USD)"),
               "Median income per occupation", icon="sack-dollar", key="q1-income")
insight_callout([
    f"% Poor ranges from {fmt_pct(occ['Poor'].min())} ({occ['Poor'].idxmin()}) to {fmt_pct(occ['Poor'].max())} "
    f"({occ['Poor'].idxmax()}): a gap of only {occ['Poor'].max() - occ['Poor'].min():.1f} points.",
    "The difference is statistically significant only because the sample is huge; the effect is very weak. "
    "Occupation alone says little about the credit score.",
], title="Answer")

# ── Q2 Income ─────────────────────────────────────────────
question(2, "Do customers with higher income get better credit scores?")
df_q2 = df.assign(Income_group=pd.qcut(df["Annual_Income"], 5,
                                       labels=["Very low", "Low", "Medium", "High", "Very high"]))
income_mix = score_mix(df_q2, "Income_group")
c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(charts.box_by_score(df, "Annual_Income", "Annual income (USD)", "currency"),
               "Annual income by credit score", icon="chart-simple", key="q2-box",
               caption=f"Kruskal-Wallis test: {describe_p(kruskal_p(df, 'Annual_Income'))}.")
with c2:
    chart_card(charts.score_stacked_bar(income_mix, "Income group (quintiles)", horizontal=False),
               "Credit score mix per income group", icon="layer-group", key="q2-mix",
               caption="Customers split into 5 equal-sized income groups.")
med = median_by_score(df, ["Annual_Income"])["Annual_Income"]
insight_callout([
    f"Median income: Poor {fmt_currency(round(med['Poor']))}, Standard {fmt_currency(round(med['Standard']))}, "
    f"Good {fmt_currency(round(med['Good']))}.",
    f"Good share: {fmt_pct(income_mix['Good'].iloc[0])} in the lowest income group vs "
    f"{fmt_pct(income_mix['Good'].iloc[-1])} in the highest. Income helps, but it does not decide the score alone.",
], title="Answer")

# ── Q3 Payment behaviour ──────────────────────────────────
question(3, "How does late payment behaviour relate to the credit score?")
min_mix = score_mix(df, "Payment_of_Min_Amount")
c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(charts.box_by_score(df, "Delay_from_due_date", "Days late after due date"),
               "Days late by credit score", icon="clock", key="q3-box",
               caption=f"Kruskal-Wallis test: {describe_p(kruskal_p(df, 'Delay_from_due_date'))}.")
with c2:
    chart_card(charts.score_stacked_bar(min_mix, label("Payment_of_Min_Amount"), horizontal=False),
               "Credit score mix by 'paid only the minimum'", icon="money-bill-wave", key="q3-mix",
               caption="Yes = paid only the minimum amount due, No = paid more, NM = not mentioned.")
delay = median_by_score(df, ["Delay_from_due_date", "Num_of_Delayed_Payment"])
answer = [f"Median days late: Poor {delay.loc['Poor', 'Delay_from_due_date']:.0f}, "
          f"Good {delay.loc['Good', 'Delay_from_due_date']:.0f}. Median delayed payments: Poor "
          f"{delay.loc['Poor', 'Num_of_Delayed_Payment']:.0f}, Good {delay.loc['Good', 'Num_of_Delayed_Payment']:.0f}."]
if "Yes" in min_mix.index:
    answer.append(f"Customers paying only the minimum are {fmt_pct(min_mix.loc['Yes', 'Poor'])} Poor and "
                  f"{fmt_pct(min_mix.loc['Yes', 'Good'])} Good.")
insight_callout(answer, title="Answer")

# ── Q4 Debt and interest ──────────────────────────────────
question(4, "How do outstanding debt and interest rate differ between credit score groups?")
c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(charts.box_by_score(df, "Outstanding_Debt", "Outstanding debt (USD)", "currency"),
               "Outstanding debt by credit score", icon="file-invoice-dollar", key="q4-box",
               caption=f"Kruskal-Wallis test: {describe_p(kruskal_p(df, 'Outstanding_Debt'))}.")
with c2:
    sample = df.sample(min(len(df), 5000), random_state=42)
    chart_card(charts.scatter_by_score(sample, "Interest_Rate", "Outstanding_Debt", "Interest rate (%)",
                                       "Outstanding debt (USD)"),
               "Debt vs interest rate", icon="braille", key="q4-scatter",
               caption=f"{len(sample):,} random rows, so the points stay readable.")
debt = median_by_score(df, ["Outstanding_Debt", "Interest_Rate"])
insight_callout([
    f"Median debt: Poor {fmt_currency(round(debt.loc['Poor', 'Outstanding_Debt']))} vs Good "
    f"{fmt_currency(round(debt.loc['Good', 'Outstanding_Debt']))}.",
    f"Median interest rate: Poor {debt.loc['Poor', 'Interest_Rate']:.0f}% vs Good "
    f"{debt.loc['Good', 'Interest_Rate']:.0f}%. Good scores sit in the low-debt, low-interest corner.",
], title="Answer")

# ── Q5 Number of credit products ──────────────────────────
question(5, "Does having more credit cards, bank accounts or loans lead to a worse credit score?")
product = st.radio("Product", ["Num_Credit_Card", "Num_Bank_Accounts", "Num_of_Loan"], format_func=label,
                   horizontal=True, key="q5_product")
rates = poor_rate(df, product)
chart_card(charts.line(rates, product, "poor", "percent", label(product), "Poor scores (%)",
                       color="#DC2626"),
           f"% Poor by number of {label(product).lower()}", icon="chart-line", key="q5-line",
           caption="Each point = all records with that many products.")
low, high = rates.iloc[0], rates.iloc[-1]
insight_callout([
    f"With {low[product]:.0f} {label(product).lower()}, {fmt_pct(low['poor'])} of records are Poor; with "
    f"{high[product]:.0f}, {fmt_pct(high['poor'])} are Poor.",
    "More credit products go with a much higher chance of a Poor score.",
], title="Answer")

# ── Q6 Credit history and mix ─────────────────────────────
question(6, "Does a longer credit history and a better credit mix mean a better credit score?")
mix = score_mix(df, "Credit_Mix").reindex(["Bad", "Standard", "Good"]).dropna()
c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(charts.histogram_by_score(df, "Credit_History_Age_months", "Credit history age (months)"),
               "Credit history age per score", icon="hourglass-half", key="q6-hist",
               caption=f"Kruskal-Wallis test: {describe_p(kruskal_p(df, 'Credit_History_Age_months'))}.")
with c2:
    chart_card(charts.heatmap(mix, "Credit score", "Credit mix", "Share of rows"),
               "Credit score mix (%) for each credit mix", icon="table-cells", key="q6-heat",
               caption=f"Each row sums to 100%. Chi-square test: {describe_p(chi_square_p(df, 'Credit_Mix'))}.")
hist = median_by_score(df, ["Credit_History_Age_months"])["Credit_History_Age_months"]
answer = [f"Median credit history: Poor {hist['Poor'] / 12:.1f} years, Good {hist['Good'] / 12:.1f} years."]
if {"Bad", "Good"} <= set(mix.index):
    answer.append(f"A Bad credit mix is {fmt_pct(mix.loc['Bad', 'Poor'])} Poor; a Good credit mix is "
                  f"{fmt_pct(mix.loc['Good', 'Good'])} Good.")
insight_callout(answer, title="Answer")
