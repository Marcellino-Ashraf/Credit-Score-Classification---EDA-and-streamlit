import pandas as pd
import plotly.express as px
import streamlit as st

# ── Settings ──────────────────────────────────────────────
SCORE_ORDER = ["Poor", "Standard", "Good"]
SCORE_COLORS = {"Poor": "#DC2626", "Standard": "#F59E0B", "Good": "#16A34A"}
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July", "August"]
SKIP_COLUMNS = ["ID", "Customer_ID", "Type_of_Loan", "Credit_History_Age"]  # ids and free text

px.defaults.template = "plotly_white"



def load_data() -> pd.DataFrame:
    return pd.read_parquet("cleaned_data.parquet")


def label(column: str) -> str:
    """Human-readable column name."""
    return column.replace("_", " ").capitalize()


# ── Small layout helpers (styles live in assets/style.css) ──
def page_header(title: str, subtitle: str, icon: str) -> None:
    st.html(f'<div class="page-header"><div class="page-header__icon"><i class="fa-solid fa-{icon}"></i></div>'
            f'<div><h1 class="page-header__title">{title}</h1><p class="page-header__subtitle">{subtitle}</p></div></div>')


def kpi_row(cards: list[tuple[str, str, str]]) -> None:
    """cards = (label, value, Font Awesome icon)."""
    html = "".join(
        f'<div class="kpi"><div class="kpi__top"><span class="kpi__label">{label}</span>'
        f'<span class="kpi__icon"><i class="fa-solid fa-{icon}"></i></span></div><div class="kpi__value">{value}</div></div>'
        for label, value, icon in cards
    )
    st.html(f'<div class="kpi-row">{html}</div>')


def chart_card(fig, title: str, icon: str, caption: str, key: str) -> None:
    fig.update_layout(title_text="")
    with st.container(key=f"card-{key}"):
        st.html(f'<div class="card__title"><i class="fa-solid fa-{icon}"></i><span>{title}</span></div>')
        st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False}, key=f"chart-{key}")
        st.html(f'<p class="card__caption">{caption}</p>')



