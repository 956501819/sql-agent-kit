import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_FEWSHOT_PATH = os.path.join(_REPO_ROOT, "data", "fewshot.json")


def _get_store():
    from sql_agent.fewshot.store import FewShotStore
    return FewShotStore(_FEWSHOT_PATH)


@router.get("/fewshot")
async def list_fewshot():
    store = _get_store()
    items = store.list_all()
    return {"items": [{"id": i, **item} for i, item in enumerate(items)]}


class FewShotItem(BaseModel):
    question: str
    sql: str


@router.post("/fewshot")
async def add_fewshot(item: FewShotItem):
    store = _get_store()
    store.add(question=item.question, sql=item.sql)
    items = store.list_all()
    return {"message": "已添加", "id": len(items) - 1}


@router.delete("/fewshot/{index}")
async def delete_fewshot(index: int):
    store = _get_store()
    items = store.list_all()
    if index < 0 or index >= len(items):
        raise HTTPException(status_code=404, detail="示例不存在")
    store.remove(index)
    return {"message": "已删除"}
