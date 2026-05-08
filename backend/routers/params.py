import os
import yaml
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SETTINGS_PATH = os.path.join(_REPO_ROOT, "config", "settings.yaml")


def _read_settings() -> dict:
    if not os.path.exists(_SETTINGS_PATH):
        return {}
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError:
        return {}


def _write_settings(settings: dict):
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        yaml.dump(settings, f, allow_unicode=True)


@router.get("/params")
async def get_params():
    s = _read_settings()
    agent = s.get("agent", {})
    executor = s.get("executor", {})
    return {
        "max_retry": agent.get("max_retry", 3),
        "confidence_threshold": agent.get("confidence_threshold", 0.6),
        "max_tables_in_prompt": agent.get("max_tables_in_prompt", 10),
        "query_timeout": executor.get("query_timeout", 30),
        "max_rows": executor.get("max_rows", 500),
    }


class ParamsPayload(BaseModel):
    max_retry: int = 3
    confidence_threshold: float = 0.6
    max_tables_in_prompt: int = 10
    query_timeout: int = 30
    max_rows: int = 500


@router.post("/params")
async def save_params(payload: ParamsPayload):
    from backend.services.agent_service import reset_agent
    s = _read_settings()
    s.setdefault("agent", {})
    s.setdefault("executor", {})
    s["agent"]["max_retry"] = payload.max_retry
    s["agent"]["confidence_threshold"] = payload.confidence_threshold
    s["agent"]["max_tables_in_prompt"] = payload.max_tables_in_prompt
    s["executor"]["query_timeout"] = payload.query_timeout
    s["executor"]["max_rows"] = payload.max_rows
    _write_settings(s)
    reset_agent()
    return {"message": "参数已保存"}
