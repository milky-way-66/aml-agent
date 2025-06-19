from typing import Dict, Any, List, Optional
from ..memory.memory_manager import MemoryManager
from ...tools.rag_client import RAGClient
from ...tools.mcp_client import MCPClient
import os
import anthropic
from ...config.settings import settings

class Executor:
    """Executes plan steps and calls tools."""
    
    def __init__(self, memory_manager: MemoryManager, rag_client: RAGClient, mcp_client: MCPClient):
        self.memory_manager = memory_manager
        self.rag_client = rag_client
        self.mcp_client = mcp_client
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", settings.get("ANTHROPIC_API_KEY"))
        self.anthropic_model = "claude-3-5-haiku-20241022"
        self.sonnet_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
    
    def execute_step(self, task_id: str, step_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute a specific step or the next pending step."""
        # Get the current state
        state = self.memory_manager.get_state(task_id)
        plan = state.get("plan", [])
        execution = state.get("execution", {"status": "pending", "steps": []})
        
        # Find the step to execute
        step_to_execute = None
        if step_id is not None:
            # Find the specific step
            for step in plan:
                if step["step_id"] == step_id:
                    step_to_execute = step
                    break
            if not step_to_execute:
                raise ValueError(f"Step with ID {step_id} not found in the plan")
        else:
            # Find the next pending step
            executed_step_ids = [s["step_id"] for s in execution.get("steps", [])]
            for step in plan:
                if step["step_id"] not in executed_step_ids:
                    step_to_execute = step
                    break
            if not step_to_execute:
                # All steps have been executed
                execution["status"] = "completed"
                self.memory_manager.update_state(task_id, {"execution": execution})
                return {"status": "completed", "message": "All steps have been executed"}
        
        # Execute the step
        result = self._execute_tool(step_to_execute)
        
        # Record the execution
        execution_record = {
            "step_id": step_to_execute["step_id"],
            "description": step_to_execute["description"],
            "tool": step_to_execute["tool"],
            "parameters": step_to_execute["parameters"],
            "result": result,
            "timestamp": None  # Will be set by DB
        }
        
        # Update the execution history
        if "steps" not in execution:
            execution["steps"] = []
        execution["steps"].append(execution_record)
        
        # Update the tool calls history
        tool_call_record = {
            "tool": step_to_execute["tool"],
            "parameters": step_to_execute["parameters"],
            "result": result,
            "timestamp": None  # Will be set by DB
        }
        state_update = {
            "execution": execution,
            "tool_calls": state.get("tool_calls", []) + [tool_call_record]
        }
        
        # Update the state
        self.memory_manager.update_state(task_id, state_update)
        
        return execution_record
    
    def _execute_tool(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool based on the step definition. Uses RAG for 'rag' tool, otherwise Sonnet 3.5 (Anthropic) model."""
        tool_name = step.get("tool", "")
        parameters = step.get("parameters", {})
        if tool_name in ["rag", "rag_tool"]:
            # Use RAG client for document retrieval
            return self.rag_client.query(parameters)
        elif tool_name in ["transaction_analyzer", "risk_checker", "report_generator"]:
            # Use MCP client for analysis tools
            return self.mcp_client.call_tool(tool_name, parameters)
        elif tool_name == "ai_model" or tool_name == "sonnet" or tool_name == "anthropic" or tool_name == "claude" or tool_name == "claude-3-sonnet-20240229":
            # Explicitly use Sonnet model
            return self._execute_with_sonnet(step)
        else:
            # Fallback: try Sonnet model as a last resort
            return self._execute_with_sonnet(step)

    def _execute_with_sonnet(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Call Sonnet 3.5 (Anthropic) model to process the step."""
        try:
            prompt = self._prepare_sonnet_prompt(step)
            system_prompt = "You are an expert AML agent. Given the following step and parameters, perform the required analysis or action and return your findings as a JSON object."
            response = self.sonnet_client.messages.create(
                model=self.anthropic_model,
                system=system_prompt,
                max_tokens=1500,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            # Try to parse the response as JSON if possible
            content = response.content[0].text
            try:
                import json
                return json.loads(content)
            except Exception:
                return {"result": content, "warning": "Could not parse Sonnet response as JSON."}
        except Exception as e:
            return {"error": f"Sonnet model call failed: {str(e)}"}

    def _prepare_sonnet_prompt(self, step: Dict[str, Any]) -> str:
        """Format a prompt for Sonnet based on the step."""
        description = step.get("description", "")
        tool = step.get("tool", "")
        parameters = step.get("parameters", {})
        import json
        prompt = f"""
# AML Agent Step

## Step Description
{description}

## Tool
{tool}

## Parameters
{json.dumps(parameters, indent=2)}

## Instructions
Perform the above step as an expert AML agent. If analysis is required, provide a summary, findings, and recommended next actions. Return your response as a JSON object.
"""
        return prompt
