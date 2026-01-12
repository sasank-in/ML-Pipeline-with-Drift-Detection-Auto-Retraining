"""Monitoring Dashboard - Real-time visualization"""
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
import sys
sys.path.append('..')

from shared.config import Config
from shared.database import DatabaseManager
from shared.logger import setup_logger

# Initialize
config = Config()
logger = setup_logger("dashboard")
db = DatabaseManager()

# Create Dash app
app = dash.Dash(__name__)
app.title = "ML Pipeline Monitor"

# Layout
app.layout = html.Div([
    html.H1("Real-Time ML Pipeline Monitoring Dashboard", 
            style={'textAlign': 'center', 'color': '#2c3e50'}),
    
    # Refresh interval
    dcc.Interval(
        id='interval-component',
        interval=5*1000,  # 5 seconds
        n_intervals=0
    ),
    
    # Stats cards
    html.Div([
        html.Div([
            html.H3("Total Predictions"),
            html.H2(id='total-predictions', children='0')
        ], className='stat-card'),
        
        html.Div([
            html.H3("Drift Events"),
            html.H2(id='drift-events', children='0')
        ], className='stat-card'),
        
        html.Div([
            html.H3("Retraining Count"),
            html.H2(id='retraining-count', children='0')
        ], className='stat-card'),
        
        html.Div([
            html.H3("Model Accuracy"),
            html.H2(id='model-accuracy', children='0.00')
        ], className='stat-card'),
    ], style={'display': 'flex', 'justifyContent': 'space-around', 'margin': '20px'}),
    
    # Charts
    html.Div([
        html.Div([
            dcc.Graph(id='accuracy-chart')
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='drift-chart')
        ], style={'width': '48%', 'display': 'inline-block'}),
    ]),
    
    html.Div([
        html.Div([
            dcc.Graph(id='prediction-distribution')
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='training-time-chart')
        ], style={'width': '48%', 'display': 'inline-block'}),
    ]),
    
], style={'fontFamily': 'Arial, sans-serif', 'padding': '20px'})

@app.callback(
    [Output('total-predictions', 'children'),
     Output('drift-events', 'children'),
     Output('retraining-count', 'children'),
     Output('model-accuracy', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_stats(n):
    """Update statistics cards"""
    try:
        # Get stats from database
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # Total predictions
        cursor.execute("SELECT COUNT(*) FROM predictions")
        total_preds = cursor.fetchone()[0]
        
        # Drift events
        cursor.execute("SELECT COUNT(*) FROM drift_events WHERE drift_detected = 1")
        drift_count = cursor.fetchone()[0]
        
        # Retraining count
        cursor.execute("SELECT COUNT(*) FROM training_jobs WHERE status = 'completed'")
        retrain_count = cursor.fetchone()[0]
        
        # Latest accuracy
        cursor.execute("SELECT accuracy FROM training_jobs WHERE status = 'completed' ORDER BY timestamp DESC LIMIT 1")
        result = cursor.fetchone()
        accuracy = f"{result[0]:.4f}" if result else "N/A"
        
        conn.close()
        
        return total_preds, drift_count, retrain_count, accuracy
        
    except Exception as e:
        logger.error(f"Stats update error: {str(e)}")
        return "Error", "Error", "Error", "Error"

@app.callback(
    Output('accuracy-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_accuracy_chart(n):
    """Update accuracy over time chart"""
    try:
        conn = db._get_connection()
        df = pd.read_sql_query("""
            SELECT timestamp, accuracy, f1_score 
            FROM training_jobs 
            WHERE status = 'completed' 
            ORDER BY timestamp
        """, conn)
        conn.close()
        
        if df.empty:
            return go.Figure()
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['accuracy'],
            mode='lines+markers', name='Accuracy',
            line=dict(color='#3498db', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['f1_score'],
            mode='lines+markers', name='F1 Score',
            line=dict(color='#2ecc71', width=2)
        ))
        
        fig.update_layout(
            title='Model Performance Over Time',
            xaxis_title='Time',
            yaxis_title='Score',
            hovermode='x unified'
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Accuracy chart error: {str(e)}")
        return go.Figure()

@app.callback(
    Output('drift-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_drift_chart(n):
    """Update drift detection chart"""
    try:
        conn = db._get_connection()
        df = pd.read_sql_query("""
            SELECT timestamp, drift_detected, drift_score 
            FROM drift_events 
            ORDER BY timestamp DESC 
            LIMIT 50
        """, conn)
        conn.close()
        
        if df.empty:
            return go.Figure()
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['drift_score'],
            mode='markers',
            marker=dict(
                size=10,
                color=df['drift_detected'].map({True: 'red', False: 'green'}),
                line=dict(width=1, color='white')
            ),
            name='Drift Score'
        ))
        
        fig.update_layout(
            title='Drift Detection Events',
            xaxis_title='Time',
            yaxis_title='Drift Score',
            hovermode='closest'
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Drift chart error: {str(e)}")
        return go.Figure()

@app.callback(
    Output('prediction-distribution', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_prediction_distribution(n):
    """Update prediction distribution"""
    try:
        conn = db._get_connection()
        df = pd.read_sql_query("""
            SELECT prediction, COUNT(*) as count 
            FROM predictions 
            GROUP BY prediction
        """, conn)
        conn.close()
        
        if df.empty:
            return go.Figure()
        
        fig = go.Figure(data=[
            go.Bar(x=df['prediction'], y=df['count'],
                   marker_color='#9b59b6')
        ])
        
        fig.update_layout(
            title='Prediction Distribution',
            xaxis_title='Class',
            yaxis_title='Count'
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Distribution chart error: {str(e)}")
        return go.Figure()

@app.callback(
    Output('training-time-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_training_time_chart(n):
    """Update training time chart"""
    try:
        conn = db._get_connection()
        df = pd.read_sql_query("""
            SELECT timestamp, training_time, samples_count 
            FROM training_jobs 
            WHERE status = 'completed' 
            ORDER BY timestamp
        """, conn)
        conn.close()
        
        if df.empty:
            return go.Figure()
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['training_time'],
            name='Training Time',
            marker_color='#e74c3c'
        ))
        
        fig.update_layout(
            title='Training Time per Job',
            xaxis_title='Time',
            yaxis_title='Training Time (seconds)'
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Training time chart error: {str(e)}")
        return go.Figure()

# Helper method for database
def _get_connection(self):
    """Get database connection"""
    import sqlite3
    return sqlite3.connect(self.db_path)

DatabaseManager._get_connection = _get_connection

if __name__ == '__main__':
    logger.info(f"Starting dashboard on port {config.service.dashboard_port}")
    app.run_server(host='0.0.0.0', port=config.service.dashboard_port, debug=False)
