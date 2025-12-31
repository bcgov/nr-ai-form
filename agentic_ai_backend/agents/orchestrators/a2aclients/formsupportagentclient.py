from a2aclients.a2a_client import CSS_AI_A2A_BaseClient

class FormSupportAgentA2AClient(CSS_AI_A2A_BaseClient):
    """Specialized A2A client for the Form Support Agent"""
    
    def __init__(self, base_url: str = "http://localhost:8001", timeout: int = 30):
        super().__init__(base_url, timeout)