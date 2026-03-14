"""Prediction Service"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import numpy as np
import joblib
import time
import glob
import json

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager

app = Flask(__name__)
CORS(app)

config = Config()
logger = setup_logger("prediction_service")
db = DatabaseManager()

current_model = None
model_version = None
model_path = None
total_predictions = 0

BASE_STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=IBM+Plex+Mono&display=swap');
    :root {
        --ink: #0b1220;
        --paper: #f7f4ef;
        --violet: #7c3aed;
        --electric: #22d3ee;
        --amber: #f59e0b;
        --rose: #fb7185;
        --shadow: 0 20px 40px rgba(12, 17, 29, 0.12);
    }
    * { box-sizing: border-box; }
    body { font-family: 'Space Grotesk', sans-serif; margin: 0; background: radial-gradient(1200px 600px at 90% -10%, #efe7ff 0%, #f7f4ef 45%, #f3efe7 100%); color: var(--ink); }
    .nav { background: linear-gradient(120deg, #0f172a 0%, #2b1d4a 60%, #0b1220 100%); padding: 16px 40px; position: sticky; top: 0; z-index: 10; }
    .nav a { color: white; text-decoration: none; margin-right: 12px; padding: 10px 16px; border-radius: 999px; font-weight: 600; letter-spacing: 0.2px; transition: all 0.2s ease; }
    .nav a:hover { background: rgba(255,255,255,0.12); transform: translateY(-1px); }
    .nav a.active { background: linear-gradient(135deg, var(--violet), #4f46e5); }
    .container { max-width: 980px; margin: 28px auto; background: rgba(255, 255, 255, 0.74); backdrop-filter: blur(8px); padding: 32px; border-radius: 18px; box-shadow: var(--shadow); border: 1px solid rgba(12, 17, 29, 0.06); animation: fadeUp 0.6s ease both; }
    h1 { color: var(--ink); border-bottom: 3px solid var(--violet); padding-bottom: 10px; margin-top: 0; font-size: 28px; letter-spacing: 0.3px; }
    .status { background: linear-gradient(120deg, #34d399, #10b981); color: #042019; padding: 6px 16px; border-radius: 999px; display: inline-block; font-weight: 700; }
    .status.warning { background: linear-gradient(120deg, #f43f5e, #fb7185); color: #1f0a0a; }
    .stats { display: flex; gap: 18px; margin: 22px 0; }
    .stat-box { background: #0f172a; color: white; padding: 20px; border-radius: 16px; text-align: left; flex: 1; box-shadow: 0 12px 24px rgba(16, 24, 39, 0.18); animation: glowIn 0.6s ease both; }
    .stat-box h3 { margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 1.2px; opacity: 0.7; }
    .stat-box p { margin: 10px 0 0 0; font-size: 28px; font-weight: 700; }
    .stat-box.alt { background: linear-gradient(135deg, #1f1147, #4c1d95); }
    .form-group { margin: 16px 0; }
    .form-group label { display: block; margin-bottom: 6px; font-weight: 600; color: #2b2f3a; }
    textarea, input { width: 100%; padding: 12px; border: 1px solid rgba(12, 17, 29, 0.12); border-radius: 12px; font-family: 'IBM Plex Mono', monospace; background: white; }
    textarea { height: 140px; }
    button { background: linear-gradient(135deg, var(--violet), #3b82f6); color: white; border: none; padding: 12px 24px; border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 700; letter-spacing: 0.3px; box-shadow: 0 10px 20px rgba(124, 58, 237, 0.25); transition: transform 0.2s ease, box-shadow 0.2s ease; }
    button:hover { transform: translateY(-2px); box-shadow: 0 16px 28px rgba(124, 58, 237, 0.35); }
    .result { background: #0b1220; color: #c7f9cc; padding: 16px; border-radius: 12px; margin-top: 15px; font-family: 'IBM Plex Mono', monospace; white-space: pre-wrap; }
    .error { color: var(--rose); }
    .success { color: #34d399; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(12, 17, 29, 0.08); }
    th { background: #111827; color: white; border-radius: 8px; }
    tr:hover { background: rgba(124, 58, 237, 0.08); }
    .model-info { background: linear-gradient(135deg, #111827, #1f2937); color: white; padding: 20px; border-radius: 14px; margin: 20px 0; box-shadow: 0 12px 24px rgba(16, 24, 39, 0.18); }
    .prediction-result { background: linear-gradient(135deg, #10b981, #22d3ee); color: #052316; padding: 20px; border-radius: 14px; margin: 20px 0; }
    .prediction-result h3 { margin-top: 0; }
    @keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes glowIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    @media (max-width: 900px) { .stats { flex-direction: column; } .nav { padding: 12px 18px; } .container { margin: 18px; } }
</style>
"""

