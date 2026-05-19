"""Prediction Service"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify
from flask_cors import CORS
from markupsafe import escape
import numpy as np
import joblib
import time
import glob
import json

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager
from shared.auth import require_api_key
from shared.web_ui import base_style, nav_html

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))
_cors_origins = os.getenv('CORS_ORIGINS', '').strip()
if _cors_origins:
    CORS(app, origins=[o.strip() for o in _cors_origins.split(',') if o.strip()])
else:
    CORS(app, origins=[])

config = Config()
logger = setup_logger("prediction_service")
db = DatabaseManager()

current_model = None
model_version = None
model_path = None

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'models'))


def _is_safe_model_path(path: str) -> bool:
    """Reject paths outside the models/ directory or with non-.pkl extensions.

    Mitigates arbitrary-file pickle deserialization if the model registry is tampered with.
    """
    try:
        resolved = os.path.abspath(path)
        return resolved.startswith(MODELS_DIR + os.sep) and resolved.endswith('.pkl')
    except Exception:
        return False

BASE_STYLE = base_style({
    "accent": "#7c3aed",       # violet
    "accent_alt": "#4f46e5",   # indigo
    "bg_glow": "#efe7ff",
    "nav_a": "#0f172a",
    "nav_b": "#2b1d4a",
})

_NAV_LINKS = [
    ("/", "Home"),
    ("/health", "Health"),
    ("/predict", "Predict"),
    ("/reload_model", "Reload Model"),
]


def _nav(active: str) -> str:
    return nav_html(_NAV_LINKS, active=active)


def load_model_from_path(path: str, version: str = None) -> bool:
    """Load a model from disk. Refuses paths outside models/ to limit pickle risk."""
    global current_model, model_version, model_path

    if not _is_safe_model_path(path):
        logger.error(f"Refusing to load model from untrusted path: {path}")
        return False

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
    try:
        total_predictions = db.count_predictions()
    except Exception:
        total_predictions = 0
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Prediction Service - Home</title>{BASE_STYLE}</head>
    <body>
        {_nav('/')}
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
                    <p style="font-size: 16px;">{escape(model_version or 'None')}</p>
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
    db_ok = db.ping()
    model_ok = current_model is not None
    # Healthy = DB up AND model loaded. Degraded if either fails.
    overall = 'healthy' if (db_ok and model_ok) else 'degraded'
    status_code = 200 if overall == 'healthy' else 503
    response = {
        'status': overall,
        'service': 'prediction_service',
        'model_loaded': model_ok,
        'model_version': model_version,
        'checks': {
            'database': 'ok' if db_ok else 'fail',
            'model': 'ok' if model_ok else 'fail',
        },
    }
    if request.headers.get('Accept', '').find('application/json') != -1:
        return jsonify(response), status_code
    
    if request.headers.get('Accept', '').find('application/json') != -1:
        return jsonify(response)
    
    model_status = "Loaded" if current_model else "Not Loaded"
    status_color = "#27ae60" if current_model else "#e74c3c"
    overall_color = "#27ae60" if overall == 'healthy' else "#e74c3c"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Prediction Service - Health</title>{BASE_STYLE}</head>
    <body>
        {_nav('/health')}
        <div class="container">
            <h1>Health Check</h1>
            <div class="stats">
                <div class="stat-box" style="background: {overall_color};">
                    <h3>Status</h3>
                    <p>{overall.capitalize()}</p>
                </div>
                <div class="stat-box" style="background: {status_color};">
                    <h3>Model</h3>
                    <p>{model_status}</p>
                </div>
                <div class="stat-box">
                    <h3>Version</h3>
                    <p style="font-size: 16px;">{escape(model_version or 'None')}</p>
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
@require_api_key
def predict():
    global current_model
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

                max_rows = int(os.getenv('MAX_PREDICT_ROWS', '1000'))
                if X.shape[0] > max_rows:
                    msg = f'Too many rows: {X.shape[0]} > {max_rows}'
                    if request.is_json:
                        return jsonify({'status': 'error', 'message': msg}), 413
                    return f'<div class="result error">Error: {msg}</div>', 413
                
                start_time = time.time()
                predictions = current_model.predict(X)
                probabilities = current_model.predict_proba(X)
                prediction_time = time.time() - start_time
                
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
                
                confidences = [round(max(p), 4) for p in probabilities.tolist()]
                result_html = f"""
                <div class="prediction-result">
                    <h3>Prediction Results</h3>
                    <p><strong>Predictions:</strong> {escape(str(predictions.tolist()))}</p>
                    <p><strong>Confidence:</strong> {escape(str(confidences))}</p>
                    <p><strong>Time:</strong> {round(prediction_time, 4)}s</p>
                </div>
                <h3>Full JSON Response</h3>
                <div class="result">{escape(json.dumps(response, indent=2))}</div>
                """
                
            except Exception as e:
                if request.is_json:
                    return jsonify({'status': 'error', 'message': str(e)}), 500
                result_html = f'<div class="result error">Error: {escape(str(e))}</div>'
    
    sample_data = json.dumps({
        "features": [[0.5, -0.3, 1.2, 0.8, -0.5, 0.1, 0.9, -0.2]]
    }, indent=2)
    
    model_info = ""
    if current_model:
        n_features = getattr(current_model, 'n_features_in_', None)
        classes = getattr(current_model, 'classes_', None)
        n_features_str = f"{n_features}" if n_features is not None else "unknown"
        classes_str = escape(str(list(classes))) if classes is not None else "unknown"
        model_info = f"""
        <div class="model-info">
            <h3>Current Model: {escape(model_version)}</h3>
            <p>Features expected: {n_features_str}</p>
            <p>Output classes: {classes_str}</p>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Prediction Service - Predict</title>{BASE_STYLE}</head>
    <body>
        {_nav('/predict')}
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
@require_api_key
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
    files_html = "<ul>" + "".join([f"<li>{escape(os.path.basename(f))}</li>" for f in model_files]) + "</ul>" if model_files else "<p>No model files found</p>"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Prediction Service - Reload Model</title>{BASE_STYLE}</head>
    <body>
        {_nav('/reload_model')}
        <div class="container">
            <h1>Reload Model</h1>
            <p>Current model: <strong>{escape(model_version or 'None')}</strong></p>
            
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
    port = config.service.prediction_port
    host = os.getenv('BIND_HOST', '127.0.0.1')
    logger.info(f"Starting Prediction Service on {host}:{port}")
    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=int(os.getenv('WAITRESS_THREADS', '8')))
    except ImportError:
        logger.warning("waitress not installed — falling back to Flask dev server")
        app.run(host=host, port=port, debug=False)
