from typing import Dict, Any, List, Optional
from ..memory.memory_manager import MemoryManager

class Orchestrator:
    """Manages workflow, agent coordination, and feedback loops."""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
    
    def start_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Start a new AML detection task."""
        # Create initial state
        initial_state = {
            "messages": [],
            "task": {
                "description": task_description,
                "status": "started",
                "created_at": None  # Will be set by DB
            },
            "plan": [],
            "execution": {"status": "pending", "steps": []},
            "evaluation": {},
            "tool_calls": [],
            "context": context or {}
        }
        
        # Create a new task and get its ID
        task_id = self.memory_manager.create_task(initial_state)
        
        return task_id
    
    def handle_feedback(self, task_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Handle feedback for a task."""
        current_state = self.memory_manager.get_state(task_id)
        
        # Update the state with feedback
        if "feedback" not in current_state:
            current_state["feedback"] = []
        
        current_state["feedback"].append(feedback)
        
        # Update the task status based on feedback
        if feedback.get("action") == "continue":
            current_state["task"]["status"] = "in_progress"
        elif feedback.get("action") == "complete":
            current_state["task"]["status"] = "completed"
        elif feedback.get("action") == "abort":
            current_state["task"]["status"] = "aborted"
        
        # Save the updated state
        self.memory_manager.update_state(task_id, current_state)
        
        return current_state