NAV_HTML = """
<div class="nav">
    <a href="/" class="{home}">Home</a>
    <a href="/health" class="{health}">Health</a>
    <a href="/predict" class="{predict}">Predict</a>
    <a href="/reload_model" class="{reload}">Reload Model</a>
</div>
"""


def load_model_from_path(path: str, version: str = None) -> bool:
    """Load a model from disk."""
    global current_model, model_version, model_path
    
    try:
        model_data = joblib.load(path)
        current_model = model_data['model']
        model_path = path
        model_version = version or os.path.basename(path).replace('.pkl', '')
        logger.info(f"Model loaded: {model_version}")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False


def load_model() -> bool:
    """Load active model from registry or fallback to latest file."""
    active = db.get_active_model()
    if active and active.get('model_path') and os.path.exists(active['model_path']):
        return load_model_from_path(active['model_path'], active.get('model_version'))
    
    model_files = glob.glob('models/*.pkl')
    if not model_files:
        logger.warning("No model files found")
        return False
    
    latest_model = max(model_files, key=os.path.getmtime)
    return load_model_from_path(latest_model)


def maybe_reload_model():
    """Reload model if a new deployed version exists."""
    active = db.get_active_model()
    if not active:
        return
    
    active_version = active.get('model_version')
    active_path = active.get('model_path')
    
    if active_version and active_path and active_version != model_version and os.path.exists(active_path):
        load_model_from_path(active_path, active_version)


@app.route('/', methods=['GET'])
def index():
    model_status = "Loaded" if current_model else "Not Loaded"
    status_class = "" if current_model else "warning"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Prediction Service - Home</title>{BASE_STYLE}</head>
    <body>
        {NAV_HTML.format(home='active', health='', predict='', reload='')}
        <div class="container">
            <h1>Prediction Service</h1>
            <span class="status {status_class}">{model_status}</span>
            <p>Version: 1.0.0 | Real-time ML predictions</p>
            
            <div class="stats">
                <div class="stat-box">
                    <h3>Total Predictions</h3>
                    <p>{total_predictions}</p>
                </div>
                <div class="stat-box alt">
                    <h3>Model Version</h3>
                    <p style="font-size: 16px;">{model_version or 'None'}</p>
                </div>
            </div>
            
            <h2>Available Endpoints</h2>
            <table>
                <tr><th>Method</th><th>Endpoint</th><th>Description</th></tr>
                <tr><td>GET</td><td>/health</td><td>Health check</td></tr>
                <tr><td>GET/POST</td><td>/predict</td><td>Make predictions</td></tr>
                <tr><td>GET/POST</td><td>/reload_model</td><td>Reload model from disk</td></tr>
            </table>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/health', methods=['GET'])
def health_check():
    response = {
        'status': 'healthy',
        'service': 'prediction_service',
        'model_loaded': current_model is not None,
        'model_version': model_version
    }
    
    if request.headers.get('Accept', '').find('application/json') != -1:
        return jsonify(response)
    
    model_status = "Loaded" if current_model else "Not Loaded"
    status_color = "#27ae60" if current_model else "#e74c3c"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Prediction Service - Health</title>{BASE_STYLE}</head>
    <body>
        {NAV_HTML.format(home='', health='active', predict='', reload='')}
        <div class="container">
            <h1>Health Check</h1>
            <div class="stats">
                <div class="stat-box" style="background: #27ae60;">
                    <h3>Status</h3>
                    <p>Healthy</p>
                </div>
                <div class="stat-box" style="background: {status_color};">
                    <h3>Model</h3>
                    <p>{model_status}</p>
                </div>
                <div class="stat-box">
                    <h3>Version</h3>
                    <p style="font-size: 16px;">{model_version or 'None'}</p>
                </div>
            </div>
            <h2>JSON Response</h2>
            <div class="result">{json.dumps(response, indent=2)}</div>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/predict', methods=['GET', 'POST'])
