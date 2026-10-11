import pandas as pd
import plotly.express as px
import streamlit as st

# ── Settings ──────────────────────────────────────────────
SCORE_ORDER = ["Poor", "Standard", "Good"]
SCORE_COLORS = {"Poor": "#DC2626", "Standard": "#F59E0B", "Good": "#16A34A"}
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July", "August"]
SKIP_COLUMNS = ["ID", "Customer_ID", "Type_of_Loan", "Credit_History_Age", "Credit_Score"]  # ids, free text, target

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


def section_header(title: str, icon: str, caption: str) -> None:
    st.html(f'<div class="section-header"><h2><i class="fa-solid fa-{icon}"></i><span>{title}</span></h2>'
            f'<p class="section-header__caption">{caption}</p></div>')


def chart_card(fig, title: str, icon: str, caption: str, key: str) -> None:
    fig.update_layout(title_text="", legend_title_text="")
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


# ── Credit score helpers ──────────────────────────────────
def score_share(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """% of Poor / Standard / Good inside every category of ``column`` (one row per category and score)."""
    share = df.groupby([column, "Credit_Score"]).size().reset_index(name="rows")
    share["Percentage"] = share["rows"] / share.groupby(column)["rows"].transform("sum") * 100
    return share


def stacked_bar(share: pd.DataFrame, column: str, category_title: str):
    """Horizontal 100% stacked bars, one colour per credit score, sorted by % Poor."""
    poor = share[share["Credit_Score"] == "Poor"].sort_values("Percentage", ascending=False)
    fig = px.bar(share, x="Percentage", y=column, color="Credit_Score", orientation="h", text_auto=".0f",
                 color_discrete_map=SCORE_COLORS, labels={"Percentage": "Share of rows (%)", column: category_title},
                 category_orders={"Credit_Score": SCORE_ORDER, column: poor[column].tolist()})
    fig.update_layout(height=max(260, 80 + 30 * share[column].nunique()), xaxis_range=[0, 100])
    return fig


# ── Page ──────────────────────────────────────────────────
page_header("Credit Score Drivers", "How each variable differs between Poor, Standard and Good credit scores.",
            "magnifying-glass-chart")

df = sidebar_filters(load_data(), key="drv")
if df.empty:
    st.html('<div class="empty"><i class="fa-solid fa-filter-circle-xmark"></i>'
            '<p class="empty__msg">No data matches the current filters.</p></div>')
    st.stop()

num_cols = df.select_dtypes(include="number").columns.tolist()
cat_cols = df.columns.drop(num_cols + SKIP_COLUMNS).tolist()
medians = df.groupby("Credit_Score")[num_cols].agg("median").reindex(SCORE_ORDER)

# ── Numeric driver ────────────────────────────────────────
section_header("Numeric variable vs credit score", "chart-column",
               "Pick a variable: compare its typical value and its spread in each score group.")
col = st.selectbox("Numeric variable", num_cols, format_func=label, key="drv_num",
                   index=num_cols.index("Outstanding_Debt"))

c1, c2 = st.columns(2, gap="medium")
with c1:
    plot_df = medians[col].rename_axis("Credit_Score").reset_index()
    fig = px.bar(plot_df, x="Credit_Score", y=col, color="Credit_Score", text_auto=",.1f",
                 color_discrete_map=SCORE_COLORS, labels={col: f"Median {label(col).lower()}", "Credit_Score": "Credit score"})
    fig.update_layout(height=360, showlegend=False)
    chart_card(fig, f"Median {label(col).lower()} by credit score", "chart-simple",
               "", "drv-median")
with c2:
    group = st.radio("Score group", SCORE_ORDER, horizontal=True, key="drv_group")
    fig = px.histogram(df[df["Credit_Score"] == group], x=col, labels={col: label(col)},
                       color_discrete_sequence=[SCORE_COLORS[group]])
    fig.update_layout(height=360, bargap=0.02, yaxis_title="Rows (count)")
    chart_card(fig, f"{label(col)} distribution: {group} scores", "chart-area",
               "", "drv-hist")

# ── Categorical driver ────────────────────────────────────
section_header("Categorical variable vs credit score", "layer-group",
               "Share of each credit score inside every category (each bar sums to 100%).")
cat = st.selectbox("Categorical variable", cat_cols, format_func=label, key="drv_cat",
                   index=cat_cols.index("Credit_Mix"))
share = score_share(df, cat)
poor = share[share["Credit_Score"] == "Poor"].sort_values("Percentage", ascending=False)
chart_card(stacked_bar(share, cat, label(cat)), f"Credit score mix by {label(cat).lower()}", "bars-progress",
           "Sorted by % Poor (highest first).", "drv-mix")

# ── Medians table ─────────────────────────────────────────
section_header("Median of every numeric variable per credit score", "table",
               "Poor vs Good = how much higher (+) or lower (-) the Poor median is than the Good median.")
rows = []
for c in num_cols:
    poor_median, good_median = medians.loc["Poor", c], medians.loc["Good", c]
    rows.append({"Variable": label(c), "Poor": poor_median, "Standard": medians.loc["Standard", c], "Good": good_median,
                 "Poor vs Good (%)": (poor_median - good_median) / good_median * 100 if good_median else None})
with st.container(key="card-drv-medians"):
    st.dataframe(pd.DataFrame(rows).round(2), hide_index=True, width="stretch")

