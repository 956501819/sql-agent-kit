import os
import json
from fastapi import APIRouter, HTTPException

router = APIRouter()

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_LOG_PATH = os.path.join(_REPO_ROOT, "logs", "queries.jsonl")


def _read_records() -> list[dict]:
    if not os.path.exists(_LOG_PATH):
        return []
    records = []
    with open(_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def _write_records(records: list[dict]):
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    with open(_LOG_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


@router.get("/history")
async def get_history(keyword: str = "", page: int = 1, page_size: int = 20):
    records = _read_records()
    records.reverse()  # newest first

    if keyword:
        kw = keyword.lower()
        records = [
            r for r in records
            if kw in r.get("question", "").lower() or kw in r.get("sql", "").lower()
        ]

    total = len(records)
    start = (page - 1) * page_size
    page_records = records[start: start + page_size]

    return {"total": total, "records": page_records}


@router.delete("/history/{index}")
async def delete_history_record(index: int, keyword: str = ""):
    records = _read_records()
    records.reverse()  # newest first

    if keyword:
        kw = keyword.lower()
        filtered = [
            r for r in records
            if kw in r.get("question", "").lower() or kw in r.get("sql", "").lower()
        ]
    else:
        filtered = records

    if index < 0 or index >= len(filtered):
        raise HTTPException(status_code=404, detail="Record not found")

    # Use timestamp as unique key to find the exact record in the original list
    target_ts = filtered[index].get("ts")
    new_records = [r for r in records if r.get("ts") != target_ts]

    # Fallback: if no ts or duplicate ts, remove by position in filtered list
    if len(new_records) == len(records):
        target = filtered[index]
        removed = False
        new_records = []
        for r in records:
            if not removed and r == target:
                removed = True
                continue
            new_records.append(r)

    new_records.reverse()
    _write_records(new_records)
    return {"message": "已删除"}


@router.delete("/history")
async def clear_history():
    _write_records([])
    return {"message": "历史记录已清空"}
