from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.utils import sanitize

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


@router.post("/query")
async def run_query(req: QueryRequest):
    import json
    import pandas as pd
    from backend.services.agent_service import get_agent
    from sql_agent.multi.chart import _infer_chart_type, _build_figure, _parse_hint

    agent = get_agent()
    result = agent.query(req.question)

    if result.need_confirm:
        status = "need_confirm"
    elif result.success:
        status = "success"
    else:
        status = "failed"

    # 生成图表
    chart_obj = None
    chart_hint = {}
    if result.success and result.data:
        try:
            df = pd.DataFrame(result.data)
            chart_type = _infer_chart_type(df, "")
            if chart_type != "table":
                hint = _parse_hint({})
                chart_json = _build_figure(
                    df, chart_type,
                    title=req.question,
                    hint=hint,
                    intent=req.question,
                )
                if chart_json:
                    chart_obj = json.loads(chart_json)
                    chart_hint = {"type": chart_type}
        except Exception:
            pass

    return JSONResponse(sanitize({
        "sql": result.sql or "",
        "success": result.success,
        "status": status,
        "confidence": result.confidence,
        "retry_count": result.retry_count,
        "data": result.data or [],
        "formatted_table": result.formatted_table or "",
        "error": result.error or "",
        "chart": chart_obj,
        "chart_hint": chart_hint,
    }))
