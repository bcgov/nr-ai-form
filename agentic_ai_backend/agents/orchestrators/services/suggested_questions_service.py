
import os
from typing import Optional
from utils.blobservice import BlobService

class SuggestedQuestionsService:
    def __init__(self, blob_service: BlobService, container_name: str):
        self.blob_service = blob_service
        self.container_name = container_name
        self.directory_path = 'suggested-questions'
        self.cache: dict[str, str] = {}

    def fetch_suggested_questions(self) -> Optional[str]:

        if 'suggested_questions' in self.cache:            
            return self.cache['suggested-questions']

        try:
            blob_name = f"{self.directory_path}/questions.json"
            
            suggested_questions = self.blob_service.read_blob_text(self.container_name, blob_name)
            self.cache['suggested-questions'] = suggested_questions
            return suggested_questions
        except Exception as e:
            print(f"Error fetching suggested questions: {e}")
            return None
