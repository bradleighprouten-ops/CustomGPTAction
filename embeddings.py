"""
Embedding Service using Voyage AI
Embeds paragraphs with voyage-3-large model
"""
import voyageai
from typing import List
from config import settings


class EmbeddingService:
    """Service for generating embeddings using Voyage AI"""
    
    def __init__(self):
        self.client = voyageai.Client(api_key=settings.voyage_api_key)
        self.model = settings.embedding_model
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts at once
        Returns list of embedding vectors
        """
        if not texts:
            return []
        
        # Voyage AI supports batch embedding
        result = self.client.embed(
            texts=texts,
            model=self.model,
            input_type="document"  # For indexing documents
        )
        
        return result.embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query text
        Uses input_type='query' for search optimization
        """
        result = self.client.embed(
            texts=[query],
            model=self.model,
            input_type="query"  # For search queries
        )
        
        return result.embeddings[0]


# Singleton instance
embedding_service = EmbeddingService()
