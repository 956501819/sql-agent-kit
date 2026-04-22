"""
Gradio Web UI
运行：python web/app.py
访问：http://localhost:7860
"""

import sys, os, json, threading
# 绕过系统代理，避免 socks5 代理拦截 localhost 自检请求（需在 import gradio 之前设置）
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
import pandas as pd
import gradio as gr
from sql_agent import build_agent, QueryResult

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
ENV_PATH = os.path.join(BASE_DIR, ".env")
SETTINGS_PATH = os.path.join(BASE_DIR, "config", "settings.yaml")
TABLES_PATH = os.path.join(BASE_DIR, "config", "tables.yaml")
ANNOTATIONS_PATH = os.path.join(BASE_DIR, "config", "schema_annotations.yaml")
LOG_PATH = os.path.join(BASE_DIR, "logs", "queries.jsonl")

# 全局 Agent 实例（懒加载 + 线程锁）
_agent = None
_agent_lock = threading.Lock()


def reset_agent():
    global _agent
    with _agent_lock:
        _agent = None


# 全局 Pipeline 实例（懒加载）
_pipeline = None
_pipeline_lock = threading.Lock()


def get_pipeline():
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            from sql_agent.graph.pipeline import build_pipeline
            _pipeline = build_pipeline()
    return _pipeline


def _render_judge_scores(scores: dict) -> str:
    """将 judge_scores 渲染为彩色 HTML"""
    if not scores:
        return "<div style='padding:10px;color:#999'>评分不可用</div>"

    def score_color(s):
        if s >= 8:
            return "#22c55e"
        elif s >= 6:
            return "#eab308"
        else:
            return "#ef4444"

    items = [
        ("SQL 准确性", scores.get("sql_correctness", 0)),
        ("图表适配", scores.get("chart_fitness", 0)),
        ("结论质量", scores.get("summary_quality", 0)),
    ]
    parts = []
    for label, val in items:
        color = score_color(val)
        parts.append(
            f"<span style='margin-right:20px'>{label}："
            f"<strong style='color:{color};font-size:1.1em'>{val}/10</strong></span>"
        )
    return f"<div style='padding:10px;display:flex;align-items:center'>{''.join(parts)}</div>"


def get_agent():
    global _agent
    with _agent_lock:
        if _agent is None:
            _agent = build_agent(
                config_dir=os.path.join(BASE_DIR, "config"),
                env_file=ENV_PATH,
            )
    return _agent


# ===== .env 读写 =====

def read_env() -> dict:
    result = {}
    if not os.path.exists(ENV_PATH):
        return result
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    return result


def write_env(updates: dict):
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}\n")
                updated_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    for k, v in updates.items():
        os.environ[k] = v


# ===== 查询功能 =====

def run_query(question: str):
    if not question.strip():
        return "", "⚠️ 请输入问题", [], "", "—"
    try:
        agent = get_agent()
    except Exception as e:
        return "", f"❌ Agent 初始化失败: {e}", [], str(e), "—"

    result: QueryResult = agent.query(question)
    status_icon = "✅" if result.success else ("⚠️" if result.need_confirm else "❌")
    status_label = "成功" if result.success else ("需确认" if result.need_confirm else "失败")
    status_text = f"{status_icon} {status_label}"
    if result.retry_count > 0:
        status_text += f"（重试 {result.retry_count} 次）"

    # 置信度信息
    confidence = result.confidence if hasattr(result, 'confidence') else 1.0
    confidence_text = f"{confidence:.0%}"

    error_info = result.error if result.error else ""

    # 将 formatted_table（Markdown 字符串）转换为 Dataframe 数据
    table_data = []
    if result.success and result.formatted_table:
        lines = result.formatted_table.strip().splitlines()
        # Markdown 表格解析：第一行为表头，第二行为分隔线，其余为数据
        data_lines = [l for l in lines if l.strip() and not set(l.replace("|", "").replace("-", "").replace(" ", "")) == set()]
        if len(data_lines) >= 1:
            headers = [h.strip() for h in data_lines[0].strip("|").split("|")]
            rows = []
            for dl in data_lines[1:]:
                if "|--" in dl or "--" in dl:
                    continue
                row = [c.strip() for c in dl.strip("|").split("|")]
                rows.append(row)
            table_data = {"headers": headers, "data": rows}

    return result.sql, status_text, table_data, error_info, confidence_text


def run_query_ui(question: str):
    """UI 包装函数，返回适合 Gradio 组件的格式"""
    sql, status, table_data, error = run_query(question)

    if isinstance(table_data, dict) and table_data:
        headers = table_data.get("headers", [])
        rows = table_data.get("data", [])
        df_value = rows if rows else []
        df_headers = headers
    else:
        df_value = []
        df_headers = ["查询结果"]

    return sql, status, {"headers": df_headers, "data": df_value}, error


