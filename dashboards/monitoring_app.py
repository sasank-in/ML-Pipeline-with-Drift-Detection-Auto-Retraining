"""Monitoring Dashboard - real-time view of the ML pipeline."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import glob
from datetime import datetime
from typing import List

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import requests
import joblib

from shared.config import Config
from shared.database import DatabaseManager
from shared.logger import setup_logger

config = Config()
logger = setup_logger("dashboard")
db = DatabaseManager()

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "ML Pipeline Monitor"

# --- Service endpoints for health checks ----------------------------------
INGESTION_URL = f"http://127.0.0.1:{config.service.ingestion_port}/health"
PREDICTION_URL = f"http://127.0.0.1:{config.service.prediction_port}/health"


# --- Theme ----------------------------------------------------------------
STYLE_BLOCK = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=IBM+Plex+Mono&display=swap');
    :root {
        --ink: #0b1220;
        --paper: #f7f4ef;
        --mint: #14b8a6;
        --orange: #f97316;
        --sky: #38bdf8;
        --violet: #8b5cf6;
        --rose: #fb7185;
        --emerald: #34d399;
        --slate: #475569;
        --shadow: 0 20px 40px rgba(12, 17, 29, 0.12);
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: 'Space Grotesk', sans-serif;
        background: radial-gradient(1200px 600px at 15% -10%, #e6fbf8 0%, #f7f4ef 45%, #f1ede6 100%);
        color: var(--ink); }
    .nav { background: linear-gradient(120deg, #0f172a 0%, #124559 60%, #0b1220 100%);
        padding: 16px 36px; position: sticky; top: 0; z-index: 10;
        display: flex; justify-content: space-between; align-items: center; }
    .nav-left a { color: white; text-decoration: none; margin-right: 12px;
        padding: 10px 16px; border-radius: 999px; font-weight: 600;
        letter-spacing: 0.2px; transition: all 0.2s ease; }
    .nav-left a:hover { background: rgba(255,255,255,0.12); transform: translateY(-1px); }
    .nav-left a.active { background: linear-gradient(135deg, var(--orange), #fbbf24); color: #1f1305; }
    .nav-right { color: rgba(255,255,255,0.7); font-family: 'IBM Plex Mono', monospace;
        font-size: 12px; display: flex; align-items: center; gap: 8px; }
    .live-dot { width: 8px; height: 8px; border-radius: 50%;
        background: var(--emerald); animation: pulse 1.6s ease-in-out infinite; }

    .page { min-height: 100vh; padding-bottom: 40px; }
    .panel { max-width: 1280px; margin: 24px auto; background: rgba(255,255,255,0.78);
        backdrop-filter: blur(8px); padding: 28px; border-radius: 18px;
        box-shadow: var(--shadow); border: 1px solid rgba(12, 17, 29, 0.06);
        animation: fadeUp 0.6s ease both; }
    .hero h1 { margin: 0 0 6px 0; font-size: 26px;
        border-bottom: 3px solid var(--orange); padding-bottom: 10px; }
    .hero p { color: #4b5563; margin: 0; font-size: 14px; }

    /* Service health strip */
    .health-strip { display: flex; gap: 10px; margin: 18px 0; flex-wrap: wrap; }
    .health-pill { flex: 1; min-width: 180px; padding: 12px 16px; border-radius: 12px;
        background: white; border: 1px solid rgba(12,17,29,0.08);
        box-shadow: 0 6px 12px rgba(15, 23, 42, 0.06);
        display: flex; align-items: center; gap: 12px; }
    .health-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
    .health-dot.up { background: var(--emerald); box-shadow: 0 0 0 4px rgba(52, 211, 153, 0.15); }
    .health-dot.down { background: var(--rose); box-shadow: 0 0 0 4px rgba(251, 113, 133, 0.15); }
    .health-dot.unknown { background: #cbd5e1; box-shadow: 0 0 0 4px rgba(203, 213, 225, 0.3); }
    .health-name { font-weight: 600; font-size: 13px; }
    .health-detail { font-size: 11px; color: var(--slate); font-family: 'IBM Plex Mono', monospace; }

    /* KPI cards */
    .stats { display: flex; gap: 16px; margin: 18px 0; }
    .stat-card { flex: 1; background: #0f172a; color: white; padding: 18px;
        border-radius: 16px; box-shadow: 0 12px 24px rgba(16, 24, 39, 0.18);
        animation: glowIn 0.6s ease both; }
    .stat-card h3 { margin: 0; font-size: 12px; text-transform: uppercase;
        letter-spacing: 1.2px; opacity: 0.7; }
    .stat-card h2 { margin: 8px 0 0 0; font-size: 26px; font-weight: 700; }
    .stat-card .subtitle { font-size: 11px; opacity: 0.6; margin-top: 4px;
        font-family: 'IBM Plex Mono', monospace; }
    .stat-card.orange { background: linear-gradient(135deg, #f97316, #f59e0b); color: #1f1305; }
    .stat-card.sky    { background: linear-gradient(135deg, #0ea5e9, #38bdf8); color: #041a25; }
    .stat-card.violet { background: linear-gradient(135deg, #7c3aed, #8b5cf6); }
    .stat-card.mint   { background: linear-gradient(135deg, #14b8a6, #34d399); color: #022620; }

    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin: 18px 0; }
    .card { background: white; padding: 18px; border-radius: 14px;
        border: 1px solid rgba(12, 17, 29, 0.08); box-shadow: 0 8px 16px rgba(15, 23, 42, 0.06); }
    .card h2 { font-size: 15px; margin: 0 0 10px 0; color: var(--slate);
        text-transform: uppercase; letter-spacing: 0.8px; font-weight: 700; }
    .card.accent-mint   { border-left: 4px solid var(--mint); }
    .card.accent-sky    { border-left: 4px solid var(--sky); }
    .card.accent-violet { border-left: 4px solid var(--violet); }
    .card.accent-orange { border-left: 4px solid var(--orange); }
    .card.accent-rose   { border-left: 4px solid var(--rose); }

    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { text-align: left; padding: 10px; color: var(--slate);
        border-bottom: 2px solid #e2e8f0; text-transform: uppercase;
        letter-spacing: 0.8px; font-size: 11px; }
    td { padding: 10px; border-bottom: 1px solid #f1f5f9; }
    tr:hover td { background: #fafbfc; }

    .empty { color: #94a3b8; text-align: center; padding: 30px;
        font-style: italic; font-size: 13px; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px;
        font-size: 11px; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
    .badge.ok { background: #d1fae5; color: #065f46; }
    .badge.warn { background: #fef3c7; color: #92400e; }
    .badge.bad { background: #fee2e2; color: #991b1b; }
    .badge.info { background: #dbeafe; color: #1e40af; }

    @keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes glowIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    @media (max-width: 900px) { .stats, .grid, .health-strip { grid-template-columns: 1fr; flex-direction: column; }
        .panel { margin: 14px; padding: 18px; } }
</style>
"""

