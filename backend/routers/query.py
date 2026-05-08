from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.utils import sanitize

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


@router.post("/query")
async def run_query(req: QueryRequest):
    from backend.services.agent_service import get_agent
    agent = get_agent()
    result = agent.query(req.question)

    if result.need_confirm:
        status = "need_confirm"
    elif result.success:
        status = "success"
    else:
        status = "failed"

    return JSONResponse(sanitize({
        "sql": result.sql or "",
        "success": result.success,
        "status": status,
        "confidence": result.confidence,
        "retry_count": result.retry_count,
        "data": result.data or [],
        "formatted_table": result.formatted_table or "",
        "error": result.error or "",
    }))
