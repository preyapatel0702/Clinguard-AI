import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

# Setup standard logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clinguard.observability")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        process_time_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Time: {process_time_ms:.2f}ms"
        )
        
        return response