app.index_string = f"""
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}<title>{{%title%}}</title>{{%favicon%}}{{%css%}}
        {STYLE_BLOCK}
    </head>
    <body>
        {{%app_entry%}}
        <footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer>
    </body>
</html>
"""


# --- Helpers --------------------------------------------------------------
FEATURE_NAMES = [
    "Recency", "Frequency", "TotalItems", "UniqueProducts",
    "AvgOrderValue", "AvgItemsPerOrder", "AvgItemPrice", "CountryEncoded",
]

_class_label_cache: dict = {"version": None, "labels": None}


def get_class_labels() -> List[str]:
    """Introspect class names from the active model. Falls back to 'Class N'.
    Cached per-model-version so we don't reload the pickle every refresh."""
    try:
        active = db.get_active_model()
        if not active:
            return []
        version = active.get('model_version')
        if _class_label_cache["version"] == version:
            return _class_label_cache["labels"]

        path = active.get('model_path')
        if not path or not os.path.exists(path):
            return []
        bundle = joblib.load(path)
        model = bundle.get('model') if isinstance(bundle, dict) else None
        classes = getattr(model, 'classes_', None)
        if classes is None:
            return []
        labels = [f"Class {c}" for c in classes]
        _class_label_cache.update({"version": version, "labels": labels})
        return labels
    except Exception as e:
        logger.warning(f"Could not introspect class labels: {e}")
        return []


