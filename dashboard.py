"""The Streamlit app: page config, global styling and navigation.

Started by app.py (st.App), which also serves the voice assistant's WebSocket route.
"""

import streamlit as st

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
        st.Page("pages/analysis_questions.py", title="Analysis Questions", icon=":material/quiz:"),
    ],
    "Assistant": [
        st.Page("pages/voice_assistant.py", title="Voice Assistant", icon=":material/mic:"),
    ],
}

st.navigation(pages).run()
