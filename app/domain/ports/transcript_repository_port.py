from abc import ABC, abstractmethod

class TranscriptRepositoryPort(ABC):
    """
    Port for transcript persistence operations.
    """
    
    @abstractmethod
    async def save(self, call_id: int, role: str, content: str) -> None:
        """
        Save a single transcript line.
        
        Args:
            call_id: Database ID of the call.
            role: "user" or "assistant".
            content: Text content of the message.
        """
        pass
