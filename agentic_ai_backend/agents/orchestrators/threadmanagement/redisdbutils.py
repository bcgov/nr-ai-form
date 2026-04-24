from dotenv import load_dotenv
from agent_framework import AgentSession
from utils.redisservice import RedisService
import os
from .thread_manager_interface import IThreadManager

load_dotenv()

class redisdbutils(IThreadManager):
    def __init__(self):
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD")
        ssl = os.getenv("REDIS_SSL", "False").lower() == "true"
        ttl_days = int(os.getenv("REDIS_TTL_DAYS", "14"))
        self.redis_service = RedisService(host=host, port=port, password=password, ssl=ssl, ttl=ttl_days*24*60*60)

    async def get_thread_state(self, thread_id: str, agent):
        session = None
        try:
            # Try to load existing session
            if thread_id:
                print(f"Loading thread {thread_id} from Redis...")
                thread_state = await self.redis_service.load_thread(thread_id)
                if thread_state:
                    print("Thread state found in Redis. Resuming conversation.")
                    session = AgentSession.from_dict(thread_state)
                else:
                    print("Thread state not found in Redis. Creating new thread.")
        
        except Exception as e:
            print(f"Error initializing Redis or loading thread: {e}")

        # Create new session if not loaded
        if session is None:
            print("Creating new thread.")
            session = agent.create_session(session_id=thread_id)
        
        return session

    async def save_thread_state(self, thread_id: str, thread):
        try:
            state = thread.to_dict()
            await self.redis_service.save_thread(thread_id, state) #setting TTL at Service level
        except Exception as e:
            print(f"Error saving thread state to Redis: {e}")

    async def close(self):
        if self.redis_service:
            await self.redis_service.close()
