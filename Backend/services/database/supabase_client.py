"""
Supabase Database Client
Handles async connections to Supabase PostgreSQL + pgvector
"""

import os
from typing import Any, Dict, List, Optional
import asyncpg
from contextlib import asynccontextmanager
import logging
from config import settings

logger = logging.getLogger(__name__)


def _parse_database_url(url: str) -> str:
    """
    Convert SQLAlchemy format to asyncpg format.
    
    SQLAlchemy: postgresql+asyncpg://user:password@host:port/database
    asyncpg:    postgresql://user:password@host:port/database
    
    Args:
        url: Database URL (either format)
    
    Returns:
        URL in asyncpg format
    """
    if url.startswith("postgresql+asyncpg://"):
        # SQLAlchemy format - convert to asyncpg
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


class SupabaseClientError(Exception):
    """Custom exception for Supabase client errors"""
    pass


class SupabaseClient:
    """
    Async Supabase PostgreSQL client with connection pooling.
    
    Handles:
    - Connection lifecycle management
    - Query execution with error handling
    - Connection pooling
    - Health checks
    """
    
    def __init__(
        self,
        database_url: str,
        min_size: int = 5,
        max_size: int = 20,
    ):
        """
        Initialize Supabase client.
        
        Args:
            database_url: Full PostgreSQL connection URL from Supabase
                         Format: postgresql://user:password@host:port/database
                         OR:     postgresql+asyncpg://user:password@host:port/database (SQLAlchemy)
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        self.database_url = _parse_database_url(database_url)
        self.min_size = min_size
        self.max_size = max_size
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """
        Initialize connection pool.
        
        Raises:
            SupabaseClientError: If connection fails
        """
        try:
            logger.info("Connecting to Supabase...")
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_size,
                max_size=self.max_size,
            )
            logger.info("✅ Supabase connection pool initialized")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Supabase: {str(e)}")
            raise SupabaseClientError(f"Connection failed: {str(e)}")
    
    async def disconnect(self) -> None:
        """
        Close connection pool.
        """
        if self.pool:
            await self.pool.close()
            logger.info("✅ Supabase connection pool closed")
    
    async def health_check(self) -> bool:
        """
        Check database connectivity.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            if not self.pool:
                return False
            
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def execute_query(
        self,
        query: str,
        params: tuple = (),
    ) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results.
        
        Args:
            query: SQL query with $1, $2, etc. placeholders
            params: Query parameters
        
        Returns:
            List of rows as dictionaries
            
        Raises:
            SupabaseClientError: If query fails
        """
        if not self.pool:
            raise SupabaseClientError("Connection pool not initialized. Call connect() first.")
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except asyncpg.PostgresError as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise SupabaseClientError(f"Query failed: {str(e)}")
    
    async def execute_update(
        self,
        query: str,
        params: tuple = (),
    ) -> int:
        """
        Execute INSERT/UPDATE/DELETE query.
        
        Args:
            query: SQL query with $1, $2, etc. placeholders
            params: Query parameters
        
        Returns:
            Number of affected rows
            
        Raises:
            SupabaseClientError: If query fails
        """
        if not self.pool:
            raise SupabaseClientError("Connection pool not initialized. Call connect() first.")
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *params)
                # result is a string like "INSERT 0 1" or "UPDATE 3"
                affected = int(result.split()[-1]) if result else 0
                return affected
        except asyncpg.PostgresError as e:
            logger.error(f"Update execution failed: {str(e)}")
            raise SupabaseClientError(f"Update failed: {str(e)}")
    
    async def execute_insert_returning(
        self,
        query: str,
        params: tuple = (),
    ) -> Dict[str, Any]:
        """
        Execute INSERT query with RETURNING clause.
        
        Args:
            query: SQL INSERT query with RETURNING clause
            params: Query parameters
        
        Returns:
            First row as dictionary
            
        Raises:
            SupabaseClientError: If query fails
        """
        if not self.pool:
            raise SupabaseClientError("Connection pool not initialized. Call connect() first.")
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)
                if row:
                    return dict(row)
                return {}
        except asyncpg.PostgresError as e:
            logger.error(f"Insert returning failed: {str(e)}")
            raise SupabaseClientError(f"Insert failed: {str(e)}")
    
    async def execute_fetchone(
        self,
        query: str,
        params: tuple = (),
    ) -> Optional[Dict[str, Any]]:
        """
        Execute query and return single row.
        
        Args:
            query: SQL query
            params: Query parameters
        
        Returns:
            Single row as dictionary or None
            
        Raises:
            SupabaseClientError: If query fails
        """
        if not self.pool:
            raise SupabaseClientError("Connection pool not initialized. Call connect() first.")
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)
                if row:
                    return dict(row)
                return None
        except asyncpg.PostgresError as e:
            logger.error(f"Fetchone failed: {str(e)}")
            raise SupabaseClientError(f"Fetchone failed: {str(e)}")
    
    async def execute_fetchval(
        self,
        query: str,
        params: tuple = (),
    ) -> Any:
        """
        Execute query and return single value.
        
        Args:
            query: SQL query
            params: Query parameters
        
        Returns:
            Single value
            
        Raises:
            SupabaseClientError: If query fails
        """
        if not self.pool:
            raise SupabaseClientError("Connection pool not initialized. Call connect() first.")
        
        try:
            async with self.pool.acquire() as conn:
                value = await conn.fetchval(query, *params)
                return value
        except asyncpg.PostgresError as e:
            logger.error(f"Fetchval failed: {str(e)}")
            raise SupabaseClientError(f"Fetchval failed: {str(e)}")
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.
        
        Usage:
            async with client.transaction():
                await client.execute_update(...)
                await client.execute_update(...)
        """
        if not self.pool:
            raise SupabaseClientError("Connection pool not initialized. Call connect() first.")
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# Global instance
_client: Optional[SupabaseClient] = None


async def get_db_client() -> SupabaseClient:
    """
    Get or create global database client instance.
    """
    global _client
    if _client is None:
        database_url = settings.database_url
        if not database_url:
            raise SupabaseClientError("DATABASE_URL not set in environment variables")
        
        _client = SupabaseClient(database_url)
        await _client.connect()
    
    return _client


async def close_db_client() -> None:
    """
    Close global database client.
    """
    global _client
    if _client:
        await _client.disconnect()
        _client = None
