from typing import Dict, Any, List, Tuple, Annotated, TypedDict, Optional
import langgraph.graph as lg
from langgraph.graph import StateGraph, END

from .agents.orchestrator import Orchestrator
from .agents.planner import Planner
from .agents.executor import Executor
from .agents.evaluator import Evaluator
from .memory.memory_manager import MemoryManager

class AgentState(TypedDict):
    messages: List[Dict[str, Any]]  # Conversation history
    task: Dict[str, Any]            # Current task details
    plan: List[Dict[str, Any]]      # Plan created by Planner
    execution: Dict[str, Any]       # Execution status and history
    evaluation: Dict[str, Any]      # Evaluation results
    tool_calls: List[Dict[str, Any]]  # History of tool calls and responses
    context: Dict[str, Any]         # Additional context information

class AMLWorkflow:
    """LangGraph workflow for AML detection."""
    
    def __init__(self, memory_manager: MemoryManager, orchestrator: Orchestrator, 
                 planner: Planner, executor: Executor, evaluator: Evaluator):
        self.memory_manager = memory_manager
        self.orchestrator = orchestrator
        self.planner = planner
        self.executor = executor
        self.evaluator = evaluator
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create a new graph
        builder = StateGraph(AgentState)
        
        # Add nodes
        builder.add_node("orchestrator", self._orchestrator_node)
        builder.add_node("planner", self._planner_node)
        builder.add_node("executor", self._executor_node)
        builder.add_node("evaluator", self._evaluator_node)
        
        # Define edges
        builder.add_edge("orchestrator", "planner")
        builder.add_edge("planner", "executor")
        builder.add_edge("executor", "evaluator")
        
        # Add conditional edges
        builder.add_conditional_edges(
            "evaluator",
            self._route_after_evaluation,
            {
                "continue_execution": "executor",
                "replan": "planner",
                "complete": END
            }
        )
        
        # Set the entry point
        builder.set_entry_point("orchestrator")
        
        return builder.compile()
    
    def _orchestrator_node(self, state: AgentState) -> AgentState:
        """Orchestrator node in the workflow."""
        # The orchestrator has already initialized the task
        # This node is mainly for handling feedback and coordination
        task_id = state["task"].get("id")
        if not task_id:
            raise ValueError("Task ID not found in state")
        
        # Update the state based on any feedback
        if "feedback" in state:
            self.orchestrator.handle_feedback(task_id, state["feedback"])
        
        return state
    
    def _planner_node(self, state: AgentState) -> AgentState:
        """Planner node in the workflow."""
        task_id = state["task"].get("id")
        if not task_id:
            raise ValueError("Task ID not found in state")
        
        # Create a plan if one doesn't exist
        if not state.get("plan"):
            plan = self.planner.create_plan(task_id)
            state["plan"] = plan
        
        return state
    
    def _executor_node(self, state: AgentState) -> AgentState:
        """Executor node in the workflow."""
        task_id = state["task"].get("id")
        if not task_id:
            raise ValueError("Task ID not found in state")
        
        # Execute the next step
        result = self.executor.execute_step(task_id)
        
        # Update the state with the execution result
        state["execution"] = self.memory_manager.get_state(task_id).get("execution", {})
        state["tool_calls"] = self.memory_manager.get_state(task_id).get("tool_calls", [])
        
        return state
    
    def _evaluator_node(self, state: AgentState) -> AgentState:
        """Evaluator node in the workflow."""
        task_id = state["task"].get("id")
        if not task_id:
            raise ValueError("Task ID not found in state")
        
        # Evaluate the current state
        evaluation = self.evaluator.evaluate(task_id)
        
        # Update the state with the evaluation
        state["evaluation"] = evaluation
        
        return state
    
    def _route_after_evaluation(self, state: AgentState) -> str:
        """Determine the next step after evaluation."""
        evaluation = state.get("evaluation", {})
        
        if evaluation.get("status") == "completed":
            return "complete"
        
        next_action = evaluation.get("next_action")
        if next_action == "continue_execution":
            return "continue_execution"
        elif next_action == "replan":
            return "replan"
        else:
            # Default to completion if no specific action
            return "complete"
    
    def run(self, task_id: str) -> Dict[str, Any]:
        """Run the workflow for a given task."""
        # Get the initial state
        initial_state = self.memory_manager.get_state(task_id)
        
        # Ensure the task ID is in the state
        initial_state["task"]["id"] = task_id
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        # Update the final state in the memory manager
        self.memory_manager.update_state(task_id, final_state)
        
        return final_state
