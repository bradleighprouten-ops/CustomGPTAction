"""
Test script to verify system components
Run this before starting the application
"""
import asyncio
from config import settings
from database import init_db, close_db
from qdrant_service import qdrant_service
from embeddings import embedding_service


async def test_database():
    """Test PostgreSQL connection and table creation"""
    print("\n🔍 Testing Database Connection...")
    try:
        await init_db()
        print("✅ Database connected and tables created")
        await close_db()
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def test_qdrant():
    """Test Qdrant connection and collection"""
    print("\n🔍 Testing Qdrant Connection...")
    try:
        collections = qdrant_service.client.get_collections()
        print(f"✅ Qdrant connected. Collections: {[c.name for c in collections.collections]}")
        
        # Verify our collection exists
        collection_names = [c.name for c in collections.collections]
        if settings.qdrant_collection in collection_names:
            print(f"✅ Collection '{settings.qdrant_collection}' exists")
        else:
            print(f"⚠️  Collection '{settings.qdrant_collection}' not found, will be created on first use")
        return True
    except Exception as e:
        print(f"❌ Qdrant error: {e}")
        return False


def test_embeddings():
    """Test Voyage AI embedding service"""
    print("\n🔍 Testing Voyage AI Embeddings...")
    try:
        test_text = "This is a test paragraph for embedding."
        embedding = embedding_service.embed_query(test_text)
        print(f"✅ Embeddings working. Dimension: {len(embedding)}")
        return True
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        return False


def test_config():
    """Test configuration and environment variables"""
    print("\n🔍 Testing Configuration...")
    
    checks = {
        "VOYAGE_API_KEY": bool(settings.voyage_api_key),
        "OPENAI_API_KEY": bool(settings.openai_api_key),
        "APP_API_KEY": bool(settings.app_api_key),
        "DATABASE_URL": bool(settings.database_url),
        "QDRANT_URL": bool(settings.qdrant_url),
    }
    
    all_passed = True
    for key, value in checks.items():
        status = "✅" if value else "❌"
        print(f"{status} {key}: {'Set' if value else 'Missing'}")
        if not value:
            all_passed = False
    
    return all_passed


async def main():
    """Run all tests"""
    print("=" * 60)
    print("RAG BACKEND SYSTEM TEST")
    print("=" * 60)
    
    results = {
        "Configuration": test_config(),
        "Database": await test_database(),
        "Qdrant": test_qdrant(),
        "Embeddings": test_embeddings()
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! System is ready.")
        print("\nTo start the application, run:")
        print("  python main.py")
        print("\nOr with uvicorn:")
        print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before starting.")
    
    return all_passed


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
