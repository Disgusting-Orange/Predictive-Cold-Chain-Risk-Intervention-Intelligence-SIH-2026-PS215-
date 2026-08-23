from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Literal

from app.services.demo_loop import get_demo_status, set_demo_mode

router = APIRouter(prefix="/demo", tags=["Demo Control"])


class DemoScenarioRequest(BaseModel):
    mode: Literal["normal", "combined_failure"] = Field(..., description="normal resets the fleet; combined_failure escalates SHP-1042")


@router.get("/status")
async def demo_status():
    return get_demo_status()


@router.post("/scenario")
async def apply_demo_scenario(body: DemoScenarioRequest):
    return await set_demo_mode(body.mode)
