"""Feature Store for managing features"""
import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.database import DatabaseManager
from shared.logger import setup_logger

logger = setup_logger("feature_store")

class FeatureStore:
    """Manages feature storage and retrieval"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def store_features(self, entity_id: str, features: dict, feature_group: str = "default"):
        """Store features for an entity"""
        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        for feature_name, feature_value in features.items():
            cursor.execute("""
                INSERT INTO feature_store (feature_name, feature_value, entity_id, feature_group)
                VALUES (?, ?, ?, ?)
            """, (feature_name, feature_value, entity_id, feature_group))
        
        conn.commit()
        conn.close()
        logger.debug(f"Stored {len(features)} features for entity {entity_id}")
        
    def get_features(self, entity_id: str, feature_group: str = "default") -> dict:
        """Retrieve features for an entity"""
        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT feature_name, feature_value 
            FROM feature_store 
            WHERE entity_id = ? AND feature_group = ?
            ORDER BY timestamp DESC
        """, (entity_id, feature_group))
        
        rows = cursor.fetchall()
        conn.close()
        
        features = {row[0]: row[1] for row in rows}
        return features
