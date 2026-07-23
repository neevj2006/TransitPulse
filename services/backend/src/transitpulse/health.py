from typing import Protocol

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from transitpulse import __version__

router = APIRouter()


class Probe(Protocol):
    name: str

    async def check(self) -> None: ...

    async def close(self) -> None: ...


class Liveness(BaseModel):
    service: str = "transitpulse-backend"
    status: str = "live"


@router.get("/health/live", response_model=Liveness)
async def live() -> Liveness:
    return Liveness()


@router.get("/health/ready")
async def ready(request: Request) -> JSONResponse:
    probes: list[Probe] = request.app.state.probes
    checks: dict[str, str] = {}

    for probe in probes:
        try:
            await probe.check()
            checks[probe.name] = "ready"
        except Exception:
            checks[probe.name] = "unavailable"

    is_ready = bool(probes) and all(value == "ready" for value in checks.values())
    return JSONResponse(
        content={"checks": checks, "status": "ready" if is_ready else "not_ready"},
        status_code=status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@router.get("/version")
async def version(request: Request) -> dict[str, str]:
    return {
        "environment": request.app.state.settings.environment,
        "service": "transitpulse-backend",
        "version": __version__,
    }
