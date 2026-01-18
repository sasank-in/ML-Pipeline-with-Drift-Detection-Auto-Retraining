"""Monitoring Dashboard"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
from datetime import datetime
import json

from shared.config import Config
from shared.database import DatabaseManager
from shared.logger import setup_logger

config = Config()
logger = setup_logger("dashboard")
db = DatabaseManager()

app = dash.Dash(__name__)
app.title = "ML Pipeline Monitor"

BASE_STYLE = """
<style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
    .nav { background: #2c3e50; padding: 15px 40px; }
    .nav a { color: white; text-decoration: none; margin-right: 20px; padding: 8px 15px; border-radius: 5px; }
    .nav a:hover { background: #34495e; }
    .nav a.active { background: #e67e22; }
</style>
"""

NAV_HTML = """
<div class="nav">
    <a href="http://localhost:8001" target="_blank">Ingestion API</a>
    <a href="http://localhost:8002" target="_blank">Prediction Service</a>
    <a href="http://localhost:8050" class="active">Dashboard</a>
</div>
"""

app.layout = html.Div([
    html.Div([
        html.A("Ingestion API", href="http://localhost:8001", target="_blank", 
               style={'color': 'white', 'textDecoration': 'none', 'marginRight': '20px', 'padding': '8px 15px', 'borderRadius': '5px'}),
        html.A("Prediction Service", href="http://localhost:8002", target="_blank",
               style={'color': 'white', 'textDecoration': 'none', 'marginRight': '20px', 'padding': '8px 15px', 'borderRadius': '5px'}),
        html.A("Dashboard", href="http://localhost:8050",
               style={'color': 'white', 'textDecoration': 'none', 'padding': '8px 15px', 'borderRadius': '5px', 'background': '#e67e22'}),
    ], style={'background': '#2c3e50', 'padding': '15px 40px'}),
    
    html.Div([
        html.Div([
            html.H1("ML Pipeline Monitoring Dashboard", style={'color': '#2c3e50', 'borderBottom': '2px solid #e67e22', 'paddingBottom': '10px', 'marginTop': 0}),
            html.P("Real-time monitoring of retail customer prediction system", style={'color': '#7f8c8d'}),
            
            html.Div([
                html.Div([
                    html.H3("Total Predictions", style={'margin': 0, 'fontSize': '14px', 'color': '#7f8c8d', 'fontWeight': 'normal'}),
                    html.H2(id='total-predictions', children='0', style={'margin': '10px 0 0 0', 'color': '#2c3e50', 'fontSize': '28px'})
                ], style={'background': '#3498db', 'color': 'white', 'padding': '20px', 'borderRadius': '10px', 'textAlign': 'center', 'flex': 1}),
                
                html.Div([
                    html.H3("Drift Events", style={'margin': 0, 'fontSize': '14px', 'color': '#7f8c8d', 'fontWeight': 'normal'}),
                    html.H2(id='drift-events', children='0', style={'margin': '10px 0 0 0', 'color': '#2c3e50', 'fontSize': '28px'})
                ], style={'background': '#e74c3c', 'color': 'white', 'padding': '20px', 'borderRadius': '10px', 'textAlign': 'center', 'flex': 1}),
                
                html.Div([
                    html.H3("Models Trained", style={'margin': 0, 'fontSize': '14px', 'color': '#7f8c8d', 'fontWeight': 'normal'}),
                    html.H2(id='retraining-count', children='0', style={'margin': '10px 0 0 0', 'color': '#2c3e50', 'fontSize': '28px'})
                ], style={'background': '#2ecc71', 'color': 'white', 'padding': '20px', 'borderRadius': '10px', 'textAlign': 'center', 'flex': 1}),
                
                html.Div([
                    html.H3("Latest Accuracy", style={'margin': 0, 'fontSize': '14px', 'color': '#7f8c8d', 'fontWeight': 'normal'}),
                    html.H2(id='model-accuracy', children='N/A', style={'margin': '10px 0 0 0', 'color': '#2c3e50', 'fontSize': '28px'})
                ], style={'background': '#9b59b6', 'color': 'white', 'padding': '20px', 'borderRadius': '10px', 'textAlign': 'center', 'flex': 1}),
            ], style={'display': 'flex', 'gap': '20px', 'margin': '20px 0'}),
            
            html.Div([
                html.Div([
                    html.H2("Prediction Distribution", style={'fontSize': '18px', 'color': '#2c3e50', 'marginBottom': '15px'}),
                    dcc.Graph(id='prediction-chart', config={'displayModeBar': False}, style={'height': '350px'})
                ], style={'background': '#ecf0f1', 'padding': '20px', 'borderRadius': '10px', 'borderLeft': '4px solid #3498db', 'flex': 1}),
                
                html.Div([
                    html.H2("Model Performance", style={'fontSize': '18px', 'color': '#2c3e50', 'marginBottom': '15px'}),
                    dcc.Graph(id='model-chart', config={'displayModeBar': False}, style={'height': '350px'})
                ], style={'background': '#ecf0f1', 'padding': '20px', 'borderRadius': '10px', 'borderLeft': '4px solid #9b59b6', 'flex': 1}),
            ], style={'display': 'flex', 'gap': '20px', 'margin': '20px 0'}),
            
            html.Div([
                html.Div([
                    html.H2("Recent Predictions", style={'fontSize': '18px', 'color': '#2c3e50', 'marginBottom': '15px'}),
                    html.Div(id='recent-predictions')
                ], style={'background': '#ecf0f1', 'padding': '20px', 'borderRadius': '10px', 'borderLeft': '4px solid #3498db', 'flex': 1}),
                
                html.Div([
                    html.H2("System Information", style={'fontSize': '18px', 'color': '#2c3e50', 'marginBottom': '15px'}),
                    html.Div(id='system-info')
                ], style={'background': '#ecf0f1', 'padding': '20px', 'borderRadius': '10px', 'borderLeft': '4px solid #2ecc71', 'flex': 1}),
            ], style={'display': 'flex', 'gap': '20px'}),
            
        ], style={'maxWidth': '1200px', 'margin': '30px auto', 'background': 'white', 'padding': '30px', 'borderRadius': '10px', 'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'}),
    ], style={'background': '#f5f5f5', 'minHeight': '100vh', 'padding': '0'}),
    
    dcc.Interval(id='interval-component', interval=5000, n_intervals=0),
    
], style={'fontFamily': 'Arial, sans-serif', 'margin': 0})


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
            metrics = json.loads(result[0]) if isinstance(result[0], str) else result[0]
            accuracy = f"{metrics.get('accuracy', 0):.2%}"
        else:
            accuracy = "N/A"
        
        conn.close()
        return f"{total_preds:,}", str(drift_count), str(model_count), accuracy
        
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
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="#95a5a6")
            )
            fig.update_layout(
                xaxis={'visible': False},
                yaxis={'visible': False},
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=300,
                margin=dict(t=0, b=0, l=0, r=0)
            )
            return fig
        
        labels = ['Regular Customer' if r[0] == 0 else 'High-Value Customer' for r in rows]
        values = [r[1] for r in rows]
        colors = ['#3498db', '#e74c3c']
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textfont=dict(size=12)
        )])
        
        fig.update_layout(
            showlegend=False,
            height=300,
            margin=dict(t=0, b=0, l=0, r=0),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Chart error: {e}")
        return go.Figure()


@app.callback(
    Output('model-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_model_chart(n):
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT model_version, metrics FROM model_registry ORDER BY timestamp")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="#95a5a6")
            )
            fig.update_layout(
                xaxis={'visible': False},
                yaxis={'visible': False},
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=300,
                margin=dict(t=0, b=0, l=0, r=0)
            )
            return fig
        
        versions = []
        accuracies = []
        
        for i, row in enumerate(rows):
            versions.append(f"v{i+1}")
            metrics = json.loads(row[1]) if isinstance(row[1], str) else row[1]
            accuracies.append(metrics.get('accuracy', 0))
        
        fig = go.Figure(data=[go.Bar(
            x=versions,
            y=accuracies,
            marker_color='#9b59b6',
            text=[f'{v:.2%}' for v in accuracies],
            textposition='outside'
        )])
        
        fig.update_layout(
            xaxis_title='Model Version',
            yaxis_title='Accuracy',
            yaxis=dict(range=[0, 1.1], tickformat='.0%'),
            height=300,
            margin=dict(t=20, b=40, l=50, r=20),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Model chart error: {e}")
        return go.Figure()


@app.callback(
    Output('recent-predictions', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_recent_predictions(n):
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT prediction, probability, timestamp FROM predictions ORDER BY timestamp DESC LIMIT 5")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return html.Div("No predictions yet", style={'color': '#95a5a6', 'textAlign': 'center', 'padding': '20px'})
        
        table_rows = []
        for row in rows:
            pred_label = 'High-Value' if row[0] == 1 else 'Regular'
            pred_color = '#e74c3c' if row[0] == 1 else '#3498db'
            table_rows.append(
                html.Tr([
                    html.Td(pred_label, style={'padding': '10px', 'borderBottom': '1px solid #ddd', 'color': pred_color, 'fontWeight': 'bold'}),
                    html.Td(f"{row[1]:.1%}", style={'padding': '10px', 'borderBottom': '1px solid #ddd'}),
                ])
            )
        
        return html.Table([
            html.Thead(html.Tr([
                html.Th("Prediction", style={'padding': '10px', 'textAlign': 'left', 'borderBottom': '2px solid #2c3e50', 'color': '#2c3e50'}),
                html.Th("Confidence", style={'padding': '10px', 'textAlign': 'left', 'borderBottom': '2px solid #2c3e50', 'color': '#2c3e50'}),
            ])),
            html.Tbody(table_rows)
        ], style={'width': '100%', 'borderCollapse': 'collapse'})
        
    except Exception as e:
        logger.error(f"Predictions error: {e}")
        return html.Div("Error loading data", style={'color': '#e74c3c'})


@app.callback(
    Output('system-info', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_system_info(n):
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM predictions")
        total_preds = cursor.fetchone()[0]
        
        cursor.execute("SELECT model_version FROM model_registry ORDER BY timestamp DESC LIMIT 1")
        result = cursor.fetchone()
        current_model = result[0][:30] if result else "None"
        
        cursor.execute("SELECT COUNT(*) FROM drift_events WHERE drift_detected = true")
        drift_count = cursor.fetchone()[0]
        
        conn.close()
        
        info_items = [
            ("Database Status", "Connected", "#2ecc71"),
            ("Active Model", current_model, "#3498db"),
            ("Total Predictions", f"{total_preds:,}", "#9b59b6"),
            ("Drift Alerts", str(drift_count), "#e74c3c"),
        ]
        
        rows = []
        for label, value, color in info_items:
            rows.append(
                html.Tr([
                    html.Td(label, style={'padding': '12px 0', 'borderBottom': '1px solid #ddd', 'fontWeight': 'bold', 'color': '#2c3e50'}),
                    html.Td(value, style={'padding': '12px 0', 'borderBottom': '1px solid #ddd', 'color': color, 'textAlign': 'right'}),
                ])
            )
        
        return html.Table(rows, style={'width': '100%'})
        
    except Exception as e:
        logger.error(f"Info error: {e}")
        return html.Div("Error loading info", style={'color': '#e74c3c'})


if __name__ == '__main__':
    logger.info(f"Starting dashboard on port {config.service.dashboard_port}")
    app.run_server(host='0.0.0.0', port=config.service.dashboard_port, debug=False)
