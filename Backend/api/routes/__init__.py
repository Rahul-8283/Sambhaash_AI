"""
API Routes Package
Imports all route modules
"""

from . import lead_routes
from . import rm_routes
from . import admin_routes
from . import kb_analytics_routes
from . import whatsapp_routes

__all__ = ["lead_routes", "rm_routes", "admin_routes", "kb_analytics_routes", "whatsapp_routes"]