def predict():
    global current_model, total_predictions
    result_html = ""
    
    if request.method == 'POST':
        maybe_reload_model()
        if current_model is None:
            load_model()
        
        if current_model is None:
            error_response = {'status': 'error', 'message': 'No model available'}
            if request.is_json:
                return jsonify(error_response), 503
            result_html = f'<div class="result error">{json.dumps(error_response, indent=2)}</div>'
        else:
            try:
                if request.is_json:
                    data = request.json
                else:
                    data = json.loads(request.form.get('data', '{}'))
                
                X = np.array(data['features'])
                if len(X.shape) == 1:
                    X = X.reshape(1, -1)
                
                start_time = time.time()
                predictions = current_model.predict(X)
                probabilities = current_model.predict_proba(X)
                prediction_time = time.time() - start_time
                
                total_predictions += len(predictions)
                
                for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
                    db.log_prediction(
                        features=X[i].tolist(),
                        prediction=int(pred),
                        probability=float(prob.max()),
                        model_version=model_version
                    )
                
                # Buffer full batch for drift monitoring
                db.enqueue('prediction_buffer', {
                    'features': X.tolist(),
                    'timestamp': time.time()
                })
                
                response = {
                    'status': 'success',
                    'predictions': predictions.tolist(),
                    'probabilities': probabilities.tolist(),
                    'prediction_time': round(prediction_time, 4),
                    'model_version': model_version
                }
                
                if request.is_json:
                    return jsonify(response)
                
                pred_labels = ['Regular Customer' if p == 0 else 'High-Value Customer' for p in predictions]
                result_html = f"""
                <div class="prediction-result">
                    <h3>Prediction Results</h3>
                    <p><strong>Predictions:</strong> {pred_labels}</p>
                    <p><strong>Raw Values:</strong> {predictions.tolist()}</p>
                    <p><strong>Confidence:</strong> {[round(max(p), 4) for p in probabilities.tolist()]}</p>
                    <p><strong>Time:</strong> {round(prediction_time, 4)}s</p>
                </div>
                <h3>Full JSON Response</h3>
                <div class="result">{json.dumps(response, indent=2)}</div>
                """
                
            except Exception as e:
                if request.is_json:
                    return jsonify({'status': 'error', 'message': str(e)}), 500
                result_html = f'<div class="result error">Error: {str(e)}</div>'
    
    sample_data = json.dumps({
        "features": [[0.5, -0.3, 1.2, 0.8, -0.5, 0.1, 0.9, -0.2]]
    }, indent=2)
    
    model_info = ""
    if current_model:
        model_info = f"""
        <div class="model-info">
            <h3>Current Model: {model_version}</h3>
            <p>Features expected: 8 (Recency, Frequency, TotalItems, UniqueProducts, AvgOrderValue, AvgItemsPerOrder, AvgItemPrice, CountryEncoded)</p>
            <p>Output: 0 = Regular Customer, 1 = High-Value Customer</p>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Prediction Service - Predict</title>{BASE_STYLE}</head>
    <body>
        {NAV_HTML.format(home='', health='', predict='active', reload='')}
        <div class="container">
            <h1>Make Predictions</h1>
            {model_info}
            
            <form method="POST">
                <div class="form-group">
                    <label>Input Features (JSON format):</label>
                    <textarea name="data" placeholder="Enter features...">{sample_data}</textarea>
                </div>
                <button type="submit">Predict</button>
            </form>
            {result_html}
            
            <h2>Expected Format</h2>
            <div class="result">{sample_data}</div>
        </div>
    </body>
    </html>
    """
    return html


@app.route('/reload_model', methods=['GET', 'POST'])
def reload_model_endpoint():
    result_html = ""
    
    if request.method == 'POST':
        success = load_model()
        if success:
            response = {'status': 'success', 'model_version': model_version}
            if request.is_json:
                return jsonify(response)
            result_html = f'<div class="result success">{json.dumps(response, indent=2)}</div>'
        else:
            response = {'status': 'error', 'message': 'Failed to load model'}
            if request.is_json:
                return jsonify(response), 500
            result_html = f'<div class="result error">{json.dumps(response, indent=2)}</div>'
    
    model_files = glob.glob('models/*.pkl')
    files_html = "<ul>" + "".join([f"<li>{os.path.basename(f)}</li>" for f in model_files]) + "</ul>" if model_files else "<p>No model files found</p>"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Prediction Service - Reload Model</title>{BASE_STYLE}</head>
    <body>
        {NAV_HTML.format(home='', health='', predict='', reload='active')}
        <div class="container">
            <h1>Reload Model</h1>
            <p>Current model: <strong>{model_version or 'None'}</strong></p>
            
            <h2>Available Models</h2>
            {files_html}
            
            <form method="POST">
                <button type="submit">Reload Model</button>
            </form>
            {result_html}
        </div>
    </body>
    </html>
    """
    return html


if __name__ == '__main__':
    load_model()
    logger.info(f"Starting Prediction Service on port {config.service.prediction_port}")
    app.run(host='0.0.0.0', port=config.service.prediction_port, debug=False)