# ===== Few-shot =====

def add_fewshot(question: str, sql: str):
    from sql_agent.fewshot.store import FewShotStore
    store = FewShotStore()
    store.add(question.strip(), sql.strip())
    return f"✅ 已添加示例：{question}", load_fewshot_list()


def load_fewshot_list():
    """加载已有 Few-shot 列表"""
    try:
        from sql_agent.fewshot.store import FewShotStore
        store = FewShotStore()
        items = store.list() if hasattr(store, "list") else []
        if not items:
            return []
        return [[i + 1, item.get("question", ""), item.get("sql", "")] for i, item in enumerate(items)]
    except Exception:
        return []


def delete_fewshot(index: int):
    """删除指定索引的 Few-shot 示例"""
    try:
        from sql_agent.fewshot.store import FewShotStore
        store = FewShotStore()
        if hasattr(store, "delete"):
            store.delete(int(index) - 1)
            return f"✅ 已删除第 {index} 条示例", load_fewshot_list()
        else:
            return "⚠️ 当前版本不支持删除操作", load_fewshot_list()
    except Exception as e:
        return f"❌ 删除失败: {e}", load_fewshot_list()


# ===== 配置管理 =====

def load_config_defaults():
    env = read_env()
    provider = "openai"
    if env.get("OPENAI_API_KEY"):
        provider = "openai"
    if env.get("DASHSCOPE_API_KEY"):
        provider = "qwen"
    if env.get("SILICONFLOW_API_KEY"):
        provider = "siliconflow"
    if env.get("BAILIAN_API_KEY"):
        provider = "bailian"

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            s = yaml.safe_load(f)
        provider = s.get("llm", {}).get("provider", provider)
    except Exception:
        pass

    return (
        provider,
        env.get("OPENAI_API_KEY", ""),
        env.get("OPENAI_BASE_URL", ""),
        env.get("OPENAI_MODEL", "gpt-4o"),
        env.get("DASHSCOPE_API_KEY", ""),
        env.get("QWEN_MODEL", "qwen-plus"),
        env.get("SILICONFLOW_API_KEY", ""),
        env.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-72B-Instruct"),
        env.get("BAILIAN_API_KEY", ""),
        env.get("BAILIAN_MODEL", "qwen-plus"),
        env.get("DB_TYPE", "mysql"),
        env.get("DB_HOST", "127.0.0.1"),
        env.get("DB_PORT", "3306"),
        env.get("DB_USER", "root"),
        env.get("DB_PASSWORD", ""),
        env.get("DB_NAME", ""),
        env.get("DB_SQLITE_PATH", "./data/local.db"),
    )


def save_llm_db_config(
    provider,
    openai_key, openai_base_url, openai_model,
    dashscope_key, qwen_model,
    siliconflow_key, siliconflow_model,
    bailian_key, bailian_model,
    db_type, db_host, db_port, db_user, db_password, db_name, sqlite_path,
):
    updates = {
        "OPENAI_API_KEY": openai_key,
        "OPENAI_BASE_URL": openai_base_url,
        "OPENAI_MODEL": openai_model,
        "DASHSCOPE_API_KEY": dashscope_key,
        "QWEN_MODEL": qwen_model,
        "SILICONFLOW_API_KEY": siliconflow_key,
        "SILICONFLOW_MODEL": siliconflow_model,
        "BAILIAN_API_KEY": bailian_key,
        "BAILIAN_MODEL": bailian_model,
        "DB_TYPE": db_type,
        "DB_HOST": db_host,
        "DB_PORT": str(db_port),
        "DB_USER": db_user,
        "DB_PASSWORD": db_password,
        "DB_NAME": db_name,
        "DB_SQLITE_PATH": sqlite_path,
    }
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = yaml.safe_load(f)
        settings["llm"]["provider"] = provider
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            yaml.dump(settings, f, allow_unicode=True, default_flow_style=False)
    except Exception:
        pass
    write_env(updates)
    reset_agent()
    return "✅ 配置已保存并立即生效"


def test_db_connection(db_type, db_host, db_port, db_user, db_password, db_name, sqlite_path):
    from urllib.parse import quote_plus
    from sqlalchemy import create_engine, text
    try:
        if db_type == "sqlite":
            url = f"sqlite:///{sqlite_path}"
        elif db_type == "postgresql":
            url = f"postgresql+psycopg2://{db_user}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"
        else:
            url = f"mysql+pymysql://{db_user}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "✅ 数据库连接成功"
    except Exception as e:
        return f"❌ 连接失败: {e}"


