"""
Chart Agent — 根据查询结果自动选图表并生成 plotly JSON
Planner 输出结构化 chart_hint（type/x/y/y2/sort/label），Chart Agent 优先按指令画图，
无指令时回退到规则推断。
"""

from .state import GraphState


def _parse_hint(chart_hint) -> dict:
    """统一 chart_hint 格式，兼容旧版字符串和新版 dict。"""
    if isinstance(chart_hint, dict):
        return chart_hint
    return {"type": chart_hint or "table", "x": "", "y": "", "y2": "", "sort": "none", "label": False}


def _resolve_col(hint_col: str, candidates: list, df) -> str:
    """将 hint 中的列名映射到 df 实际列名（大小写不敏感，找不到返回空）。"""
    if not hint_col:
        return ""
    cols_lower = {c.lower(): c for c in df.columns}
    return cols_lower.get(hint_col.lower(), "")


def _infer_chart_type(df, hint_type: str) -> str:
    """根据 DataFrame 列类型推断图表类型（仅在 hint_type 为空或 table 时触发）。"""
    if hint_type and hint_type != "table":
        return hint_type

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
    effective_time_cols = [c for c in time_cols if df[c].nunique() > 1]

    if effective_time_cols and numeric_cols:
        return "area" if cat_cols else "line"
    if len(cat_cols) >= 2 and len(numeric_cols) == 1:
        return "heatmap"
    if cat_cols and len(numeric_cols) == 1:
        if len(df) <= 6:
            return "pie"
        col_text = " ".join(cols).lower()
        if any(kw in col_text for kw in ["funnel", "stage", "step", "转化", "漏斗", "步骤"]):
            return "funnel"
        return "bar"
    if time_cols and cat_cols and numeric_cols:
        return "bar_stack"
    if len(numeric_cols) >= 2 and cat_cols:
        return "bar_stack"
    if len(numeric_cols) == 2 and not cat_cols:
        return "scatter"
    if numeric_cols:
        return "bar"
    return "table"


def _pick_y_col(numeric_cols: list, intent: str) -> str:
    """从多个数值列中选出最合适的 Y 轴列（无 hint 时的兜底逻辑）。"""
    if not numeric_cols:
        return ""
    if len(numeric_cols) == 1:
        return numeric_cols[0]

    import re
    intent_lower = (intent or "").lower()
    intent_tokens = [t for t in re.split(r'[\s,，。？?、/\\]+', intent_lower) if len(t) >= 2]
    for col in reversed(numeric_cols):
        col_lower = col.lower()
        if any(tok in col_lower or col_lower in tok for tok in intent_tokens):
            return col

    derived_kws = ["roi", "rate", "ratio", "growth", "pct", "percent",
                   "比", "率", "增长", "占比", "转化", "利润", "毛利", "净"]
    for col in reversed(numeric_cols):
        if any(kw in col.lower() for kw in derived_kws):
            return col

    return numeric_cols[-1]


