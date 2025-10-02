from fastapi import APIRouter
from routers.api.v1 import event, routine, series, team, match

api_v1_router = APIRouter(prefix="/api/v1", tags=["v1"])

api_v1_router.include_router(event.router, prefix="/event", tags=["event"]) # events
api_v1_router.include_router(series.router, prefix="/series", tags=["series"]) # series
api_v1_router.include_router(team.router, prefix="/team", tags=["team"]) # team
api_v1_router.include_router(match.router, prefix="/match", tags=["match"]) # match

api_v1_router.include_router(routine.router, prefix="/routine", tags=["routine"]) # routines
