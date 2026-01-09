
import os
from azure.storage.blob import BlobServiceClient
from typing import List, Optional

class BlobService:

    def __init__(self, connection_string: str):
        if not connection_string:
            raise ValueError("connection_string must be provided.")
        self.connection_string = connection_string
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize BlobServiceClient: {e}")

    def download_blob(self, container_name: str, blob_name: str, destination_path: str) -> str:

        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            with open(destination_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
                
            return os.path.abspath(destination_path)
        except Exception as e:
            raise RuntimeError(f"Failed to download blob {blob_name}: {e}")

    def read_blob_text(self, container_name: str, blob_name: str, encoding: str = 'utf-8') -> str:

        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            return blob_client.download_blob().readall().decode(encoding)
        except Exception as e:
            raise RuntimeError(f"Failed to read blob {blob_name}: {e}")

    def list_blobs(self, container_name: str, name_starts_with: Optional[str] = None) -> List[str]:
   
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            return [blob.name for blob in container_client.list_blobs(name_starts_with=name_starts_with)]
        except Exception as e:
            raise RuntimeError(f"Failed to list blobs in container {container_name}: {e}")
