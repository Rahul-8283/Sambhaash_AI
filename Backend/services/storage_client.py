"""
Supabase Storage Client
Handles file uploads, downloads, and management in Supabase Storage buckets
"""

from typing import Optional, List
import logging
from config import settings

logger = logging.getLogger(__name__)


class SupabaseStorageClient:
    """
    Supabase Storage client for managing document uploads.
    Uses the REST API approach with proper error handling.
    """
    
    def __init__(self, supabase_url: str, supabase_key: str, bucket_name: str):
        """
        Initialize storage client.
        
        Args:
            supabase_url: Supabase project URL (e.g., https://project.supabase.co)
            supabase_key: Supabase service role key (from settings)
            bucket_name: Storage bucket name (from settings)
        """
        self.supabase_url = supabase_url.rstrip('/')
        self.supabase_key = supabase_key
        self.bucket_name = bucket_name
        
        logger.info(f"[STORAGE] Initialized with bucket: {self.bucket_name}")
    
    async def upload_file(
        self,
        file_path: str,
        file_content: bytes,
        content_type: str = "application/octet-stream"
    ) -> dict:
        """
        Upload file to Supabase Storage.
        
        Args:
            file_path: Path in bucket (e.g., "documents/appendix_a.pdf")
            file_content: File bytes to upload
            content_type: MIME type of file
        
        Returns:
            Dict with file info including path and URL
        """
        import httpx
        
        try:
            # Build upload URL
            # Format: {supabase_url}/storage/v1/object/{bucket}/{path}
            upload_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{file_path}"
            
            # Prepare headers with authentication
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": content_type,
            }
            
            # Upload file using HTTP (async)
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    upload_url,
                    content=file_content,
                    headers=headers
                )
            
            if response.status_code not in [200, 201]:
                error_msg = response.text
                logger.error(f"[STORAGE] Upload failed ({response.status_code}): {error_msg}")
                raise Exception(f"Upload failed: {error_msg}")
            
            # Build public URL for retrieval
            public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"
            
            logger.info(f"[STORAGE] Successfully uploaded: {file_path}")
            
            return {
                "path": file_path,
                "bucket": self.bucket_name,
                "public_url": public_url,
                "status": "uploaded"
            }
        
        except Exception as e:
            logger.error(f"[STORAGE] Upload error: {e}")
            raise
    
    async def download_file(self, file_path: str) -> bytes:
        """
        Download file from Supabase Storage.
        
        Args:
            file_path: Path in bucket
        
        Returns:
            File bytes
        """
        import httpx
        
        try:
            download_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{file_path}"
            
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(download_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"[STORAGE] Download failed ({response.status_code})")
                raise Exception(f"Download failed: {response.text}")
            
            logger.info(f"[STORAGE] Downloaded: {file_path}")
            return response.content
        
        except Exception as e:
            logger.error(f"[STORAGE] Download error: {e}")
            raise
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from Supabase Storage.
        
        Args:
            file_path: Path in bucket
        
        Returns:
            True if deleted, False otherwise
        """
        import httpx
        
        try:
            delete_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{file_path}"
            
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.delete(delete_url, headers=headers)
            
            if response.status_code not in [200, 204]:
                logger.error(f"[STORAGE] Delete failed ({response.status_code})")
                return False
            
            logger.info(f"[STORAGE] Deleted: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"[STORAGE] Delete error: {e}")
            return False
    
    async def list_files(self, prefix: str = "") -> List[dict]:
        """
        List files in bucket with optional prefix.
        
        Args:
            prefix: Optional prefix filter (e.g., "documents/")
        
        Returns:
            List of file info dicts
        """
        import httpx
        
        try:
            list_url = f"{self.supabase_url}/storage/v1/object/list/{self.bucket_name}"
            
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
            }
            
            params = {}
            if prefix:
                params["prefix"] = prefix
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(list_url, headers=headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"[STORAGE] List failed ({response.status_code})")
                return []
            
            data = response.json()
            files = data.get("data", []) if data else []
            
            logger.info(f"[STORAGE] Listed {len(files)} files with prefix '{prefix}'")
            return files
        
        except Exception as e:
            logger.error(f"[STORAGE] List error: {e}")
            return []
    
    def get_file_url(self, file_path: str, expires_in_seconds: Optional[int] = None) -> str:
        """
        Get URL for a file in storage.
        
        Args:
            file_path: Path in bucket
            expires_in_seconds: Optional expiration time (for signed URLs)
        
        Returns:
            Public URL for the file
        """
        # For public URLs (public bucket)
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"
    
    async def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            file_path: Path in bucket
        
        Returns:
            True if exists, False otherwise
        """
        try:
            files = await self.list_files(prefix=file_path)
            return len(files) > 0
        except Exception as e:
            logger.error(f"[STORAGE] Exists check error: {e}")
            return False


# Global instance
_storage_client: Optional[SupabaseStorageClient] = None


async def get_storage_client() -> SupabaseStorageClient:
    """
    Get or create global storage client instance.
    Reads configuration from settings (config.py).
    """
    global _storage_client
    if _storage_client is None:
        supabase_url = settings.supabase_url
        supabase_key = settings.supabase_key
        bucket_name = settings.supabase_bucket_name
        
        if not supabase_url or not supabase_key or not bucket_name:
            raise Exception("SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_BUCKET_NAME must be set")
        
        _storage_client = SupabaseStorageClient(supabase_url, supabase_key, bucket_name)
        logger.info(f"[STORAGE] Storage client initialized with bucket: {bucket_name}")
    
    return _storage_client
