import httpx
from typing import Dict, Any, Optional, List
import time
from functools import wraps
from aml_agent.utils.timed_cache import timed_cache

# Decorator to cache function result for a given timeout (in seconds)
def timed_cache(timeout: int = 60):
    """Decorator to cache function result for a given timeout (in seconds)."""
    def decorator(func):
        cache = {}
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            now = time.time()
            key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < timeout:
                    return result
            result = func(self, *args, **kwargs)
            cache[key] = (result, now)
            return result
        return wrapper
    return decorator

class MCPClient:
    """Client for standardized tool calls (risk scoring, clustering, etc.)."""
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)
        
        # For demo purposes, we'll use mock data if no API is configured
        self.use_mock = True
    
    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool with the given parameters."""
        if self.use_mock:
            return self._mock_tool_call(tool_name, params)
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        response = self.client.post(
            f"{self.base_url}/tools/{tool_name}",
            json=params,
            headers=headers
        )
        
        if response.status_code != 200:
            return {
                "error": f"API error: {response.status_code}",
                "message": response.text
            }
        
        return response.json()
    
    def _mock_tool_call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock data for demonstration purposes."""
        if tool_name == "transaction_analyzer":
            min_amount = params.get("min_amount", 0)
            
            # Mock transaction analysis
            return {
                "total_transactions": 20,
                "high_value_transactions": 5,
                "suspicious_patterns": [
                    {
                        "pattern": "circular_transfer",
                        "confidence": 0.85,
                        "transactions": ["0x123", "0x456"]
                    },
                    {
                        "pattern": "layering",
                        "confidence": 0.72,
                        "transactions": ["0x789", "0xabc"]
                    }
                ],
                "average_amount": 15000,
                "largest_amount": 50000
            }
        
        elif tool_name == "fetch_transaction":
            return {
                "transactions": [
                    {"id": "1", "amount": 1000, "sender": "0x123", "receiver": "0x456"},
                    {"id": "2", "amount": 2000, "sender": "0x789", "receiver": "0xabc"},
                    {"id": "3", "amount": 3000, "sender": "0xdef", "receiver": "0xghi"},
                    {"id": "4", "amount": 4000, "sender": "0xjkl", "receiver": "0xmnop"},
                    {"id": "5", "amount": 5000, "sender": "0xqrst", "receiver": "0xuvwxyz"}
                ]
            }
        
        elif tool_name == "risk_checker":
            # Mock risk checking
            return {
                "risk_level": "medium",
                "risk_factors": [
                    {"factor": "mixer_interaction", "score": 65},
                    {"factor": "high_value_transfers", "score": 40}
                ],
                "known_entities": [
                    {"address": "0xdef", "category": "exchange", "name": "Exchange X"},
                    {"address": "0xghi", "category": "mixer", "name": "Mixer Y"}
                ],
                "overall_score": 58
            }
        
        elif tool_name == "report_generator":
            include_evidence = params.get("include_evidence", False)
            
            # Mock report generation
            report = {
                "summary": "The address shows moderate risk patterns with some suspicious transactions.",
                "risk_assessment": "Medium risk due to mixer interactions and high-value transfers.",
                "recommendations": [
                    "Monitor for additional suspicious patterns",
                    "Investigate connections to known mixer addresses"
                ]
            }
            
            if include_evidence:
                report["evidence"] = [
                    {
                        "type": "transaction",
                        "description": "Large transfer to known mixer",
                        "data": {"tx_hash": "0x123", "amount": 25000}
                    },
                    {
                        "type": "pattern",
                        "description": "Circular transaction pattern detected",
                        "data": {"addresses": ["0xabc", "0xdef", "0xghi"]}
                    }
                ]
            
            return report
        
        else:
            return {
                "error": "Unknown tool",
                "message": f"Tool '{tool_name}' not supported in mock mode"
            }

    @timed_cache(timeout=60)
    def list_tools(self) -> list:
        """
        List available tools from the MCP API. Cached for 60 seconds.
        Returns:
            List of dicts, each with 'name', 'description', and 'parameters' (list of dicts with 'name' and 'type').
        """
        if self.use_mock:
            # Return a static mock list for testing
            return [
                {"name": "fetch_transaction", "description": "Fetch transaction data from the blockchain.", "parameters": [{"name": "limit", "type": "int"}]},
            ]
        try:
            response = self.client.get(f"{self.base_url}/tools")
            if response.status_code != 200:
                return {"error": f"API error: {response.status_code}", "message": response.text}
            return response.json().get("tools", [])
        except Exception as e:
            return {"error": f"MCP API call failed: {str(e)}"}