def sidebar_filters(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Occupation, month and age filters; empty selections mean 'all'."""
    with st.sidebar:
        st.html('<div class="sidebar-label">Filters</div>')
        occupations = st.multiselect("Occupation", sorted(df["Occupation"].unique()), placeholder="All occupations",
                                     key=f"{key}_occ")
        months = st.multiselect("Month", MONTH_ORDER, placeholder="All months", key=f"{key}_months")
        ages = st.slider("Age", int(df["Age"].min()), int(df["Age"].max()), (int(df["Age"].min()), int(df["Age"].max())),
                         key=f"{key}_age")
    if occupations:
        df = df[df["Occupation"].isin(occupations)]
    if months:
        df = df[df["Month"].isin(months)]
    return df[(df["Age"] >= ages[0]) & (df["Age"] <= ages[1])]


# ── Page ──────────────────────────────────────────────────
page_header("Univariate Analysis", "Distribution of every numeric and categorical column, one at a time.",
            "chart-simple")

df = sidebar_filters(load_data(), key="uni")
if df.empty:
    st.html('<div class="empty"><i class="fa-solid fa-filter-circle-xmark"></i>'
            '<p class="empty__msg">No data matches the current filters.</p></div>')
    st.stop()

num_cols = df.select_dtypes(include="number").columns.tolist()
cat_cols = df.columns.drop(num_cols + SKIP_COLUMNS).tolist()

# Make two tabs for Numerical and Categorical Analysis
tab1, tab2 = st.tabs(["Numerical Analysis", "Categorical Analysis"])

with tab1:
    c1, c2 = st.columns([3, 2])
    with c1:
        col_select = st.selectbox("Column", num_cols, format_func=label, key="uni_num_col")
    with c2:
        group = st.radio("Customers", ["All"] + SCORE_ORDER, horizontal=True, key="uni_group")
    rows = df if group == "All" else df[df["Credit_Score"] == group]
    series = rows[col_select]

    # Five-number summary (the values a box plot draws) plus the mean, as cards.
    q1, median, q3 = series.quantile([0.25, 0.5, 0.75])
    iqr = q3 - q1
    outliers = int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())
    kpi_row([
        ("Minimum", f"{series.min():,.2f}", "arrow-down-short-wide"),
        ("Q1 (25%)", f"{q1:,.2f}", "chart-simple"),
        ("Median", f"{median:,.2f}", "grip-lines"),
        ("Q3 (75%)", f"{q3:,.2f}", "chart-simple"),
        ("Maximum", f"{series.max():,.2f}", "arrow-up-wide-short"),
        ("Mean", f"{series.mean():,.2f}", "calculator"),
    ])

    # Each bar is split into Poor / Standard / Good (stacked), so you see how the scores spread over the values
    fig = px.histogram(rows, x=col_select, color="Credit_Score", labels={col_select: label(col_select)},
                       color_discrete_map=SCORE_COLORS, category_orders={"Credit_Score": SCORE_ORDER})
    fig.update_layout(height=360, bargap=0.02, yaxis_title="Rows (count)", legend_title_text="")
    who = "all customers" if group == "All" else f"{group} credit scores"
    chart_card(fig, f"Distribution of {label(col_select)} ({who})", "chart-column",
               "", "uni-hist")

    skew = "right (a tail of high values)" if series.mean() > median else \
        "left (a tail of low values)" if series.mean() < median else "symmetric"


# Categorical Analysis
with tab2:
    c1, c2 = st.columns([3, 2])
    with c1:
        col_select = st.selectbox("Column", cat_cols, format_func=label, key="uni_cat_col")
    with c2:
        chart_select = st.radio("Chart", ["Counts", "Share"], horizontal=True, key="uni_cat_chart")

    counts = df[col_select].value_counts().rename_axis(col_select).reset_index(name="rows")
    counts["share"] = counts["rows"] / counts["rows"].sum() * 100
    n_cats = len(counts)

    if chart_select == "Counts":
        # Rows per category AND credit score, so each bar is split into Poor / Standard / Good
        by = [col_select] if col_select == "Credit_Score" else [col_select, "Credit_Score"]
        score_counts = df.groupby(by).size().reset_index(name="rows")
        fig = px.bar(score_counts, x="rows", y=col_select, color="Credit_Score", orientation="h",
                     labels={"rows": "Rows (count)", col_select: label(col_select)}, color_discrete_map=SCORE_COLORS,
                     category_orders={"Credit_Score": SCORE_ORDER, col_select: counts[col_select].tolist()}, text_auto=",.0f")
        fig.update_layout(height=max(260, 60 + 45 * n_cats), legend_title_text="")
        chart_card(fig, f"{label(col_select)}: rows per category", "chart-bar",
                   f"{n_cats} categories, largest first. Each bar is split by credit score.", "uni-counts")
    elif col_select == "Credit_Score":
        # The target itself: nothing to split, so a donut of its shares
        fig = px.pie(counts, names=col_select, values="rows", hole=0.55, color=col_select,
                     color_discrete_map=SCORE_COLORS)
        fig.update_layout(height=360)
        chart_card(fig, f"{label(col_select)}: share of rows", "chart-pie", f"{n_cats} categories.", "uni-share")
    else:
        # % of Poor / Standard / Good inside every category (each bar sums to 100%)
        score_share = df.groupby([col_select, "Credit_Score"]).size().reset_index(name="rows")
        score_share["Percentage"] = score_share["rows"] / score_share.groupby(col_select)["rows"].transform("sum") * 100
        # Show each category's own share of all rows in its label, e.g. "Lawyer (7.4%)"
        names = {c: f"{c} ({s:.1f}%)" for c, s in zip(counts[col_select], counts["share"])}
        score_share["Category"] = score_share[col_select].map(names)
        fig = px.bar(score_share, x="Percentage", y="Category", color="Credit_Score", orientation="h",
                     text_auto=".0f", color_discrete_map=SCORE_COLORS,
                     labels={"Percentage": "Share of rows (%)", "Category": label(col_select)},
                     category_orders={"Credit_Score": SCORE_ORDER, "Category": [names[c] for c in counts[col_select]]})
        fig.update_layout(height=max(260, 60 + 45 * n_cats), legend_title_text="", xaxis_range=[0, 100])
        chart_card(fig, f"{label(col_select)}: credit score share per category", "chart-bar",
                   f"{n_cats} categories, largest first (their share of all rows is in brackets). "
                   "Each bar is split into Poor / Standard / Good and sums to 100%.", "uni-share")

    top, least = counts.iloc[0], counts.iloc[-1]

