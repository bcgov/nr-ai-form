import os

from agent_framework import AgentSession
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from dotenv import load_dotenv

from .thread_manager_interface import IThreadManager

load_dotenv()


class cosmosdbutils(IThreadManager):
    def __init__(self):
        self.database_name = os.getenv("AZURE_COSMOS_DB_DATABASE_NAME", "AgentMemoryDB")
        self.container_name = os.getenv("AZURE_COSMOS_DB_CONTAINER_NAME", "Conversations")
        self.cosmos_endpoint = os.getenv("AZURE_COSMOS_DB_ENDPOINT")
        self.cosmos_api_key = os.getenv("AZURE_COSMOS_DB_KEY")
        self.environment = os.getenv("CSSAI_EXECUTION_ENV", "localhost")
        self.client = None
        self.container = None

    async def _connect(self):
        if self.container:
            return
        if not self.cosmos_endpoint:
            raise RuntimeError("AZURE_COSMOS_DB_ENDPOINT is required for Cosmos thread management.")
        if not self.cosmos_api_key:
            raise RuntimeError("AZURE_COSMOS_DB_KEY is required for Cosmos thread management.")

        client_options = {
            "connection_verify": self.environment != "localhost",
            "enable_endpoint_discovery": self.environment != "localhost",
        }
        self.client = CosmosClient(self.cosmos_endpoint, credential=self.cosmos_api_key, **client_options)
        database = self.client.get_database_client(self.database_name)
        self.container = database.get_container_client(self.container_name)

    async def get_thread_state(self, thread_id: str, agent):
        session = None
        try:
            if thread_id:
                await self._connect()
                print(f"Loading thread {thread_id} from Cosmos DB...")
                try:
                    item = await self.container.read_item(item=thread_id, partition_key=thread_id)
                    thread_state = item.get("thread_state") or item.get("state") or item
                    print("Thread state found. Resuming conversation.")
                    session = AgentSession.from_dict(thread_state)
                except CosmosResourceNotFoundError:
                    print("Thread state not found. Creating new thread.")
        except Exception as e:
            print(f"Error initializing Cosmos DB or loading thread: {e}")
        finally:
            await self.close()

        if session is None:
            print("Creating new thread.")
            session = agent.create_session(session_id=thread_id)

        return session

    async def save_thread_state(self, thread_id: str, thread):
        try:
            await self._connect()
            state = thread.to_dict()
            item = {
                "id": thread_id,
                "thread_state": state,
            }
            await self.container.upsert_item(item)
        except Exception as e:
            print(f"Error saving thread state: {e}")
        finally:
            await self.close()

    async def close(self):
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                print(f"Error closing Cosmos client: {e}")
            finally:
                self.client = None
                self.container = None
