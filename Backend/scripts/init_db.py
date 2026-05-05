"""
Database Initialization Script
Creates all tables in the database from SQLAlchemy models
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from sqlalchemy import text
from config import settings
from services.database.models import Base


async def init_database():
    """Initialize database by creating all tables"""
    
    print("🔧 Initializing Sambhaash AI Database...")
    
    # Get database URL and convert if needed
    database_url = settings.database_url
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"📡 Connecting to: {database_url}")
    
    # Connect to database
    conn = await asyncpg.connect(database_url)
    
    try:
        # Enable pgvector extension
        print("📦 Enabling pgvector extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("✅ pgvector extension enabled")
        
        print("\n📋 Creating tables from models...")
        
        # Create all tables using SQLAlchemy Base metadata
        from sqlalchemy import create_engine
        
        # Use synchronous engine for metadata operations
        engine = create_engine(
            database_url,
            echo=True,
            pool_pre_ping=True
        )
        
        Base.metadata.create_all(engine)
        engine.dispose()
        
        print("\n✅ All tables created successfully!")
        
        # Verify tables were created
        print("\n📊 Verifying tables...")
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """
        
        tables = await conn.fetch(tables_query)
        
        expected_tables = [
            "call_sessions",
            "documents",
            "knowledge_base",
            "lead_scores",
            "leads",
            "objections_log",
            "rm_assignments"
        ]
        
        created_tables = [row['table_name'] for row in tables]
        
        print("\n📝 Created Tables:")
        for table_name in created_tables:
            if table_name in expected_tables:
                print(f"  ✅ {table_name}")
        
        missing = set(expected_tables) - set(created_tables)
        if missing:
            print(f"\n⚠️  Missing tables: {missing}")
            return False
        
        print("\n✅ Database initialization complete!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {str(e)}")
        return False
    finally:
        await conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("SAMBHAASH AI - DATABASE INITIALIZATION")
    print("=" * 60)
    
    success = asyncio.run(init_database())
    
    if success:
        print("\n✅ Ready to use! Start the backend with: uvicorn main:app --reload")
        sys.exit(0)
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)
