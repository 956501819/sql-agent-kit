"""
Chart Agent — 根据查询结果自动选图表并生成 plotly JSON
规则层优先，Planner chart_hint 次之，兜底为 table（不生成图）
"""

from .state import GraphState


def _infer_chart_type(df, chart_hint: str) -> str:
    """根据 DataFrame 列类型和 Planner hint 推断图表类型"""
    # Planner 已给出明确 hint 且不是 table，优先使用
    if chart_hint and chart_hint != "table":
        return chart_hint

    if df is None or df.empty:
        return "table"

    import pandas as pd

    cols = df.columns.tolist()

    if not cols:
        return "table"

    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    time_cols = [c for c in cols if pd.api.types.is_datetime64_any_dtype(df[c])
                 or any(kw in c.lower() for kw in ["date", "time", "month", "year", "day", "日", "月", "年"])]
    cat_cols = [c for c in cols if c not in numeric_cols and c not in time_cols]

    if time_cols and numeric_cols:
        return "line"
    if cat_cols and len(numeric_cols) == 1:
        return "bar"
    if cat_cols and len(numeric_cols) == 1 and len(df) <= 8:
        return "pie"
    if len(numeric_cols) == 2 and not cat_cols:
        return "scatter"
    if len(numeric_cols) >= 1:
        return "bar"

    return "table"


def _build_figure(df, chart_type: str, title: str) -> str:
    """用 plotly.express 生成图表 JSON"""
    import plotly.express as px
    import pandas as pd

    cols = df.columns.tolist()
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in cols if c not in numeric_cols]
    time_cols = [c for c in cols if any(kw in c.lower()
                  for kw in ["date", "time", "month", "year", "day", "日", "月", "年"])]

    x_col = time_cols[0] if time_cols else (cat_cols[0] if cat_cols else cols[0])
    y_col = numeric_cols[0] if numeric_cols else cols[-1]

    try:
        if chart_type == "line":
            fig = px.line(df, x=x_col, y=y_col, title=title, markers=True)
        elif chart_type == "bar":
            fig = px.bar(df, x=x_col, y=y_col, title=title)
        elif chart_type == "pie":
            fig = px.pie(df, names=x_col, values=y_col, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=cols[0], y=cols[1], title=title)
        else:
            return ""

        fig.update_layout(
            font=dict(family="Microsoft YaHei, Arial, sans-serif"),
            margin=dict(l=40, r=40, t=60, b=40),
        )
        return fig.to_json()

    except Exception:
        return ""


def chart_node(state: GraphState) -> GraphState:
    """Chart Agent 节点：自动选图表类型并生成 plotly JSON"""
    import pandas as pd

    sql_results = state.get("sql_results", [])
    chart_hint = state.get("chart_hint", "table")
    intent = state.get("intent", state.get("question", ""))
    log = list(state.get("process_log") or [])
    log.append("📊 [Chart Agent] 正在判断图表类型...")

    target = None
    for r in sql_results:
        if r.get("success") and r.get("data"):
            target = r
            break

    if not target:
        log.append("   ⚠️ 无有效数据，跳过图表生成")
        return {**state, "chart_json": "", "process_log": log}

    try:
        df = pd.DataFrame(target["data"])
        if df.empty:
            log.append("   ⚠️ 数据为空，跳过图表生成")
            return {**state, "chart_json": "", "process_log": log}

        chart_type = _infer_chart_type(df, chart_hint)

        if chart_type == "table":
            log.append(f"   📋 判断结果：纯表格展示（数据列：{list(df.columns)}）")
            return {**state, "chart_json": "", "process_log": log}

        chart_json = _build_figure(df, chart_type, title=intent)
        source = "Planner 建议" if (chart_hint and chart_hint != "table") else "规则推断"
        log.append(
            f"   ✅ 图表类型：{chart_type}（{source}）\n"
            f"   数据：{len(df)} 行 × {len(df.columns)} 列，X轴列：{list(df.columns)[0]}"
        )
        return {**state, "chart_json": chart_json, "process_log": log}

    except Exception as e:
        log.append(f"   ❌ 图表生成失败：{e}")
        return {**state, "chart_json": "", "error": state.get("error") or f"Chart 生成失败: {e}", "process_log": log}
