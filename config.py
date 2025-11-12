"""
Configuration management for RAG Backend Application
Loads environment variables and provides app-wide settings
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    voyage_api_key: str = os.getenv("VOYAGE_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    app_api_key: str = os.getenv("APP_API_KEY", "")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # Qdrant
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "report-paragraphs")
    
    # Embedding
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "voyage-3-large")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
    
    # Reranking
    rerank_model: str = os.getenv("RERANK_MODEL", "rerank-2.5-lite")
    
    # Search
    initial_retrieval_count: int = 6
    final_results_count: int = 3
    
    # Upload
    upload_dir: str = "uploads"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    
    class Config:
        env_file = ".env"


settings = Settings()
