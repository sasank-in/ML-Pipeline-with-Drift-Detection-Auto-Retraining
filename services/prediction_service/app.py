"""Prediction Service - Serves model predictions"""
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import joblib
import time

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager
from shared.redis_client import RedisClient

app = Flask(__name__)
CORS(app)

# Initialize
config = Config()
logger = setup_logger("prediction_service")
db = DatabaseManager()
redis_client = RedisClient(config.redis.host, config.redis.port)

# Model state
current_model = None
model_version = None

def load_model():
    """Load the active model"""
    global current_model, model_version
    
    # Check cache first
    cached_model = redis_client.get('active_model')
    if cached_model:
        model_version = cached_model['version']
        logger.info(f"Model loaded from cache: {model_version}")
        return
    
    # Load from database
    active_model = db.get_active_model()
    if active_model:
        try:
            model_data = joblib.load(active_model['model_path'])
            current_model = model_data['model']
            model_version = model_data['version']
            
            # Cache it
            redis_client.set('active_model', {
                'version': model_version,
                'path': active_model['model_path']
            }, ex=3600)
            
            logger.info(f"Model loaded: {model_version}")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
    else:
        logger.warning("No active model found")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'prediction_service',
        'model_loaded': current_model is not None,
        'model_version': model_version
    })

@app.route('/predict', methods=['POST'])
def predict():
    """Make predictions"""
    try:
        if current_model is None:
            load_model()
            
        if current_model is None:
            return jsonify({
                'status': 'error',
                'message': 'No model available'
            }), 503
        
        data = request.json
        X = np.array(data['features'])
        
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        
        start_time = time.time()
        predictions = current_model.predict(X)
        probabilities = current_model.predict_proba(X)
        prediction_time = time.time() - start_time
        
        # Log predictions
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            db.log_prediction(
                features=X[i].tolist(),
                prediction=int(pred),
                probability=float(prob.max()),
                model_version=model_version,
                service_id='prediction_service'
            )
        
        # Store in Redis for drift monitoring
        redis_client.lpush('prediction_buffer', {
            'features': X.tolist(),
            'predictions': predictions.tolist(),
            'timestamp': time.time()
        })
        
        logger.info(f"Predictions made: {len(predictions)} samples in {prediction_time:.4f}s")
        
        return jsonify({
            'status': 'success',
            'predictions': predictions.tolist(),
            'probabilities': probabilities.tolist(),
            'prediction_time': prediction_time,
            'model_version': model_version
        })
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/predict/batch', methods=['POST'])
def predict_batch():
    """Batch predictions for high throughput"""
    try:
        if current_model is None:
            load_model()
            
        if current_model is None:
            return jsonify({
                'status': 'error',
                'message': 'No model available'
            }), 503
        
        data = request.json
        X = np.array(data['features'])
        batch_size = data.get('batch_size', 100)
        
        all_predictions = []
        all_probabilities = []
        
        # Process in batches
        for i in range(0, len(X), batch_size):
            batch = X[i:i+batch_size]
            preds = current_model.predict(batch)
            probs = current_model.predict_proba(batch)
            all_predictions.extend(preds.tolist())
            all_probabilities.extend(probs.tolist())
        
        logger.info(f"Batch predictions: {len(X)} samples")
        
        return jsonify({
            'status': 'success',
            'predictions': all_predictions,
            'probabilities': all_probabilities,
            'total_samples': len(X),
            'model_version': model_version
        })
        
    except Exception as e:
        logger.error(f"Batch prediction error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/reload_model', methods=['POST'])
def reload_model():
    """Reload the model (after retraining)"""
    try:
        redis_client.set('active_model', None)  # Clear cache
        load_model()
        
        return jsonify({
            'status': 'success',
            'model_version': model_version
        })
        
    except Exception as e:
        logger.error(f"Model reload error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    load_model()
    logger.info(f"Starting Prediction Service on port {config.service.prediction_port}")
    app.run(host='0.0.0.0', port=config.service.prediction_port, debug=False)
