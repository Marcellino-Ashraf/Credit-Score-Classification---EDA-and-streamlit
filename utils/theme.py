"""Design tokens and the shared Plotly template ("credit").

Importing this module registers the template and makes it the Plotly default,
so every figure in the app picks up the same look.
"""

import plotly.graph_objects as go
import plotly.io as pio

# ── Palette ───────────────────────────────────────────────
PRIMARY = "#0E7490"
PRIMARY_DARK = "#164E63"
ACCENT = "#0891B2"
SKY = "#22D3EE"
TEXT = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"
SURFACE = "#F8FAFC"
WHITE = "#FFFFFF"

# Credit score colours: traffic-light order, used everywhere the target appears
SCORE_ORDER = ["Poor", "Standard", "Good"]
SCORE_COLORS = {"Poor": "#DC2626", "Standard": "#F59E0B", "Good": "#16A34A"}

CATEGORICAL = ["#0E7490", "#0891B2", "#22D3EE", "#6366F1", "#94A3B8", "#164E63"]

# Sequential scale for heatmaps (light cyan -> primary-dark)
SEQUENTIAL = [[0.0, "#ECFEFF"], [0.35, "#67E8F9"], [0.7, "#0891B2"], [1.0, PRIMARY_DARK]]
# Diverging scale for correlations (-1 red, 0 white, +1 teal)
DIVERGING = [[0.0, "#DC2626"], [0.5, "#FFFFFF"], [1.0, PRIMARY]]

FONT_FAMILY = "Inter, system-ui, sans-serif"

# ── Number formats (d3-format): exact values on hover, compact on bar/point labels and axes ──
FORMATS: dict[str, dict[str, str]] = {
    "currency": {"hover": "$%{VALUE:,.2f}", "label": "$%{VALUE:,.0f}", "tick": "$,.0f"},
    "count": {"hover": "%{VALUE:,}", "label": "%{VALUE:,}", "tick": ",d"},
    "percent": {"hover": "%{VALUE:.1f}%", "label": "%{VALUE:.1f}%", "tick": ".0f"},
    "number": {"hover": "%{VALUE:,.2f}", "label": "%{VALUE:,.1f}", "tick": ",.0f"},
}


def hover_value(kind: str, axis: str) -> str:
    """Return a hover-template fragment that formats ``axis`` ('x', 'y', 'z', 'value') as ``kind``."""
    return FORMATS[kind]["hover"].replace("VALUE", axis)


def label_value(kind: str, axis: str) -> str:
    """Return a compact text-template fragment for bar and point labels."""
    return FORMATS[kind]["label"].replace("VALUE", axis)


def _axis() -> dict:
    return dict(
        gridcolor=BORDER,
        linecolor=BORDER,
        zeroline=False,
        showline=False,
        ticks="",
        automargin=True,
        tickfont=dict(color=MUTED, size=12),
        title=dict(font=dict(color=MUTED, size=12), standoff=10),
    )


def _build_template() -> go.layout.Template:
    template = go.layout.Template(pio.templates["plotly_white"])
    template.layout.update(
        font=dict(family=FONT_FAMILY, size=13, color=TEXT),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        colorway=CATEGORICAL,
        xaxis=_axis(),
        yaxis=_axis(),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            title_text="", font=dict(color=MUTED, size=12),
        ),
        margin=dict(l=8, r=16, t=32, b=8),
        hoverlabel=dict(
            bgcolor="#FFFFFF", bordercolor=BORDER,
            font=dict(family=FONT_FAMILY, size=13, color=TEXT),
        ),
        bargap=0.3,
        title=dict(text=""),
    )
    template.data.bar = [go.Bar(marker=dict(line=dict(width=0)))]
    template.data.pie = [go.Pie(marker=dict(line=dict(color="#FFFFFF", width=2)))]
    return template


pio.templates["credit"] = _build_template()
pio.templates.default = "credit"
