import os
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_TABLES_PATH = os.path.join(_REPO_ROOT, "data", "tables.yaml")


@router.get("/tables")
async def get_tables():
    if not os.path.exists(_TABLES_PATH):
        return {"tables": []}
    with open(_TABLES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {"tables": data.get("allowed_tables", [])}


class TablesPayload(BaseModel):
    tables: list[str]


@router.post("/tables")
async def save_tables(payload: TablesPayload):
    from backend.services.agent_service import reset_agent
    with open(_TABLES_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"allowed_tables": payload.tables}, f, allow_unicode=True)
    reset_agent()
    return {"message": "白名单已保存"}
