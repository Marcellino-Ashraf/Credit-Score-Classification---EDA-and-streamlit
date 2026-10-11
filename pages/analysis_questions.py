import pandas as pd
import plotly.express as px
import streamlit as st

# ── Settings ──────────────────────────────────────────────
SCORE_ORDER = ["Poor", "Standard", "Good"]
SCORE_COLORS = {"Poor": "#DC2626", "Standard": "#F59E0B", "Good": "#16A34A"}
PRIMARY = "#0E7490"
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July", "August"]
PRODUCT_LABELS = {"Num_Credit_Card": "Credit cards", "Num_Bank_Accounts": "Bank accounts", "Num_of_Loan": "Loans"}

px.defaults.template = "plotly_white"


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    return pd.read_parquet("cleaned_data.parquet")


# ── Small layout helpers (styles live in assets/style.css) ──
def page_header(title: str, subtitle: str, icon: str) -> None:
    st.html(f'<div class="page-header"><div class="page-header__icon"><i class="fa-solid fa-{icon}"></i></div>'
            f'<div><h1 class="page-header__title">{title}</h1><p class="page-header__subtitle">{subtitle}</p></div></div>')


def question(number: int, text: str) -> None:
    st.html(f'<div class="question"><div class="question__label">Question {number}</div>'
            f'<p class="question__text">{text}</p></div>')


def chart_card(fig, title: str, icon: str, caption: str, key: str) -> None:
    fig.update_layout(title_text="", legend_title_text="")
    with st.container(key=f"card-{key}"):
        st.html(f'<div class="card__title"><i class="fa-solid fa-{icon}"></i><span>{title}</span></div>')
        st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False}, key=f"chart-{key}")
        st.html(f'<p class="card__caption">{caption}</p>')