def _ping_service(url: str, timeout: float = 1.5) -> dict:
    try:
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=timeout)
        body = r.json() if r.headers.get('Content-Type', '').startswith('application/json') else {}
        return {"up": r.status_code < 500, "code": r.status_code, "body": body}
    except Exception:
        return {"up": False, "code": None, "body": {}}


def _empty_fig(message: str = "No data yet") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(size=13, color="#94a3b8"))
    fig.update_layout(
        xaxis={'visible': False}, yaxis={'visible': False},
        plot_bgcolor='white', paper_bgcolor='white',
        height=280, margin=dict(t=10, b=10, l=10, r=10),
    )
    return fig


def _style_axes(fig: go.Figure):
    fig.update_xaxes(gridcolor='#f1f5f9', linecolor='#cbd5e1', tickfont=dict(size=11))
    fig.update_yaxes(gridcolor='#f1f5f9', linecolor='#cbd5e1', tickfont=dict(size=11))
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                      font=dict(family='Space Grotesk', size=12, color='#0b1220'))


# --- Layout ---------------------------------------------------------------
def health_pill(name: str, dot_class: str, detail: str) -> html.Div:
    return html.Div([
        html.Div(className=f"health-dot {dot_class}"),
        html.Div([
            html.Div(name, className="health-name"),
            html.Div(detail, className="health-detail"),
        ]),
    ], className="health-pill")


app.layout = html.Div([
    # Nav
    html.Div([
        html.Div([
            html.A("Ingestion API", href=f"http://localhost:{config.service.ingestion_port}", target="_blank"),
            html.A("Prediction Service", href=f"http://localhost:{config.service.prediction_port}", target="_blank"),
            html.A("Dashboard", href="#", className="active"),
        ], className="nav-left"),
        html.Div([
            html.Div(className="live-dot"),
            html.Span("Live", id="live-indicator"),
            html.Span(id="last-update", style={"marginLeft": "16px"}),
        ], className="nav-right"),
    ], className="nav"),

    html.Div([
        html.Div([
            html.Div([
                html.H1("ML Pipeline Monitor"),
                html.P("Real-time view of ingestion, predictions, drift detection, and retraining."),
            ], className="hero"),

            # Service health strip
            html.Div(id="health-strip", className="health-strip"),

            # KPI cards
            html.Div([
                html.Div([html.H3("Total Predictions"),
                          html.H2(id='kpi-predictions', children='0'),
                          html.Div(id='kpi-predictions-sub', className='subtitle')], className="stat-card sky"),
                html.Div([html.H3("Drift Events"),
                          html.H2(id='kpi-drift', children='0'),
                          html.Div(id='kpi-drift-sub', className='subtitle')], className="stat-card orange"),
                html.Div([html.H3("Models Trained"),
                          html.H2(id='kpi-models', children='0'),
                          html.Div(id='kpi-models-sub', className='subtitle')], className="stat-card mint"),
                html.Div([html.H3("Latest Accuracy"),
                          html.H2(id='kpi-accuracy', children='N/A'),
                          html.Div(id='kpi-accuracy-sub', className='subtitle')], className="stat-card violet"),
            ], className="stats"),

            # Row 1: drift over time + per-feature heatmap
            html.Div([
                html.Div([html.H2("Drift Score Over Time"),
                          dcc.Graph(id='drift-timeline', config={'displayModeBar': False}, style={'height': '320px'})],
                         className="card accent-orange"),
                html.Div([html.H2("Per-Feature Drift (last 20 checks)"),
                          dcc.Graph(id='drift-heatmap', config={'displayModeBar': False}, style={'height': '320px'})],
                         className="card accent-rose"),
            ], className="grid"),

            # Row 2: model performance + queue depths
            html.Div([
                html.Div([html.H2("Model Performance History"),
                          dcc.Graph(id='model-chart', config={'displayModeBar': False}, style={'height': '320px'})],
                         className="card accent-violet"),
                html.Div([html.H2("Pipeline Queue Depths"),
                          dcc.Graph(id='queue-chart', config={'displayModeBar': False}, style={'height': '320px'})],
                         className="card accent-sky"),
            ], className="grid"),

            # Row 3: prediction distribution + training history
            html.Div([
                html.Div([html.H2("Prediction Distribution"),
                          dcc.Graph(id='prediction-chart', config={'displayModeBar': False}, style={'height': '300px'})],
                         className="card accent-sky"),
                html.Div([html.H2("Retraining History"),
                          html.Div(id='training-history')],
                         className="card accent-mint"),
            ], className="grid"),

            # Row 4: recent predictions + system info
            html.Div([
                html.Div([html.H2("Recent Predictions"),
                          html.Div(id='recent-predictions')],
                         className="card accent-sky"),
                html.Div([html.H2("System Info"),
                          html.Div(id='system-info')],
                         className="card accent-mint"),
            ], className="grid"),

        ], className="panel"),
    ], className="page"),

    dcc.Interval(id='tick', interval=5000, n_intervals=0),
])


