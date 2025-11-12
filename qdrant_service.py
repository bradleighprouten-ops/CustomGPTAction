"""
Qdrant Vector Database Client
Handles storage and retrieval of embedded paragraphs
"""
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from config import settings
import uuid


class QdrantService:
    """Service for interacting with Qdrant vector database"""
    
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE
                )
            )
    
    def index_paragraphs(self, paragraphs: List[Dict[str, any]], embeddings: List[List[float]]):
        """
        Index paragraphs with their embeddings in Qdrant
        Each paragraph has: text, report_id, section, report_type, page_number
        """
        points = []
        
        for paragraph, embedding in zip(paragraphs, embeddings):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "text": paragraph["text"],
                    "report_id": paragraph["report_id"],
                    "section": paragraph["section"],
                    "report_type": paragraph["report_type"],
                    "page_number": paragraph["page_number"]
                }
            )
            points.append(point)
        
        # Batch upload
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 6,
        report_type: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Search for similar paragraphs using cosine similarity
        Optionally filter by report_type
        Returns list of results with text, metadata, and score
        """
        search_filter = None
        if report_type:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="report_type",
                        match=MatchValue(value=report_type)
                    )
                ]
            )
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=search_filter
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "text": result.payload["text"],
                "report_id": result.payload["report_id"],
                "section": result.payload["section"],
                "report_type": result.payload["report_type"],
                "page_number": result.payload["page_number"],
                "score": result.score
            })
        
        return formatted_results
    
    def delete_by_report_id(self, report_id: str):
        """Delete all paragraphs belonging to a specific report"""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="report_id",
                        match=MatchValue(value=report_id)
                    )
                ]
            )
        )


# Singleton instance
qdrant_service = QdrantService()