def answer(items: list[str]) -> None:
    st.html('<div class="callout"><div class="callout__title"><i class="fa-solid fa-lightbulb"></i>'
            '<span>Answer</span></div><ul>' + "".join(f"<li>{i}</li>" for i in items) + "</ul></div>")


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
def score_mix(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """% of Poor / Standard / Good inside every category of ``column`` (each row sums to 100)."""
    counts = df.groupby([column, "Credit_Score"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=SCORE_ORDER, fill_value=0)
    return counts.div(counts.sum(axis=1), axis=0) * 100


def score_share(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Same as score_mix but in long format (one row per category and score), ready for plotly express."""
    share = df.groupby([column, "Credit_Score"]).size().reset_index(name="rows")
    share["Percentage"] = share["rows"] / share.groupby(column)["rows"].transform("sum") * 100
    return share


def stacked_bar(df: pd.DataFrame, column: str, category_title: str, order: list, horizontal: bool = True):
    """100% stacked bars, one colour per credit score; ``order`` = order of the categories."""
    share = score_share(df, column)
    common = dict(color="Credit_Score", text_auto=".0f", color_discrete_map=SCORE_COLORS,
                  labels={"Percentage": "Share of rows (%)", column: category_title},
                  category_orders={"Credit_Score": SCORE_ORDER, column: order})
    if horizontal:
        fig = px.bar(share, x="Percentage", y=column, orientation="h", **common)
        fig.update_layout(height=max(260, 80 + 30 * share[column].nunique()), xaxis_range=[0, 100])
    else:
        fig = px.bar(share, x=column, y="Percentage", **common)
        fig.update_layout(height=360, yaxis_range=[0, 100])
    return fig


def score_bar(df: pd.DataFrame, column: str, value_title: str, money: bool = False):
    """Median of ``column`` for Poor / Standard / Good, in the score colours."""
    medians = df.groupby("Credit_Score")[column].agg("median").reindex(SCORE_ORDER).reset_index()
    fig = px.bar(medians, x="Credit_Score", y=column, color="Credit_Score", text_auto="$,.0f" if money else ",.1f",
                 color_discrete_map=SCORE_COLORS, labels={column: value_title, "Credit_Score": "Credit score"})
    fig.update_layout(height=360, showlegend=False)
    return fig


# ── Page ──────────────────────────────────────────────────
page_header("Analysis Questions", "The six questions answered in the notebook, recalculated for the current filters.",
            "circle-question")

df = sidebar_filters(load_data(), key="qa")
if df.empty:
    st.html('<div class="empty"><i class="fa-solid fa-filter-circle-xmark"></i>'
            '<p class="empty__msg">No data matches the current filters.</p></div>')
    st.stop()

medians = df.groupby("Credit_Score")[[
    "Annual_Income", "Delay_from_due_date", "Num_of_Delayed_Payment", "Outstanding_Debt", "Interest_Rate",
    "Credit_History_Age_months",
]].agg("median").reindex(SCORE_ORDER)

# ── Q1 Occupation ─────────────────────────────────────────
question(1, "Does the occupation of a customer affect the credit score?")
occ = score_mix(df, "Occupation").sort_values("Poor", ascending=False)
c1, c2 = st.columns([3, 2], gap="medium")
with c1:
    chart_card(stacked_bar(df, "Occupation", "Occupation", occ.index.tolist()), "Credit score mix per occupation", "briefcase",
               "Sorted by % Poor. Each bar sums to 100%.", "q1-mix")
with c2:
    income = df.groupby("Occupation")["Annual_Income"].agg("median").sort_values(ascending=False).reset_index()
    fig = px.bar(income, x="Annual_Income", y="Occupation", orientation="h", text_auto="$,.0f",
                 labels={"Annual_Income": "Median annual income (USD)"}, color_discrete_sequence=[PRIMARY])
    fig.update_layout(height=max(260, 80 + 30 * len(income)), yaxis_autorange="reversed")
    chart_card(fig, "Median income per occupation", "sack-dollar", "Highest first.", "q1-income")
answer([
    "Every job sits close to the overall Poor share, so occupation alone says little about the credit score.",
])

# ── Q2 Income ─────────────────────────────────────────────
question(2, "Do customers with higher income get better credit scores?")
# 4 equal-sized income groups (quartiles), same idea as the notebook
income_groups = pd.qcut(df["Annual_Income"], 4, labels=["1. Low", "2. Lower-middle", "3. Upper-middle", "4. High"])
df_q2 = df.assign(Income_group=income_groups.astype(str))
income_mix = score_mix(df_q2, "Income_group")
c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(score_bar(df, "Annual_Income", "Median annual income (USD)", money=True),
               "Median annual income by credit score", "chart-simple", "Median = the middle customer of each group.",
               "q2-median")
with c2:
    chart_card(stacked_bar(df_q2, "Income_group", "Income group (quartiles)", sorted(income_mix.index), horizontal=False),
               "Credit score mix per income group", "layer-group", "Customers split into 4 equal-sized income groups.",
               "q2-mix")
answer([
    f"Median income: Poor ${medians.loc['Poor', 'Annual_Income']:,.0f}, Standard "
    f"${medians.loc['Standard', 'Annual_Income']:,.0f}, Good ${medians.loc['Good', 'Annual_Income']:,.0f}.",
    f"Good share: {income_mix['Good'].iloc[0]:.1f}% in the lowest income group vs {income_mix['Good'].iloc[-1]:.1f}% "
    "in the highest. Income helps, but it does not decide the score alone.",
])

# ── Q3 Payment behaviour ──────────────────────────────────
question(3, "How does late payment behaviour relate to the credit score?")
min_mix = score_mix(df, "Payment_of_Min_Amount")
c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(score_bar(df, "Delay_from_due_date", "Median days late"), "Median days late by credit score",
               "clock", "Days between the due date and the payment.", "q3-median")
with c2:
    chart_card(stacked_bar(df, "Payment_of_Min_Amount", "Paid only the minimum amount", ["Yes", "NM", "No"],
                           horizontal=False),
               "Credit score mix by 'paid only the minimum'", "money-bill-wave",
               "Yes = paid only the minimum amount due, No = paid more, NM = not mentioned.", "q3-mix")
items = [f"Median days late: Poor {medians.loc['Poor', 'Delay_from_due_date']:.0f}, Good "
         f"{medians.loc['Good', 'Delay_from_due_date']:.0f}. Median delayed payments: Poor "
         f"{medians.loc['Poor', 'Num_of_Delayed_Payment']:.0f}, Good {medians.loc['Good', 'Num_of_Delayed_Payment']:.0f}."]
if "Yes" in min_mix.index:
    items.append(f"Customers paying only the minimum are {min_mix.loc['Yes', 'Poor']:.1f}% Poor and "
                 f"{min_mix.loc['Yes', 'Good']:.1f}% Good.")
answer(items)

# ── Q4 Debt and interest ──────────────────────────────────
question(4, "How do outstanding debt and interest rate differ between credit score groups?")
c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(score_bar(df, "Outstanding_Debt", "Median outstanding debt (USD)", money=True),
               "Median outstanding debt by credit score", "file-invoice-dollar", "What the customer still owes.",
               "q4-debt")
with c2:
    chart_card(score_bar(df, "Interest_Rate", "Median interest rate (%)"), "Median interest rate by credit score",
               "percent", "Interest rate on the credit card.", "q4-rate")
answer([
    f"Median debt: Poor ${medians.loc['Poor', 'Outstanding_Debt']:,.0f} vs Good "
    f"${medians.loc['Good', 'Outstanding_Debt']:,.0f}.",
    f"Median interest rate: Poor {medians.loc['Poor', 'Interest_Rate']:.0f}% vs Good "
    f"{medians.loc['Good', 'Interest_Rate']:.0f}%.",
])

# ── Q5 Number of credit products ──────────────────────────
question(5, "Does having more credit cards, bank accounts or loans lead to a worse credit score?")
product = st.radio("Product", list(PRODUCT_LABELS), format_func=lambda c: PRODUCT_LABELS[c], horizontal=True,
                   key="q5_product")
rates = df.groupby(product).agg(poor=("Credit_Score", lambda s: (s == "Poor").mean() * 100)).reset_index()
fig = px.line(rates, x=product, y="poor", markers=True, color_discrete_sequence=[SCORE_COLORS["Poor"]],
              labels={product: PRODUCT_LABELS[product], "poor": "Poor scores (%)"})
fig.update_layout(height=360)
chart_card(fig, f"% Poor by number of {PRODUCT_LABELS[product].lower()}", "chart-line",
           "Each point = all records with that many products.", "q5-line")
low, high = rates.iloc[0], rates.iloc[-1]
answer([
    f"With {low[product]:.0f} {PRODUCT_LABELS[product].lower()}, {low['poor']:.1f}% of records are Poor; with "
    f"{high[product]:.0f}, {high['poor']:.1f}% are Poor.",
    "More credit products go with a much higher chance of a Poor score.",
])

# ── Q6 Credit history and mix ─────────────────────────────
question(6, "Does a longer credit history and a better credit mix mean a better credit score?")
mix = score_mix(df, "Credit_Mix")
mix = mix.reindex([m for m in ["Bad", "Standard", "Good"] if m in mix.index])
c1, c2 = st.columns(2, gap="medium")
with c1:
    chart_card(score_bar(df, "Credit_History_Age_months", "Median credit history (months)"),
               "Median credit history age by score", "hourglass-half", "Months since the first credit.", "q6-history")
with c2:
    chart_card(stacked_bar(df, "Credit_Mix", "Credit mix", ["Bad", "Standard", "Good"], horizontal=False),
               "Credit score mix for each credit mix", "layer-group", "Each bar sums to 100%.", "q6-mix")
items = [f"Median credit history: Poor {medians.loc['Poor', 'Credit_History_Age_months'] / 12:.1f} years, "
         f"Good {medians.loc['Good', 'Credit_History_Age_months'] / 12:.1f} years."]
if "Bad" in mix.index and "Good" in mix.index:
    items.append(f"A Bad credit mix is {mix.loc['Bad', 'Poor']:.1f}% Poor; a Good credit mix is "
                 f"{mix.loc['Good', 'Good']:.1f}% Good.")
answer(items)
