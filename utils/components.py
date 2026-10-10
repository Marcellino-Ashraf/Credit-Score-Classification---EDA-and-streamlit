"""Reusable UI building blocks. Pages compose these and never write their own HTML/CSS.

Components render through ``st.html`` (no Markdown parsing, so ``$`` amounts are
never mistaken for LaTeX). All styling lives in ``assets/style.css``.
"""

from __future__ import annotations

import html
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import theme

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PATH = os.path.join(ROOT, "assets", "style.css")

FONT_IMPORTS = (
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');\n"
    "@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css');\n"
)
PLOTLY_CONFIG = {"displayModeBar": False}


# ── Formatting ────────────────────────────────────────────
def fmt_currency(value: float, decimals: int | None = None) -> str:
    """'$11,201' for whole amounts, '$861.62' otherwise (or a fixed number of decimals)."""
    if decimals is None:
        decimals = 0 if float(value).is_integer() else 2
    return f"${value:,.{decimals}f}"


def fmt_count(value: float) -> str:
    """Thousands-separated integer."""
    return f"{value:,.0f}"


def fmt_pct(value: float) -> str:
    """Percentage with one decimal."""
    return f"{value:.1f}%"


def fmt_number(value: float, decimals: int = 2) -> str:
    """Thousands-separated number; trailing zeros dropped for whole values."""
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.{decimals}f}"


def _esc(text: object) -> str:
    return html.escape(str(text))


def _icon(name: str | None) -> str:
    return f'<i class="fa-solid fa-{_esc(name)}"></i>' if name else ""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


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


def hero(title: str, subtitle: str, icon: str) -> None:
    """Large banner used on the overview page only."""
    st.html(
        f'<div class="hero"><div class="hero__icon">{_icon(icon)}</div>'
        f'<h1 class="hero__title">{_esc(title)}</h1><p class="hero__subtitle">{_esc(subtitle)}</p></div>'
    )


def section_header(title: str, icon: str | None = None, caption: str | None = None, new: bool = False) -> None:
    """Section title (18px/600) with optional icon, caption and a 'New insight' badge."""
    badge = '<span class="badge">New insight</span>' if new else ""
    cap = f'<p class="section-header__caption">{_esc(caption)}</p>' if caption else ""
    st.html(
        f'<div class="section-header"><h2>{_icon(icon)}<span>{_esc(title)}</span>{badge}</h2>{cap}</div>'
    )


def sidebar_label(text: str) -> None:
    """Small uppercase label that groups sidebar controls."""
    st.html(f'<div class="sidebar-label">{_esc(text)}</div>')


# ── KPI cards ─────────────────────────────────────────────
@dataclass
class Kpi:
    """One KPI card. ``delta`` is a % change; ``delta_caption`` says what it compares."""

    label: str
    value: str
    icon: str
    delta: float | None = None
    delta_caption: str = ""


def _kpi_html(k: Kpi) -> str:
    delta = ""
    if k.delta is not None:
        up = k.delta >= 0
        cls = "up" if up else "down"
        arrow = _icon("arrow-up" if up else "arrow-down")
        delta = (
            f'<div class="kpi__delta kpi__delta--{cls}">{arrow}{abs(k.delta):.1f}%'
            f'<span>{_esc(k.delta_caption)}</span></div>'
        )
    elif k.delta_caption:
        delta = f'<div class="kpi__delta"><span>{_esc(k.delta_caption)}</span></div>'
    return (
        f'<div class="kpi"><div class="kpi__top"><span class="kpi__label">{_esc(k.label)}</span>'
        f'<span class="kpi__icon">{_icon(k.icon)}</span></div>'
        f'<div class="kpi__value">{_esc(k.value)}</div>{delta}</div>'
    )


def kpi_card(k: Kpi) -> None:
    """Render a single KPI card."""
    st.html(f'<div class="kpi-row">{_kpi_html(k)}</div>')


def kpi_row(kpis: list[Kpi]) -> None:
    """Render KPI cards in a responsive grid (wraps on narrow screens)."""
    st.html(f'<div class="kpi-row">{"".join(_kpi_html(k) for k in kpis)}</div>')


# ── Cards ─────────────────────────────────────────────────
@contextmanager
def card(title: str, icon: str | None = None, caption: str | None = None, key: str | None = None) -> Iterator[None]:
    """White bordered card with a title; anything rendered inside the ``with`` block goes in the card.

    ``caption`` is the one-line business explanation shown under the content.
    """
    with st.container(key=f"card-{key or _slug(title)}"):
        st.html(f'<div class="card__title">{_icon(icon)}<span>{_esc(title)}</span></div>')
        yield
        if caption:
            st.html(f'<p class="card__caption">{_esc(caption)}</p>')


