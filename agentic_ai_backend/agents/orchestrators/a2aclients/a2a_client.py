"""
A2A (Agent to Agent) Client for communicating with agents via HTTP endpoints.
This module provides a client class to interact with agents that follow the A2A protocol.
"""
import aiohttp
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class AgentManifest:
    """Represents an agent's manifest/capabilities"""
    name: str
    author: str
    description: str
    version: str
    base_url: str
    invoke_endpoint: str
    discovery_endpoint: str
    capabilities: list[Dict[str, Any]]


class CSS_AI_A2A_BaseClient:
    """
    Client for communicating with agents via A2A protocol.
    """
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize the A2A client.
        
        Args:
            base_url: The base URL of the agent's A2A server (e.g., http://localhost:8000)
            timeout: Timeout in seconds for HTTP requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._manifest: Optional[AgentManifest] = None
        
    async def get_manifest(self) -> AgentManifest:
        """
        Fetch the agent's manifest from the discovery endpoint.
        
        Returns:
            AgentManifest: The agent's capabilities and metadata
        """
        if self._manifest is not None:
            return self._manifest
            
        url = f"{self.base_url}/.well-known/agent.json"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                
                identity = data.get('identity', {})
                interaction = data.get('interaction', {})
                endpoints = interaction.get('endpoints', {})
                
                self._manifest = AgentManifest(
                    name=identity.get('name', 'Unknown'),
                    author=identity.get('author', 'Unknown'),
                    description=identity.get('description', ''),
                    version=identity.get('version', '1.0.0'),
                    base_url=interaction.get('baseUrl', self.base_url),
                    invoke_endpoint=endpoints.get('invoke', {}).get('url', '/invoke'),
                    discovery_endpoint=endpoints.get('discovery', {}).get('url', '/.well-known/agent.json'),
                    capabilities=data.get('capabilities', [])
                )
                
        return self._manifest
    
    async def invoke(self, query: str, session_id: Optional[str] = None, **kwargs) -> str:
        """
        Invoke the agent with a query.
        
        Args:
            query: The user query to send to the agent
            session_id: Optional session ID for maintaining conversation context
            **kwargs: Additional parameters to pass to the agent (e.g., step_number)
            
        Returns:
            str: The agent's response
        """
        # Get manifest to ensure we have the correct endpoint
        manifest = await self.get_manifest()
        
        url = f"{self.base_url}{manifest.invoke_endpoint}"
        payload = {
            "query": query,
            "session_id": session_id,
            **kwargs  # Include any additional parameters (like step_number)
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                return result.get('response', '')
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the agent is healthy and available.
        
        Returns:
            Dict: Health status information
        """
        url = f"{self.base_url}/health"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()






    