def _build_figure(df, chart_type: str, title: str, hint: dict, intent: str = "") -> str:
    """用 plotly.express / plotly.graph_objects 生成图表 JSON。
    hint 字段：type / x / y / y2 / sort / label
    出错时抛出异常，由调用方记录日志。
    """
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd

    cols = df.columns.tolist()
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    time_cols = [c for c in cols if any(kw in c.lower()
                  for kw in ["date", "time", "month", "year", "day", "日", "月", "年"])]
    cat_cols = [c for c in cols if c not in numeric_cols and c not in time_cols]
    effective_time_cols = [c for c in time_cols if df[c].nunique() > 1]

    hint_x = _resolve_col(hint.get("x", ""), cols, df)
    hint_y = _resolve_col(hint.get("y", ""), cols, df)
    hint_y2 = _resolve_col(hint.get("y2", ""), cols, df)
    show_label = hint.get("label", False)
    sort_order = hint.get("sort", "none")

    # y_col：优先 hint，其次按意图推断，最后取最后一个数值列，实在没有取最后一列
    y_col = hint_y or _pick_y_col(numeric_cols, intent) or (numeric_cols[-1] if numeric_cols else cols[-1])

    _layout = dict(
        font=dict(family="Microsoft YaHei, Arial, sans-serif"),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    def _try_parse_datetime(df, col):
        try:
            converted = pd.to_datetime(df[col], infer_datetime_format=True)
            df = df.copy()
            df[col] = converted
            return df, True
        except Exception:
            return df, False

    def _apply_sort(df, col, order):
        if order == "desc":
            return df.sort_values(col, ascending=False)
        if order == "asc":
            return df.sort_values(col, ascending=True)
        return df

    fig = None

    if chart_type == "dual_axis":
        x_col = hint_x or (cat_cols[0] if cat_cols else (time_cols[0] if time_cols else cols[0]))
        y2_col = hint_y2 or (numeric_cols[1] if len(numeric_cols) >= 2 else "")
        if not y2_col:
            # 没有第二指标，降级为普通柱状图
            chart_type = "bar"
        else:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df[x_col], y=df[y_col], name=y_col,
                yaxis="y1",
                text=[f"{v:,.0f}" for v in df[y_col]] if show_label else None,
                textposition="outside" if show_label else None,
            ))
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df[y2_col], name=y2_col,
                mode="lines+markers" + ("+text" if show_label else ""),
                yaxis="y2",
                text=[f"{v:.2f}" for v in df[y2_col]] if show_label else None,
                textposition="top center" if show_label else None,
            ))
            fig.update_layout(
                title=title,
                yaxis=dict(title=y_col),
                yaxis2=dict(title=y2_col, overlaying="y", side="right"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                **_layout,
            )
            return fig.to_json()

    if chart_type == "line":
        x_col = hint_x or (effective_time_cols[0] if effective_time_cols else (time_cols[0] if time_cols else cols[0]))
        df, parsed = _try_parse_datetime(df, x_col)
        df = df.sort_values(x_col)
        color_col = cat_cols[0] if cat_cols else None
        if not parsed:
            fig = go.Figure()
            if color_col:
                for grp, gdf in df.groupby(color_col):
                    fig.add_trace(go.Scatter(x=gdf[x_col], y=gdf[y_col],
                                             mode="lines+markers", name=str(grp)))
            else:
                fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col],
                                         mode="lines+markers", name=y_col))
            fig.update_layout(title=title, xaxis_title=x_col, yaxis_title=y_col, **_layout)
        else:
            fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title, markers=True)
        if show_label:
            fig.update_traces(texttemplate="%{y:,.0f}", textposition="top center",
                              mode="lines+markers+text")

    elif chart_type == "area":
        x_col = hint_x or (effective_time_cols[0] if effective_time_cols else (time_cols[0] if time_cols else cols[0]))
        df, _ = _try_parse_datetime(df, x_col)
        df = df.sort_values(x_col)
        color_col = cat_cols[0] if cat_cols else None
        fig = px.area(df, x=x_col, y=y_col, color=color_col, title=title)

    elif chart_type == "bar":
        x_col = hint_x or (cat_cols[0] if cat_cols else (time_cols[0] if time_cols else cols[0]))
        color_col = (time_cols[0] if time_cols and df[time_cols[0]].nunique() > 1 else None) if (not hint_x and cat_cols) else None
        df = _apply_sort(df, y_col, sort_order)
        fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title, barmode="group")
        if show_label:
            fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside")

    elif chart_type == "bar_stack":
        if cat_cols and len(numeric_cols) >= 2:
            id_col = hint_x or cat_cols[0]
            value_cols = [c for c in numeric_cols if c != id_col]
            df_melted = df.melt(id_vars=id_col, value_vars=value_cols,
                                var_name="_metric", value_name="_value")
            fig = px.bar(df_melted, x=id_col, y="_value", color="_metric",
                         title=title, barmode="stack")
        else:
            x_col = hint_x or (cat_cols[0] if cat_cols else (time_cols[0] if time_cols else cols[0]))
            color_col = (time_cols[0] if time_cols else None) if cat_cols else None
            fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title, barmode="stack")
        if show_label:
            fig.update_traces(texttemplate="%{y:,.0f}", textposition="inside")

    elif chart_type == "pie":
        x_col = hint_x or (cat_cols[0] if cat_cols else cols[0])
        fig = px.pie(df, names=x_col, values=y_col, title=title)
        if show_label:
            fig.update_traces(textinfo="label+percent+value")

    elif chart_type == "scatter":
        scatter_x = hint_x or (numeric_cols[0] if len(numeric_cols) >= 2 else cols[0])
        scatter_y = hint_y or (numeric_cols[1] if len(numeric_cols) >= 2 else cols[1])
        color_col = cat_cols[0] if cat_cols else None
        fig = px.scatter(df, x=scatter_x, y=scatter_y, color=color_col, title=title)

    elif chart_type == "funnel":
        # 情况1：单行宽表（1行×N数值列） → 转置为长表，画标准漏斗
        if len(df) == 1 and not cat_cols and len(numeric_cols) >= 2:
            step_col = "step"
            val_col = "value"
            df_funnel = df[numeric_cols].T.reset_index()
            df_funnel.columns = [step_col, val_col]
            df_funnel[val_col] = pd.to_numeric(df_funnel[val_col], errors="coerce")
            df_funnel = df_funnel.sort_values(val_col, ascending=False)
            fig = px.funnel(df_funnel, x=val_col, y=step_col, title=title)
        # 情况2：多行宽表（多分类×N数值列） → melt 为长表，画分组柱状图
        elif len(df) > 1 and cat_cols and len(numeric_cols) >= 2:
            id_col = hint_x or cat_cols[0]
            count_cols = [c for c in numeric_cols if not any(
                kw in c.lower() for kw in ["rate", "ratio", "pct", "percent", "率", "比"]
            )]
            value_cols = count_cols if count_cols else numeric_cols
            df_melted = df.melt(id_vars=id_col, value_vars=value_cols,
                                var_name="stage", value_name="count")
            fig = px.bar(df_melted, x="stage", y="count", color=id_col,
                         title=title, barmode="group",
                         labels={"stage": "漏斗阶段", "count": "用户数"})
            if show_label:
                fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside")
        # 情况3：普通长表（每行一个阶段）
        else:
            x_col = hint_x or (cat_cols[0] if cat_cols else cols[0])
            fig = px.funnel(df, x=y_col, y=x_col, title=title)

    elif chart_type == "heatmap":
        hm_x = hint_x or (cat_cols[0] if len(cat_cols) >= 1 else cols[0])
        hm_y = cat_cols[1] if len(cat_cols) >= 2 else cols[1]
        try:
            pivot = df.pivot(index=hm_y, columns=hm_x, values=y_col)
            fig = go.Figure(data=go.Heatmap(
                z=pivot.values.tolist(),
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale="Blues",
                text=[[f"{v:,.0f}" for v in row] for row in pivot.values.tolist()] if show_label else None,
                texttemplate="%{text}" if show_label else None,
            ))
            fig.update_layout(title=title, **_layout)
            return fig.to_json()
        except Exception:
            # pivot 失败时降级为分组柱状图
            fig = px.bar(df, x=hm_x, y=y_col, color=hm_y, title=title, barmode="group")

    if fig is None:
        raise ValueError(f"未知图表类型：{chart_type}")

    fig.update_layout(**_layout)
    return fig.to_json()