# --- Callbacks ------------------------------------------------------------
@app.callback(
    [Output('health-strip', 'children'), Output('last-update', 'children')],
    Input('tick', 'n_intervals'),
)
def update_health(_):
    db_ok = db.ping()
    ing = _ping_service(INGESTION_URL)
    pred = _ping_service(PREDICTION_URL)

    queues = db.get_queue_depths() if db_ok else {}
    retraining_pending = queues.get('retraining_queue', 0)
    pred_buffer_size = queues.get('prediction_buffer', 0)

    pills = [
        health_pill(
            "Ingestion API",
            'up' if ing['up'] else 'down',
            f"port {config.service.ingestion_port} | {ing['body'].get('status', 'unreachable')}",
        ),
        health_pill(
            "Prediction Service",
            'up' if pred['up'] else 'down',
            f"port {config.service.prediction_port} | model {pred['body'].get('model_version', 'none')}",
        ),
        health_pill(
            "Drift Monitor",
            'up' if pred_buffer_size > 0 or db_ok else 'unknown',
            f"buffer: {pred_buffer_size} samples",
        ),
        health_pill(
            "Retraining Worker",
            'up' if db_ok else 'unknown',
            f"queue: {retraining_pending} pending",
        ),
        health_pill(
            "Database",
            'up' if db_ok else 'down',
            "PostgreSQL" if db.use_postgres else "SQLite",
        ),
    ]
    return pills, f"updated {datetime.now().strftime('%H:%M:%S')}"


@app.callback(
    [Output('kpi-predictions', 'children'), Output('kpi-predictions-sub', 'children'),
     Output('kpi-drift', 'children'), Output('kpi-drift-sub', 'children'),
     Output('kpi-models', 'children'), Output('kpi-models-sub', 'children'),
     Output('kpi-accuracy', 'children'), Output('kpi-accuracy-sub', 'children')],
    Input('tick', 'n_intervals'),
)
def update_kpis(_):
    try:
        total_preds = db.count_predictions()
        drift_count = db.count_drift_detected()
        model_count = db.count_models()
        active = db.get_active_model()

        accuracy_str = "N/A"
        accuracy_sub = "no model yet"
        if active and active.get('metrics'):
            m = active['metrics']
            acc = m.get('accuracy')
            if acc is not None:
                accuracy_str = f"{acc:.1%}"
                f1 = m.get('f1_score')
                accuracy_sub = f"F1: {f1:.3f}" if f1 is not None else f"v{active.get('model_version', '')}"

        return (
            f"{total_preds:,}", "logged",
            str(drift_count), "with action",
            str(model_count), f"active: {active.get('model_version', '-')[:20] if active else 'none'}",
            accuracy_str, accuracy_sub,
        )
    except Exception as e:
        logger.error(f"KPI error: {e}")
        return "0", "error", "0", "", "0", "", "N/A", ""


