from dotenv import load_dotenv
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
        self.redis_service = RedisService(host=host, port=port, password=password, ssl=ssl)

    async def get_thread_state(self, thread_id: str, agent):
        thread = None
        try:
            # Try to load existing thread
            if thread_id:
                print(f"Loading thread {thread_id} from Redis...")
                thread_state = await self.redis_service.load_thread(thread_id)
                if thread_state:
                    print("Thread state found in Redis. Resuming conversation.")
                    thread = await agent.deserialize_thread(thread_state)
                else:
                    print("Thread state not found in Redis. Creating new thread.")
        
        except Exception as e:
            print(f"Error initializing Redis or loading thread: {e}")

        # Create new thread if not loaded
        if thread is None:
            print("Creating new thread.")
            thread = agent.get_new_thread()
        
        return thread

    async def save_thread_state(self, thread_id: str, thread):
        try:
            state = await thread.serialize()            
            await self.redis_service.save_thread(thread_id, state)
        except Exception as e:
            print(f"Error saving thread state to Redis: {e}")

    async def close(self):
        if self.redis_service:
            await self.redis_service.close()
