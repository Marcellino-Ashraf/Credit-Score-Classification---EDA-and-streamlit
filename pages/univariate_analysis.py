import streamlit as st

from utils import charts
from utils.components import Kpi, chart_card, empty_state, fmt_count, fmt_number, fmt_pct, insight_callout, \
    kpi_row, page_header, section_header, sidebar_filters
from utils.data import categorical_columns, label, load_cleaned, numeric_columns

page_header("Univariate Analysis", "Distribution of every numeric and categorical column, one at a time.",
            "chart-simple")

df = sidebar_filters(load_cleaned(), key="uni")
if df.empty:
    empty_state()
    st.stop()

# Make two tabs for Numerical and Categorical Analysis
tab1, tab2 = st.tabs(["Numerical Analysis", "Categorical Analysis"])

with tab1:
    c1, c2 = st.columns([3, 2])
    with c1:
        col_select = st.selectbox("Column", numeric_columns(df), format_func=label, key="uni_num_col")
    with c2:
        split = st.toggle("Split by credit score", key="uni_split")
    series = df[col_select]

    # Five-number summary (the values a box plot draws) plus the mean, as cards.
    q1, median, q3 = series.quantile([0.25, 0.5, 0.75])
    iqr = q3 - q1
    outliers = int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())
    section_header(f"{label(col_select)}: summary statistics", "list-ol",
                   "Minimum, quartiles and maximum: the same figures a box plot shows.")
    kpi_row([
        Kpi("Minimum", fmt_number(series.min()), "arrow-down-short-wide"),
        Kpi("Q1 (25th pct.)", fmt_number(q1), "chart-simple"),
        Kpi("Median", fmt_number(median), "grip-lines"),
        Kpi("Q3 (75th pct.)", fmt_number(q3), "chart-simple"),
        Kpi("Maximum", fmt_number(series.max()), "arrow-up-wide-short"),
        Kpi("Mean", fmt_number(series.mean()), "calculator"),
    ])

    if split:
        fig = charts.histogram_by_score(df, col_select, label(col_select))
        caption = "Each score group is scaled to 100%, so the shapes compare fairly although Standard is the largest group."
    else:
        fig = charts.histogram(series, label(col_select))
        caption = (f"{fmt_count(len(series))} rows. {outliers:,} values fall outside 1.5x the "
                   f"interquartile range (box-plot whiskers).")
    chart_card(fig, f"Distribution of {label(col_select)}", icon="chart-column", key="uni-hist", caption=caption)

    skew = series.skew()
    shape = "right-skewed (a tail of high values)" if skew > 0.5 else \
        "left-skewed (a tail of low values)" if skew < -0.5 else "roughly symmetric"
    insight_callout([
        f"Half of all rows have a {label(col_select).lower()} between {fmt_number(q1)} and {fmt_number(q3)}.",
        f"Skewness is {skew:.2f}: the distribution is {shape}.",
        f"{outliers:,} rows ({fmt_pct(outliers / len(series) * 100)}) are statistical outliers.",
    ])

# Categorical Analysis
with tab2:
    c1, c2 = st.columns([3, 2])
    with c1:
        col_select = st.selectbox("Column", categorical_columns(df) + ["Credit_Score"], format_func=label,
                                  key="uni_cat_col")
    with c2:
        chart_select = st.radio("Chart", ["Counts", "Share"], horizontal=True, key="uni_cat_chart")

    counts = df[col_select].value_counts().rename_axis(col_select).reset_index(name="rows")
    counts = counts[counts["rows"] > 0]
    n_cats = len(counts)

    if chart_select == "Counts":
        fig = charts.bar(counts, col_select, "rows", "count", label(col_select), "Rows (count)", sort=False)
        chart_card(fig, f"{label(col_select)}: rows per category", icon="chart-bar", key="uni-counts",
                   caption=f"{n_cats} categories, largest first.")
    elif n_cats <= 5:
        fig = charts.donut(counts[col_select], counts["rows"], "Rows")
        chart_card(fig, f"{label(col_select)}: share of rows", icon="chart-pie", key="uni-share",
                   caption=f"{n_cats} categories.")
    else:
        share = counts.assign(share=counts["rows"] / counts["rows"].sum() * 100)
        fig = charts.bar(share, col_select, "share", "percent", label(col_select), "Share of rows (%)",
                         sort=False)
        chart_card(fig, f"{label(col_select)}: share of rows", icon="chart-bar", key="uni-share",
                   caption=f"{n_cats} categories (too many for a readable pie), largest first.")

    top = counts.iloc[0]
    insight_callout([
        f"{label(col_select)} has {n_cats} distinct values.",
        f"The most common is {top[col_select]} with {fmt_count(top['rows'])} rows "
        f"({fmt_pct(top['rows'] / counts['rows'].sum() * 100)}).",
        f"The least common is {counts.iloc[-1][col_select]} with {fmt_count(counts.iloc[-1]['rows'])} rows.",
    ])
