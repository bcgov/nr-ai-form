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

    def read_blob_text(self, container_name: str, blob_name: str, encoding: str = "utf-8") -> str:
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


def load_blob_text_required(
    connection_string: str | None,
    container_name: str | None,
    directory: str | None,
    blob_filename: str,
) -> str:
    """Load a text asset from Azure Blob Storage; never fall back to local files."""
    if not connection_string or not container_name or not directory:
        raise RuntimeError(f"Blob asset config is required for {blob_filename}.")

    blob_name = f"{directory.strip('/')}/{blob_filename}"
    try:
        service = BlobService(connection_string)
        text = service.read_blob_text(container_name, blob_name)
        print(f"Loaded asset from blob: container={container_name}, blob={blob_name}")
        return text
    except Exception as exc:
        print(
            "Failed to load required blob asset. "
            f"connection_string={'***' if connection_string else '<none>'}, "
            f"container={container_name}, "
            f"directory={directory}, "
            f"blob_filename={blob_filename}, "
            f"resolved_blob={blob_name}, "
            f"error={exc}"
        )
        raise RuntimeError(
            f"Failed to load required blob asset {blob_name} from container {container_name}."
        ) from exc