def chart_node(state: GraphState) -> GraphState:
    """Chart Agent 节点：自动选图表类型并生成 plotly JSON"""
    import pandas as pd

    sql_results = state.get("sql_results", [])
    raw_hint = state.get("chart_hint", {})
    hint = _parse_hint(raw_hint)
    intent = state.get("intent", state.get("question", ""))
    log = list(state.get("process_log") or [])
    log.append("📊 [Chart Agent] 正在判断图表类型...")

    target = None
    target_index = 0
    best_score = -1
    for i, r in enumerate(sql_results):
        if not (r.get("success") and r.get("data")):
            continue
        df_tmp = pd.DataFrame(r["data"])
        if df_tmp.empty:
            continue
        cols_tmp = df_tmp.columns.tolist()
        time_kws = ["date", "time", "month", "year", "day", "日", "月", "年"]
        has_time = any(any(kw in c.lower() for kw in time_kws) for c in cols_tmp)
        numeric_cnt = sum(1 for c in cols_tmp if pd.api.types.is_numeric_dtype(df_tmp[c]))
        # 漏斗图：多行宽表也给高分
        is_funnel = hint.get("type") == "funnel" and numeric_cnt >= 2
        score = 20 if is_funnel else ((10 if has_time else 0) - numeric_cnt)
        if score > best_score:
            best_score = score
            target = r
            target_index = i

    if not target:
        log.append("   ⚠️ 无有效数据，跳过图表生成")
        return {**state, "chart_json": "", "chart_source_index": 0, "process_log": log}

    try:
        df = pd.DataFrame(target["data"])
        if df.empty:
            log.append("   ⚠️ 数据为空，跳过图表生成")
            return {**state, "chart_json": "", "chart_source_index": 0, "process_log": log}

        chart_type = _infer_chart_type(df, hint.get("type", ""))

        if chart_type == "table":
            log.append(f"   📋 判断结果：纯表格展示（数据列：{list(df.columns)}）")
            return {**state, "chart_json": "", "chart_source_index": target_index, "process_log": log}

        chart_json = _build_figure(df, chart_type, title=intent, hint=hint, intent=intent)
        source = "Planner 建议" if hint.get("type") and hint.get("type") != "table" else "规则推断"
        log.append(
            f"   ✅ 图表类型：{chart_type}（{source}）"
            + (f"  x={hint.get('x')}" if hint.get("x") else "")
            + (f"  y={hint.get('y')}" if hint.get("y") else "")
            + (f"  y2={hint.get('y2')}" if hint.get("y2") else "")
            + f"\n   数据：{len(df)} 行 × {len(df.columns)} 列"
        )
        return {**state, "chart_json": chart_json, "chart_source_index": target_index, "process_log": log}

    except Exception as e:
        log.append(f"   ❌ 图表生成失败：{e}")
        return {**state, "chart_json": "", "chart_source_index": 0,
                "error": state.get("error") or f"Chart 生成失败: {e}", "process_log": log}
