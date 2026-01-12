"""Data Ingestion API - Receives and validates incoming data"""
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np

from shared.config import Config
from shared.logger import setup_logger
from shared.database import DatabaseManager
from shared.redis_client import RedisClient

app = Flask(__name__)
CORS(app)

# Initialize
config = Config()
logger = setup_logger("ingestion_api")
db = DatabaseManager()
redis_client = RedisClient(config.redis.host, config.redis.port)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'ingestion_api',
        'version': '1.0.0'
    })

@app.route('/ingest/batch', methods=['POST'])
def ingest_batch():
    """Ingest a batch of data"""
    try:
        data = request.json
        X = np.array(data['features'])
        y = data.get('labels')
        
        # Validate data
        if len(X.shape) != 2:
            return jsonify({
                'status': 'error',
                'message': 'Features must be 2D array'
            }), 400
        
        # Store in Redis queue for processing
        batch_data = {
            'features': X.tolist(),
            'labels': y,
            'timestamp': data.get('timestamp'),
            'batch_id': data.get('batch_id')
        }
        redis_client.lpush('data_queue', batch_data)
        
        logger.info(f"Ingested batch: {X.shape[0]} samples")
        
        return jsonify({
            'status': 'success',
            'samples_ingested': X.shape[0],
            'batch_id': data.get('batch_id')
        })
        
    except Exception as e:
        logger.error(f"Ingestion error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/ingest/stream', methods=['POST'])
def ingest_stream():
    """Ingest streaming data (single sample)"""
    try:
        data = request.json
        features = data['features']
        label = data.get('label')
        
        # Validate
        if not isinstance(features, list):
            return jsonify({
                'status': 'error',
                'message': 'Features must be a list'
            }), 400
        
        # Store in Redis
        stream_data = {
            'features': features,
            'label': label,
            'timestamp': data.get('timestamp')
        }
        redis_client.lpush('stream_queue', stream_data)
        
        logger.debug(f"Ingested stream sample")
        
        return jsonify({
            'status': 'success',
            'message': 'Sample ingested'
        })
        
    except Exception as e:
        logger.error(f"Stream ingestion error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get ingestion statistics"""
    try:
        queue_size = redis_client.llen('data_queue')
        stream_size = redis_client.llen('stream_queue')
        
        return jsonify({
            'status': 'success',
            'batch_queue_size': queue_size,
            'stream_queue_size': stream_size
        })
        
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    logger.info(f"Starting Ingestion API on port {config.service.ingestion_port}")
    app.run(host='0.0.0.0', port=config.service.ingestion_port, debug=False)
