from dotenv import load_dotenv
from utils.cosmosdbservice import CosmosDBService
import os
from .thread_manager_interface import IThreadManager

load_dotenv()

class cosmosdbutils(IThreadManager):
    def __init__(self):
        self.connection_string = os.getenv("AZURE_COSMOS_CONNECTION_STRING")
        self.database_name = os.getenv("AZURE_COSMOS_DB_DATABASE_NAME", "AgentMemoryDB")
        self.container_name = os.getenv("AZURE_COSMOS_DB_CONTAINER_NAME", "Conversations")
        self.cosmos_endpoint = os.getenv("AZURE_COSMOS_DB_ENDPOINT")
        self.cosmos_api_key = os.getenv("AZURE_COSMOS_DB_KEY")
        self.environment = os.getenv("CSSAI_EXECUTION_ENV","localhost")
        self.cosmos_service = CosmosDBService(connection_string=None, endpoint=self.cosmos_endpoint, cosmosapi_key=self.cosmos_api_key, database_name=self.database_name, environment=self.environment)

    async def get_thread_state(self, thread_id: str, agent):
        thread = None
        try:                          
                # Try to load existing thread
                if thread_id:
                    print(f"Loading thread {thread_id} from Cosmos DB...")
                    thread_state = await self.cosmos_service.load_item(self.container_name, thread_id, thread_id)                    
                    if thread_state:
                        print("Thread state found. Resuming conversation.")
                        thread = await agent.deserialize_thread(thread_state)
                    else:
                        print("Thread state not found. Creating new thread.")

        except Exception as e:
            print(f"Error initializing Cosmos DB or loading thread: {e}")
        finally:
            await self.close()
        #ABIN: Add a check here to see if the thread is expired, if so, create a new thread.

        # Create new thread if not loaded
        if thread is None:
            print("Creating new thread.")
            thread = agent.get_new_thread()

        return thread   

    async def save_thread_state(self, thread_id: str,thread):
        try:
            state = await thread.serialize()
            item = {
                "id": thread_id,
                "thread_state": state
            }
            await self.cosmos_service.save_item(self.container_name, item)
        except Exception as e:
            print(f"Error saving thread state: {e}")
        finally:
            await self.close()

    async def close(self):
        if self.cosmos_service and self.cosmos_service.client:
            try:
                await self.cosmos_service.client.close()
            except Exception as e:
                print(f"Error closing Cosmos client: {e}")