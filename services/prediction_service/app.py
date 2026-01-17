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
from shared.redis_client import RedisClient

app = Flask(__name__)
CORS(app)

config = Config()
logger = setup_logger("prediction_service")
db = DatabaseManager()
redis_client = RedisClient(config.redis.host, config.redis.port)

current_model = None
model_version = None
total_predictions = 0

BASE_STYLE = """
<style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f5f5f5; }
    .nav { background: #2c3e50; padding: 15px 40px; }
    .nav a { color: white; text-decoration: none; margin-right: 20px; padding: 8px 15px; border-radius: 5px; }
    .nav a:hover { background: #34495e; }
    .nav a.active { background: #9b59b6; }
    .container { max-width: 900px; margin: 30px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #2c3e50; border-bottom: 2px solid #9b59b6; padding-bottom: 10px; margin-top: 0; }
    .status { background: #27ae60; color: white; padding: 5px 15px; border-radius: 20px; display: inline-block; }
    .status.warning { background: #e74c3c; }
    .stats { display: flex; gap: 20px; margin: 20px 0; }
    .stat-box { background: #9b59b6; color: white; padding: 20px; border-radius: 10px; text-align: center; flex: 1; }
    .stat-box h3 { margin: 0; font-size: 14px; opacity: 0.8; }
    .stat-box p { margin: 10px 0 0 0; font-size: 28px; font-weight: bold; }
    .form-group { margin: 15px 0; }
    .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #2c3e50; }
    textarea, input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-family: monospace; box-sizing: border-box; }
    textarea { height: 120px; }
    button { background: #9b59b6; color: white; border: none; padding: 12px 25px; border-radius: 5px; cursor: pointer; font-size: 14px; }
    button:hover { background: #8e44ad; }
    .result { background: #2c3e50; color: #2ecc71; padding: 15px; border-radius: 5px; margin-top: 15px; font-family: monospace; white-space: pre-wrap; }
    .error { color: #e74c3c; }
    .success { color: #2ecc71; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background: #9b59b6; color: white; }
    tr:hover { background: #f5f5f5; }
    .model-info { background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin: 20px 0; }
    .prediction-result { background: #27ae60; color: white; padding: 20px; border-radius: 10px; margin: 20px 0; }
    .prediction-result h3 { margin-top: 0; }
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


def load_model():
    global current_model, model_version
    
    model_files = glob.glob('models/*.pkl')
    if not model_files:
        logger.warning("No model files found")
        return False
    
    latest_model = max(model_files, key=os.path.getmtime)
    
    try:
        model_data = joblib.load(latest_model)
        current_model = model_data['model']
        model_version = os.path.basename(latest_model).replace('.pkl', '')
        logger.info(f"Model loaded: {model_version}")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False


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
                <div class="stat-box" style="background: #3498db;">
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
