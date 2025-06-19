import uuid
from typing import Dict, Any, List, Optional

from ..memory.memory_manager import MemoryManager

class ConversationManager:
    """Manages conversational sessions and their lifetime."""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
    
    def start_session(self) -> str:
        """Start a new conversation session and return its ID."""
        session_id = str(uuid.uuid4())
        self.memory_manager.update_conversation(
            session_id, 
            {"system": "Conversation started."}
        )
        return session_id
    
    def process_input(self, session_id: str, user_input: str) -> None:
        """Process user input and add it to the conversation."""
        self.memory_manager.update_conversation(
            session_id,
            {"user": user_input}
        )
    
    def add_response(self, session_id: str, response: str) -> None:
        """Add an agent response to the conversation."""
        self.memory_manager.update_conversation(
            session_id,
            {"assistant": response}
        )
    
    def format_response(self, session_id: str, response: Dict[str, Any]) -> str:
        """Format the agent response for display."""
        # Add the response to the conversation history
        self.add_response(session_id, response.get("content", ""))
        
        # Return a formatted version for display
        return response.get("content", "")
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the full conversation history for a session."""
        context = self.memory_manager.get_conversation_context(session_id)
        return context.get("messages", [])
    
    def get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """Get the conversation context for a session."""
        # Get the conversation context from the memory manager
        context = self.memory_manager.get_conversation_context(session_id)
        
        # If there's no context, return an empty dictionary
        if not context:
            return {}
        
        return context
    
    def save_session(self, session_id: str) -> None:
        """Save the current session (already handled by memory manager)."""
        pass  # The memory manager already persists after each update
    
    def load_session(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Load a session by ID."""
        context = self.memory_manager.get_conversation_context(session_id)
        if not context or not context.get("messages"):
            return None
        return context.get("messages")

    def update_conversation(self, session_id: str, turn: Dict[str, Any]) -> None:
        """Update the conversation with a new turn (public method for UI)."""
        self.memory_manager.update_conversation(session_id, turn)
