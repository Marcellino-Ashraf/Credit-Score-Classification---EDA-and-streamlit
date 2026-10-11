"""
Voice Assistant Page — Gemini Live voice conversation about the credit score data.

The audio bridge to Gemini lives in utils/voice_bridge.py and is served by app.py as the
WebSocket route /voice-ws on the same address as the app (so it also works on Streamlit Cloud).
This page shows the voice widget and the KPIs / charts the assistant decides to show.
"""

import os
import uuid

import streamlit as st
import streamlit.components.v1 as components

from utils import voice_visuals
from utils.components import page_header, sidebar_label
from utils.voice_bridge import LIVE_MODELS, _df, api_key

# One id per browser session, so the assistant's charts only appear for the person who asked
if "voice_session" not in st.session_state:
    st.session_state["voice_session"] = uuid.uuid4().hex
SESSION_ID = st.session_state["voice_session"]

# ─────────────────────────────────────────────────────────
# HTML / JS Live Conversation Component (markup lives in assets/voice_widget.html)
# ─────────────────────────────────────────────────────────
_WIDGET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "voice_widget.html")


def _make_component(voice: str, session_id: str) -> str:
    with open(_WIDGET_PATH, encoding="utf-8") as f:
        return f.read().replace("__VOICE__", voice).replace("__SESSION__", session_id)


# ─────────────────────────────────────────────────────────
# Streamlit Page
# ─────────────────────────────────────────────────────────
page_header("Voice Assistant", "Ask questions about the credit score data out loud (Egyptian Arabic, Gemini Live).",
            "microphone-lines")

# ── Sidebar ──
with st.sidebar:
    sidebar_label("Gemini Live Voice")
    voice_sel = st.selectbox(
        "نبرة الصوت:",
        options=["Puck", "Aoede", "Kore", "Fenrir", "Charon"],
        index=0,
        help="أصوات Gemini Live الطبيعية المدمجة في النموذج"
    )
    st.divider()
    if not api_key():
        st.error("`GEMINI_API_KEY` غير موجودة في `.env` أو في Secrets")
    else:
        st.success("Gemini Live Bridge جاهز")

    st.caption(f"البيانات: **{len(_df):,}** سجل  |  `{LIVE_MODELS[0]}`")

# ── Main component ──
_, center, _ = st.columns([1, 2, 1])
with center:
    components.html(_make_component(voice_sel, SESSION_ID), height=520, scrolling=False)


# ── Live visuals: KPIs and charts the assistant decides to show ──
@st.fragment(run_every=2)
def _live_visuals():
    """Re-runs every 2 seconds (only this part of the page) and draws the newest visual from the assistant."""
    visual = voice_visuals.latest_visual(SESSION_ID)
    if visual is None:
        st.html('<div class="empty"><i class="fa-solid fa-chart-column"></i>'
                '<p class="empty__msg">الرسومات والأرقام هتظهر هنا</p>'
                '<p class="empty__hint">اسأل مثلاً: أنهي مهنة فيها أكتر تقييم ضعيف؟ أو: العملاء اللي تقييمهم جيد دخلهم أعلى؟</p></div>')
    else:
        voice_visuals.render(visual)


_live_visuals()