def test_llm_connection(
    provider,
    openai_key, openai_base_url, openai_model,
    dashscope_key, qwen_model,
    siliconflow_key, siliconflow_model,
    bailian_key, bailian_model,
):
    """向选中的 LLM 发送一条测试消息，验证 API Key 和模型是否可用"""
    from openai import OpenAI
    try:
        if provider == "openai":
            if not openai_key:
                return "❌ 请填写 OpenAI API Key"
            client = OpenAI(
                api_key=openai_key,
                base_url=openai_base_url or "https://api.openai.com/v1",
            )
            model = openai_model or "gpt-4o"
        elif provider == "qwen":
            if not dashscope_key:
                return "❌ 请填写 DashScope API Key"
            client = OpenAI(
                api_key=dashscope_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            model = qwen_model or "qwen-plus"
        elif provider == "siliconflow":
            if not siliconflow_key:
                return "❌ 请填写 SiliconFlow API Key"
            client = OpenAI(
                api_key=siliconflow_key,
                base_url="https://api.siliconflow.cn/v1",
            )
            model = siliconflow_model or "Qwen/Qwen2.5-72B-Instruct"
        elif provider == "bailian":
            if not bailian_key:
                return "❌ 请填写百炼 API Key"
            client = OpenAI(
                api_key=bailian_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            model = bailian_model or "qwen-plus"
        else:
            return f"❌ 未知 provider: {provider}"

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "你好，请回复 OK"}],
            max_tokens=16,
            temperature=0.0,
        )
        reply = response.choices[0].message.content.strip()
        return f"✅ 连接成功，模型 [{model}] 响应：{reply}"
    except Exception as e:
        return f"❌ 连接失败: {e}"


# ===== 查询历史 =====

def load_query_history(keyword: str = ""):
    if not os.path.exists(LOG_PATH):
        return []
    rows = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                conf = d.get("confidence", "")
                conf_str = f"{conf:.0%}" if isinstance(conf, float) else ""
                row = [
                    d.get("ts", d.get("timestamp", "")),
                    d.get("question", ""),
                    d.get("sql", ""),
                    "✅" if d.get("success") else "❌",
                    str(d.get("rows_count", "")),
                    str(d.get("retry_count", 0)),
                    conf_str,
                ]
                # 关键词过滤
                if keyword and keyword.strip():
                    kw = keyword.strip().lower()
                    if not any(kw in str(cell).lower() for cell in row):
                        continue
                rows.append(row)
            except Exception:
                continue
    rows.reverse()
    return rows


def delete_history_record(index: int, keyword: str = ""):
    """删除显示列表中第 index 条（1-based）记录，正确处理关键词过滤"""
    if not os.path.exists(LOG_PATH):
        return "⚠️ 暂无历史记录", load_query_history(keyword)
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            all_lines = [l for l in f.readlines() if l.strip()]

        # 构建过滤+倒序后的 (文件行号, record) 列表，与界面显示一致
        indexed = []
        for i, line in enumerate(all_lines):
            try:
                d = json.loads(line)
            except Exception:
                continue
            conf = d.get("confidence", "")
            conf_str = f"{conf:.0%}" if isinstance(conf, float) else ""
            row = [
                d.get("ts", d.get("timestamp", "")),
                d.get("question", ""),
                d.get("sql", ""),
                "✅" if d.get("success") else "❌",
                str(d.get("rows_count", "")),
                str(d.get("retry_count", 0)),
                conf_str,
            ]
            if keyword and keyword.strip():
                kw = keyword.strip().lower()
                if not any(kw in str(cell).lower() for cell in row):
                    continue
            indexed.append(i)

        indexed.reverse()  # 倒序，第 1 条 = 最新

        idx = int(index) - 1
        if idx < 0 or idx >= len(indexed):
            return f"❌ 序号 {index} 超出范围（当前显示共 {len(indexed)} 条）", load_query_history(keyword)

        file_line_idx = indexed[idx]
        all_lines.pop(file_line_idx)

        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.writelines(all_lines)

        return f"✅ 已删除第 {index} 条记录", load_query_history(keyword)
    except Exception as e:
        return f"❌ 删除失败: {e}", load_query_history(keyword)


def clear_all_history():
    """清空所有历史记录"""
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("")
        return "✅ 已清空所有历史记录", []
    except Exception as e:
        return f"❌ 清空失败: {e}", load_query_history()


# ===== 表白名单 =====

