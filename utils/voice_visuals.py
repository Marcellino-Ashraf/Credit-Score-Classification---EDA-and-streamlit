"""Tools the voice assistant (Gemini Live) can call to show KPIs and charts on the page.

How it works:
  1. Gemini decides a visual would help and calls one of the functions declared in ``TOOLS``.
  2. The WebSocket bridge (pages/voice_assistant.py) passes the call to ``run_tool``. It computes the
     numbers from the data, stores a "visual" (KPI cards + a plotly express figure) in ``_store`` and
     returns the same numbers to Gemini, so the spoken answer uses real figures.
  3. The page polls ``latest_visual()`` every couple of seconds and draws the newest visual.

This module is imported (not re-executed on every Streamlit rerun), so ``_store`` is shared between
the bridge thread and the page. It is one store per server: fine for a local, single-user app.
"""

from __future__ import annotations

import threading

import pandas as pd
import plotly.express as px
import streamlit as st
from google.genai import types

SCORE_ORDER = ["Poor", "Standard", "Good"]
SCORE_COLORS = {"Poor": "#DC2626", "Standard": "#F59E0B", "Good": "#16A34A"}
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July", "August"]

CATEGORY_COLUMNS = ["Occupation", "Credit_Mix", "Payment_of_Min_Amount", "Payment_Behaviour", "Month"]
NUMERIC_COLUMNS = ["Age", "Annual_Income", "Monthly_Inhand_Salary", "Outstanding_Debt", "Interest_Rate",
                   "Delay_from_due_date", "Num_of_Delayed_Payment", "Num_Credit_Card", "Num_Bank_Accounts",
                   "Num_of_Loan", "Num_Credit_Inquiries", "Credit_Utilization_Ratio", "Credit_History_Age_months",
                   "Total_EMI_per_month", "Amount_invested_monthly", "Monthly_Balance", "Changed_Credit_Limit"]
COUNT_COLUMNS = ["Num_Credit_Card", "Num_Bank_Accounts", "Num_of_Loan", "Num_Credit_Inquiries",
                 "Num_of_Delayed_Payment"]
MONEY_COLUMNS = ["Annual_Income", "Monthly_Inhand_Salary", "Outstanding_Debt", "Total_EMI_per_month",
                 "Amount_invested_monthly", "Monthly_Balance"]
OCCUPATIONS = ["Accountant", "Architect", "Developer", "Doctor", "Engineer", "Entrepreneur", "Journalist", "Lawyer",
               "Manager", "Media_Manager", "Mechanic", "Musician", "Scientist", "Teacher", "Writer"]


def label(column: str) -> str:
    return column.replace("_", " ").capitalize()


def money(column: str, value: float) -> str:
    return f"${value:,.0f}" if column in MONEY_COLUMNS else f"{value:,.1f}"


# ── Tool declarations (what Gemini is allowed to call) ─────
def _string(description: str, options: list[str] | None = None) -> types.Schema:
    return types.Schema(type=types.Type.STRING, description=description, enum=options)


_OCCUPATION_ARG = _string("Optional: limit the data to one occupation.", OCCUPATIONS)

TOOLS = [types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="show_overview",
        description="Show headline KPIs (records, customers, % Poor / Standard / Good) and a donut of the credit "
                    "score split. Use for general questions about the data or the score distribution.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={"occupation": _OCCUPATION_ARG}),
    ),
    types.FunctionDeclaration(
        name="compare_scores_by_category",
        description="Show the % of Poor / Standard / Good credit scores inside every category of a column "
                    "(100% stacked bars) plus KPIs for the best and worst category. Use for questions like "
                    "'which occupation has the most poor scores' or 'does credit mix matter'.",
        parameters=types.Schema(type=types.Type.OBJECT, required=["column"], properties={
            "column": _string("The categorical column to compare.", CATEGORY_COLUMNS),
            "occupation": _OCCUPATION_ARG,
        }),
    ),
    types.FunctionDeclaration(
        name="compare_numeric_by_score",
        description="Show the median of a numeric column for Poor, Standard and Good credit scores (bar chart + "
                    "KPIs). Use for questions like 'do good customers earn more' or 'how much debt do poor "
                    "customers have'.",
        parameters=types.Schema(type=types.Type.OBJECT, required=["column"], properties={
            "column": _string("The numeric column to compare.", NUMERIC_COLUMNS),
            "occupation": _OCCUPATION_ARG,
        }),
    ),
    types.FunctionDeclaration(
        name="show_distribution",
        description="Show the distribution (histogram split by credit score) and summary KPIs (min, median, mean, "
                    "max) of one numeric column. Use for questions about ranges, typical values or spread.",
        parameters=types.Schema(type=types.Type.OBJECT, required=["column"], properties={
            "column": _string("The numeric column to show.", NUMERIC_COLUMNS),
            "occupation": _OCCUPATION_ARG,
        }),
    ),
    types.FunctionDeclaration(
        name="poor_rate_by_count",
        description="Show how the % of Poor credit scores changes with the number of credit cards, bank accounts, "
                    "loans, credit inquiries or delayed payments (line chart + KPIs).",
        parameters=types.Schema(type=types.Type.OBJECT, required=["column"], properties={
            "column": _string("The count column.", COUNT_COLUMNS),
            "occupation": _OCCUPATION_ARG,
        }),
    ),
])]


