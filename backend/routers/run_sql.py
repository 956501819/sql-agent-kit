"""
直接执行原始 SQL 接口
用于前端 SQL 编辑后重新执行查询
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.utils import sanitize

router = APIRouter()


class RunSqlRequest(BaseModel):
    sql: str
    intent: str = ""        # 可选，用于图表生成时匹配 Y 轴
    chart_hint: dict = {}   # 可选，传入原始 chart_hint 保持图表类型一致


@router.post("/run-sql")
async def run_sql(req: RunSqlRequest):
    """直接执行用户提供的 SQL，返回数据 + 图表 JSON"""
    import pandas as pd
    from backend.services.agent_service import get_agent
    from sql_agent.multi.chart import _infer_chart_type, _build_figure

    agent = get_agent()

    # 直接执行 SQL
    try:
        rows = agent.db.execute(req.sql)
        if rows is None:
            rows = []
        data = [dict(r) for r in rows] if rows else []
    except Exception as e:
        return JSONResponse(sanitize({
            "success": False,
            "sql": req.sql,
            "data": [],
            "chart": None,
            "error": str(e),
        }))

    # 生成图表
    chart_obj = None
    if data:
        try:
            df = pd.DataFrame(data)
            hint = req.chart_hint or {}
            chart_type = _infer_chart_type(df, hint.get("type", ""))
            if chart_type != "table":
                import json
                from sql_agent.multi.chart import _parse_hint
                chart_json = _build_figure(
                    df, chart_type,
                    title=req.intent or req.sql[:60],
                    hint=_parse_hint(hint),
                    intent=req.intent,
                )
                if chart_json:
                    chart_obj = json.loads(chart_json)
        except Exception:
            pass

    return JSONResponse(sanitize({
        "success": True,
        "sql": req.sql,
        "data": data,
        "chart": chart_obj,
        "error": "",
    }))
