"""Global styling for app.py and the header helpers used by the Voice Assistant page.

The analysis pages are self-contained: they write their own small HTML blocks using the
CSS classes in ``assets/style.css``.
"""

from __future__ import annotations

import html
import os

import streamlit as st


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PATH = os.path.join(ROOT, "assets", "style.css")

FONT_IMPORTS = (
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');\n"
    "@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css');\n"
)


def _esc(text: object) -> str:
    return html.escape(str(text))


def _icon(name: str | None) -> str:
    return f'<i class="fa-solid fa-{_esc(name)}"></i>' if name else ""


# ── Global styling ────────────────────────────────────────
def inject_global_css() -> None:
    """Load Inter, Font Awesome and ``assets/style.css`` into the page (call once per run, in app.py)."""
    with open(CSS_PATH, encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{FONT_IMPORTS}{css}</style>", unsafe_allow_html=True)


# ── Headers ───────────────────────────────────────────────
def page_header(title: str, subtitle: str, icon: str) -> None:
    """Page title block with a Font Awesome icon badge and a one-line subtitle."""
    st.html(
        f'<div class="page-header"><div class="page-header__icon">{_icon(icon)}</div>'
        f'<div><h1 class="page-header__title">{_esc(title)}</h1>'
        f'<p class="page-header__subtitle">{_esc(subtitle)}</p></div></div>'
    )


def sidebar_label(text: str) -> None:
    """Small uppercase label that groups sidebar controls."""
    st.html(f'<div class="sidebar-label">{_esc(text)}</div>')