def load_tables():
    try:
        with open(TABLES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return "\n".join(data.get("allowed_tables", []))
    except Exception:
        return ""


def save_tables(text: str):
    tables = [t.strip() for t in text.strip().splitlines() if t.strip()]
    with open(TABLES_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"allowed_tables": tables}, f, allow_unicode=True, default_flow_style=False)
    reset_agent()
    return f"✅ 已保存 {len(tables)} 张表到白名单"


# ===== Schema 注释 =====

def load_annotations():
    try:
        with open(ANNOTATIONS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "# 暂无注释，请在此添加字段业务含义\n"


def save_annotations(text: str):
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as e:
        return f"❌ YAML 格式错误: {e}"
    with open(ANNOTATIONS_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    reset_agent()
    return "✅ Schema 注释已保存"


# ===== Agent 参数 =====

_DEFAULT_AGENT_PARAMS = (3, 0.7, 10, 30, 500)


def load_agent_params():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            s = yaml.safe_load(f)
        return (
            s["agent"]["max_retry"],
            s["agent"]["confidence_threshold"],
            s["agent"]["max_tables_in_prompt"],
            s["executor"]["query_timeout"],
            s["executor"]["max_rows"],
        )
    except Exception:
        return _DEFAULT_AGENT_PARAMS


def save_agent_params(max_retry, confidence_threshold, max_tables, query_timeout, max_rows):
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            s = yaml.safe_load(f)
    except Exception:
        s = {"agent": {}, "executor": {}}
    s["agent"]["max_retry"] = int(max_retry)
    s["agent"]["confidence_threshold"] = float(confidence_threshold)
    s["agent"]["max_tables_in_prompt"] = int(max_tables)
    s["executor"]["query_timeout"] = int(query_timeout)
    s["executor"]["max_rows"] = int(max_rows)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        yaml.dump(s, f, allow_unicode=True, default_flow_style=False)
    reset_agent()
    return "✅ Agent 参数已保存"


def toggle_db_fields(db_type):
    is_sqlite = db_type == "sqlite"
    return (
        gr.update(visible=not is_sqlite),
        gr.update(visible=not is_sqlite),
        gr.update(visible=not is_sqlite),
        gr.update(visible=not is_sqlite),
        gr.update(visible=not is_sqlite),
        gr.update(visible=is_sqlite),
    )


# ===== 读取初始值 =====
_defaults = load_config_defaults()
_agent_params = load_agent_params()

# ===== Gradio UI =====
with gr.Blocks(
    title="sql-agent-kit",
    theme=gr.themes.Soft(),
    css="""
    .status-box textarea { font-size: 1.05em; font-weight: bold; }
    .result-table { margin-top: 8px; }
    footer { display: none !important; }
    """
) as demo:
    gr.Markdown("""
# 🤖 sql-agent-kit
**生产级 Text-to-SQL Agent 演示** &nbsp;|&nbsp; 自然语言 → SQL → 数据结果
""")

    # ========== Tab: 查询 ==========
    with gr.Tab("💬 单Agent查询"):
        with gr.Row():
            question_input = gr.Textbox(
                label="输入你的问题（自然语言）",
                placeholder="例如：上个月销售额最高的商品是什么？",
                lines=2,
                scale=5,
            )
            query_btn = gr.Button("🔍 查询", variant="primary", scale=1, min_width=80)

        # 加载状态显示
        loading_html = gr.HTML(
            value="",
            visible=False,
        )

        status_output = gr.Textbox(
            label="执行状态",
            interactive=False,
            elem_classes=["status-box"],
        )

        confidence_display = gr.HTML(
            label="置信度",
            value="<div style='padding: 10px; font-size: 16px;'>—</div>",
        )

        with gr.Row():
            sql_output = gr.Code(label="生成的 SQL", language="sql")

        # 查询结果用 Dataframe 展示
        result_df = gr.Dataframe(
            label="查询结果",
            wrap=True,
            elem_classes=["result-table"],
        )

        error_output = gr.Textbox(
            label="错误信息",
            interactive=False,
            visible=True,
        )

        def run_and_display(question):
            sql, status, table_data, error, confidence = run_query(question)
            # 构造 Dataframe 数据
            if isinstance(table_data, dict) and table_data.get("data"):
                headers = table_data["headers"]
                rows = table_data["data"]
                import pandas as pd
                try:
                    df = pd.DataFrame(rows, columns=headers)
                except Exception:
                    df = pd.DataFrame(rows)
            else:
                import pandas as pd
                df = pd.DataFrame()
            
            # 置信度颜色指示：绿色(>=80%)、黄色(60-80%)、红色(<60%)
            try:
                conf_float = float(confidence.rstrip('%')) / 100
            except Exception:
                conf_float = 0
            
            if conf_float >= 0.8:
                color = "#22c55e"  # 绿色
            elif conf_float >= 0.6:
                color = "#eab308"  # 黄色
            else:
                color = "#ef4444"  # 红色
            
            confidence_html = f"""
            <div style='padding: 10px; font-size: 16px; display: flex; align-items: center; gap: 10px;'>
                <span style='color: #6b7280; font-size: 13px;'>置信度（AI 对生成 SQL 的把握程度）：</span>
                <span style='font-weight: bold;'>{confidence}</span>
                <div style='flex: 1; background: #e5e7eb; border-radius: 4px; height: 20px;'>
                    <div style='width: {confidence}; background: {color}; height: 100%; border-radius: 4px;'></div>
                </div>
            </div>
            """
            return sql, status, df, error, confidence_html

        def start_loading():
            return (
                gr.update(visible=True, value="<div style='padding: 10px; color: #666;'>⏳ 正在查询中，请稍候...</div>"),
                gr.update(interactive=False),
            )

        def end_loading():
            return (
                gr.update(visible=False),
                gr.update(interactive=True),
            )

        # 注：click/submit 事件在 history_table 定义之后统一注册（见文件末尾）

    # ========== Tab: 智能分析（多 Agent 流程）==========
    with gr.Tab("🧠 多Agent智能分析"):
        gr.Markdown(
            "**多 Agent 全流程**：Planner → SQL Agent → Chart Agent → Summary Agent → LLM-as-Judge"
        )

        with gr.Row():
            analysis_input = gr.Textbox(
                label="输入分析问题",
                placeholder="例如：上个月各商品的销售趋势如何？",
                lines=2,
                scale=5,
            )
            analysis_btn = gr.Button("🧠 分析", variant="primary", scale=1, min_width=80)

        analysis_loading = gr.HTML(value="", visible=False)
        analysis_status = gr.Textbox(label="执行状态", interactive=False, elem_classes=["status-box"])

        # 思考过程面板（折叠，默认展开）
        with gr.Accordion("🔄 思考过程（Agent 执行日志）", open=True):
            analysis_process = gr.Textbox(
                label="",
                interactive=False,
                lines=10,
                placeholder="分析完成后，这里将显示各 Agent 的决策过程...",
            )

        with gr.Row():
            analysis_sql = gr.Code(label="📝 生成的 SQL", language="sql", scale=1)

        analysis_df = gr.Dataframe(label="📊 查询数据", wrap=True)
        analysis_chart = gr.Plot(label="📈 数据图表")
        analysis_summary = gr.Textbox(label="💡 分析结论", interactive=False, lines=4)
        analysis_scores = gr.HTML(label="🏅 质量评分（LLM-as-Judge）", value="<div style='padding:10px'>—</div>")

        def do_analysis(question):
            if not question.strip():
                return "", "⚠️ 请输入问题", "", pd.DataFrame(), None, "", "<div>—</div>", load_query_history()
            try:
                pipeline = get_pipeline()
                state = pipeline.invoke({"question": question})

                sql_results = state.get("sql_results", [])

                # SQL
                first_sql = sql_results[0].get("sql", "") if sql_results else ""

                # 状态
                success = any(r.get("success") for r in sql_results)
                if success:
                    status = f"✅ 成功（共 {len(sql_results)} 个子查询）"
                    if state.get("error"):
                        status += f" | ⚠️ {state['error']}"
                else:
                    err = sql_results[0].get("error", "未知错误") if sql_results else state.get("error", "无结果")
                    status = f"❌ 失败：{err}"

                # 思考过程日志
                process_entries = state.get("process_log") or []
                process_text = "\n\n".join(process_entries) if process_entries else "（无日志）"

                # DataFrame
                df = pd.DataFrame()
                for r in sql_results:
                    if r.get("success") and r.get("data"):
                        df = pd.DataFrame(r["data"])
                        break

                # 图表
                chart_fig = None
                chart_json = state.get("chart_json", "")
                if chart_json:
                    try:
                        import plotly.io as pio
                        chart_fig = pio.from_json(chart_json)
                    except Exception:
                        chart_fig = None

                # 结论
                summary = state.get("summary", "")

                # 质量评分
                scores_html = _render_judge_scores(state.get("judge_scores", {}))

                return first_sql, status, process_text, df, chart_fig, summary, scores_html, load_query_history()

            except Exception as e:
                return "", f"❌ 分析失败: {e}", f"❌ 异常：{e}", pd.DataFrame(), None, "", "<div>—</div>", load_query_history()

        def _start_analysis():
            return (
                gr.update(visible=True, value="<div style='padding:10px;color:#666'>⏳ 多 Agent 分析中（Planner → SQL → Chart → Summary → Judge）...</div>"),
                gr.update(interactive=False),
            )

        def _end_analysis():
            return gr.update(visible=False), gr.update(interactive=True)

        # 注：事件绑定在 history_table 定义后统一注册（见下方）

    # ========== Tab: 配置管理 ==========
    with gr.Tab("⚙️ 配置管理"):
        with gr.Accordion("🤖 大模型 API 配置", open=True):
            cfg_provider = gr.Dropdown(
                choices=["openai", "qwen", "siliconflow", "bailian"],
                value=_defaults[0], label="LLM Provider 请在这里勾选后测试"
            )

            with gr.Group() as openai_group:
                gr.Markdown("**OpenAI / 兼容接口**")
                cfg_openai_key = gr.Textbox(label="API Key", value=_defaults[1], type="password")
                cfg_openai_base_url = gr.Textbox(label="Base URL（兼容接口，可选）", value=_defaults[2])
                cfg_openai_model = gr.Textbox(label="模型名称", value=_defaults[3])

            with gr.Group(visible=(_defaults[0] == "qwen")) as qwen_group:
                gr.Markdown("**通义千问（DashScope）**")
                cfg_dashscope_key = gr.Textbox(label="DashScope API Key", value=_defaults[4], type="password")
                cfg_qwen_model = gr.Textbox(label="Qwen 模型名称", value=_defaults[5])

            with gr.Group(visible=(_defaults[0] == "siliconflow")) as sf_group:
                gr.Markdown("**硅基流动（SiliconFlow）**")
                cfg_sf_key = gr.Textbox(label="SiliconFlow API Key", value=_defaults[6], type="password")
                cfg_sf_model = gr.Textbox(label="模型名称", value=_defaults[7])

            with gr.Group(visible=(_defaults[0] == "bailian")) as bailian_group:
                gr.Markdown("**阿里云百炼平台**（[控制台](https://bailian.console.aliyun.com/)）")
                cfg_bailian_key = gr.Textbox(label="百炼 API Key", value=_defaults[8], type="password")
                cfg_bailian_model = gr.Textbox(
                    label="模型名称",
                    value=_defaults[9],
                    placeholder="qwen-plus / qwen-max / qwen-turbo / qwen-long",
                )

            def toggle_llm_groups(provider):
                return (
                    gr.update(visible=(provider == "openai")),
                    gr.update(visible=(provider == "qwen")),
                    gr.update(visible=(provider == "siliconflow")),
                    gr.update(visible=(provider == "bailian")),
                )

            cfg_provider.change(
                fn=toggle_llm_groups,
                inputs=[cfg_provider],
                outputs=[openai_group, qwen_group, sf_group, bailian_group],
            )

            with gr.Row():
                test_llm_btn = gr.Button("🔗 测试模型连接", variant="secondary")
            llm_test_result = gr.Textbox(label="模型连接测试结果", interactive=False)

            test_llm_btn.click(
                fn=test_llm_connection,
                inputs=[
                    cfg_provider,
                    cfg_openai_key, cfg_openai_base_url, cfg_openai_model,
                    cfg_dashscope_key, cfg_qwen_model,
                    cfg_sf_key, cfg_sf_model,
                    cfg_bailian_key, cfg_bailian_model,
                ],
                outputs=[llm_test_result],
            )

        with gr.Accordion("🗄️ 数据库连接配置", open=True):
            cfg_db_type = gr.Dropdown(
                choices=["mysql", "postgresql", "sqlite"],
                value=_defaults[10], label="数据库类型"
            )
            with gr.Row():
                cfg_host = gr.Textbox(label="Host", value=_defaults[11], visible=_defaults[10] != "sqlite")
                cfg_port = gr.Textbox(label="Port", value=_defaults[12], visible=_defaults[10] != "sqlite")
            with gr.Row():
                cfg_user = gr.Textbox(label="用户名", value=_defaults[13], visible=_defaults[10] != "sqlite")
                cfg_password = gr.Textbox(label="密码", value=_defaults[14], type="password", visible=_defaults[10] != "sqlite")
            with gr.Row():
                cfg_db_name = gr.Textbox(label="数据库名", value=_defaults[15], visible=_defaults[10] != "sqlite")
                cfg_sqlite_path = gr.Textbox(label="SQLite 文件路径", value=_defaults[16], visible=_defaults[10] == "sqlite")

            cfg_db_type.change(
                fn=toggle_db_fields,
                inputs=[cfg_db_type],
                outputs=[cfg_host, cfg_port, cfg_user, cfg_password, cfg_db_name, cfg_sqlite_path],
            )

            with gr.Row():
                test_db_btn = gr.Button("🔌 测试数据库连接", variant="secondary")
                save_cfg_btn = gr.Button("💾 保存所有配置", variant="primary")
            test_result = gr.Textbox(label="数据库连接测试结果", interactive=False)
            save_cfg_result = gr.Textbox(label="保存结果", interactive=False)

            test_db_btn.click(
                fn=test_db_connection,
                inputs=[cfg_db_type, cfg_host, cfg_port, cfg_user, cfg_password, cfg_db_name, cfg_sqlite_path],
                outputs=[test_result],
            )
            save_cfg_btn.click(
                fn=save_llm_db_config,
                inputs=[
                    cfg_provider,
                    cfg_openai_key, cfg_openai_base_url, cfg_openai_model,
                    cfg_dashscope_key, cfg_qwen_model,
                    cfg_sf_key, cfg_sf_model,
                    cfg_bailian_key, cfg_bailian_model,
                    cfg_db_type, cfg_host, cfg_port, cfg_user, cfg_password, cfg_db_name, cfg_sqlite_path,
                ],
                outputs=[save_cfg_result],
            )

    # ========== Tab: 查询历史 ==========
    with gr.Tab("📋 查询历史") as history_tab:
        with gr.Row():
            history_search = gr.Textbox(
                label="关键词搜索（问题/SQL/状态）",
                placeholder="输入关键词过滤历史记录...",
                scale=4,
            )
            refresh_btn = gr.Button("🔄 刷新", variant="secondary", scale=1)

        history_table = gr.Dataframe(
            headers=["时间", "问题", "SQL", "状态", "行数", "重试", "置信度"],
            datatype=["str", "str", "str", "str", "str", "str", "str"],
            value=load_query_history(),
            wrap=True,
            interactive=False,
        )

        with gr.Row():
            del_index = gr.Number(label="删除指定条（序号从 1 开始，最新记录为第 1 条）", precision=0, minimum=1, scale=3)
            del_btn = gr.Button("🗑️ 删除该条", variant="stop", scale=1)
            clear_btn = gr.Button("🧹 清空所有历史", variant="stop", scale=1)
        del_result = gr.Textbox(label="操作结果", interactive=False)

        def load_history(keyword: str = ""):
            return load_query_history(keyword)

        def do_delete(index, keyword):
            return delete_history_record(index, keyword)

        def do_clear():
            return clear_all_history()

        refresh_btn.click(fn=load_history, inputs=[history_search], outputs=[history_table])
        history_search.submit(fn=load_history, inputs=[history_search], outputs=[history_table])
        del_btn.click(fn=do_delete, inputs=[del_index, history_search], outputs=[del_result, history_table])
        clear_btn.click(fn=do_clear, outputs=[del_result, history_table])

    # ========== 查询按钮事件（在 history_table 定义后统一注册）==========
    def _run_and_refresh(question):
        sql, status, df, error, confidence_html = run_and_display(question)
        return sql, status, df, error, confidence_html, load_query_history()

    for _trigger in [query_btn.click, question_input.submit]:
        _trigger(
            fn=start_loading,
            outputs=[loading_html, query_btn],
        ).then(
            fn=_run_and_refresh,
            inputs=[question_input],
            outputs=[sql_output, status_output, result_df, error_output, confidence_display, history_table],
        ).then(
            fn=end_loading,
            outputs=[loading_html, query_btn],
        )

    # ========== 智能分析按钮事件（在 history_table 定义后注册）==========
    for _atrigger in [analysis_btn.click, analysis_input.submit]:
        _atrigger(
            fn=_start_analysis,
            outputs=[analysis_loading, analysis_btn],
        ).then(
            fn=do_analysis,
            inputs=[analysis_input],
            outputs=[analysis_sql, analysis_status, analysis_process, analysis_df, analysis_chart, analysis_summary, analysis_scores, history_table],
        ).then(
            fn=_end_analysis,
            outputs=[analysis_loading, analysis_btn],
        )

    # ========== Tab: 表白名单 ==========
    with gr.Tab("🗂️ 表白名单"):
        gr.Markdown("每行一个表名，只有白名单内的表才允许被查询。")
        tables_editor = gr.Textbox(
            label="允许查询的表（每行一个）",
            value=load_tables(),
            lines=10,
        )
        save_tables_btn = gr.Button("💾 保存白名单", variant="primary")
        save_tables_result = gr.Textbox(label="保存结果", interactive=False)
        save_tables_btn.click(fn=save_tables, inputs=[tables_editor], outputs=[save_tables_result])

    # ========== Tab: Schema 注释 ==========
    with gr.Tab("🏷️ Schema 注释"):
        gr.Markdown("编辑字段业务含义，帮助 LLM 理解数据库结构。保存后立即生效。")
        annotations_editor = gr.Code(
            label="schema_annotations.yaml",
            language="yaml",
            value=load_annotations(),
            lines=30,
        )
        save_ann_btn = gr.Button("💾 保存注释", variant="primary")
        save_ann_result = gr.Textbox(label="保存结果", interactive=False)
        save_ann_btn.click(fn=save_annotations, inputs=[annotations_editor], outputs=[save_ann_result])

    # ========== Tab: Agent 参数 ==========
    with gr.Tab("🔧 Agent 参数"):
        gr.Markdown("调整 Agent 行为参数，保存后立即生效。")
        param_max_retry = gr.Slider(1, 10, step=1, value=_agent_params[0], label="最大重试次数 (max_retry)")
        param_confidence = gr.Slider(0.1, 1.0, step=0.05, value=_agent_params[1], label="置信度阈值 (confidence_threshold)")
        param_max_tables = gr.Slider(1, 30, step=1, value=_agent_params[2], label="Prompt 最多注入表数 (max_tables_in_prompt)")
        param_timeout = gr.Number(value=_agent_params[3], label="查询超时（秒）")
        param_max_rows = gr.Number(value=_agent_params[4], label="最大返回行数")
        save_params_btn = gr.Button("💾 保存参数", variant="primary")
        save_params_result = gr.Textbox(label="保存结果", interactive=False)
        save_params_btn.click(
            fn=save_agent_params,
            inputs=[param_max_retry, param_confidence, param_max_tables, param_timeout, param_max_rows],
            outputs=[save_params_result],
        )

    # ========== Tab: Few-shot 管理 ==========
    with gr.Tab("📚 Few-shot 管理"):
        gr.Markdown("添加正确的问题-SQL 示例对，提升查询准确率。支持查看和删除已有示例。")

        with gr.Accordion("➕ 添加新示例", open=True):
            fs_question = gr.Textbox(label="问题", placeholder="用户的自然语言问题")
            fs_sql = gr.Code(label="正确的 SQL", language="sql")
            fs_btn = gr.Button("添加示例", variant="secondary")
            fs_result = gr.Textbox(label="添加结果", interactive=False)

        gr.Markdown("### 📋 已有示例列表")
        fs_list = gr.Dataframe(
            headers=["序号", "问题", "SQL"],
            datatype=["str", "str", "str"],
            value=load_fewshot_list(),
            wrap=True,
            label="Few-shot 示例",
        )

        with gr.Row():
            fs_delete_idx = gr.Number(label="输入序号删除", precision=0, minimum=1)
            fs_delete_btn = gr.Button("🗑️ 删除指定示例", variant="stop")
        fs_delete_result = gr.Textbox(label="删除结果", interactive=False)

        fs_btn.click(
            fn=add_fewshot,
            inputs=[fs_question, fs_sql],
            outputs=[fs_result, fs_list],
        )
        fs_delete_btn.click(
            fn=delete_fewshot,
            inputs=[fs_delete_idx],
            outputs=[fs_delete_result, fs_list],
        )

    # ========== Tab: 关于 ==========
    with gr.Tab("ℹ️ 关于"):
        gr.Markdown("""
## sql-agent-kit

**面向生产环境的 Text-to-SQL Agent 工具包**

### 核心特性
- ✅ **表名白名单**：只允许查询指定的表，安全可控
- ✅ **语义注释层**：给字段加上业务含义，解决企业数据库字段名模糊问题
- ✅ **SQL 安全校验**：只允许 SELECT，过滤所有写操作
- ✅ **错误自愈重试**：执行失败自动反馈错误给 LLM 重试
- ✅ **置信度评估**：低置信度时提示用户确认，不静默执行
- ✅ **Few-shot 管理**：持续积累正确示例，支持查看和删除
- ✅ **查询日志**：完整记录每次查询，支持关键词搜索过滤
- ✅ **Web 配置管理**：无需手动编辑文件，网页端完成所有配置

### 支持的 LLM Provider
- **openai**：OpenAI 官方 API 及兼容接口（Ollama、vLLM 等）
- **qwen**：通义千问（阿里云 DashScope）
- **siliconflow**：硅基流动（Qwen、DeepSeek、GLM 等开源模型）
- **bailian**：阿里云百炼平台

### 配置文件
- `config/tables.yaml`：配置白名单表
- `config/schema_annotations.yaml`：配置字段业务含义
- `config/settings.yaml`：全局参数配置
- `.env`：数据库连接和 API Key
        """)


if __name__ == "__main__":
    os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
