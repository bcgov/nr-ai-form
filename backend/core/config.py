from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pydantic import Field
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Project settings
    PROJECT_NAME: str = "AI Agent API"
    PROJECT_VERSION: str = "0.1.0"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS settings - handle comma-separated string or list
    ALLOWED_HOSTS: str = "*"
    
    # Azure OpenAI settings with fallbacks for different environments
    AZURE_OPENAI_API_KEY: str = Field(
        default="", 
        description="Azure OpenAI API Key - injected via GitHub Secrets in production"
    )
    AZURE_OPENAI_ENDPOINT: str = Field(
        default="", 
        description="Azure OpenAI Endpoint - injected via GitHub Secrets in production"
    )
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o-mini"
    
    # Local tunnel settings for development
    USE_LOCAL_TUNNEL: bool = False
    LOCAL_TUNNEL_PORT: int = 8082
    LOCAL_TUNNEL_HOST: str = "localhost"
    TUNNEL_RESOLVE_HOST: Optional[str] = None
    
    # LangChain settings (optional)
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: Optional[str] = None

    @property
    def azure_openai_base_url(self) -> str:
        """Get the appropriate base URL based on tunnel configuration"""
        if self.USE_LOCAL_TUNNEL:
            return f"https://{self.LOCAL_TUNNEL_HOST}:{self.LOCAL_TUNNEL_PORT}"
        return self.AZURE_OPENAI_ENDPOINT

    @property
    def allowed_hosts_list(self) -> List[str]:
        """Convert ALLOWED_HOSTS string to list"""
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return os.getenv("ENVIRONMENT", "dev").lower() == "prod"
    
    def validate_required_settings(self):
        """Validate that required settings are present"""
        if not self.AZURE_OPENAI_API_KEY:
            raise ValueError("AZURE_OPENAI_API_KEY is required")
        if not self.AZURE_OPENAI_ENDPOINT:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required")


settings = Settings()

# Validate settings on startup in production
if settings.is_production:
    settings.validate_required_settings()