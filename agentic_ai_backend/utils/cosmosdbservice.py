
import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from typing import Any, Dict, Optional, List

class CosmosDBService:
    def __init__(self, connection_string: str, database_name: str):
        if not connection_string:
            raise ValueError("connection_string must be provided.")
        if not database_name:
            raise ValueError("database_name must be provided.")
            
        self.connection_string = connection_string
        self.database_name = database_name
        
        try:
            self.client = CosmosClient.from_connection_string(connection_string)
            self.database = self.client.get_database_client(database_name)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize CosmosClient: {e}")

    def get_container(self, container_name: str):
        try:
            return self.database.get_container_client(container_name)
        except Exception as e:
            raise RuntimeError(f"Failed to get container {container_name}: {e}")

    def load_item(self, container_name: str, item_id: str, partition_key: str) -> Optional[Dict[str, Any]]:
        try:
            container = self.get_container(container_name)
            item = container.read_item(item=item_id, partition_key=partition_key)
            return item
        except CosmosResourceNotFoundError:
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to load item {item_id} from {container_name}: {e}")

    def save_item(self, container_name: str, item: Dict[str, Any]):
        try:
            container = self.get_container(container_name)
            container.upsert_item(body=item)
        except Exception as e:
            raise RuntimeError(f"Failed to save item to {container_name}: {e}")
