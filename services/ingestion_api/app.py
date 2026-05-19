"""Data Ingestion API"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify
from flask_cors import CORS
from markupsafe import escape
import numpy as np
import json

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager
from shared.auth import require_api_key
from shared.web_ui import base_style, nav_html

app = Flask(__name__)
# Limit request body to 10 MB to prevent memory exhaustion via huge payloads.
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))
# Lock CORS to configured origins; default deny-all if not set.
_cors_origins = os.getenv('CORS_ORIGINS', '').strip()
if _cors_origins:
    CORS(app, origins=[o.strip() for o in _cors_origins.split(',') if o.strip()])
else:
    CORS(app, origins=[])

config = Config()
logger = setup_logger("ingestion_api")
db = DatabaseManager()

BASE_STYLE = base_style()  # default aqua/blue palette suits ingestion

_NAV_LINKS = [
    ("/", "Home"),
    ("/health", "Health"),
    ("/stats", "Stats"),
    ("/ingest/batch", "Batch Ingest"),
    ("/ingest/stream", "Stream Ingest"),
]


def _nav(active: str) -> str:
    return nav_html(_NAV_LINKS, active=active)

@app.route('/', methods=['GET'])
def index():
    batch_queue = db.get_queue_length('data_queue')
    stream_queue = db.get_queue_length('stream_queue')
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ingestion API - Home</title>{BASE_STYLE}</head>
    <body>
        {_nav('/')}
        <div class="container">
            <h1>Data Ingestion API</h1>
            <span class="status">Running</span>
            <p>Version: 1.0.0 | Service for ingesting data into the ML pipeline</p>
            
            <div class="stats">
                <div class="stat-box">
                    <h3>Batch Queue Size</h3>
                    <p>{batch_queue}</p>
                </div>
                <div class="stat-box alt">
                    <h3>Stream Queue Size</h3>
                    <p>{stream_queue}</p>
                </div>
            </div>
            
            <h2>Available Endpoints</h2>
            <table>
                <tr><th>Method</th><th>Endpoint</th><th>Description</th></tr>
                <tr><td>GET</td><td>/health</td><td>Health check</td></tr>
                <tr><td>GET</td><td>/stats</td><td>Queue statistics</td></tr>
                <tr><td>POST</td><td>/ingest/batch</td><td>Ingest batch data</td></tr>
                <tr><td>POST</td><td>/ingest/stream</td><td>Ingest single sample</td></tr>
            </table>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/health', methods=['GET'])
def health_check():
    db_ok = db.ping()
    overall = 'healthy' if db_ok else 'degraded'
    status_code = 200 if db_ok else 503
    response = {
        'status': overall,
        'service': 'ingestion_api',
        'version': '1.0.0',
        'checks': {'database': 'ok' if db_ok else 'fail'},
    }
    if request.headers.get('Accept', '').find('application/json') != -1:
        return jsonify(response), status_code
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ingestion API - Health</title>{BASE_STYLE}</head>
    <body>
        {_nav('/health')}
        <div class="container">
            <h1>Health Check</h1>
            <div class="stats">
                <div class="stat-box" style="background: #27ae60;">
                    <h3>Status</h3>
                    <p>Healthy</p>
                </div>
                <div class="stat-box">
                    <h3>Service</h3>
                    <p>ingestion_api</p>
                </div>
                <div class="stat-box" style="background: #9b59b6;">
                    <h3>Version</h3>
                    <p>1.0.0</p>
                </div>
            </div>
            <h2>JSON Response</h2>
            <div class="result">{json.dumps({'status': 'healthy', 'service': 'ingestion_api', 'version': '1.0.0'}, indent=2)}</div>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/stats', methods=['GET'])
def get_stats():
    batch_queue = db.get_queue_length('data_queue')
    stream_queue = db.get_queue_length('stream_queue')
    
    if request.headers.get('Accept', '').find('application/json') != -1:
        return jsonify({'status': 'success', 'batch_queue_size': batch_queue, 'stream_queue_size': stream_queue})
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ingestion API - Stats</title>{BASE_STYLE}</head>
    <body>
        {_nav('/stats')}
        <div class="container">
            <h1>Queue Statistics</h1>
            <div class="stats">
                <div class="stat-box">
                    <h3>Batch Queue Size</h3>
                    <p>{batch_queue}</p>
                </div>
                <div class="stat-box alt">
                    <h3>Stream Queue Size</h3>
                    <p>{stream_queue}</p>
                </div>
            </div>
            <h2>JSON Response</h2>
            <div class="result">{json.dumps({'status': 'success', 'batch_queue_size': batch_queue, 'stream_queue_size': stream_queue}, indent=2)}</div>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/ingest/batch', methods=['GET', 'POST'])
@require_api_key
def ingest_batch():
    result_html = ""
    
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.json
            else:
                data = json.loads(request.form.get('data', '{}'))
            
            X = np.array(data['features'])
            y = data.get('labels')

            max_rows = int(os.getenv('MAX_BATCH_ROWS', '10000'))
            if len(X.shape) == 2 and X.shape[0] > max_rows:
                msg = f'Batch too large: {X.shape[0]} > {max_rows}'
                if request.is_json:
                    return jsonify({'status': 'error', 'message': msg}), 413
                return f'<div class="result error">Error: {msg}</div>', 413

            if len(X.shape) != 2:
                if request.is_json:
                    return jsonify({'status': 'error', 'message': 'Features must be 2D array'}), 400
                result_html = '<div class="result error">Error: Features must be 2D array</div>'
            else:
                batch_data = {'features': X.tolist(), 'labels': y, 'batch_id': data.get('batch_id')}
                db.enqueue('data_queue', batch_data)
                logger.info(f"Ingested batch: {X.shape[0]} samples")
                
                response = {'status': 'success', 'samples_ingested': X.shape[0], 'batch_id': data.get('batch_id')}
                if request.is_json:
                    return jsonify(response)
                result_html = f'<div class="result success">{escape(json.dumps(response, indent=2))}</div>'
        except Exception as e:
            if request.is_json:
                return jsonify({'status': 'error', 'message': str(e)}), 500
            result_html = f'<div class="result error">Error: {escape(str(e))}</div>'
    
    sample_data = json.dumps({
        "features": [[0.5, -0.3, 1.2, 0.8, -0.5, 0.1, 0.9, -0.2], [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]],
        "labels": [0, 1],
        "batch_id": "batch_001"
    }, indent=2)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ingestion API - Batch Ingest</title>{BASE_STYLE}</head>
    <body>
        {_nav('/ingest/batch')}
        <div class="container">
            <h1>Batch Data Ingestion</h1>
            <p>Ingest multiple samples at once</p>
            
            <form method="POST">
                <div class="form-group">
                    <label>Data (JSON format):</label>
                    <textarea name="data" placeholder="Enter JSON data...">{sample_data}</textarea>
                </div>
                <button type="submit">Ingest Batch</button>
            </form>
            {result_html}
            
            <h2>Expected Format</h2>
            <div class="result">{sample_data}</div>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/ingest/stream', methods=['GET', 'POST'])
@require_api_key
def ingest_stream():
    result_html = ""
    
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.json
            else:
                data = json.loads(request.form.get('data', '{}'))
            
            features = data['features']
            label = data.get('label')
            
            if not isinstance(features, list):
                if request.is_json:
                    return jsonify({'status': 'error', 'message': 'Features must be a list'}), 400
                result_html = '<div class="result error">Error: Features must be a list</div>'
            else:
                stream_data = {'features': features, 'label': label}
                db.enqueue('stream_queue', stream_data)
                
                response = {'status': 'success', 'message': 'Sample ingested'}
                if request.is_json:
                    return jsonify(response)
                result_html = f'<div class="result success">{escape(json.dumps(response, indent=2))}</div>'
        except Exception as e:
            if request.is_json:
                return jsonify({'status': 'error', 'message': str(e)}), 500
            result_html = f'<div class="result error">Error: {escape(str(e))}</div>'
    
    sample_data = json.dumps({
        "features": [0.5, -0.3, 1.2, 0.8, -0.5, 0.1, 0.9, -0.2],
        "label": 1
    }, indent=2)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ingestion API - Stream Ingest</title>{BASE_STYLE}</head>
    <body>
        {_nav('/ingest/stream')}
        <div class="container">
            <h1>Stream Data Ingestion</h1>
            <p>Ingest a single sample</p>
            
            <form method="POST">
                <div class="form-group">
                    <label>Data (JSON format):</label>
                    <textarea name="data" placeholder="Enter JSON data...">{sample_data}</textarea>
                </div>
                <button type="submit">Ingest Sample</button>
            </form>
            {result_html}
            
            <h2>Expected Format</h2>
            <div class="result">{sample_data}</div>
        </div>
    </body>
    </html>
    """
    return html


if __name__ == '__main__':
    port = config.service.ingestion_port
    host = os.getenv('BIND_HOST', '127.0.0.1')
    logger.info(f"Starting Ingestion API on {host}:{port}")
    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=int(os.getenv('WAITRESS_THREADS', '8')))
    except ImportError:
        logger.warning("waitress not installed — falling back to Flask dev server")
        app.run(host=host, port=port, debug=False)
