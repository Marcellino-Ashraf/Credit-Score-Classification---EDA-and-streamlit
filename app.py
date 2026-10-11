"""Entry point: the Streamlit app (dashboard.py) plus the voice assistant's WebSocket route.

Run with:  streamlit run app.py      (same command locally and on Streamlit Community Cloud)

The voice bridge is mounted on the app's own address (/voice-ws) instead of a separate port,
because Streamlit Cloud only exposes the app's port.
"""

import streamlit as st
from starlette.routing import WebSocketRoute

from utils.voice_bridge import voice_ws

app = st.App("dashboard.py", routes=[WebSocketRoute("/voice-ws", voice_ws)])
