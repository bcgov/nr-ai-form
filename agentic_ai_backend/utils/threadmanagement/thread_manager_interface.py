from abc import ABC, abstractmethod
from typing import Any, Tuple, Optional

#TODO: ABIN add more Abstract  methods as required. 
class IThreadManager(ABC):
    """
    Interface for thread state management strategies (e.g., CosmosDB, Redis or with any CSS AI NoSQL Service).
    """

    @abstractmethod
    async def get_thread_state(self, thread_id: str, agent: Any) -> Any:        
        pass

    @abstractmethod
    async def save_thread_state(self, thread_id: str, thread: Any) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass
