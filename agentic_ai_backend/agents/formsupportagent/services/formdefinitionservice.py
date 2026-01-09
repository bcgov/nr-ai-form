
import os
import json
from typing import Dict, Any, Optional
from utils.blobservice import BlobService

class FormDefinitionService:
    def __init__(self, blob_service: BlobService, container_name: str):
        self.blob_service = blob_service
        self.container_name = container_name
        self.cache: Dict[str, Any] = {}

    def fetch_form_definition(self, definition_name: str) -> Optional[Dict[str, Any]]:

        if definition_name in self.cache:            
            return self.cache[definition_name]

        try:
            json_content = self.blob_service.read_blob_text(self.container_name, definition_name)
            form_data = json.loads(json_content)
            self.cache[definition_name] = form_data
            return form_data
        except Exception as e:
            print(f"Error fetching form definition {definition_name}: {e}")
            return None

    def list_available_definitions(self) -> list[str]:
        try:
            blobs = self.blob_service.list_blobs(self.container_name)
            return [b for b in blobs if b.endswith('.json')]
        except Exception as e:
            print(f"Error listing form definitions: {e}")
            return []
