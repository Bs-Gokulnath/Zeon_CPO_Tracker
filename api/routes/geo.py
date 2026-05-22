from __future__ import annotations

from fastapi import APIRouter, Query

from api.dependencies import DB
from api.schemas.responses import NearbyResult
from api.services import geo_service as svc

router = APIRouter(prefix="/nearby", tags=["geo"])


@router.get("", response_model=list[NearbyResult])
async def nearby(
    session:      DB,
    lat:          float       = Query(..., ge=-90,  le=90),
    lon:          float       = Query(..., ge=-180, le=180),
    radius_km:    float       = Query(5.0, gt=0, le=100),
    charger_type: str | None  = Query(None),
    limit:        int         = Query(20, ge=1, le=100),
) -> list[NearbyResult]:
    return await svc.nearby_stations(session, lat, lon, radius_km, charger_type, limit)
