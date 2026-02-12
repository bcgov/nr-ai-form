
import os
import json
import redis.asyncio as redis
from typing import Any, Dict, Optional

class RedisService:
    def __init__(self, host: str, port: int, password: str = None, ssl: bool = False):
        self.host = host
        self.port = port
        self.password = password
        self.ssl = ssl
        self.client = None

    async def connect(self):
        """Initializes the Redis client."""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                ssl=self.ssl,
                decode_responses=True  # Important for string/json handling
            )
            await self.client.ping()
            print(f"Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}")

    async def load_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Loads a thread state from Redis."""
        try:
            if not self.client:
                await self.connect()
            
            data = await self.client.get(thread_id)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Failed to load thread {thread_id} from Redis: {e}")
            return None

    async def save_thread(self, thread_id: str, thread_state: Dict[str, Any], ttl: int = 3600):
        """Saves a thread state to Redis with optional TTL (default 1 hour)."""
        try:
            if not self.client:
                await self.connect()
            
            data = json.dumps(thread_state)
            await self.client.set(thread_id, data, ex=ttl)
            print(f"Thread {thread_id} saved to Redis.")
        except Exception as e:
            raise RuntimeError(f"Failed to save thread to Redis: {e}")

    async def close(self):
        """Closes the Redis connection."""
        if self.client:
            await self.client.aclose()
            print("Redis connection closed.")
