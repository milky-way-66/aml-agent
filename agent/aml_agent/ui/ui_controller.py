from typing import Dict, Any, List, Optional
from ..core.agents.orchestrator import Orchestrator
from ..core.conversation.conversation_manager import ConversationManager
from ..core.workflow import AMLWorkflow
import json

class UIController:
    """Mediates between UI and core system."""
    
    def __init__(self, orchestrator: Orchestrator, conversation_manager: ConversationManager, workflow: AMLWorkflow):
        self.orchestrator = orchestrator
        self.conversation_manager = conversation_manager
        self.workflow = workflow
    
    def handle_command(self, command_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a command from the UI."""
        if command_type == "start_task":
            task_description = parameters.get("description", "")
            context = parameters.get("context", {})
            
            # Start a new task
            task_id = self.orchestrator.start_task(task_description, context)
            
            # Run the workflow
            result = self.workflow.run(task_id)
            
            return {
                "status": "success",
                "task_id": task_id,
                "result": result
            }
        
        elif command_type == "get_task_status":
            task_id = parameters.get("task_id")
            if not task_id:
                return {"status": "error", "message": "Task ID is required"}
            
            # Get the task state
            state = self.orchestrator.memory_manager.get_state(task_id)
            
            return {
                "status": "success",
                "task_id": task_id,
                "state": state
            }
        
        elif command_type == "list_tasks":
            limit = parameters.get("limit", 10)
            
            # List recent tasks
            tasks = self.orchestrator.memory_manager.list_tasks(limit)
            
            return {
                "status": "success",
                "tasks": tasks
            }
        
        elif command_type == "start_chat":
            # Start a new chat session
            session_id = self.conversation_manager.start_session()
            
            return {
                "status": "success",
                "session_id": session_id,
                "message": "Chat session started"
            }
        
        elif command_type == "chat_message":
            session_id = parameters.get("session_id")
            message = parameters.get("message", "")
            
            if not session_id:
                return {"status": "error", "message": "Session ID is required"}
            
            # Process the message
            self.conversation_manager.process_input(session_id, message)
            
            # Create a task for the message
            context = self.conversation_manager.get_conversation_context(session_id)
            task_id = self.orchestrator.start_task(message, context)
            
            # Run the workflow to process the message
            result = self.workflow.run(task_id)
            
            # Extract the response from the result
            evaluation = result.get("evaluation", {})
            response = {
                "content": evaluation.get("summary", "I couldn't process that request."),
                "risk_level": evaluation.get("risk_level", "unknown"),
                "suspicious_patterns": evaluation.get("suspicious_patterns", []),
                "next_actions": evaluation.get("next_actions", []),
                "task_id": task_id
            }
            
            # Format and add the response to the conversation
            formatted_response = self.conversation_manager.format_response(session_id, response)
            
            # Update the conversation context with the task result
            self.conversation_manager.update_conversation(
                session_id, 
                {"role": "assistant", "content": formatted_response, "task_id": task_id}
            )
            
            return {
                "status": "success",
                "session_id": session_id,
                "response": formatted_response
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unknown command type: {command_type}"
            }
    
    def _format_step_output(self, output: dict) -> str:
        """Format a step output dictionary as readable text."""
        if not output:
            return "No output."
        lines = []
        for key, value in output.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    if isinstance(item, dict):
                        sublines = [f"    {k}: {v}" for k, v in item.items()]
                        lines.extend(sublines)
                    else:
                        lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"    {k}: {v}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def display_response(self, response_data: Dict[str, Any]) -> str:
        """Format a response for display in the UI."""
        if response_data.get("status") == "error":
            return f"Error: {response_data.get('message', 'Unknown error')}"
        
        # Show step-by-step execution if available
        if "result" in response_data:
            result = response_data["result"]
            execution = result.get("execution", {})
            steps = execution.get("steps", [])
            evaluation = result.get("evaluation", {})
            if evaluation and evaluation.get("steps_summary"):
                return evaluation["steps_summary"]
            if steps:
                step_outputs = []
                for step in steps:
                    step_outputs.append(
                        f"[Step {step.get('step_id', '?')}] {step.get('description', '')}\n"
                        f"  Tool: {step.get('tool', '')}\n"
                        f"  Parameters: {json.dumps(step.get('parameters', {}), ensure_ascii=False)}\n"
                        f"  Output:\n{self._format_step_output(step.get('result', {}))}\n"
                    )
                return "\n".join(step_outputs)
        
        # For chat, show step-by-step if available in evaluation
        if "session_id" in response_data and "response" in response_data:
            session_id = response_data["session_id"]
            # Try to get the latest task for this session
            # (Assume the last task is the one just run)
            # This is a best-effort approach
            from ..core.memory.memory_manager import MemoryManager
            memory_manager = self.orchestrator.memory_manager
            tasks = memory_manager.list_tasks(limit=1)
            if tasks:
                task_id = tasks[0]["task_id"]
                state = memory_manager.get_state(task_id)
                execution = state.get("execution", {})
                steps = execution.get("steps", [])
                if steps:
                    step_outputs = []
                    for step in steps:
                        step_outputs.append(
                            f"[Step {step.get('step_id', '?')}] {step.get('description', '')}\n"
                            f"  Tool: {step.get('tool', '')}\n"
                            f"  Parameters: {json.dumps(step.get('parameters', {}), ensure_ascii=False)}\n"
                            f"  Output:\n{self._format_step_output(step.get('result', {}))}\n"
                        )
                    return "\n".join(step_outputs)
        
        if "task_id" in response_data:
            task_id = response_data["task_id"]
            
            if "result" in response_data:
                result = response_data["result"]
                evaluation = result.get("evaluation", {})
                
                if evaluation:
                    patterns_text = ""
                    if suspicious_patterns := evaluation.get("suspicious_patterns", []):
                        patterns_text = "\nSuspicious Patterns:\n" + "\n".join(
                            f"- {pattern}" for pattern in suspicious_patterns
                        )
                    
                    next_actions_text = ""
                    if next_actions := evaluation.get("next_actions", []):
                        next_actions_text = "\nRecommended Next Actions:\n" + "\n".join(
                            f"- {action}" for action in next_actions
                        )
                    
                    return (
                        f"Task {task_id} completed.\n"
                        f"Risk Level: {evaluation.get('risk_level', 'Unknown')}\n"
                        f"Summary: {evaluation.get('summary', 'No summary available.')}"
                        f"{patterns_text}"
                        f"{next_actions_text}"
                    )
                else:
                    return f"Task {task_id} is in progress."
            
            elif "state" in response_data:
                state = response_data["state"]
                task_status = state.get("task", {}).get("status", "unknown")
                return f"Task {task_id} status: {task_status}"
        
        elif "session_id" in response_data:
            if "response" in response_data:
                # For chat responses, we want to display the formatted response
                # which may include risk assessment and other structured information
                response = response_data["response"]
                
                # If the response has additional structured data, format it nicely
                if isinstance(response_data.get("response"), dict):
                    resp = response_data["response"]
                    
                    patterns_text = ""
                    if suspicious_patterns := resp.get("suspicious_patterns", []):
                        patterns_text = "\nSuspicious Patterns:\n" + "\n".join(
                            f"- {pattern}" for pattern in suspicious_patterns
                        )
                    
                    next_actions_text = ""
                    if next_actions := resp.get("next_actions", []):
                        next_actions_text = "\nRecommended Next Actions:\n" + "\n".join(
                            f"- {action}" for action in next_actions
                        )
                    
                    risk_level = f"\nRisk Level: {resp.get('risk_level', 'Unknown')}" if "risk_level" in resp else ""
                    
                    return (
                        f"{resp.get('content', '')}"
                        f"{risk_level}"
                        f"{patterns_text}"
                        f"{next_actions_text}"
                    )
                
                return response_data["response"]
            else:
                return f"Session {response_data['session_id']} started."
        
        elif "tasks" in response_data:
            tasks = response_data["tasks"]
            if not tasks:
                return "No tasks found."
            
            task_list = "\n".join([
                f"Task {task['task_id']} - Created: {task['created_at']}, Updated: {task['updated_at']}"
                for task in tasks
            ])
            
            return f"Recent tasks:\n{task_list}"
        
        return str(response_data)
    
    def initialize_interface(self, config: Dict[str, Any]) -> None:
        """Initialize the UI interface with the given configuration."""
        # This is a placeholder for UI initialization
        # In a real implementation, this would configure the UI based on the config
        pass
    
    def update_display(self, update_type: str, data: Dict[str, Any]) -> None:
        """Update the UI display with new data."""
        # This is a placeholder for UI updates
        # In a real implementation, this would update the UI based on the update type and data
        pass

    def display_plan(self, plan: list) -> None:
        """Display the plan to the user in a readable format."""
        print("\n[Plan created by agent]")
        print(json.dumps({"plan": plan}, indent=2, ensure_ascii=False))

    def run_task(self, task_description: str, context: dict = None) -> None:
        # ... existing code ...
        # After plan is created, display it
        plan = state.get("plan", [])
        if plan:
            self.display_plan(plan)
        # ... existing code ...

    def chat(self, session_id: str) -> None:
        # ... existing code ...
        # After plan is created, display it
        plan = state.get("plan", [])
        if plan:
            self.display_plan(plan)
        # ... existing code ...