# ── Shared store between the bridge thread and the page ───
_lock = threading.Lock()
_store: dict = {"id": 0, "visual": None}


def latest_visual() -> dict | None:
    with _lock:
        return _store["visual"]


def _publish(visual: dict) -> None:
    with _lock:
        _store["id"] += 1
        visual["id"] = _store["id"]
        _store["visual"] = visual


# ── Tool implementations ──────────────────────────────────
def _score_share(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """% of each credit score inside every category of ``column`` (long format for plotly express)."""
    share = df.groupby([column, "Credit_Score"]).size().reset_index(name="rows")
    share["Percentage"] = share["rows"] / share.groupby(column)["rows"].transform("sum") * 100
    return share


def _overview(df: pd.DataFrame, scope: str) -> tuple[dict, dict]:
    counts = df["Credit_Score"].value_counts().reindex(SCORE_ORDER, fill_value=0)
    shares = counts / counts.sum() * 100
    fig = px.pie(counts.reset_index(), names="Credit_Score", values="count", hole=0.55, color="Credit_Score",
                 color_discrete_map=SCORE_COLORS)
    kpis = [("Records", f"{len(df):,}", scope), ("Customers", f"{df['Customer_ID'].nunique():,}", scope)] + \
           [(f"{s} score", f"{shares[s]:.1f}%", "of records") for s in SCORE_ORDER]
    result = {"records": len(df), "customers": int(df["Customer_ID"].nunique()),
              "percent_by_score": shares.round(1).to_dict()}
    return {"title": f"Credit score overview ({scope})", "kpis": kpis, "fig": fig}, result


def _by_category(df: pd.DataFrame, column: str, scope: str) -> tuple[dict, dict]:
    share = _score_share(df, column)
    poor = share[share["Credit_Score"] == "Poor"].sort_values("Percentage", ascending=False)
    good = share[share["Credit_Score"] == "Good"].sort_values("Percentage", ascending=False)
    order = MONTH_ORDER if column == "Month" else poor[column].tolist()
    fig = px.bar(share, x="Percentage", y=column, color="Credit_Score", orientation="h", text_auto=".0f",
                 color_discrete_map=SCORE_COLORS, labels={"Percentage": "Share of rows (%)", column: label(column)},
                 category_orders={"Credit_Score": SCORE_ORDER, column: order})
    fig.update_layout(height=max(280, 80 + 32 * share[column].nunique()), xaxis_range=[0, 100])
    kpis = [
        ("Most Poor", str(poor[column].iloc[0]), f"{poor['Percentage'].iloc[0]:.1f}% Poor"),
        ("Least Poor", str(poor[column].iloc[-1]), f"{poor['Percentage'].iloc[-1]:.1f}% Poor"),
        ("Most Good", str(good[column].iloc[0]), f"{good['Percentage'].iloc[0]:.1f}% Good"),
        ("Gap in % Poor", f"{poor['Percentage'].iloc[0] - poor['Percentage'].iloc[-1]:.1f} pts", "highest vs lowest"),
    ]
    table = share.pivot_table(index=column, columns="Credit_Score", values="Percentage").round(1)
    result = {"percent_by_category": table.to_dict(orient="index")}
    return {"title": f"Credit score mix by {label(column).lower()} ({scope})", "kpis": kpis, "fig": fig}, result


def _numeric_by_score(df: pd.DataFrame, column: str, scope: str) -> tuple[dict, dict]:
    medians = df.groupby("Credit_Score")[column].agg("median").reindex(SCORE_ORDER)
    plot_df = medians.rename_axis("Credit_Score").reset_index()
    fig = px.bar(plot_df, x="Credit_Score", y=column, color="Credit_Score", color_discrete_map=SCORE_COLORS,
                 text_auto="$,.0f" if column in MONEY_COLUMNS else ",.1f",
                 labels={column: f"Median {label(column).lower()}", "Credit_Score": "Credit score"})
    fig.update_layout(showlegend=False)
    kpis = [(f"Median ({s})", money(column, medians[s]), label(column)) for s in SCORE_ORDER]
    if medians["Good"]:
        kpis.append(("Poor vs Good", f"{(medians['Poor'] - medians['Good']) / medians['Good'] * 100:+.0f}%",
                     "difference in median"))
    result = {"median_by_score": medians.round(2).to_dict()}
    return {"title": f"Median {label(column).lower()} by credit score ({scope})", "kpis": kpis, "fig": fig}, result


def _distribution(df: pd.DataFrame, column: str, scope: str) -> tuple[dict, dict]:
    series = df[column]
    fig = px.histogram(df, x=column, color="Credit_Score", color_discrete_map=SCORE_COLORS,
                       category_orders={"Credit_Score": SCORE_ORDER}, labels={column: label(column)})
    fig.update_layout(bargap=0.02, yaxis_title="Rows (count)")
    stats = {"min": series.min(), "median": series.median(), "mean": series.mean(), "max": series.max()}
    kpis = [(name.capitalize(), money(column, value), label(column)) for name, value in stats.items()]
    result = {name: round(float(value), 2) for name, value in stats.items()}
    return {"title": f"Distribution of {label(column).lower()} ({scope})", "kpis": kpis, "fig": fig}, result


def _poor_rate(df: pd.DataFrame, column: str, scope: str) -> tuple[dict, dict]:
    rates = df.groupby(column).agg(poor=("Credit_Score", lambda s: (s == "Poor").mean() * 100)).reset_index()
    fig = px.line(rates, x=column, y="poor", markers=True, color_discrete_sequence=[SCORE_COLORS["Poor"]],
                  labels={column: label(column), "poor": "Poor scores (%)"})
    low, high = rates.sort_values("poor").iloc[0], rates.sort_values("poor").iloc[-1]
    kpis = [
        ("Lowest % Poor", f"{low['poor']:.1f}%", f"at {low[column]:.0f}"),
        ("Highest % Poor", f"{high['poor']:.1f}%", f"at {high[column]:.0f}"),
        ("Overall % Poor", f"{(df['Credit_Score'] == 'Poor').mean() * 100:.1f}%", scope),
    ]
    result = {"percent_poor_by_value": rates.set_index(column)["poor"].round(1).to_dict()}
    return {"title": f"% Poor by {label(column).lower()} ({scope})", "kpis": kpis, "fig": fig}, result


_HANDLERS = {
    "show_overview": lambda df, args, scope: _overview(df, scope),
    "compare_scores_by_category": lambda df, args, scope: _by_category(df, args["column"], scope),
    "compare_numeric_by_score": lambda df, args, scope: _numeric_by_score(df, args["column"], scope),
    "show_distribution": lambda df, args, scope: _distribution(df, args["column"], scope),
    "poor_rate_by_count": lambda df, args, scope: _poor_rate(df, args["column"], scope),
}


def run_tool(name: str, args: dict, df: pd.DataFrame) -> dict:
    """Run one tool call: publish the visual for the page and return the numbers for Gemini."""
    try:
        occupation = args.get("occupation")
        scope = "all customers"
        if occupation:
            df = df[df["Occupation"] == occupation]
            scope = occupation
        if df.empty:
            return {"error": "No data for this selection."}
        visual, result = _HANDLERS[name](df, args, scope)
        _publish(visual)
        result["note"] = "The chart and KPI cards are now shown on the page under the assistant."
        return result
    except Exception as e:  # never break the voice session because of a chart
        return {"error": f"Could not build the visual: {e}"}


# ── Drawing on the page ───────────────────────────────────
def render(visual: dict) -> None:
    """Draw the KPI cards and the figure of one visual (styles come from assets/style.css)."""
    cards = "".join(
        f'<div class="kpi"><div class="kpi__top"><span class="kpi__label">{k_label}</span></div>'
        f'<div class="kpi__value">{value}</div><div class="kpi__delta"><span>{caption}</span></div></div>'
        for k_label, value, caption in visual["kpis"]
    )
    st.html(f'<div class="section-header"><h2><i class="fa-solid fa-wand-magic-sparkles"></i>'
            f'<span>{visual["title"]}</span></h2></div><div class="kpi-row">{cards}</div>')
    fig = visual["fig"]
    fig.update_layout(template="plotly_white", title_text="", legend_title_text="")
    with st.container(key=f"card-voice-visual-{visual['id']}"):
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"voice-chart-{visual['id']}")
