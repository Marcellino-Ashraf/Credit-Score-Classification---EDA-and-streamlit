import streamlit as st

from utils import charts, theme
from utils.components import card, chart_card, data_table, empty_state, fmt_pct, insight_callout, page_header, \
    section_header, sidebar_filters
from utils.data import categorical_columns, chi_square_p, describe_p, kind_of, kruskal_p, label, load_cleaned, \
    median_by_score, numeric_columns, score_mix

page_header("Credit Score Drivers", "How each variable differs between Poor, Standard and Good credit scores.",
            "magnifying-glass-chart")

df = sidebar_filters(load_cleaned(), key="drv")
if df.empty:
    empty_state()
    st.stop()

num_cols = numeric_columns(df)

# ── Numeric driver ────────────────────────────────────────
section_header("Numeric variable vs credit score", "chart-column",
               "Pick a variable: the box plot compares its spread in each score group.")
col = st.selectbox("Numeric variable", num_cols, format_func=label, key="drv_num",
                   index=num_cols.index("Outstanding_Debt"))

medians = median_by_score(df, [col])[col]
c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(charts.box_by_score(df, col, label(col), kind_of(col)), f"{label(col)} by credit score",
               icon="chart-simple", key="drv-box",
               caption=f"Kruskal-Wallis test: {describe_p(kruskal_p(df, col))}.")
with c2:
    chart_card(charts.histogram_by_score(df, col, label(col)), f"{label(col)} distribution per score",
               icon="chart-area", key="drv-hist",
               caption="Each score group is scaled to 100% so the shapes are comparable.")

# ── Categorical driver ────────────────────────────────────
section_header("Categorical variable vs credit score", "layer-group",
               "Share of each credit score inside every category (each bar sums to 100%).")
cat = st.selectbox("Categorical variable", categorical_columns(df), format_func=label, key="drv_cat",
                   index=categorical_columns(df).index("Credit_Mix"))
mix = score_mix(df, cat)
if cat != "Month":
    mix = mix.sort_values("Poor", ascending=False)
chart_card(charts.score_stacked_bar(mix, label(cat)), f"Credit score mix by {label(cat).lower()}",
           icon="bars-progress", key="drv-mix",
           caption=f"Sorted by % Poor. Chi-square test: {describe_p(chi_square_p(df, cat))}.")

# ── Correlations ──────────────────────────────────────────
section_header("Correlation between numeric variables", "table-cells",
               "Pearson correlation: +1 move together, -1 move in opposite directions, 0 unrelated.")
corr = df[num_cols].corr().round(2)
corr.index = corr.columns = [label(c) for c in num_cols]
chart_card(charts.heatmap(corr, "", "", "Correlation", zmin=-1, zmax=1, colorscale=theme.DIVERGING,
                          fmt=".2f", suffix=""),
           "Correlation matrix", icon="table-cells", key="drv-corr")

# ── Medians table ─────────────────────────────────────────
with card("Median of every numeric variable per credit score", icon="table", key="drv-medians",
          caption="Variables sorted by how much the Poor median differs from the Good median."):
    table = median_by_score(df, num_cols).T
    good = table["Good"].abs().where(table["Good"] != 0)  # a zero median has no meaningful % change
    table["Poor vs Good"] = (table["Poor"] - table["Good"]) / good * 100
    table = table.sort_values("Poor vs Good", key=abs, ascending=False)
    table.insert(0, "Variable", [label(c) for c in table.index])
    data_table(table.round(2), formats={"Poor": "number", "Standard": "number", "Good": "number",
                                        "Poor vs Good": "percent"})

worst = mix["Poor"].idxmax()
insight_callout([
    f"Median {label(col).lower()}: Poor {medians['Poor']:,.2f}, Standard {medians['Standard']:,.2f}, "
    f"Good {medians['Good']:,.2f}.",
    f"Within {label(cat).lower()}, '{worst}' has the highest Poor share ({fmt_pct(mix.loc[worst, 'Poor'])}).",
    f"The variable that separates Poor from Good the most (by median) is {table.iloc[0]['Variable'].lower()}.",
])
