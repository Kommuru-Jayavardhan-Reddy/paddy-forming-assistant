"""
Paddy Farming Assistant - FastAPI Main Application Entrypoint
Initializes the FastAPI application, mounts CORS middleware, and registers routes.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import config
from app.exceptions import AppBaseException
from app.api.routes import router as api_router
from app.models.model_loader import ModelLoader

from app.models.multimodal_model import MultimodalModelLoader
from app.services.field_mapping import FieldMappingService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("paddy_backend")
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the server starts: loads the AI models and field mappings into memory
    so requests are fast and deterministic.
    """
    try:
        ModelLoader.get_model()
        logger.info("EfficientNet-B4 model warm-up complete.")
    except Exception as e:
        logger.error("EfficientNet-B4 model warm-up error: %s", e)

    try:
        MultimodalModelLoader.get_model()
        logger.info("Multimodal Cross-Attention model warm-up complete.")
    except Exception as e:
        logger.error("Multimodal model warm-up error: %s", e)

    try:
        FieldMappingService.get_instance().load()
        logger.info("FieldMappingService warm-up complete.")
    except Exception as e:
        logger.error("FieldMappingService warm-up error: %s", e)

    try:
        from app.services.shap_service import SHAPService
        SHAPService.get_instance()
        logger.info("SHAPService warm-up complete.")
    except Exception as e:
        logger.error("SHAPService warm-up error: %s", e)

    try:
        from app.db.session import init_db_engine, check_db_connectivity
        init_db_engine()
        db_check = await check_db_connectivity()
        if db_check.get("connected"):
            logger.info("Database connectivity check succeeded: db='%s', user='%s'.", db_check.get("database"), db_check.get("user"))
        else:
            logger.warning("Database connectivity check failed on startup [%s]: %s (Application will continue running)", db_check.get("error_type"), db_check.get("detail"))
    except Exception as e:
        logger.warning("Database engine initialization error on startup: %s (Application will continue running)", e)

    yield

    try:
        from app.db.session import close_db_engine
        await close_db_engine()
        logger.info("Database engine shutdown complete.")
    except Exception as e:
        logger.error("Error shutting down database engine: %s", e)


# Initialize FastAPI App
app = FastAPI(
    title=config.PROJECT_NAME,
    version=config.PROJECT_VERSION,
    description="Multimodal Paddy Disease Detection and Advisory Backend",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS Middleware (React + Vite frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(AppBaseException)
async def app_base_exception_handler(request: Request, exc: AppBaseException):
    logger.warning("Application error [%s] on %s: %s", exc.status_code, request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "detail": exc.message},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning("HTTP error [%s] on %s: %s", exc.status_code, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Request validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={"error": "ValidationError", "detail": "Invalid request parameters."},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "detail": "An internal server error occurred. Please contact the administrator.",
        },
    )


from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from app.api.auth import router as auth_router

# Register API Routers
app.include_router(api_router)
app.include_router(auth_router)

# Also mount un-prefixed /auth routes for direct access (e.g. POST /auth/forgot-password, /auth/verify-otp)
auth_direct_router = APIRouter(tags=["Authentication Direct Routes"])
for route in auth_router.routes:
    if hasattr(route, "path") and route.path.startswith("/api/v1/auth"):
        clean_path = route.path.replace("/api/v1/auth", "/auth")
        auth_direct_router.add_api_route(
            clean_path,
            route.endpoint,
            methods=route.methods,
            response_model=getattr(route, "response_model", None),
            status_code=getattr(route, "status_code", 200),
            summary=getattr(route, "summary", None),
            description=getattr(route, "description", None),
            include_in_schema=False,
        )
app.include_router(auth_direct_router)

# Mount Static Files (e.g. for Grad-CAM visualizations)
config.GRADCAM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")


@app.get("/", summary="Root Index", tags=["System"])
async def root():
    return {
        "project": config.PROJECT_NAME,
        "version": config.PROJECT_VERSION,
        "api_version": config.API_VERSION,
        "status": "ready",
        "docs": "/docs",
        "health": "/health",
        "health_model": "/health/model",
        "health_database": "/health/database",
        "classes": "/classes",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )