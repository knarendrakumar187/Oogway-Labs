import time
import logging
import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import init_db
from backend.app.services.rag import rag_service
from backend.app.api.endpoints import router as api_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lenny_assistant")

app = FastAPI(
    title="The Lenny Growth Assistant",
    description="Grounded AI Advisor for Product Managers & Growth Practitioners built exclusively on Lenny's Podcast transcripts.",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request latency & logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        "HTTP %s %s -> %d (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        process_time_ms
    )
    response.headers["X-Process-Time-Ms"] = str(process_time_ms)
    return response

# Global structured error handler (No bare 500s)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled Exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "code": "INTERNAL_SERVER_ERROR",
            "troubleshooting": "Please check backend logs or verify that data/chunks.json exists."
        }
    )

# Include API router under both /api and root for maximum flexibility
app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(api_router, tags=["Root API"])

@app.on_event("startup")
def on_startup():
    logger.info("Starting up Lenny Growth Assistant backend...")
    init_db()
    # Preload RAG index
    try:
        rag_service.initialize()
    except Exception as e:
        logger.error("Error preloading RAG service on startup: %s", e)

# Mount frontend directory for static serving
FRONTEND_DIR = os.path.join(settings.BASE_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    logger.info("Frontend mounted from %s at root /", FRONTEND_DIR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
