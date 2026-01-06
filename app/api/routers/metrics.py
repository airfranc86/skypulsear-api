"""Router para exponer métricas de Prometheus."""

from fastapi import APIRouter
from fastapi.responses import Response

from app.utils.metrics import get_metrics

router = APIRouter()


@router.get("/metrics")
async def metrics() -> Response:
    """
    Endpoint para exponer métricas en formato Prometheus.

    Returns:
        Response con métricas en formato Prometheus
    """
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain; version=0.0.4")
