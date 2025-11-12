"""
Reranking Service using Voyage AI rerank-2.5-lite
Post-retrieval reranking to improve search results
"""
import voyageai
from typing import List, Dict
from config import settings


class RerankService:
    """Service for reranking search results"""
    
    def __init__(self):
        self.client = voyageai.Client(api_key=settings.voyage_api_key)
        self.model = settings.rerank_model
    
    def rerank(
        self,
        query: str,
        documents: List[Dict[str, any]],
        top_k: int = 3
    ) -> List[Dict[str, any]]:
        """
        Rerank documents based on query relevance
        
        Args:
            query: The search query
            documents: List of document dicts with 'text' field
            top_k: Number of top results to return (default 3)
        
        Returns:
            List of reranked documents with relevance scores
        """
        if not documents:
            return []
        
        # Extract texts for reranking
        texts = [doc["text"] for doc in documents]
        
        # Call Voyage AI rerank API
        reranking = self.client.rerank(
            query=query,
            documents=texts,
            model=self.model,
            top_k=top_k
        )
        
        # Map reranked results back to original documents
        reranked_results = []
        for result in reranking.results:
            # Get original document by index
            original_doc = documents[result.index].copy()
            # Add rerank score
            original_doc["rerank_score"] = result.relevance_score
            reranked_results.append(original_doc)
        
        return reranked_results


# Singleton instance
rerank_service = RerankService()
