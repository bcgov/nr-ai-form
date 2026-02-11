from dotenv import load_dotenv
from utils.cosmosdbservice import CosmosDBService
import os

load_dotenv()

class cosmosdbutils:
    def __init__(self):
        connection_string = os.getenv("AZURE_COSMOS_CONNECTION_STRING")
        database_name = os.getenv("AZURE_COSMOS_DB_DATABASE_NAME", "AgentMemoryDB")
        container_name = os.getenv("AZURE_COSMOS_DB_CONTAINER_NAME", "Conversations")
        cosmos_endpoint = os.getenv("AZURE_COSMOS_DB_ENDPOINT")
        cosmos_api_key = os.getenv("AZURE_COSMOS_DB_KEY")
        environment = os.getenv("CSSAI_EXECUTION_ENV","localhost")
        self.cosmos_service = CosmosDBService(connection_string=None, endpoint=cosmos_endpoint, cosmosapi_key=cosmos_api_key, database_name=database_name, environment=environment)

    async def get_thread_state(self, thread_id: str, agent):
        thread = None
        try:
            # Initialize Cosmos DB Service
            connection_string = os.getenv("AZURE_COSMOS_CONNECTION_STRING")
            database_name = os.getenv("AZURE_COSMOS_DB_DATABASE_NAME", "AgentMemoryDB")
            container_name = os.getenv("AZURE_COSMOS_DB_CONTAINER_NAME", "Conversations")
            cosmos_endpoint = os.getenv("AZURE_COSMOS_DB_ENDPOINT")
            cosmos_api_key = os.getenv("AZURE_COSMOS_DB_KEY")
            environment = os.getenv("CSSAI_EXECUTION_ENV","localhost")
            
            if connection_string:                
                # Try to load existing thread
                if thread_id:
                    print(f"Loading thread {thread_id} from Cosmos DB...")
                    thread_state = await self.cosmos_service.load_item(container_name, thread_id, thread_id)
                    await self.close()
                    if thread_state:
                        print("Thread state found. Resuming conversation.")
                        thread = await agent.deserialize_thread(thread_state)
                    else:
                        print("Thread state not found. Creating new thread.")
            else:
                print("Warning: AZURE_COSMOS_CONNECTION_STRING not set. Thread persistence disabled.")

        except Exception as e:
            print(f"Error initializing Cosmos DB or loading thread: {e}")

        # Create new thread if not loaded
        if thread is None:
            print("Creating new thread.")
            thread = agent.get_new_thread()

        return thread   

    async def save_thread_state(self, thread_id: str,thread):
        try:
            state = await thread.serialize()
            container_name = os.getenv("AZURE_COSMOS_DB_CONTAINER_NAME", "Conversations")
            item = {
                "id": thread_id,
                "thread_state": state
            }
            await self.cosmos_service.save_item(container_name, item)
            await self.close()
        except Exception as e:
            print(f"Error saving thread state: {e}")

    async def close(self):
        if self.cosmos_service and self.cosmos_service.client:
            try:
                await self.cosmos_service.client.close()
            except Exception as e:
                print(f"Error closing Cosmos client: {e}")