@app.callback(Output('drift-timeline', 'figure'), Input('tick', 'n_intervals'))
def update_drift_timeline(_):
    events = db.get_recent_drift_events(limit=80)
    if not events:
        return _empty_fig("No drift checks yet — ingest a batch and wait for the drift monitor")

    events = list(reversed(events))
    times = [e['timestamp'] for e in events]
    scores = [e['drift_score'] if e['drift_score'] is not None else 0 for e in events]
    detected = [e['drift_detected'] for e in events]
    colors = ['#fb7185' if d else '#34d399' for d in detected]
    actions = [e['action_taken'] for e in events]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=scores, mode='lines',
        line=dict(color='#cbd5e1', width=2),
        showlegend=False, hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=times, y=scores, mode='markers',
        marker=dict(color=colors, size=10, line=dict(width=1, color='white')),
        text=[f"score: {s:.3f}<br>detected: {d}<br>action: {a}"
              for s, d, a in zip(scores, detected, actions)],
        hovertemplate='%{text}<extra></extra>',
        showlegend=False,
    ))
    # Retraining trigger threshold line (20% of features per drift_detector)
    fig.add_hline(y=0.2, line_dash='dash', line_color='#f97316',
                  annotation_text='trigger threshold', annotation_position='right')
    fig.update_layout(
        height=280, margin=dict(t=10, b=30, l=40, r=20),
        xaxis_title='', yaxis_title='Drift Score',
        yaxis=dict(range=[0, max(1.0, max(scores) * 1.15 if scores else 1.0)]),
    )
    _style_axes(fig)
    return fig


@app.callback(Output('drift-heatmap', 'figure'), Input('tick', 'n_intervals'))
def update_drift_heatmap(_):
    events = db.get_recent_drift_events(limit=20)
    if not events:
        return _empty_fig("Per-feature drift will appear after the first drift check")

    events = list(reversed(events))
    # Collect feature names from all events (handle schema variation)
    feature_set = set()
    for e in events:
        feature_set.update(e['drift_metrics'].get('features', {}).keys())
    features = sorted(feature_set) if feature_set else FEATURE_NAMES

    # Build matrix: rows=features, cols=time
    z = []
    for feat in features:
        row = []
        for e in events:
            feat_metrics = e['drift_metrics'].get('features', {}).get(feat, {})
            psi = feat_metrics.get('psi')
            row.append(psi if psi is not None else 0)
        z.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=z, x=[str(e['timestamp'])[-8:] for e in events], y=features,
        colorscale=[[0, '#dcfce7'], [0.3, '#fef3c7'], [0.6, '#fed7aa'], [1.0, '#fca5a5']],
        zmin=0, zmax=0.5,
        colorbar=dict(title='PSI', thickness=10, len=0.7),
        hovertemplate='feature: %{y}<br>time: %{x}<br>PSI: %{z:.3f}<extra></extra>',
    ))
    fig.update_layout(height=280, margin=dict(t=10, b=30, l=120, r=20))
    _style_axes(fig)
    fig.update_xaxes(showgrid=False)
    return fig


