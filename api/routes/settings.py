"""
Runtime LLM settings, readable/writable from the frontend's Settings
panel. The API key is write-only through this API — GET never returns
it, only whether one is currently configured.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import config

router = APIRouter()


class LLMSettingsUpdate(BaseModel):
    provider: str
    api_key: str | None = None
    model: str | None = None


@router.get("/")
async def get_settings():
    return config.status()


@router.post("/")
async def update_settings(settings: LLMSettingsUpdate):
    if settings.provider not in config.SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"provider must be one of {config.SUPPORTED_PROVIDERS}",
        )
    config.set_llm_config(settings.provider, settings.api_key, settings.model)
    return config.status()
