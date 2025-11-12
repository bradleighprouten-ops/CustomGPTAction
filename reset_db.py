"""
Reset database tables
Drops all tables and recreates them with correct schema
"""
import asyncio
from database import engine, Base


async def reset_database():
    """Drop all tables and recreate them"""
    print("🗑️  Dropping existing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✅ Tables dropped")
    
    print("🔨 Creating tables with correct schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_database())
    print("\n✅ Database reset complete!")