@app.callback(Output('model-chart', 'figure'), Input('tick', 'n_intervals'))
def update_model_chart(_):
    history = db.get_training_history(limit=20)
    completed = [h for h in history if h['status'] == 'completed' and h['accuracy'] is not None]
    if not completed:
        return _empty_fig("No completed training runs yet")

    completed = list(reversed(completed))
    versions = [h['model_version'][-15:] if h['model_version'] else '?' for h in completed]
    accuracy = [h['accuracy'] for h in completed]
    f1 = [h['f1_score'] or 0 for h in completed]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=versions, y=accuracy, name='Accuracy',
        marker_color='#8b5cf6',
        text=[f'{v:.1%}' for v in accuracy], textposition='outside',
        hovertemplate='%{x}<br>accuracy: %{y:.3f}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=versions, y=f1, name='F1 Score',
        mode='lines+markers', line=dict(color='#f97316', width=3),
        marker=dict(size=9, line=dict(width=2, color='white')),
        hovertemplate='%{x}<br>F1: %{y:.3f}<extra></extra>',
    ))
    fig.update_layout(
        height=280, margin=dict(t=10, b=80, l=50, r=20),
        yaxis=dict(range=[0, 1.1], tickformat='.0%'),
        legend=dict(orientation='h', y=1.15, x=0),
        xaxis_tickangle=-30,
    )
    _style_axes(fig)
    return fig


@app.callback(Output('queue-chart', 'figure'), Input('tick', 'n_intervals'))
def update_queue_chart(_):
    queues = db.get_queue_depths()
    # Ensure consistent ordering with zeros for absent queues
    known = ['data_queue', 'stream_queue', 'prediction_buffer', 'retraining_queue']
    labels = [q.replace('_', ' ') for q in known]
    values = [queues.get(q, 0) for q in known]

    if sum(values) == 0:
        return _empty_fig("All queues empty — ingest some data to see activity")

    palette = ['#38bdf8', '#14b8a6', '#8b5cf6', '#f97316']
    fig = go.Figure(data=[go.Bar(
        y=labels, x=values, orientation='h',
        marker_color=palette,
        text=[f'{v:,}' for v in values], textposition='outside',
        hovertemplate='%{y}: %{x:,} items<extra></extra>',
    )])
    fig.update_layout(
        height=280, margin=dict(t=10, b=30, l=130, r=40),
        xaxis_title='items', showlegend=False,
    )
    _style_axes(fig)
    fig.update_yaxes(showgrid=False)
    return fig


@app.callback(Output('prediction-chart', 'figure'), Input('tick', 'n_intervals'))
def update_prediction_chart(_):
    rows = db._exec(
        "SELECT prediction, COUNT(*) FROM predictions GROUP BY prediction ORDER BY prediction",
        fetch='all',
    ) or []
    if not rows:
        return _empty_fig("No predictions logged yet")

    class_labels = get_class_labels()
    labels, values = [], []
    for r in rows:
        cls_idx = int(r[0])
        if cls_idx < len(class_labels):
            labels.append(class_labels[cls_idx])
        else:
            labels.append(f"Class {cls_idx}")
        values.append(int(r[1]))

    palette = ['#38bdf8', '#fb7185', '#8b5cf6', '#14b8a6', '#f97316']
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=palette[:len(labels)], line=dict(color='white', width=3)),
        textinfo='label+percent', textfont=dict(size=12),
        hovertemplate='%{label}<br>count: %{value:,}<br>%{percent}<extra></extra>',
    )])
    fig.update_layout(
        height=260, margin=dict(t=10, b=10, l=10, r=10),
        showlegend=False, paper_bgcolor='white',
    )
    return fig


