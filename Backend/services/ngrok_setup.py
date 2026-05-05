"""
Ngrok Tunnel Setup for Development

In development mode, this automatically creates an ngrok tunnel
to allow Twilio to reach your local backend via a public URL.

In production, this is skipped and the configured URL is used directly.
"""

import logging
import json
from pathlib import Path
from typing import Optional

from config import get_config


logger = logging.getLogger(__name__)

# Path to store ngrok URL (shared between backend and worker)
NGROK_URL_FILE = Path(__file__).parent.parent / "ngrok_url.json"


async def setup_ngrok_tunnel() -> Optional[str]:
    """
    Setup ngrok tunnel if in development mode.
    
    Returns:
        Public ngrok URL if setup successful and in development mode, else None
    """
    settings = get_config()
    
    # Only setup tunnel in development mode
    if settings.mode.lower() != "development":
        logger.info("[NGROK] Production mode detected - skipping ngrok tunnel")
        return None
    
    # Check if ngrok auth token is configured
    if not settings.ngrok_auth_token:
        logger.warning("[NGROK] Development mode but NGROK_AUTH_TOKEN not set - skipping tunnel")
        return None
    
    try:
        from pyngrok import ngrok
        
        # Set auth token
        ngrok.set_auth_token(settings.ngrok_auth_token)
        logger.info("[NGROK] Auth token configured")
        
        # Try to connect with auto-update enabled
        try:
            public_url = ngrok.connect(8000, "http")
            
            # Extract the public URL
            tunnel_url = public_url.public_url if hasattr(public_url, 'public_url') else str(public_url)
            
            logger.info(f"[NGROK] Tunnel created successfully!")
            logger.info(f"[NGROK] Public URL: {tunnel_url}")
            logger.info(f"[NGROK] Twilio will use this URL for webhooks")
            
            return tunnel_url
        
        except Exception as connect_error:
            # Check if error is version-related
            error_str = str(connect_error)
            if "too old" in error_str or "ERR_NGROK_121" in error_str:
                logger.warning("[NGROK] Ngrok agent version too old - attempting auto-update...")
                try:
                    # Try to update ngrok binary
                    from pyngrok import installer
                    installer.install_ngrok()
                    logger.info("[NGROK] Ngrok binary updated successfully")
                    
                    # Retry connection after update
                    ngrok.kill()  # Kill old process
                    public_url = ngrok.connect(8000, "http")
                    tunnel_url = public_url.public_url if hasattr(public_url, 'public_url') else str(public_url)
                    
                    logger.info(f"[NGROK] Tunnel created after update: {tunnel_url}")
                    return tunnel_url
                
                except Exception as update_error:
                    logger.error(f"[NGROK] Auto-update failed: {update_error}")
                    logger.error("[NGROK] Please manually update ngrok: https://ngrok.com/download")
                    return None
            else:
                raise
    
    except ImportError:
        logger.error("[NGROK] pyngrok not installed - run: pip install pyngrok")
        return None
    except Exception as e:
        logger.error(f"[NGROK] Failed to setup tunnel: {e}", exc_info=False)
        logger.info("[NGROK] Proceeding with localhost URL (Twilio webhooks may not work)")
        return None


def save_ngrok_url(tunnel_url: Optional[str]) -> None:
    """
    Save ngrok URL to shared file for worker to read.
    
    Args:
        tunnel_url: The ngrok public URL to save
    """
    if not tunnel_url:
        return
    
    try:
        data = {"ngrok_url": tunnel_url, "timestamp": str(__import__('datetime').datetime.utcnow())}
        with open(NGROK_URL_FILE, "w") as f:
            json.dump(data, f)
        logger.info(f"[NGROK] URL saved to {NGROK_URL_FILE}")
    except Exception as e:
        logger.error(f"[NGROK] Failed to save URL to file: {e}")


def load_ngrok_url() -> Optional[str]:
    """
    Load ngrok URL from shared file (called by worker).
    
    Returns:
        The ngrok URL if available, else None
    """
    if not NGROK_URL_FILE.exists():
        return None
    
    try:
        with open(NGROK_URL_FILE, "r") as f:
            data = json.load(f)
        url = data.get("ngrok_url")
        if url:
            logger.info(f"[NGROK] Loaded tunnel URL from file: {url}")
        return url
    except Exception as e:
        logger.error(f"[NGROK] Failed to load URL from file: {e}")
        return None


def update_twilio_webhook_url(tunnel_url: Optional[str]) -> str:
    """
    Update Twilio webhook URL based on environment mode.
    
    Args:
        tunnel_url: Ngrok tunnel URL (if development)
        
    Returns:
        The final URL to use for Twilio webhooks
    """
    settings = get_config()
    
    if tunnel_url:
        logger.info(f"[NGROK] Using ngrok tunnel URL: {tunnel_url}")
        # Update the settings (for TwilioClient to pick up)
        settings.twilio_webhook_base_url = tunnel_url
        return tunnel_url
    else:
        logger.info(f"[NGROK] Using configured URL: {settings.twilio_webhook_base_url}")
        return settings.twilio_webhook_base_url


async def initialize_ngrok():
    """
    Main initialization function - call this at app startup.
    
    Returns:
        Final webhook URL to be used
    """
    logger.info(f"[NGROK] Initializing ngrok (MODE={get_config().mode})")
    
    tunnel_url = await setup_ngrok_tunnel()
    
    # Save URL to file for worker to read
    if tunnel_url:
        save_ngrok_url(tunnel_url)
    
    final_url = update_twilio_webhook_url(tunnel_url)
    
    return final_url
