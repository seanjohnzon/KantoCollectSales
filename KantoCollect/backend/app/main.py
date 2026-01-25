"""
Kanto Collect - Main FastAPI Application.

Entry point for the backend API server.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_db
from app.core.inventory_database import init_inventory_db
from app.core.whatnot_database import init_whatnot_db
from app.api.v1.router import api_router

# Static files directory (backend/app/main.py -> KantoCollect/apps/admin-dashboard)
STATIC_DIR = Path(__file__).parent.parent.parent / "apps" / "admin-dashboard"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    print(f"🚀 Starting {settings.app_name}...")
    await init_db()
    print("✅ Database initialized")
    init_inventory_db()
    print("✅ Inventory database initialized")
    init_whatnot_db()
    print("✅ WhatNot sales database initialized")

    yield
    
    # Shutdown
    print(f"👋 Shutting down {settings.app_name}...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Internal tools for collectibles business management",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8000",  # FastAPI server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "https://kantocollectsales-production.up.railway.app",  # Railway production
        "*",  # Allow all origins for API access
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "name": settings.app_name,
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/debug/paths")
async def debug_paths():
    """Debug endpoint to check file paths."""
    import os
    html_file = STATIC_DIR / "whatnot-sales" / "index.html"
    return {
        "static_dir": str(STATIC_DIR),
        "static_dir_exists": STATIC_DIR.exists(),
        "whatnot_html": str(html_file),
        "whatnot_html_exists": html_file.exists(),
        "cwd": os.getcwd(),
        "file_location": str(Path(__file__)),
        "static_dir_contents": os.listdir(str(STATIC_DIR)) if STATIC_DIR.exists() else "DIR NOT FOUND",
    }


# Admin Dashboard Routes
@app.get("/deal-analyzer")
async def deal_analyzer_ui():
    """Serve the Deal Analyzer UI."""
    html_file = STATIC_DIR / "deal-analyzer" / "index.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    return {"error": "UI not found"}


@app.get("/inventory")
async def inventory_ui():
    """Serve the Inventory Tool UI (placeholder)."""
    html_file = STATIC_DIR / "inventory-tool" / "index.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    return {"message": "Inventory Tool - Coming Soon"}


@app.get("/calendar")
async def calendar_ui():
    """Serve the Calendar & Tasks UI (placeholder)."""
    html_file = STATIC_DIR / "calendar-tasks" / "index.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    return {"message": "Calendar & Tasks - Coming Soon"}


@app.get("/whatnot-sales")
async def whatnot_sales_ui():
    """Serve the WhatNot Sales Tracker UI."""
    html_file = STATIC_DIR / "whatnot-sales" / "index.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    return {"message": "WhatNot Sales - Loading..."}


@app.get("/whatnot-sales/add-catalog-items")
async def add_catalog_items_ui():
    """Serve the Add Catalog Items helper tool."""
    html_file = STATIC_DIR / "whatnot-sales" / "add-catalog-items.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    return {"error": "Tool not found"}
