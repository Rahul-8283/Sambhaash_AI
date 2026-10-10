"""
Sambhaash AI - Main FastAPI Application
Entry point for the backend server
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from config import get_config
from services.database.supabase_client import get_db_client, close_db_client
from services.ngrok_setup import initialize_ngrok
from api.routes import lead_routes, rm_routes, admin_routes, kb_analytics_routes, call_routes, webhook_routes, whatsapp_routes, queue_routes, public_routes, summary_routes, call_recordings_routes

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== LIFESPAN CONTEXT ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Handles startup and shutdown events.
    """
    # STARTUP
    logger.info("[APP] Starting Sambhaash AI Backend...")
    
    try:
        # Initialize ngrok tunnel if in development mode
        logger.info("[APP] Setting up ngrok tunnel...")
        await initialize_ngrok()
    except Exception as e:
        logger.error(f"[APP] Ngrok setup error: {e}")
    
    try:
        db = await get_db_client()
        health = await db.health_check()
        if health:
            logger.info("[APP] Database connection successful")
        else:
            logger.warning("[APP] Database health check failed - running in degraded mode")
    except Exception as e:
        logger.warning(f"[APP] Database connection failed - running in degraded mode: {str(e)}")
    
    try:
        # Load the embedding model before the first call needs it
        from services.llm.embedder import EmbedderService
        await asyncio.to_thread(EmbedderService().warm_up)
    except Exception as e:
        logger.warning(f"[APP] Embedding model failed to load, KB retrieval will be unavailable: {e}")

    yield
    
    # SHUTDOWN
    logger.info("[APP] Shutting down Sambhaash AI Backend...")
    try:
        await close_db_client()
        logger.info("[APP] Database connection closed")
    except Exception as e:
        logger.error(f"[APP] Error during shutdown: {str(e)}")


# ==================== APPLICATION SETUP ====================

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    """
    config = get_config()
    
    app = FastAPI(
        title="Sambhaash AI",
        description="Voice Agent Backend for Partner Lead Conversion",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # ==================== MIDDLEWARE ====================
    
    config = get_config()

    # CORS Middleware: explicit origins only (credentials are not allowed with "*")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in config.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted Host Middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[h.strip() for h in config.trusted_hosts.split(",") if h.strip()]
    )
    
    # ==================== ROUTES ====================
    
    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "Sambhaash AI Backend",
            "version": "1.0.0"
        }
    
    # API Routes
    app.include_router(lead_routes.router)
    app.include_router(rm_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(kb_analytics_routes.router)
    app.include_router(call_routes.router)
    app.include_router(webhook_routes.router)
    app.include_router(whatsapp_routes.router)
    app.include_router(queue_routes.router)
    app.include_router(public_routes.router)
    app.include_router(summary_routes.router)
    app.include_router(call_recordings_routes.router)
    
    # ==================== ROOT ENDPOINT ====================
    
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API info"""
        return {
            "name": "Sambhaash AI",
            "description": "Voice Agent Backend for Partner Lead Conversion",
            "version": "1.0.0",
            "docs": "/docs",
            "endpoints": {
                "health": "/health",
                "leads": "/api/leads"
            }
        }
    
    # ==================== ERROR HANDLERS ====================
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle general exceptions"""
        # Log the real error server-side; never send exception text to the client
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
    
    logger.info("[APP] FastAPI application created successfully")
    return app


# ==================== APPLICATION INSTANCE ====================

app = create_app()


# ==================== MAIN ====================

if __name__ == "__main__":
    config = get_config()
    
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )
