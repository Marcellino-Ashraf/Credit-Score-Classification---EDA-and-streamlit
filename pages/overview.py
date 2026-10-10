import pandas as pd
import streamlit as st

from utils import charts
from utils.components import Kpi, card, chart_card, data_table, fmt_count, fmt_pct, hero, insight_callout, \
    kpi_row, raw_table, section_header
from utils.data import load_cleaned, score_mix, score_shares

hero(
    "Credit Score Classification EDA",
    "Banking and credit profile of 12,500 customers tracked monthly from January to August: "
    "income, debt, payment behaviour and the credit score the bank gave them (Poor, Standard or Good).",
    "credit-card",
)

# Load Data
df = load_cleaned()
shares = score_shares(df)

kpi_row([
    Kpi("Records", fmt_count(len(df)), "table-list", delta_caption=f"{df.shape[1]} columns"),
    Kpi("Customers", fmt_count(df["Customer_ID"].nunique()), "users",
        delta_caption=f"{df['Month'].nunique()} months each"),
    Kpi("Occupations", fmt_count(df["Occupation"].nunique()), "briefcase"),
    Kpi("Good score", fmt_pct(shares["Good"]), "circle-check", delta_caption="of all records"),
    Kpi("Poor score", fmt_pct(shares["Poor"]), "triangle-exclamation", delta_caption="of all records"),
])

# Target overview
section_header("Credit score at a glance", "gauge", "The target variable and how it moves over the 8 months.")
c1, c2 = st.columns([2, 3], gap="medium")
with c1:
    counts = df["Credit_Score"].value_counts()
    chart_card(charts.score_donut(shares, counts), "Credit score distribution", icon="chart-pie",
               caption="Share of customer-month records in each score. Standard dominates; Good is the rarest.")
with c2:
    trend = score_mix(df, "Month").reset_index()
    chart_card(charts.score_lines(trend, "Month", "Month"), "Credit score mix by month", icon="chart-line",
               caption="Share of each score per month. A rising Good line means customers improve over time.")

# Show sample of data
section_header("Data Overview", "table", "Cleaned dataset, one row per customer per month.")
with card("Cleaned dataset", icon="database", key="overview-data"):
    raw_table(df.head(1000))
    st.caption("First 1,000 rows shown.")

# Column descriptions
column_descriptions = {
    "ID": "Unique identifier of the record",
    "Customer_ID": "Unique identifier of the customer",
    "Month": "Month of the record (January to August)",
    "Age": "Age of the customer",
    "Occupation": "Occupation of the customer",
    "Annual_Income": "Annual income of the customer",
    "Monthly_Inhand_Salary": "Monthly take-home salary",
    "Num_Bank_Accounts": "Number of bank accounts held",
    "Num_Credit_Card": "Number of credit cards held",
    "Interest_Rate": "Interest rate on the credit card (%)",
    "Num_of_Loan": "Number of loans taken",
    "Type_of_Loan": "Types of loans taken",
    "Delay_from_due_date": "Average days a payment is late",
    "Num_of_Delayed_Payment": "Number of delayed payments",
    "Changed_Credit_Limit": "% change in the credit card limit",
    "Num_Credit_Inquiries": "Number of credit card inquiries",
    "Credit_Mix": "Quality of the customer's mix of credits (Bad, Standard, Good)",
    "Outstanding_Debt": "Remaining debt to be paid",
    "Credit_Utilization_Ratio": "Used credit as % of available credit",
    "Credit_History_Age": "Age of the credit history (text)",
    "Payment_of_Min_Amount": "Whether the customer paid only the minimum amount (Yes, No, NM)",
    "Total_EMI_per_month": "Total monthly loan instalments (EMI)",
    "Amount_invested_monthly": "Amount invested each month",
    "Payment_Behaviour": "Spending level combined with payment size",
    "Monthly_Balance": "Monthly balance of the customer",
    "Credit_Score": "Target: credit score bracket (Poor, Standard, Good)",
    "Credit_History_Age_months": "Engineered: credit history age in months",
}

description_df = pd.DataFrame(
    [
        {"Column": column, "Type": str(df[column].dtype),
         "Description": column_descriptions.get(column, "Description not available")}
        for column in df.columns
    ]
)

section_header("Dataset Column Descriptions", "book-open", "What each field means after cleaning.")
with card("Column dictionary", icon="list", key="overview-columns"):
    data_table(description_df, max_height=720)

first, last = trend.iloc[0], trend.iloc[-1]
insight_callout([
    f"The dataset holds {len(df):,} monthly records for {df['Customer_ID'].nunique():,} customers in "
    f"{df['Occupation'].nunique()} occupations.",
    f"{fmt_pct(shares['Standard'])} of records are Standard, {fmt_pct(shares['Poor'])} Poor and only "
    f"{fmt_pct(shares['Good'])} Good: the target is imbalanced.",
    f"The Good share moved from {fmt_pct(first['Good'])} in {first['Month']} to {fmt_pct(last['Good'])} in "
    f"{last['Month']}.",
    "Use the pages in the sidebar to explore single variables, the drivers of the credit score, "
    "occupations, the analysis questions and individual customers.",
])
