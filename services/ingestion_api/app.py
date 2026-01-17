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
from shared.redis_client import RedisClient

app = Flask(__name__)
CORS(app)

config = Config()
logger = setup_logger("ingestion_api")
db = DatabaseManager()
redis_client = RedisClient(config.redis.host, config.redis.port)

BASE_STYLE = """
<style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
    .nav { background: #2c3e50; padding: 15px 40px; }
    .nav a { color: white; text-decoration: none; margin-right: 20px; padding: 8px 15px; border-radius: 5px; }
    .nav a:hover { background: #34495e; }
    .nav a.active { background: #3498db; }
    .container { max-width: 900px; margin: 30px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-top: 0; }
    .status { background: #27ae60; color: white; padding: 5px 15px; border-radius: 20px; display: inline-block; }
    .stats { display: flex; gap: 20px; margin: 20px 0; }
    .stat-box { background: #3498db; color: white; padding: 20px; border-radius: 10px; text-align: center; flex: 1; }
    .stat-box h3 { margin: 0; font-size: 14px; opacity: 0.8; }
    .stat-box p { margin: 10px 0 0 0; font-size: 28px; font-weight: bold; }
    .form-group { margin: 15px 0; }
    .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #2c3e50; }
    textarea, input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-family: monospace; box-sizing: border-box; }
    textarea { height: 120px; }
    button { background: #3498db; color: white; border: none; padding: 12px 25px; border-radius: 5px; cursor: pointer; font-size: 14px; }
    button:hover { background: #2980b9; }
    .result { background: #2c3e50; color: #2ecc71; padding: 15px; border-radius: 5px; margin-top: 15px; font-family: monospace; white-space: pre-wrap; }
    .error { color: #e74c3c; }
    .success { color: #2ecc71; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background: #3498db; color: white; }
    tr:hover { background: #f5f5f5; }
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
    batch_queue = redis_client.llen('data_queue')
    stream_queue = redis_client.llen('stream_queue')
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
                <div class="stat-box" style="background: #9b59b6;">
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
    batch_queue = redis_client.llen('data_queue')
    stream_queue = redis_client.llen('stream_queue')
    
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
                <div class="stat-box" style="background: #9b59b6;">
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
                redis_client.lpush('data_queue', batch_data)
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
                redis_client.lpush('stream_queue', stream_data)
                
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
