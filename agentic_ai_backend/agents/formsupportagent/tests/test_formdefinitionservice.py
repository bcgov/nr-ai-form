
import unittest
import os
import json
from dotenv import load_dotenv
from services.formdefinitionservice import FormDefinitionService
from utils.blobservice import BlobService

load_dotenv()

class TestFormDefinitionServiceIntegration(unittest.TestCase):
    def setUp(self):
        self.connection_string = os.getenv("AZURE_BLOBSTORAGE_CONNECTIONSTRING")
        self.container_name = os.getenv("AZURE_BLOBSTORAGE_CONTAINER")
        
        if not self.connection_string:
            self.skipTest("AZURE_BLOBSTORAGE_CONNECTIONSTRING not set in .env")
            
        self.blob_service = BlobService(self.connection_string)
        self.service = FormDefinitionService(self.blob_service, self.container_name)
        
        print(f"\nUsing Container: {self.container_name}")

    def test_fetch_real_form_definition(self):
        blob_name = "step1-Introduction.json"
        
        print(f"Attempting to fetch {blob_name}...")
        result = self.service.fetch_form_definition(blob_name)
        
        self.assertIsNotNone(result, f"Failed to fetch {blob_name}. Check if file exists in container.")
        self.assertIsInstance(result, dict, "Result should be a dictionary parsed from JSON")
        
        print(f"Successfully fetched {blob_name}. Keys: {list(result.keys())}")
        
    def test_list_real_definitions(self):
        print("Listing available definitions...")
        definitions = self.service.list_available_definitions()
        print(f"Found definitions: {definitions}")
        
        self.assertIsInstance(definitions, list)
        if "step1-Introduction.json" in definitions:
             self.assertIn("step1-Introduction.json", definitions)

if __name__ == '__main__':
    unittest.main()
