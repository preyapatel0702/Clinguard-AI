import sys
import os
import logging
from fastapi import FastAPI


# Resolve backend module namespace when running inside or outside backend/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api.endpoints import router
from backend.api.chat_endpoints import router as chat_router
from backend.observability.middleware import LoggingMiddleware

# ---------------- Phase 10 ----------------
from backend.dependencies import get_analytics
from backend.middleware.analytics_middleware import AnalyticsMiddleware
from backend.middleware.observability import CorrelationIdMiddleware
from backend.routers.metrics_router import router as metrics_router
from backend.routers.health_router import router as health_router
# ------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s [%(correlation_id)s] %(message)s",
)

app = FastAPI(
    title="ClinGuard AI",
    description="Backend foundation for healthcare AI safety platform ClinGuard AI",
    version="0.3.0"
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# ---------------- Phase 10 middleware ----------------
# CorrelationId should be added before AnalyticsMiddleware
app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    AnalyticsMiddleware,
    analytics_service=get_analytics(),
    tracked_paths=("/analyze", "/pipeline"),
)

# Include API endpoints router
app.include_router(router)

# Chat compatibility endpoint (POST /chat/messages -> ClinGuardPipeline via /analyze contract)
app.include_router(chat_router)

# ---------------- Phase 10 routes ----------------
app.include_router(metrics_router)
app.include_router(health_router)

@app.get("/", tags=["root"])
def root():
    return {
        "service": "ClinGuard AI",
        "status": "operational",
        "phase": 10,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)