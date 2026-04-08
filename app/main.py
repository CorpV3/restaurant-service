"""
Restaurant Service - Main application
"""
import mimetypes
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

# Register MIME types missing from Python's default mimetypes on Linux
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('image/avif', '.avif')
mimetypes.add_type('image/heic', '.heic')
from shared.config.settings import settings
from shared.utils.logger import setup_logger
from .database import init_db, close_db
from .routes import restaurants, menu_items, tables, feedback, orders, inventory, partners, system

# Setup logger
logger = setup_logger("restaurant-service", settings.log_level, settings.log_format)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Restaurant Service...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Restaurant Service...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Restaurant Management - Restaurant Service",
    description="Restaurant, Menu, Table, and Feedback Management Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploaded images
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include routers
app.include_router(
    restaurants.router,
    prefix="/api/v1/restaurants",
    tags=["Restaurants"]
)

app.include_router(
    menu_items.router,
    prefix="/api/v1/restaurants",
    tags=["Menu Items"]
)

app.include_router(
    tables.router,
    prefix="/api/v1/restaurants",
    tags=["Tables"]
)

app.include_router(
    feedback.router,
    prefix="/api/v1/restaurants",
    tags=["Feedback"]
)

app.include_router(
    orders.router,
    prefix="/api/v1",
    tags=["Orders"]
)

app.include_router(
    inventory.router,
    prefix="/api/v1/restaurants",
    tags=["Inventory"]
)

app.include_router(
    partners.router,
    prefix="/api/v1/partners",
    tags=["Partners"]
)

app.include_router(
    system.router,
    prefix="/api/v1/system",
    tags=["System"]
)


@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint"""
    return {
        "service": "Restaurant Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "restaurant-service"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.restaurant_service_port,
        reload=True if settings.environment == "development" else False,
        log_level=settings.log_level.lower()
    )
