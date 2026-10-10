"""Figure builders on top of the 'credit' template: sorted bars, formatted hovers, labelled axes.

``kind`` arguments are one of 'currency' | 'count' | 'percent' | 'number' (see ``utils.theme.FORMATS``).
Every chart that splits by credit score uses the same traffic-light colours (``theme.SCORE_COLORS``).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from utils import theme

DEFAULT_HEIGHT = 360


def bar(df: pd.DataFrame, category: str, value: str, kind: str, category_title: str, value_title: str,
        horizontal: bool = True, sort: bool = True, labels: bool = True, color: str = theme.PRIMARY,
        height: int | None = None) -> go.Figure:
    """Single-series bar chart. ``sort=True`` puts the largest bar first; ``False`` keeps row order."""
    if sort:
        df = df.sort_values(value, ascending=False)
    cat, val = df[category].astype(str), df[value]
    if horizontal:
        x, y, v_axis, c_axis = val, cat, "x", "y"
    else:
        x, y, v_axis, c_axis = cat, val, "y", "x"
    fig = go.Figure(go.Bar(
        x=x, y=y, orientation="h" if horizontal else "v", marker_color=color,
        text=val if labels else None,
        texttemplate=theme.label_value(kind, v_axis) if labels else None,
        textposition="outside", cliponaxis=False, textfont=dict(color=theme.MUTED, size=12),
        hovertemplate=f"<b>%{{{c_axis}}}</b><br>{value_title}: {theme.hover_value(kind, v_axis)}<extra></extra>",
    ))
    value_axis = dict(title_text=value_title, tickformat=theme.FORMATS[kind]["tick"])
    if labels and len(val) and val.max() > 0:
        value_axis["range"] = [0, val.max() * 1.18]  # headroom so outside labels are not clipped
    if horizontal:
        # Plotly draws horizontal bars bottom-up; reverse so the first row sits on top.
        fig.update_layout(xaxis=value_axis, yaxis=dict(title_text=category_title, autorange="reversed",
                                                      showgrid=False, type="category"))
        height = height or max(260, min(900, 60 + 28 * len(df)))
    else:
        fig.update_layout(yaxis=value_axis, xaxis=dict(title_text=category_title, showgrid=False,
                                                      type="category"))
    fig.update_layout(height=height or DEFAULT_HEIGHT, showlegend=False)
    return fig


def donut(labels: pd.Series, values: pd.Series, value_title: str, colors: list[str] | None = None) -> go.Figure:
    """Donut for 5 or fewer categories, slices sorted largest first."""
    if len(labels) > 5:
        raise ValueError("Donut charts are limited to 5 categories; use a bar chart instead.")
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55, sort=colors is None, direction="clockwise",
        marker=dict(colors=colors or theme.CATEGORICAL), textinfo="percent", texttemplate="%{percent:.1%}",
        hovertemplate=f"<b>%{{label}}</b><br>{value_title}: %{{value:,}}<br>Share: %{{percent:.1%}}<extra></extra>",
    ))
    fig.update_layout(height=DEFAULT_HEIGHT)
    return fig


def score_donut(shares: pd.Series, counts: pd.Series) -> go.Figure:
    """Credit score donut in Poor -> Good order with the score colours."""
    return donut(pd.Series(shares.index), counts.reindex(shares.index).values, "Rows",
                 colors=[theme.SCORE_COLORS[s] for s in shares.index])


def histogram(series: pd.Series, x_title: str, nbins: int = 50) -> go.Figure:
    """Distribution of a numeric column."""
    fig = go.Figure(go.Histogram(
        x=series, nbinsx=nbins, marker_color=theme.PRIMARY, marker_line=dict(color="#FFFFFF", width=1),
        hovertemplate=f"{x_title}: %{{x}}<br>Rows: %{{y:,}}<extra></extra>",
    ))
    fig.update_layout(height=DEFAULT_HEIGHT, bargap=0.02, showlegend=False,
                      xaxis=dict(title_text=x_title, showgrid=False),
                      yaxis=dict(title_text="Rows (count)", tickformat=",d"))
    return fig


def histogram_by_score(df: pd.DataFrame, column: str, x_title: str, nbins: int = 50) -> go.Figure:
    """Overlaid histograms of ``column``, one per credit score, as % of each group (so sizes compare fairly)."""
    fig = go.Figure()
    for s in theme.SCORE_ORDER:
        fig.add_histogram(x=df.loc[df["Credit_Score"] == s, column], name=s, nbinsx=nbins,
                          histnorm="percent", marker_color=theme.SCORE_COLORS[s], opacity=0.55,
                          hovertemplate=f"<b>{s}</b><br>{x_title}: %{{x}}<br>%{{y:.1f}}% of group<extra></extra>")
    fig.update_layout(barmode="overlay", bargap=0.02, height=DEFAULT_HEIGHT,
                      xaxis=dict(title_text=x_title, showgrid=False),
                      yaxis=dict(title_text="% of score group", ticksuffix="%"))
    return fig


def box_by_score(df: pd.DataFrame, column: str, y_title: str, kind: str = "number") -> go.Figure:
    """One box per credit score (outlier points hidden to keep 90K rows light)."""
    fig = go.Figure()
    for s in theme.SCORE_ORDER:
        fig.add_box(y=df.loc[df["Credit_Score"] == s, column], name=s, marker_color=theme.SCORE_COLORS[s],
                    boxpoints=False, hoverinfo="y")
    fig.update_layout(height=DEFAULT_HEIGHT, showlegend=False,
                      xaxis=dict(title_text="Credit score", showgrid=False),
                      yaxis=dict(title_text=y_title, tickformat=theme.FORMATS[kind]["tick"]))
    return fig


def score_stacked_bar(mix: pd.DataFrame, category_title: str, horizontal: bool = True,
                      height: int | None = None) -> go.Figure:
    """100% stacked bars: credit score mix (columns Poor/Standard/Good, rows = categories) in row order."""
    cats = [str(c) for c in mix.index]
    fig = go.Figure()
    for s in theme.SCORE_ORDER:
        vals = mix[s].values
        common = dict(name=s, marker_color=theme.SCORE_COLORS[s], text=vals, texttemplate="%{text:.0f}%",
                      textposition="inside", insidetextanchor="middle", textfont=dict(color="#FFFFFF", size=11))
        if horizontal:
            fig.add_bar(y=cats, x=vals, orientation="h",
                        hovertemplate=f"<b>%{{y}}</b><br>{s}: %{{x:.1f}}%<extra></extra>", **common)
        else:
            fig.add_bar(x=cats, y=vals, hovertemplate=f"<b>%{{x}}</b><br>{s}: %{{y:.1f}}%<extra></extra>", **common)
    pct_axis = dict(title_text="Share of rows (%)", range=[0, 100], ticksuffix="%")
    cat_axis = dict(title_text=category_title, showgrid=False, type="category")
    if horizontal:
        fig.update_layout(xaxis=pct_axis, yaxis=dict(**cat_axis, autorange="reversed"),
                          height=height or max(260, min(900, 80 + 30 * len(cats))))
    else:
        fig.update_layout(yaxis=pct_axis, xaxis=cat_axis, height=height or DEFAULT_HEIGHT)
    fig.update_layout(barmode="stack", bargap=0.25)
    return fig


def score_lines(df: pd.DataFrame, x: str, x_title: str, y_title: str = "Share of rows (%)") -> go.Figure:
    """One line per credit score over an ordered x (``df`` has column ``x`` plus Poor/Standard/Good)."""
    fig = go.Figure()
    for s in theme.SCORE_ORDER:
        fig.add_scatter(x=df[x].astype(str), y=df[s], name=s, mode="lines+markers",
                        line=dict(color=theme.SCORE_COLORS[s], width=2.5), marker=dict(size=7),
                        hovertemplate=f"<b>%{{x}}</b><br>{s}: %{{y:.1f}}%<extra></extra>")
    fig.update_layout(height=DEFAULT_HEIGHT, xaxis=dict(title_text=x_title, showgrid=False, type="category"),
                      yaxis=dict(title_text=y_title, ticksuffix="%", rangemode="tozero"))
    return fig


def line(df: pd.DataFrame, x: str, y: str, kind: str, x_title: str, y_title: str,
         color: str = theme.PRIMARY) -> go.Figure:
    """Single-series line chart with markers."""
    fig = go.Figure(go.Scatter(
        x=df[x], y=df[y], mode="lines+markers", line=dict(color=color, width=2.5), marker=dict(size=7),
        hovertemplate=f"<b>%{{x}}</b><br>{y_title}: {theme.hover_value(kind, 'y')}<extra></extra>",
    ))
    fig.update_layout(height=DEFAULT_HEIGHT, showlegend=False, xaxis=dict(title_text=x_title, showgrid=False),
                      yaxis=dict(title_text=y_title, tickformat=theme.FORMATS[kind]["tick"], rangemode="tozero"))
    return fig


def scatter_by_score(df: pd.DataFrame, x: str, y: str, x_title: str, y_title: str) -> go.Figure:
    """Scatter coloured by credit score (pass a sample: thousands of points, not 90K)."""
    fig = go.Figure()
    for s in theme.SCORE_ORDER:
        d = df[df["Credit_Score"] == s]
        fig.add_scattergl(x=d[x], y=d[y], name=s, mode="markers",
                          marker=dict(color=theme.SCORE_COLORS[s], size=5, opacity=0.5),
                          hovertemplate=f"<b>{s}</b><br>{x_title}: %{{x:,.2f}}<br>{y_title}: %{{y:,.2f}}<extra></extra>")
    fig.update_layout(height=420, xaxis=dict(title_text=x_title), yaxis=dict(title_text=y_title))
    return fig


def heatmap(matrix: pd.DataFrame, x_title: str, y_title: str, value_title: str, zmin: float = 0,
            zmax: float = 100, colorscale: list | None = None, fmt: str = ".0f", suffix: str = "%") -> go.Figure:
    """Annotated grid (score mix tables, correlation matrices)."""
    fig = go.Figure(go.Heatmap(
        z=matrix.values, x=[str(c) for c in matrix.columns], y=[str(i) for i in matrix.index],
        colorscale=colorscale or theme.SEQUENTIAL, zmin=zmin, zmax=zmax, xgap=2, ygap=2,
        texttemplate=f"%{{z:{fmt}}}{suffix}", textfont=dict(size=11),
        colorbar=dict(thickness=10, outlinewidth=0, ticksuffix=suffix),
        hovertemplate=f"{y_title}: %{{y}}<br>{x_title}: %{{x}}<br>{value_title}: %{{z:{fmt}}}{suffix}<extra></extra>",
    ))
    fig.update_layout(height=max(320, 80 + 34 * len(matrix)),
                      xaxis=dict(title_text=x_title, showgrid=False, type="category"),
                      yaxis=dict(title_text=y_title, showgrid=False, autorange="reversed", type="category"))
    return fig
