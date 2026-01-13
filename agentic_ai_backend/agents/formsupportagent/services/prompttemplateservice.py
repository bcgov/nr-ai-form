
import os
from typing import Optional
from utils.blobservice import BlobService

class PromptTemplateService:
    def __init__(self, blob_service: BlobService, container_name: str, directory_path: str = "prompttemplates"):
        self.blob_service = blob_service
        self.container_name = container_name
        self.directory_path = directory_path
        self.cache: dict[str, str] = {}

    def fetch_prompt_template(self, template_name: str) -> Optional[str]:

        if template_name in self.cache:            
            return self.cache[template_name]

        try:
            blob_name = f"{self.directory_path}/{template_name}" if self.directory_path else template_name
            
            template_content = self.blob_service.read_blob_text(self.container_name, blob_name)
            self.cache[template_name] = template_content
            return template_content
        except Exception as e:
            print(f"Error fetching prompt template {template_name}: {e}")
            return None

    def list_available_templates(self) -> list[str]:
        try:
            blobs = self.blob_service.list_blobs(self.container_name, name_starts_with=self.directory_path)
            return [b for b in blobs if b.endswith('.md')]
        except Exception as e:
            print(f"Error listing prompt templates: {e}")
            return []
