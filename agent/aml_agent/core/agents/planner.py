from typing import Dict, Any, List, Optional
import json
from anthropic import Anthropic
from ..memory.memory_manager import MemoryManager
from ...utils.logging import app_logger, log_agent_action
from ...config.settings import settings
from ...tools.rag_client import RAGClient
import os
import re

class Planner:
    """Creates plans for AML detection tasks."""
    
    def __init__(self, memory_manager: MemoryManager, mcp_client=None, rag_client: Optional[RAGClient] = None):
        """Initialize the Planner agent.
        
        Args:
            memory_manager: The memory manager for state access and updates.
            mcp_client: The MCP client for fetching available tools.
            rag_client: The RAG client for retrieving relevant information.
        """
        self.memory_manager = memory_manager
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", settings.get("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-haiku-20241022"  # Hard coded model
        self.client = Anthropic(api_key=self.api_key)
        self.mcp_client = mcp_client
        self.rag_client = rag_client
        
        if not self.api_key:
            app_logger.warning("Anthropic API key not found in settings. Planner will use fallback mode.")
        else:
            self.client = Anthropic(api_key=self.api_key)
    
    def create_plan(self, task_id: str) -> List[Dict[str, Any]]:
        """Create a plan for the given task using Sonnet 3.5 (Anthropic)."""
        # Get the current state
        state = self.memory_manager.get_state(task_id)
        task_description = state.get("task", {}).get("description", "")
        context = state.get("context", {}).copy() if state.get("context") else {}

        # First, gather relevant information using RAG
        if self.rag_client:
            log_agent_action("planner", f"Gathering RAG context for task: {task_description}", {"task_description": task_description})
            rag_context = self._gather_rag_context(task_description)
            context.update(rag_context)

        # Fetch available tools from MCP client and add to context
        if self.mcp_client:
            tools = self.mcp_client.list_tools()
            context["tools"] = tools
        
        # Always use Sonnet 3.5 to generate the plan
        try:
            plan = self._generate_plan_with_sonnet(task_description, context)
            if not plan:
                raise ValueError("Sonnet returned empty plan")
        except Exception as e:
            # If Sonnet fails, create a single-step fallback plan
            app_logger.error(f"Failed to generate plan: {str(e)}")
            app_logger.error(f"Fallback back to single-step plan")  
            plan = [
                {
                    "step_id": 1,
                    "description": f"Answer the following question: {task_description}",
                    "tool": "ai_model",
                    "parameters": {"question": task_description}
                }
            ]
        self.memory_manager.update_state(task_id, {"plan": plan})
        
        log_agent_action("planner", f"plan_created: {self._format_plan_to_string(plan)}", {"plan": plan})
        return plan
    
    def _format_plan_to_string(self, plan: List[Dict[str, Any]]) -> str:
        """Format the plan to a string."""
        plan_str = ""
        for step in plan:
            plan_str += f"\n\n"
            plan_str += f"Step {step['step_id']}: {step['description']}\n"
            plan_str += f"Tool: {step['tool']}\n"
            plan_str += f"Parameters: {step['parameters']}"
        return plan_str
    
    def _generate_plan_with_sonnet(self, task_description: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a plan using Anthropic Claude API."""
        # Prepare the prompt for Anthropic
        prompt = self._prepare_planning_prompt(task_description, context)
        
        # Call Anthropic API using SDK
        system_prompt = "You are an expert AML investigator. Create a detailed step-by-step plan for investigating potential money laundering activities."
        
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            assistant_message = response.content[0].text
            
            # Extract JSON from code block if present
            code_block_match = re.search(r"```json(.*?)```", assistant_message, re.DOTALL)
            if code_block_match:
                json_str = code_block_match.group(1).strip()
            else:
                # Fallback: try to find any code block
                code_block_match = re.search(r"```(.*?)```", assistant_message, re.DOTALL)
                if code_block_match:
                    json_str = code_block_match.group(1).strip()
                else:
                    # If no code block, use the whole message
                    json_str = assistant_message.strip()
            
            try:
                plan_data = json.loads(json_str)
                if isinstance(plan_data, dict) and "plan" in plan_data:
                    steps = plan_data["plan"]
                elif isinstance(plan_data, list):
                    steps = plan_data
                else:
                    raise ValueError("Response JSON is not in expected format (dict with 'plan' key or list)")
            except json.JSONDecodeError:
                app_logger.error(f"Failed to parse response as JSON: {json_str}")
                raise ValueError("Invalid JSON response from API")
                
            app_logger.debug(f"Plan: {steps}")
            # Format the steps to match our expected structure
            formatted_steps = []
            for i, step in enumerate(steps):
                formatted_step = {
                    "step_id": i + 1,
                    "description": step.get("description", ""),
                    "tool": step.get("tool", ""),
                    "parameters": step.get("parameters", {})
                }
                formatted_steps.append(formatted_step)
            
            return formatted_steps
        except json.JSONDecodeError:
            app_logger.error(f"Failed to parse Sonnet response as JSON: {assistant_message}")
            raise ValueError("Invalid JSON response from Sonnet API")
        except Exception as e:
            app_logger.error(f"Failed to generate plan: {str(e)}")
            raise
    
    def _prepare_planning_prompt(self, task_description: str, context: Dict[str, Any]) -> str:
        """Prepare a prompt for the Sonnet API based on the task and context."""
        # Extract and format context sections
        history = ""
        rag_data = ""
        tools_list = ""

        # 1. History (excluding rag_context and tools)
        context_items = []
        for k, v in context.items():
            if k not in ["rag_context", "tools"]:
                context_items.append(f"{k}: {v}")
        history = "\n".join(context_items) if context_items else "No history provided."
        
        # 2. Additional data from RAG
        if "rag_context" in context:
            rag_matches = context["rag_context"].get("matches", [])
            rag_query = context["rag_context"].get("query", "")
            if rag_matches:
                rag_data = f"Query: {rag_query}\nMatches:\n"
                for i, match in enumerate(rag_matches, 1):
                    rag_data += f"  {i}. Content: {match}\n"
            else:
                rag_data = f"Query: {rag_query}\nNo relevant matches found."
        else:
            rag_data = "No RAG data available."

        # 3. Available tools
        if "tools" in context and context["tools"]:
            tools = context["tools"]
            tool_lines = []
            for tool in tools:
                name = tool.get("name", "")
                desc = tool.get("description", "")
                params = tool.get("parameters", [])
                param_str = ", ".join([f"{p['name']} ({p['type']})" for p in params]) if params else "None"
                tool_lines.append(f"- {name}: {desc} | Parameters: {param_str}")
            tools_list = "\n".join(tool_lines)
        else:
            tools_list = "No tools available."

        prompt = f"""
# Task: {task_description}

# History:
{history}

# Additional Data from RAG:
{rag_data}

# Available Tools:
{tools_list}

# Instructions:
You are an expert AI assistant. Your job is to create a clear, step-by-step plan to resolve the above task. You may use any of the available tools listed in the context as needed. Each step should specify:
- A concise description of the action
- The tool to use (from the provided tools, or 'ai_model' for general reasoning)
- The parameters required for the tool

The plan should follow the Re-Act pattern. First is reasoning, then action.
In most situations, it will use RAG to get more information, context, and knowledge, then based on the new information, it can replan or execute the action.
Then it will execute the action, and update the context with the result.

So The plan should be at least 3 steps: 1. Reasoning, 2. Action, 3. Update context (summary).

The plan must be a JSON object with a 'plan' key (list of steps). Each step must be an object with:
- 'step_id': integer
- 'description': string
- 'tool': string
- 'parameters': object (dictionary of parameters)

Return ONLY the plan JSON inside a code block like this:
```json
# the plan
{{
  "plan": [
    {{
      "step_id": 1,
      "description": "...",
      "tool": "...",
      "parameters": {{ ... }}
    }}
  ]
}}
```
Do not include any explanation or extra text outside the code block.
"""
        return prompt

    def _gather_rag_context(self, task_description: str) -> Dict[str, Any]:
        """Gather relevant information using RAG before planning.
        
        Args:
            task_description: The task description to gather context for.
            
        Returns:
            Dict containing relevant information from RAG.
        """
        if not self.rag_client:
            return {}
            
        try:
            # Query RAG with the task description
            rag_response = self.rag_client.query({
                "query": task_description,
                "top_k": 5  # Get top 5 most relevant documents
            })
            
            if "error" in rag_response:
                app_logger.warning(f"RAG query failed: {rag_response['error']}")
                return {}
                
            # Extract and format the matches
            matches = rag_response.get("matches", [])
            
            return {
                "rag_context": {
                    "matches": matches,
                    "query": task_description
                }
            }
            
        except Exception as e:
            app_logger.error(f"Error gathering RAG context: {str(e)}")
            return {}
