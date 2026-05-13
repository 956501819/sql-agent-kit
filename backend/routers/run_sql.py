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


@router.post("/run-sql")
async def run_sql(req: RunSqlRequest):
    """直接执行用户提供的 SQL，返回数据 + 图表 JSON"""
    import pandas as pd
    from backend.services.agent_service import get_agent
    from sql_agent.multi.chart import _infer_chart_type, _build_figure

    agent = get_agent()

    # 直接执行 SQL
    success, data_or_error = agent._runner.run(req.sql)
    if not success:
        return JSONResponse(sanitize({
            "success": False,
            "sql": req.sql,
            "data": [],
            "chart": None,
            "error": data_or_error,
        }))
    data = data_or_error or []

    # 生成图表（纯规则推断，不依赖外部 hint）
    chart_obj = None
    if data:
        try:
            df = pd.DataFrame(data)
            chart_type = _infer_chart_type(df, req.intent)
            if chart_type != "table":
                import json
                chart_json = _build_figure(
                    df, chart_type,
                    title=req.intent or req.sql[:60],
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
