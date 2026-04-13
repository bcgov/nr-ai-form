
import os
from typing import Optional
from utils.blobservice import BlobService

class GuidedPromptsService:
    def __init__(self, blob_service: BlobService, container_name: str):
        self.blob_service = blob_service
        self.container_name = container_name
        self.directory_path = 'guided-prompts'
        self.cache: dict[str, str] = {}

    def fetch_guided_prompts(self) -> Optional[str]:

        # TODO: Cache the response
        # if 'guided_prompts' in self.cache:            
        #     return self.cache['guided_prompts']

        try:
            blob_name = f"{self.directory_path}/guided-prompts.json"
            
            guided_prompts = self.blob_service.read_blob_text(self.container_name, blob_name)
            # self.cache['guided_prompts'] = guided_prompts
            return guided_prompts
        except Exception as e:
            print(f"Error fetching guided prompts: {e}")
            return None
