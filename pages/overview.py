import pandas as pd
import plotly.express as px
import streamlit as st

# ── Settings ──────────────────────────────────────────────
SCORE_ORDER = ["Poor", "Standard", "Good"]
SCORE_COLORS = {"Poor": "#DC2626", "Standard": "#F59E0B", "Good": "#16A34A"}
IMAGE_PATH = "assets/credit_score.svg"

px.defaults.template = "plotly_white"




# ── Small layout helpers (styles live in assets/style.css) ──
def kpi_row(cards: list[tuple[str, str, str, str]]) -> None:
    """cards = (label, value, Font Awesome icon, caption)."""
    html = "".join(
        f'<div class="kpi"><div class="kpi__top"><span class="kpi__label">{label}</span>'
        f'<span class="kpi__icon"><i class="fa-solid fa-{icon}"></i></span></div>'
        f'<div class="kpi__value">{value}</div><div class="kpi__delta"><span>{caption}</span></div></div>'
        for label, value, icon, caption in cards
    )
    st.html(f'<div class="kpi-row">{html}</div>')


def section_header(title: str, icon: str, caption: str) -> None:
    st.html(f'<div class="section-header"><h2><i class="fa-solid fa-{icon}"></i><span>{title}</span></h2>'
            f'<p class="section-header__caption">{caption}</p></div>')


def chart_card(fig, title: str, icon: str, caption: str, key: str) -> None:
    fig.update_layout(height=360, title_text="", legend_title_text="")
    with st.container(key=f"card-{key}"):
        st.html(f'<div class="card__title"><i class="fa-solid fa-{icon}"></i><span>{title}</span></div>')
        st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False}, key=f"chart-{key}")
        st.html(f'<p class="card__caption">{caption}</p>')


# ── Page ──────────────────────────────────────────────────
df = pd.read_parquet("cleaned_data.parquet")

c1, c2 = st.columns([3, 2], gap="medium")
with c1:
    st.html(
        '<div class="hero"><div class="hero__icon"><i class="fa-solid fa-credit-card"></i></div>'
        '<h1 class="hero__title">Credit Score Classification EDA</h1>'
        '<p class="hero__subtitle">Banking and credit profile of 12,500 customers tracked monthly from January '
        'to August: income, debt, payment behaviour and the credit score the bank gave them '
        '(Poor, Standard or Good).</p></div>'
    )
with c2:
    st.image(IMAGE_PATH, width="stretch")

# Share of each credit score (Poor -> Good)
counts = df["Credit_Score"].value_counts().reindex(SCORE_ORDER, fill_value=0)
shares = counts / counts.sum() * 100

kpi_row([
    ("Records", f"{len(df):,}", "table-list", f"{df.shape[1]} columns"),
    ("Customers", f"{df['Customer_ID'].nunique():,}", "users", f"{df['Month'].nunique()} months each"),
    ("Occupations", f"{df['Occupation'].nunique()}", "briefcase", "almost equal sizes"),
    ("Good score", f"{shares['Good']:.1f}%", "circle-check", "of all records"),
    ("Poor score", f"{shares['Poor']:.1f}%", "triangle-exclamation", "of all records"),
])

# Target overview
section_header("Credit score at a glance", "gauge", "The target variable and how it changes with age.")
c1, c2 = st.columns([2, 3], gap="medium")
with c1:
    fig = px.pie(counts.reset_index(), names="Credit_Score", values="count", hole=0.55, color="Credit_Score",
                 color_discrete_map=SCORE_COLORS)
    chart_card(fig, "Credit score distribution", "chart-pie",
               "Share of customer-month records in each score. Standard dominates; Good is the rarest.", "ov-donut")
with c2:
    # barnorm="percent" turns every age bar into 100%, so each bar shows the score mix at that age
    fig = px.histogram(df, x="Age", color="Credit_Score", nbins=20, barnorm="percent",
                       color_discrete_map=SCORE_COLORS, category_orders={"Credit_Score": SCORE_ORDER})
    fig.update_layout(yaxis_title="Share of rows (%)", bargap=0.05)
    chart_card(fig, "Credit score mix by age", "cake-candles",
               "Each bar is one age range split into Poor / Standard / Good. Older customers have clearly better "
               "scores.", "ov-age")

# Show sample of data
section_header("Data Overview", "table", "Cleaned dataset, one row per customer per month (first 1,000 rows).")
money = ["Annual_Income", "Monthly_Inhand_Salary", "Outstanding_Debt", "Total_EMI_per_month",
         "Amount_invested_monthly", "Monthly_Balance"]
with st.container(key="card-overview-data"):
    st.dataframe(df.head(1000), hide_index=True, width="stretch", height=420,
                 column_config={c: st.column_config.NumberColumn(format="$%.2f") for c in money})

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
description_df = pd.DataFrame([
    {"Column": c, "Type": str(df[c].dtype), "Description": column_descriptions.get(c, "Description not available")}
    for c in df.columns
])
section_header("Dataset Column Descriptions", "book-open", "What each field means after cleaning.")
with st.container(key="card-overview-columns"):
    st.dataframe(description_df, hide_index=True, width="stretch", height=720)

