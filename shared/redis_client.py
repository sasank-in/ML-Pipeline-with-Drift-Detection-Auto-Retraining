"""Redis client for caching and message queues"""
import json
from typing import Any, Optional
import time

class RedisClient:
    """Redis client wrapper (mock for now, can use real Redis)"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self._cache = {}  # In-memory cache for demo
        self._queues = {}  # In-memory queues for demo
        
    def set(self, key: str, value: Any, ex: int = None):
        """Set a value in cache"""
        self._cache[key] = {
            'value': json.dumps(value),
            'expires': time.time() + ex if ex else None
        }
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        if key in self._cache:
            item = self._cache[key]
            if item['expires'] is None or item['expires'] > time.time():
                return json.loads(item['value'])
            else:
                del self._cache[key]
        return None
        
    def lpush(self, queue: str, value: Any):
        """Push to queue"""
        if queue not in self._queues:
            self._queues[queue] = []
        self._queues[queue].insert(0, json.dumps(value))
        
    def rpop(self, queue: str) -> Optional[Any]:
        """Pop from queue"""
        if queue in self._queues and self._queues[queue]:
            return json.loads(self._queues[queue].pop())
        return None
        
    def llen(self, queue: str) -> int:
        """Get queue length"""
        return len(self._queues.get(queue, []))
