"""
Database models and connection management
Tables: Upload, UploadError
"""
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from config import settings

Base = declarative_base()


class Upload(Base):
    """Tracks PDF file uploads and processing status"""
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255), nullable=False)
    topic = Column(String(100), nullable=False)  # Report type: building movement, retaining wall, etc
    status = Column(String(20), default="pending")  # pending, processing, success, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to errors
    errors = relationship("UploadError", back_populates="upload", cascade="all, delete-orphan")


class UploadError(Base):
    """Tracks errors during processing pipeline"""
    __tablename__ = "upload_errors"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(50), nullable=False)  # parsing, embedding, qdrant
    message = Column(Text, nullable=False)  # Error message
    details = Column(Text, nullable=True)  # Additional error details (stack trace, etc)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to upload
    upload = relationship("Upload", back_populates="errors")


# Async engine and session
engine = create_async_engine(
    settings.database_url,
    echo=True,
    future=True
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database sessions"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await engine.dispose()
