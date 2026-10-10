"""Entry point: page config, global styling and navigation.

Run with:  conda run -n ML streamlit run app.py
"""

import streamlit as st

from utils import theme  # noqa: F401  (registers the "credit" Plotly template as default)
from utils.components import inject_global_css

st.set_page_config(page_title="Credit Score Analytics", layout="wide", initial_sidebar_state="auto")
inject_global_css()

pages = {
    "Overview": [
        st.Page("pages/overview.py", title="Overview", icon=":material/home:", default=True),
    ],
    "Analysis": [
        st.Page("pages/univariate_analysis.py", title="Univariate Analysis", icon=":material/bar_chart:"),
        st.Page("pages/score_drivers.py", title="Credit Score Drivers", icon=":material/query_stats:"),
        st.Page("pages/occupation_insights.py", title="Occupation Insights", icon=":material/work:"),
        st.Page("pages/analysis_questions.py", title="Analysis Questions", icon=":material/quiz:"),
    ],
    "Customers": [
        st.Page("pages/customer_lookup.py", title="Customer Lookup", icon=":material/person_search:"),
    ],
}

st.navigation(pages).run()
