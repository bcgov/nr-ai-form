
import unittest
import os
from dotenv import load_dotenv
from services.prompttemplateservice import PromptTemplateService
from utils.blobservice import BlobService

load_dotenv()

class TestPromptTemplateServiceIntegration(unittest.TestCase):
    def setUp(self):
        self.connection_string = os.getenv("AZURE_BLOBSTORAGE_CONNECTIONSTRING")
        self.container_name = os.getenv("AZURE_BLOBSTORAGE_CONTAINER")
        self.directory = "prompttemplates"
        
        if not self.connection_string:
            self.skipTest("AZURE_BLOBSTORAGE_CONNECTIONSTRING not set in .env")
            
        self.blob_service = BlobService(self.connection_string)
        self.service = PromptTemplateService(self.blob_service, self.container_name, self.directory)
        
        print(f"\nUsing Container: {self.container_name}")

    def test_fetch_real_prompt_template(self):
        template_name = "step1-Introduction.md"
        
        print(f"Attempting to fetch {template_name}...")
        result = self.service.fetch_prompt_template(template_name)
        
        self.assertIsNotNone(result, f"Failed to fetch {template_name}. Check if file exists in container.")
        self.assertIsInstance(result, str, "Result should be a string")
        self.assertGreater(len(result), 0, "Template content should not be empty")
        
        print(f"Successfully fetched {template_name}. Length: {len(result)} characters")
        
    def test_list_real_templates(self):
        print("Listing available templates...")
        templates = self.service.list_available_templates()
        print(f"Found templates: {templates}")
        
        self.assertIsInstance(templates, list)
        if "prompttemplates/step1-Introduction.md" in templates:
             self.assertIn("prompttemplates/step1-Introduction.md", templates)

if __name__ == '__main__':
    unittest.main()
