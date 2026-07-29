"""Plotly figures rendered to HTML <div>s for the dashboard/report templates."""
import plotly.graph_objects as go
from plotly.offline import plot

FLAG_COLORS = {"normal": "#2e7d32", "low": "#f9a825", "high": "#ef6c00", "critical": "#c62828"}


def _to_div(fig):
    fig.update_layout(margin=dict(l=30, r=20, t=40, b=30), paper_bgcolor="rgba(0,0,0,0)")
    return plot(fig, output_type="div", include_plotlyjs=False, config={"displayModeBar": False})


def lab_values_bar(lab_results: list) -> str:
    if not lab_results:
        return "<p class='text-muted'>No lab values detected.</p>"
    fig = go.Figure(go.Bar(
        x=[r["label"] for r in lab_results],
        y=[r["value"] for r in lab_results],
        marker_color=[FLAG_COLORS.get(r["flag"], "#1565c0") for r in lab_results],
    ))
    fig.update_layout(title="Lab Values", height=350)
    return _to_div(fig)


def flag_distribution_pie(lab_results: list) -> str:
    if not lab_results:
        return "<p class='text-muted'>No lab values detected.</p>"
    counts = {}
    for r in lab_results:
        counts[r["flag"]] = counts.get(r["flag"], 0) + 1
    fig = go.Figure(go.Pie(
        labels=[k.title() for k in counts.keys()],
        values=list(counts.values()),
        marker_colors=[FLAG_COLORS.get(k, "#1565c0") for k in counts.keys()],
        hole=0.45,
    ))
    fig.update_layout(title="Result Distribution", height=320)
    return _to_div(fig)


def risk_radar(risks: list) -> str:
    if not risks:
        return "<p class='text-muted'>Not enough data for a risk profile.</p>"
    level_score = {"low": 25, "moderate": 60, "high": 90}
    fig = go.Figure(go.Scatterpolar(
        r=[level_score.get(r["level"], 0) for r in risks],
        theta=[r["condition"] for r in risks],
        fill="toself",
        line_color="#1565c0",
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                       title="Risk Profile", height=380, showlegend=False)
    return _to_div(fig)


def health_score_gauge(score: int) -> str:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": "Health Score"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#1565c0"},
            "steps": [
                {"range": [0, 50], "color": "#fde0e0"},
                {"range": [50, 75], "color": "#fff2cc"},
                {"range": [75, 100], "color": "#e2f0d9"},
            ],
        },
    ))
    fig.update_layout(height=300)
    return _to_div(fig)


def score_trend_line(reports: list) -> str:
    """reports: list of {created_at, health_score} oldest->newest."""
    if len(reports) < 2:
        return "<p class='text-muted'>Upload more reports to see your trend.</p>"
    fig = go.Figure(go.Scatter(
        x=[r["created_at"][:10] for r in reports],
        y=[r["health_score"] for r in reports],
        mode="lines+markers", line_color="#1565c0",
    ))
    fig.update_layout(title="Health Score Trend", height=320, yaxis_range=[0, 100])
    return _to_div(fig)