@app.callback(Output('training-history', 'children'), Input('tick', 'n_intervals'))
def update_training_history(_):
    history = db.get_training_history(limit=8)
    if not history:
        return html.Div("No training jobs yet", className="empty")

    rows = []
    for h in history:
        status = h['status']
        badge_cls = {'completed': 'ok', 'failed': 'bad', 'started': 'info'}.get(status, 'warn')
        ts = str(h['timestamp'])[5:19] if h['timestamp'] else '-'
        version = (h['model_version'] or '-')[-15:]
        acc = f"{h['accuracy']:.1%}" if h['accuracy'] is not None else '-'
        trigger = h['trigger_reason'] or '-'
        rows.append(html.Tr([
            html.Td(ts, style={'fontFamily': 'IBM Plex Mono', 'fontSize': '11px'}),
            html.Td(version, style={'fontFamily': 'IBM Plex Mono', 'fontSize': '11px'}),
            html.Td(html.Span(status, className=f'badge {badge_cls}')),
            html.Td(acc),
            html.Td(trigger, style={'color': '#64748b', 'fontSize': '11px'}),
        ]))
    return html.Table([
        html.Thead(html.Tr([html.Th('Time'), html.Th('Version'),
                            html.Th('Status'), html.Th('Acc'), html.Th('Trigger')])),
        html.Tbody(rows),
    ])


@app.callback(Output('recent-predictions', 'children'), Input('tick', 'n_intervals'))
def update_recent_predictions(_):
    rows = db._exec(
        "SELECT prediction, probability, timestamp, model_version "
        "FROM predictions ORDER BY id DESC LIMIT 8",
        fetch='all',
    ) or []
    if not rows:
        return html.Div("No predictions yet — try POST /predict", className="empty")

    class_labels = get_class_labels()
    palette = ['#38bdf8', '#fb7185', '#8b5cf6', '#14b8a6', '#f97316']

    table_rows = []
    for r in rows:
        cls_idx = int(r[0])
        label = class_labels[cls_idx] if cls_idx < len(class_labels) else f"Class {cls_idx}"
        color = palette[cls_idx % len(palette)]
        prob = f"{float(r[1]):.1%}" if r[1] is not None else '-'
        ts = str(r[2])[11:19] if r[2] else '-'
        version = (r[3] or '-')[-15:]
        table_rows.append(html.Tr([
            html.Td(ts, style={'fontFamily': 'IBM Plex Mono', 'fontSize': '11px'}),
            html.Td(label, style={'color': color, 'fontWeight': '600'}),
            html.Td(prob),
            html.Td(version, style={'fontFamily': 'IBM Plex Mono', 'fontSize': '11px', 'color': '#64748b'}),
        ]))
    return html.Table([
        html.Thead(html.Tr([html.Th('Time'), html.Th('Prediction'),
                            html.Th('Confidence'), html.Th('Model')])),
        html.Tbody(table_rows),
    ])


@app.callback(Output('system-info', 'children'), Input('tick', 'n_intervals'))
def update_system_info(_):
    active = db.get_active_model()
    queues = db.get_queue_depths()
    model_files = glob.glob('models/*.pkl')

    items = [
        ("Database", "PostgreSQL" if db.use_postgres else "SQLite", 'ok' if db.ping() else 'bad'),
        ("Active Model", (active['model_version'][:30] if active else 'none'), 'ok' if active else 'warn'),
        ("Model Files on Disk", str(len(model_files)), 'info'),
        ("Data Queue", str(queues.get('data_queue', 0)), 'info'),
        ("Stream Queue", str(queues.get('stream_queue', 0)), 'info'),
        ("Prediction Buffer", str(queues.get('prediction_buffer', 0)), 'info'),
        ("Retraining Queue", str(queues.get('retraining_queue', 0)), 'info'),
    ]
    rows = []
    for label, value, badge_cls in items:
        rows.append(html.Tr([
            html.Td(label, style={'fontWeight': '600', 'color': '#475569'}),
            html.Td(html.Span(value, className=f'badge {badge_cls}'),
                    style={'textAlign': 'right'}),
        ]))
    return html.Table(rows)


# --- Main -----------------------------------------------------------------
if __name__ == '__main__':
    host = os.getenv('BIND_HOST', '127.0.0.1')
    port = config.service.dashboard_port
    logger.info(f"Starting dashboard on {host}:{port}")
    app.run(host=host, port=port, debug=False)