def chart_card(fig: go.Figure, title: str, caption: str | None = None, icon: str | None = None,
               key: str | None = None) -> None:
    """Plotly figure inside a card, rendered with the app template (Streamlit theme disabled)."""
    key = key or _slug(title)
    # Streamlit's frontend fills an unset plot_bgcolor with the theme's secondary background, so pin it.
    fig.update_layout(plot_bgcolor=theme.WHITE, paper_bgcolor=theme.WHITE)
    with card(title, icon=icon, caption=caption, key=key):
        st.plotly_chart(fig, width="stretch", theme=None, config=PLOTLY_CONFIG, key=f"chart-{key}")


def insight_callout(items: list[str], title: str = "Key takeaways") -> None:
    """Callout listing short factual sentences derived from the data."""
    if not items:
        return
    lis = "".join(f"<li>{_esc(i)}</li>" for i in items)
    st.html(
        f'<div class="callout"><div class="callout__title">{_icon("lightbulb")}<span>{_esc(title)}</span></div>'
        f"<ul>{lis}</ul></div>"
    )


def empty_state(message: str = "No data matches the current filters.",
                hint: str = "Clear some of the sidebar filters.") -> None:
    """Friendly placeholder for filters that return no rows."""
    st.html(
        f'<div class="empty">{_icon("filter-circle-xmark")}<p class="empty__msg">{_esc(message)}</p>'
        f'<p class="empty__hint">{_esc(hint)}</p></div>'
    )


# ── Tables ────────────────────────────────────────────────
FORMATTERS = {
    "currency": fmt_currency,
    "count": fmt_count,
    "percent": fmt_pct,
    "number": fmt_number,
}


def data_table(df: pd.DataFrame, formats: dict[str, str] | None = None, max_height: int = 420) -> None:
    """Small formatted HTML table: zebra rows, sticky header, right-aligned numbers, no index.

    ``formats`` maps a column to 'currency' | 'count' | 'percent' | 'number'. NaN renders as an em dash.
    For large raw data use ``raw_table`` instead.
    """
    formats = formats or {}
    numeric = {c for c in df.columns if c in formats or pd.api.types.is_numeric_dtype(df[c])}
    head = "".join(f'<th class="{"num" if c in numeric else ""}">{_esc(c)}</th>' for c in df.columns)
    rows = []
    for rec in df.itertuples(index=False):
        cells = []
        for c, v in zip(df.columns, rec):
            if pd.isna(v):
                text = "—"
            elif c in formats:
                text = FORMATTERS[formats[c]](v)
            else:
                text = v
            cells.append(f'<td class="{"num" if c in numeric else ""}">{_esc(text)}</td>')
        rows.append(f"<tr>{''.join(cells)}</tr>")
    st.html(
        f'<div class="table-wrap" style="max-height:{max_height}px"><table class="data-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def raw_table(df: pd.DataFrame, height: int = 420) -> None:
    """Scrollable interactive table for large raw data, with formatted money columns and no index."""
    from utils.data import MONEY_COLUMNS

    config = {c: st.column_config.NumberColumn(format="$%.2f") for c in df.columns if c in MONEY_COLUMNS}
    st.dataframe(df, hide_index=True, width="stretch", height=height, column_config=config)


# ── Analysis questions ────────────────────────────────────
def question(number: int, text: str) -> None:
    """Numbered analysis question banner (same questions as the notebook)."""
    st.html(
        f'<div class="question"><div class="question__label">Question {number}</div>'
        f'<p class="question__text">{_esc(text)}</p></div>'
    )


# ── Filters ───────────────────────────────────────────────
def sidebar_filters(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Shared sidebar filters (occupation, month, age range); returns the filtered frame.

    Defaults select everything, so unfiltered numbers match the notebook.
    """
    with st.sidebar:
        sidebar_label("Filters")
        occupations = st.multiselect(
            "Occupation", sorted(df["Occupation"].unique()), placeholder="All occupations", key=f"{key}_occ",
        )
        months = st.multiselect(
            "Month", list(df["Month"].cat.categories), placeholder="All months", key=f"{key}_months",
        )
        lo, hi = int(df["Age"].min()), int(df["Age"].max())
        ages = st.slider("Age", lo, hi, (lo, hi), key=f"{key}_age")

    if occupations:
        df = df[df["Occupation"].isin(occupations)]
    if months:
        df = df[df["Month"].isin(months)]
    return df[df["Age"].between(*ages)]
