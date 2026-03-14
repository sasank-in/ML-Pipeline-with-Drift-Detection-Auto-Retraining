"""Data Ingestion API"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import numpy as np
import json

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager

app = Flask(__name__)
CORS(app)

config = Config()
logger = setup_logger("ingestion_api")
db = DatabaseManager()

BASE_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=IBM+Plex+Mono&display=swap');
    :root {
        --ink: #0b1220;
        --paper: #f7f4ef;
        --aqua: #00c2b3;
        --sun: #ffb703;
        --coral: #ff6b6b;
        --slate: #223249;
        --glass: rgba(255, 255, 255, 0.72);
        --shadow: 0 20px 40px rgba(12, 17, 29, 0.12);
    }
    * { box-sizing: border-box; }
    body { font-family: 'Space Grotesk', sans-serif; margin: 0; background: radial-gradient(1200px 600px at 10% -10%, #dff7f2 0%, #f7f4ef 45%, #f3efe7 100%); color: var(--ink); }
    .nav { background: linear-gradient(120deg, #101827 0%, #1d2d44 60%, #0b1220 100%); padding: 16px 40px; position: sticky; top: 0; z-index: 10; }
    .nav a { color: white; text-decoration: none; margin-right: 12px; padding: 10px 16px; border-radius: 999px; font-weight: 600; letter-spacing: 0.2px; transition: all 0.2s ease; }
    .nav a:hover { background: rgba(255,255,255,0.12); transform: translateY(-1px); }
    .nav a.active { background: linear-gradient(135deg, var(--aqua), #00a6ff); }
    .container { max-width: 980px; margin: 28px auto; background: var(--glass); backdrop-filter: blur(8px); padding: 32px; border-radius: 18px; box-shadow: var(--shadow); border: 1px solid rgba(12, 17, 29, 0.06); animation: fadeUp 0.6s ease both; }
    h1 { color: var(--ink); border-bottom: 3px solid var(--aqua); padding-bottom: 10px; margin-top: 0; font-size: 28px; letter-spacing: 0.3px; }
    .status { background: linear-gradient(120deg, #1dd3b0, #06d6a0); color: #042019; padding: 6px 16px; border-radius: 999px; display: inline-block; font-weight: 700; }
    .stats { display: flex; gap: 18px; margin: 22px 0; }
    .stat-box { background: #101827; color: white; padding: 20px; border-radius: 16px; text-align: left; flex: 1; box-shadow: 0 12px 24px rgba(16, 24, 39, 0.18); animation: glowIn 0.6s ease both; }
    .stat-box h3 { margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1.2px; opacity: 0.7; }
    .stat-box p { margin: 10px 0 0 0; font-size: 28px; font-weight: 700; }
    .stat-box.alt { background: linear-gradient(135deg, #003049, #1f6f8b); }
    .form-group { margin: 16px 0; }
    .form-group label { display: block; margin-bottom: 6px; font-weight: 600; color: var(--slate); }
    textarea, input { width: 100%; padding: 12px; border: 1px solid rgba(12, 17, 29, 0.12); border-radius: 12px; font-family: 'IBM Plex Mono', monospace; background: white; }
    textarea { height: 140px; }
    button { background: linear-gradient(135deg, var(--aqua), #3a86ff); color: white; border: none; padding: 12px 24px; border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 700; letter-spacing: 0.3px; box-shadow: 0 10px 20px rgba(0, 194, 179, 0.2); transition: transform 0.2s ease, box-shadow 0.2s ease; }
    button:hover { transform: translateY(-2px); box-shadow: 0 16px 28px rgba(0, 194, 179, 0.3); }
    .result { background: #0b1220; color: #c7f9cc; padding: 16px; border-radius: 12px; margin-top: 15px; font-family: 'IBM Plex Mono', monospace; white-space: pre-wrap; }
    .error { color: var(--coral); }
    .success { color: #1dd3b0; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(12, 17, 29, 0.08); }
    th { background: #101827; color: white; border-radius: 8px; }
    tr:hover { background: rgba(0, 194, 179, 0.08); }
    @keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes glowIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    @media (max-width: 900px) { .stats { flex-direction: column; } .nav { padding: 12px 18px; } .container { margin: 18px; } }
</style>
"""

NAV_HTML = """
<div class="nav">
    <a href="/" class="{home}">Home</a>
    <a href="/health" class="{health}">Health</a>
    <a href="/stats" class="{stats}">Stats</a>
    <a href="/ingest/batch" class="{batch}">Batch Ingest</a>
    <a href="/ingest/stream" class="{stream}">Stream Ingest</a>
</div>
"""

@app.route('/', methods=['GET'])
def index():
    batch_queue = db.get_queue_length('data_queue')
    stream_queue = db.get_queue_length('stream_queue')
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ingestion API - Home</title>{BASE_STYLE}</head>
    <body>
        {NAV_HTML.format(home='active', health='', stats='', batch='', stream='')}
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
    if request.headers.get('Accept', '').find('application/json') != -1:
        return jsonify({'status': 'healthy', 'service': 'ingestion_api', 'version': '1.0.0'})
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ingestion API - Health</title>{BASE_STYLE}</head>
    <body>
        {NAV_HTML.format(home='', health='active', stats='', batch='', stream='')}
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
        {NAV_HTML.format(home='', health='', stats='active', batch='', stream='')}
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
                result_html = f'<div class="result success">{json.dumps(response, indent=2)}</div>'
        except Exception as e:
            if request.is_json:
                return jsonify({'status': 'error', 'message': str(e)}), 500
            result_html = f'<div class="result error">Error: {str(e)}</div>'
    
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
        {NAV_HTML.format(home='', health='', stats='', batch='active', stream='')}
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
                result_html = f'<div class="result success">{json.dumps(response, indent=2)}</div>'
        except Exception as e:
            if request.is_json:
                return jsonify({'status': 'error', 'message': str(e)}), 500
            result_html = f'<div class="result error">Error: {str(e)}</div>'
    
    sample_data = json.dumps({
        "features": [0.5, -0.3, 1.2, 0.8, -0.5, 0.1, 0.9, -0.2],
        "label": 1
    }, indent=2)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Ingestion API - Stream Ingest</title>{BASE_STYLE}</head>
    <body>
        {NAV_HTML.format(home='', health='', stats='', batch='', stream='active')}
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
    logger.info(f"Starting Ingestion API on port {config.service.ingestion_port}")
    app.run(host='0.0.0.0', port=config.service.ingestion_port, debug=False)
