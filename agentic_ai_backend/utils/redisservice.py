
import os
import json
import redis.asyncio as redis
from typing import Any, Dict, Optional

class RedisService:
    def __init__(self, host: str, port: int, password: str = None, ssl: bool = False, ttl:int = 3600):
        self.host = host
        self.port = port
        self.password = password
        self.ssl = ssl
        self.ttl = ttl
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
    
    async def load_conversation_history(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Loads the thread state but in a conversation history format."""
        try:
            if not self.client:
                await self.connect()
            
            data = await self.client.get(thread_id)
            if data:
                return json.loads(data)
            return data
        except Exception as e:
            print(f"Failed to load thread {thread_id} from Redis: {e}")
            return None

    async def save_thread(self, thread_id: str, thread_state: Dict[str, Any]):
        """Saves a thread state to Redis with optional TTL (default 1 hour)."""
        try:
            if not self.client:
                await self.connect()
            
            data = json.dumps(thread_state)
            await self.client.set(thread_id, data, ex=self.ttl)
            print(f"Thread {thread_id} saved to Redis.")
        except Exception as e:
            raise RuntimeError(f"Failed to save thread to Redis: {e}")

    async def get_int(self, key: str) -> int:
        """Reads a plain integer counter from Redis, defaulting to 0 if missing/unreadable."""
        try:
            if not self.client:
                await self.connect()

            data = await self.client.get(key)
            return int(data) if data else 0
        except Exception as e:
            print(f"Failed to get counter {key} from Redis: {e}")
            return 0

    async def set_int(self, key: str, value: int):
        """Writes a plain integer counter to Redis with the service's default TTL."""
        try:
            if not self.client:
                await self.connect()

            await self.client.set(key, str(value), ex=self.ttl)
        except Exception as e:
            print(f"Failed to set counter {key} in Redis: {e}")

    async def close(self):
        """Closes the Redis connection."""
        if self.client:
            await self.client.aclose()
            print("Redis connection closed.")
