import httpx
from typing import Dict, Any, Optional, List
from ..utils.logging import log_agent_action

class RAGClient:
    """Client for retrieving relevant documents using the RAG API."""
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url 
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)
    
    def query(self, query_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query the RAG service for relevant documents.
        Args:
            query_payload: Dict with keys 'query' (str) and optional 'top_k' (int, default 5)
        Returns:
            Dict with 'matches' (list of document texts) or error info.
        """
        query = query_payload.get("query")
        top_k = query_payload.get("top_k", 5)
        if not query:
            return {"error": "Missing 'query' in payload"}
        try:

            response = self.client.post(
                f"{self.base_url}/query",
                json={"query": query, "top_k": top_k},
                headers={"accept": "application/json", "Content-Type": "application/json"}
            )
            if response.status_code != 200:
                return {
                    "error": f"API error: {response.status_code}",
                    "message": response.text
                }
            data = response.json()
            # Extract only document texts from matches
            matches = data.get("matches", [])
            formatted_matches = [match.get("document", "") for match in matches if match.get("document")]
            return {"matches": formatted_matches}
        except Exception as e:
            return {"error": f"RAG API call failed: {str(e)}"}
