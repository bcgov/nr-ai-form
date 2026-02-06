
import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from typing import Any, Dict, Optional, List

class CosmosDBService:
    def __init__(self, connection_string: str, database_name: str,cosmosapi_key: str=None, endpoint: str=None):

        if not database_name:
            raise ValueError("database_name must be provided.")
            
        self.connection_string = connection_string
        self.database_name = database_name
        self.cosmosapi_key = cosmosapi_key
        self.endpoint = endpoint
        self.client = None
        try:
            if self.connection_string is not None:
                self.client = CosmosClient.from_connection_string(connection_string)
            else:
                    if "localhost" in endpoint or "127.0.0.1" in endpoint:
                        print("Detected local Cosmos DB Emulator. Disabling SSL verification and Endpoint Discovery.")
                        self.client = CosmosClient(
                            endpoint, 
                            credential=cosmosapi_key, 
                            connection_verify=False,
                            enable_endpoint_discovery=False
                        )
                    else:
                        self.client = CosmosClient(endpoint, credential=cosmosapi_key)


            self.database = self.client.get_database_client(database_name)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize CosmosClient: {e}")

    async def get_container(self, container_name: str, database_name: str):
        try:
            db = await self.client.create_database_if_not_exists(id=database_name)
            container = await db.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path="/id"),
                offer_throughput=400
            )

            return container
        except Exception as e:
            raise RuntimeError(f"Failed to get container {container_name}: {e}")

    async def load_item(self, container_name: str, item_id: str, partition_key: str) -> Optional[Dict[str, Any]]:
        try:
            container = await self.get_container(container_name, self.database_name)
            item = await container.read_item(item=item_id, partition_key=partition_key)
            return  item.get("thread_state")
        except CosmosResourceNotFoundError:
            return None
        except Exception as e:
             print(f"Failed to load item {item_id} from {container_name}: {e}")
             return None

    async def save_item(self, container_name: str, item: Dict[str, Any]):
        try:
            container = await self.get_container(container_name, self.database_name)
            await container.upsert_item(body=item)
        except Exception as e:
            raise RuntimeError(f"Failed to save item to {container_name}: {e}")
