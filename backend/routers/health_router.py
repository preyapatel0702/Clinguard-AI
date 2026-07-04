"""
health_router.py
----------------
FastAPI router for all Phase 10 /health/* endpoints.

Endpoints
---------
GET /health              — full system health report
GET /health/pipeline     — pipeline health
GET /health/storage      — persistence layer health
GET /health/models       — ML model availability
GET /health/system       — OS / resource health
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from backend.dependencies import get_health_service
from backend.services.system_health_service import SystemHealthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", summary="Full system health report")
def health_full(
    svc: SystemHealthService = Depends(get_health_service),
) -> Dict[str, Any]:
    """
    Return a comprehensive health report for all subsystems: pipeline,
    storage, ML models, and system resources.
    """
    logger.debug("GET /health")
    return svc.get_full_health().to_dict()


@router.get("/pipeline", summary="Pipeline health")
def health_pipeline(
    svc: SystemHealthService = Depends(get_health_service),
) -> Dict[str, Any]:
    """Return health status of the analytics pipeline."""
    logger.debug("GET /health/pipeline")
    return svc.check_pipeline().to_dict()


@router.get("/storage", summary="Persistence layer health")
def health_storage(
    svc: SystemHealthService = Depends(get_health_service),
) -> Dict[str, Any]:
    """Return health status of all persistence layers."""
    logger.debug("GET /health/storage")
    return svc.check_storage().to_dict()


@router.get("/models", summary="ML model availability")
def health_models(
    svc: SystemHealthService = Depends(get_health_service),
) -> Dict[str, Any]:
    """Return availability status of configured ML model files."""
    logger.debug("GET /health/models")
    return svc.check_models().to_dict()


@router.get("/system", summary="System resource health")
def health_system(
    svc: SystemHealthService = Depends(get_health_service),
) -> Dict[str, Any]:
    """Return CPU, memory, and disk resource health."""
    logger.debug("GET /health/system")
    return svc.check_system().to_dict()
