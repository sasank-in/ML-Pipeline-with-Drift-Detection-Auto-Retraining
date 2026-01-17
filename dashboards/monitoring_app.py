"""Monitoring Dashboard"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd

from shared.config import Config
from shared.database import DatabaseManager
from shared.logger import setup_logger

config = Config()
logger = setup_logger("dashboard")
db = DatabaseManager()

app = dash.Dash(__name__)
app.title = "ML Pipeline Monitor"

app.layout = html.Div([
    html.H1("ML Pipeline Monitoring Dashboard", 
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
    
    dcc.Interval(id='interval-component', interval=5000, n_intervals=0),
    
    html.Div([
        html.Div([
            html.H3("Total Predictions", style={'color': '#7f8c8d'}),
            html.H2(id='total-predictions', children='0', style={'color': '#3498db'})
        ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px', 'width': '22%'}),
        
        html.Div([
            html.H3("Drift Events", style={'color': '#7f8c8d'}),
            html.H2(id='drift-events', children='0', style={'color': '#e74c3c'})
        ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px', 'width': '22%'}),
        
        html.Div([
            html.H3("Models Trained", style={'color': '#7f8c8d'}),
            html.H2(id='retraining-count', children='0', style={'color': '#2ecc71'})
        ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px', 'width': '22%'}),
        
        html.Div([
            html.H3("Latest Accuracy", style={'color': '#7f8c8d'}),
            html.H2(id='model-accuracy', children='N/A', style={'color': '#9b59b6'})
        ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px', 'width': '22%'}),
    ], style={'display': 'flex', 'justifyContent': 'space-around', 'margin': '20px 0'}),
    
    html.Div([
        html.Div([dcc.Graph(id='prediction-chart')], style={'width': '48%', 'display': 'inline-block'}),
        html.Div([dcc.Graph(id='model-chart')], style={'width': '48%', 'display': 'inline-block', 'float': 'right'}),
    ]),
    
], style={'fontFamily': 'Arial', 'padding': '20px', 'backgroundColor': '#fff'})


@app.callback(
    [Output('total-predictions', 'children'),
     Output('drift-events', 'children'),
     Output('retraining-count', 'children'),
     Output('model-accuracy', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_stats(n):
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM predictions")
        total_preds = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM drift_events WHERE drift_detected = true")
        drift_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM model_registry")
        model_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT metrics FROM model_registry ORDER BY timestamp DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            import json
            metrics = json.loads(result[0]) if isinstance(result[0], str) else result[0]
            accuracy = f"{metrics.get('accuracy', 0):.4f}"
        else:
            accuracy = "N/A"
        
        conn.close()
        return str(total_preds), str(drift_count), str(model_count), accuracy
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return "0", "0", "0", "N/A"


@app.callback(
    Output('prediction-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_prediction_chart(n):
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT prediction, COUNT(*) FROM predictions GROUP BY prediction")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return go.Figure(layout={'title': 'Prediction Distribution (No Data)'})
        
        labels = [f"Class {r[0]}" for r in rows]
        values = [r[1] for r in rows]
        
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
        fig.update_layout(title='Prediction Distribution')
        return fig
        
    except Exception as e:
        logger.error(f"Chart error: {e}")
        return go.Figure(layout={'title': 'Prediction Distribution (Error)'})


@app.callback(
    Output('model-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_model_chart(n):
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT model_version, metrics, timestamp FROM model_registry ORDER BY timestamp")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return go.Figure(layout={'title': 'Model Performance (No Data)'})
        
        import json
        versions = []
        accuracies = []
        for row in rows:
            versions.append(row[0][:15])
            metrics = json.loads(row[1]) if isinstance(row[1], str) else row[1]
            accuracies.append(metrics.get('accuracy', 0))
        
        fig = go.Figure(data=[go.Bar(x=versions, y=accuracies, marker_color='#3498db')])
        fig.update_layout(title='Model Accuracy History', xaxis_title='Version', yaxis_title='Accuracy')
        return fig
        
    except Exception as e:
        logger.error(f"Model chart error: {e}")
        return go.Figure(layout={'title': 'Model Performance (Error)'})


if __name__ == '__main__':
    logger.info(f"Starting dashboard on port {config.service.dashboard_port}")
    app.run_server(host='0.0.0.0', port=config.service.dashboard_port, debug=False)
