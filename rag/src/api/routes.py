"""
API module for the RAG application.
"""
import logging
from typing import Dict, List, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.scanner import DocumentScanner

logger = logging.getLogger(__name__)

# Initialize document scanner
document_scanner = DocumentScanner()

# Initialize FastAPI app
app = FastAPI(
    title="RAG Document Search API",
    description="API for searching documents using RAG technique",
    version="0.1.0",
)


class QueryRequest(BaseModel):
    """Query request model."""
    
    query: str = Field(..., description="The search query")
    top_k: int = Field(5, description="Number of results to return", ge=1, le=50)


class QueryResponse(BaseModel):
    """Query response model."""
    
    matches: List[Dict[str, Any]] = Field(..., description="Matched documents")


@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest) -> Dict[str, Any]:
    """Query for relevant documents."""
    try:
        results = document_scanner.query_documents(request.query, top_k=request.top_k)
        
        # Format results
        response = {
            "matches": []
        }
        
        for i in range(len(results["documents"][0])):
            match = {
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": results["distances"][0][i] if "distances" in results else None,
            }
            response["matches"].append(match)
        
        return response
    
    except Exception as e:
        logger.error(f"Error querying documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scan")
async def scan_documents(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Scan for new documents in the background."""
    background_tasks.add_task(document_scanner.scan_directory)
    return {"status": "Document scanning initiated in the background"}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
