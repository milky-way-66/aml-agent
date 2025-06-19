from typing import Dict, Any, List, Optional
import json
import os
from ..memory.memory_manager import MemoryManager
from ...utils.logging import log_agent_action
from ...config.settings import settings
import anthropic

class Evaluator:
    """Evaluates execution results and determines next steps using Sonnet 3.5."""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.risk_thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8
        }
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", settings.get("ANTHROPIC_API_KEY"))
        self.anthropic_model = "claude-3-5-haiku-20241022"
        self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
    
    def evaluate(self, task_id: str) -> Dict[str, Any]:
        """Evaluate the current state of the task and determine next steps."""
        # Get the current state
        state = self.memory_manager.get_state(task_id)
        execution = state.get("execution", {})
        evaluation_state = state.get("evaluation", {})
        
        # Track how many times is_done=False has been returned
        is_done_false_count = evaluation_state.get("is_done_false_count", 0)
        
        # Check if all steps have been executed
        if execution.get("status") == "completed":
            # Analyze the results
            evaluation = self._analyze_results(state)

            # Generate a summary of what the agent did
            steps = execution.get("steps", [])
            summary_lines = ["[Agent Summary of Actions]"]
            for step in steps:
                summary_lines.append(f"[Step {step.get('step_id', '?')}] {step.get('description', '')}")
                summary_lines.append(f"  Tool: {step.get('tool', '')}")
                summary_lines.append(f"  Parameters: {json.dumps(step.get('parameters', {}), ensure_ascii=False)}")
                summary_lines.append(f"  Output:\n{self._format_step_output(step.get('result', {}))}\n")
            evaluation["steps_summary"] = "\n".join(summary_lines)

            # If is_done is False, increment the counter
            if not evaluation.get("is_done", False):
                is_done_false_count += 1
                evaluation["is_done_false_count"] = is_done_false_count
                # If we've already returned is_done=False twice, force is_done True
                if is_done_false_count >= 2:
                    evaluation["is_done"] = True
                    evaluation["forced_done"] = True
            else:
                # Reset the counter if is_done is True
                is_done_false_count = 0
                evaluation["is_done_false_count"] = is_done_false_count

            # Update the state with the evaluation
            self.memory_manager.update_state(task_id, {"evaluation": evaluation})
            
            return evaluation
        else:
            return {
                "status": "incomplete",
                "message": "Not all steps have been executed yet",
                "next_action": "continue_execution"
            }
    
    def _analyze_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the execution results using Sonnet 3.5 for comprehensive evaluation."""
        execution_steps = state.get("execution", {}).get("steps", [])
        plan = state.get("plan", [])
        task_description = state.get("task_description", "")
        
        # Extract data to provide context to Sonnet
        transaction_data = self._extract_transaction_data(execution_steps)
        entity_data = self._extract_entity_data(execution_steps)
        
        # Prepare the context for Sonnet
        context = self._prepare_sonnet_context(
            task_description,
            execution_steps,
            transaction_data,
            entity_data
        )
        
        # Get evaluation from Sonnet
        sonnet_evaluation = self._evaluate_with_sonnet(context)
        
        # Parse and structure the Sonnet response
        evaluation = self._parse_sonnet_response(sonnet_evaluation)
        
        # Log the evaluation action
        log_agent_action("evaluator", "analyze_results", {
            "risk_level": evaluation.get("risk_level", "unknown"),
            "suspicious_patterns_count": len(evaluation.get("suspicious_patterns", [])),
            "next_actions": evaluation.get("next_actions", [])
        })
        
        return evaluation
        
    def _prepare_sonnet_context(
        self,
        task_description: str,
        execution_steps: List[Dict[str, Any]],
        transaction_data: List[Dict[str, Any]],
        entity_data: List[Dict[str, Any]]
    ) -> str:
        """Prepare context for Sonnet evaluation."""
        def summarize_steps(steps):
            lines = []
            for i, step in enumerate(steps):
                tool = step.get("tool", "unknown_tool")
                status = step.get("status", "unknown")
                result = step.get("result", {})
                result_summary = self._summarize_result(result)
                output_text = self._format_step_output(result)
                lines.append(f"Step {i+1}: {tool} - {status} - {result_summary}\n{output_text}")
            return lines

        def summarize_transactions(transactions, limit=10):
            lines = []
            for tx in transactions[:limit]:
                tx_id = tx.get("id", "unknown")
                sender = tx.get("sender", "unknown")
                receiver = tx.get("receiver", "unknown")
                amount = tx.get("amount", 0)
                lines.append(f"Transaction {tx_id}: {sender} -> {receiver}, Amount: {amount}")
            if len(transactions) > limit:
                lines.append(f"...and {len(transactions) - limit} more transactions")
            return lines

        def summarize_entities(entities, limit=10):
            lines = []
            for entity in entities[:limit]:
                entity_id = entity.get("id", "unknown")
                entity_type = entity.get("type", "unknown")
                risk = entity.get("risk_score", entity.get("risk_level", "unknown"))
                lines.append(f"Entity {entity_id}: Type: {entity_type}, Risk: {risk}")
            if len(entities) > limit:
                lines.append(f"...and {len(entities) - limit} more entities")
            return lines

        steps_summary = summarize_steps(execution_steps)
        tx_summary = summarize_transactions(transaction_data)
        entity_summary = summarize_entities(entity_data)

        context = (
            "# AML Detection Task Evaluation\n\n"
            "## Task Description\n"
            f"{task_description}\n\n"
            "## Execution Steps Summary\n"
            f"{chr(10).join(steps_summary)}\n\n"
            "## Transaction Data\n"
            f"{chr(10).join(tx_summary)}\n\n"
            "## Entity Data\n"
            f"{chr(10).join(entity_summary)}\n\n"
            "## Raw Data for Analysis\n"
            f"Execution Steps: {json.dumps(execution_steps, indent=2)}\n"
            f"Transactions: {json.dumps(transaction_data, indent=2)}\n"
            f"Entities: {json.dumps(entity_data, indent=2)}\n\n"
            "## Evaluation Instructions\n"
            "As an AML expert, please analyze the above data and provide:\n"
            "1. Whether the task is complete. Return only True or False in a code block labeled 'is_done'.\n"
            "2. A detailed explanation of your reasoning in a code block labeled 'explanation'.\n\n"
            "Example output:\n"
            "```is_done\n"
            "True\n"
            "```\n"
            "```explanation\n"
            "# Your explanation here\n"
            "```\n"
            "Return only these two code blocks, nothing else.\n"
        )
        return context
    
    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Create a brief summary of a step result."""
        if not result:
            return "No results"
            
        summary_parts = []
        
        if "transactions" in result:
            summary_parts.append(f"Found {len(result['transactions'])} transactions")
        
        if "entities" in result:
            summary_parts.append(f"Found {len(result['entities'])} entities")
            
        if "risk_score" in result:
            summary_parts.append(f"Risk score: {result['risk_score']}")
            
        if "risk_level" in result:
            summary_parts.append(f"Risk level: {result['risk_level']}")
            
        if "suspicious_patterns" in result:
            summary_parts.append(f"Found {len(result['suspicious_patterns'])} suspicious patterns")
            
        if not summary_parts:
            # If we couldn't extract specific details, return a generic summary
            return f"Result keys: {', '.join(result.keys())}"
            
        return "; ".join(summary_parts)
    
    def _evaluate_with_sonnet(self, context: str) -> str:
        """Send the context to Claude for evaluation."""
        try:
            # Check if we're in test mode
            if os.environ.get("TESTING") == "true":
                return self._mock_sonnet_response()
                
            # Make API call to Anthropic Claude
            system_prompt = "You are an expert in Anti-Money Laundering (AML) analysis. Provide detailed evaluations of financial transactions and entities to identify potential money laundering activities."
            
            response = self.client.messages.create(
                model=self.anthropic_model,
                system=system_prompt,
                max_tokens=2000,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": context}
                ]
            )
            
            return response.content[0].text
                
        except Exception as e:
            log_agent_action("evaluator", "anthropic_api_exception", {"error": str(e)})
            return self._mock_sonnet_response()
    
    def _mock_sonnet_response(self) -> str:
        """Provide a mock response when Sonnet API is unavailable."""
        return json.dumps({
            "risk_level": "medium",
            "risk_score": 0.65,
            "suspicious_patterns": [
                {
                    "type": "structuring",
                    "description": "Multiple transactions just below reporting thresholds",
                    "severity": "high",
                    "evidence": {
                        "transactions": ["tx123", "tx124", "tx125"]
                    }
                },
                {
                    "type": "round_amounts",
                    "description": "Multiple transactions with suspiciously round amounts",
                    "severity": "medium",
                    "evidence": {
                        "transactions": ["tx126", "tx127"]
                    }
                }
            ],
            "findings": [
                {
                    "type": "suspicious_pattern",
                    "pattern_type": "structuring",
                    "description": "Multiple transactions just below reporting thresholds",
                    "severity": "high",
                    "evidence": {
                        "transactions": ["tx123", "tx124", "tx125"]
                    }
                },
                {
                    "type": "high_value_transactions",
                    "description": "Identified 3 high-value transactions",
                    "severity": "medium",
                    "evidence": {
                        "transactions": ["tx128", "tx129", "tx130"]
                    }
                }
            ],
            "next_actions": [
                "investigate_further",
                "monitor_closely",
                "review_structuring_patterns"
            ],
            "explanation": "This case presents MEDIUM risk indicators that warrant further investigation. The presence of multiple transactions just below reporting thresholds suggests potential structuring activity, which is a common money laundering technique. Additionally, several transactions with round amounts were identified, which is another red flag. While the evidence is not conclusive for definitive money laundering, these patterns justify enhanced monitoring and further investigation.",
            "summary": "Analysis complete. Risk level: medium. Found 2 suspicious patterns including potential structuring and round amount transactions."
        })
    
    def _parse_sonnet_response(self, response: str) -> Dict[str, Any]:
        """Parse the Sonnet response for is_done and explanation code blocks."""
        import re
        is_done = False
        explanation = ""
        # Extract is_done code block
        is_done_match = re.search(r"```is_done\s*([\s\S]*?)```", response)
        if is_done_match:
            is_done_str = is_done_match.group(1).strip().lower()
            is_done = is_done_str in ["true", "yes", "1"]
        # Extract explanation code block
        explanation_match = re.search(r"```explanation\s*([\s\S]*?)```", response)
        if explanation_match:
            explanation = explanation_match.group(1).strip()
        return {
            "status": "completed",
            "is_done": is_done,
            "explanation": explanation
        }
    
    def _extract_transaction_data(self, execution_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract transaction data from execution steps."""
        transactions = []
        
        for step in execution_steps:
            result = step.get("result", {})
            
            if step.get("tool") == "transaction_analyzer":
                if "transactions" in result:
                    transactions.extend(result["transactions"])
            elif step.get("tool") == "blockchain_query":
                if "transactions" in result:
                    transactions.extend(result["transactions"])
        
        return transactions
    
    def _extract_entity_data(self, execution_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract entity data from execution steps."""
        entities = []
        
        for step in execution_steps:
            result = step.get("result", {})
            
            if step.get("tool") == "entity_analyzer" or step.get("tool") == "kyc_checker":
                if "entities" in result:
                    entities.extend(result["entities"])
            elif step.get("tool") == "address_profiler":
                if "profiles" in result:
                    entities.extend(result["profiles"])
        
        return entities
    
    # Keep these methods for extracting data to provide to Sonnet
    def _extract_risk_scores(self, execution_steps: List[Dict[str, Any]]) -> List[float]:
        """Extract risk scores from execution steps."""
        risk_scores = []
        
        for step in execution_steps:
            result = step.get("result", {})
            
            if step.get("tool") == "risk_checker" and "risk_score" in result:
                risk_scores.append(float(result["risk_score"]))
            elif step.get("tool") == "transaction_analyzer" and "risk_score" in result:
                risk_scores.append(float(result["risk_score"]))
            elif "risk_level" in result:
                # Convert risk level to score if numerical score not available
                risk_level = result["risk_level"].lower()
                if risk_level == "low":
                    risk_scores.append(0.2)
                elif risk_level == "medium":
                    risk_scores.append(0.5)
                elif risk_level == "high":
                    risk_scores.append(0.8)
        
        return risk_scores

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
