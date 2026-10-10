"""Data loading and the credit-score aggregations shared by the pages.

The app reads ``cleaned_data.parquet``, written by the last cleaning step of
``Credit Score Classification - EDA.ipynb``. One row = one customer in one month.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from scipy import stats

from utils.theme import SCORE_ORDER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEANED_PATH = os.path.join(ROOT, "cleaned_data.parquet")

MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July", "August"]
ID_COLUMNS = ["ID", "Customer_ID"]
TEXT_COLUMNS = ["Type_of_Loan", "Credit_History_Age"]  # free text, too many values to chart

# Human-readable names for axes, titles and select boxes
LABELS = {
    "Age": "Age",
    "Annual_Income": "Annual income",
    "Monthly_Inhand_Salary": "Monthly in-hand salary",
    "Num_Bank_Accounts": "Bank accounts",
    "Num_Credit_Card": "Credit cards",
    "Interest_Rate": "Interest rate (%)",
    "Num_of_Loan": "Loans",
    "Delay_from_due_date": "Days late after due date",
    "Num_of_Delayed_Payment": "Delayed payments",
    "Changed_Credit_Limit": "Change in credit limit (%)",
    "Num_Credit_Inquiries": "Credit inquiries",
    "Outstanding_Debt": "Outstanding debt",
    "Credit_Utilization_Ratio": "Credit utilization (%)",
    "Total_EMI_per_month": "Total EMI per month",
    "Amount_invested_monthly": "Amount invested monthly",
    "Monthly_Balance": "Monthly balance",
    "Credit_History_Age_months": "Credit history age (months)",
    "Occupation": "Occupation",
    "Month": "Month",
    "Credit_Mix": "Credit mix",
    "Payment_of_Min_Amount": "Paid only minimum amount",
    "Payment_Behaviour": "Payment behaviour",
    "Credit_Score": "Credit score",
}

# Money columns are shown with a $ sign
MONEY_COLUMNS = {"Annual_Income", "Monthly_Inhand_Salary", "Outstanding_Debt", "Total_EMI_per_month",
                 "Amount_invested_monthly", "Monthly_Balance"}


def label(column: str) -> str:
    """Human-readable column name."""
    return LABELS.get(column, column.replace("_", " ").capitalize())


def kind_of(column: str) -> str:
    """Number format for a column: 'currency' for money, 'number' otherwise."""
    return "currency" if column in MONEY_COLUMNS else "number"


# ── Loading ───────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_cleaned() -> pd.DataFrame:
    """Cleaned dataset with ordered categories for Month and Credit_Score."""
    df = pd.read_parquet(CLEANED_PATH)
    df["Month"] = pd.Categorical(df["Month"], categories=MONTH_ORDER, ordered=True)
    df["Credit_Score"] = pd.Categorical(df["Credit_Score"], categories=SCORE_ORDER, ordered=True)
    return df


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include="number").columns.tolist()


def categorical_columns(df: pd.DataFrame) -> list[str]:
    drop = set(ID_COLUMNS + TEXT_COLUMNS + ["Credit_Score"])
    return [c for c in df.columns if c not in drop and not pd.api.types.is_numeric_dtype(df[c])]


# ── Credit score aggregations ─────────────────────────────
def score_mix(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """% of Poor / Standard / Good rows inside every category of ``column`` (rows sum to 100)."""
    mix = pd.crosstab(df[column], df["Credit_Score"], normalize="index") * 100
    # Categories with no rows (e.g. filtered-out months) come back as NaN rows: drop them.
    return mix.reindex(columns=SCORE_ORDER, fill_value=0).dropna(how="all")


def score_shares(df: pd.DataFrame) -> pd.Series:
    """% of rows in each credit score, in Poor -> Good order."""
    return df["Credit_Score"].value_counts(normalize=True).reindex(SCORE_ORDER, fill_value=0) * 100


def median_by_score(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Median of each column per credit score."""
    return df.groupby("Credit_Score", observed=False)[columns].median().reindex(SCORE_ORDER)


def poor_rate(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """% of Poor scores and row count for every value of ``column``."""
    out = df.groupby(column, observed=True).agg(
        rows=("Credit_Score", "size"),
        poor=("Credit_Score", lambda s: (s == "Poor").mean() * 100),
    )
    return out.reset_index()


def kruskal_p(df: pd.DataFrame, column: str) -> float:
    """p-value of a Kruskal-Wallis test: same distribution of ``column`` in all score groups?"""
    groups = [g[column].to_numpy() for _, g in df.groupby("Credit_Score", observed=True)]
    if len(groups) < 2:
        return float("nan")
    return stats.kruskal(*groups).pvalue


def chi_square_p(df: pd.DataFrame, column: str) -> float:
    """p-value of a chi-square test of independence between ``column`` and the credit score."""
    table = pd.crosstab(df[column], df["Credit_Score"])
    if table.shape[0] < 2 or table.shape[1] < 2:
        return float("nan")
    return stats.chi2_contingency(table).pvalue


def describe_p(p: float) -> str:
    """Plain-language reading of a p-value."""
    if pd.isna(p):
        return "not enough groups to test"
    if p < 0.001:
        return "p < 0.001: the difference is statistically significant"
    if p < 0.05:
        return f"p = {p:.3f}: the difference is statistically significant"
    return f"p = {p:.3f}: no significant difference"
