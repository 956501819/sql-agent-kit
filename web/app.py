"""
Gradio Web UI
运行：python web/app.py
访问：http://localhost:7860
"""

import sys, os, json
# 绕过系统代理，避免 socks5 代理拦截 localhost 自检请求（需在 import gradio 之前设置）
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import yaml
import gradio as gr
from sql_agent import build_agent, QueryResult

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
ENV_PATH = os.path.join(BASE_DIR, ".env")
SETTINGS_PATH = os.path.join(BASE_DIR, "config", "settings.yaml")
TABLES_PATH = os.path.join(BASE_DIR, "config", "tables.yaml")
ANNOTATIONS_PATH = os.path.join(BASE_DIR, "config", "schema_annotations.yaml")
LOG_PATH = os.path.join(BASE_DIR, "logs", "queries.jsonl")

# 全局 Agent 实例（懒加载）
_agent = None


def reset_agent():
    global _agent
    _agent = None


def get_agent():
    global _agent
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
        return "", "请输入问题", "", ""
    try:
        agent = get_agent()
    except Exception as e:
        return "", f"Agent 初始化失败: {e}", "", ""

    result: QueryResult = agent.query(question)
    status_icon = "✅" if result.success else ("⚠️" if result.need_confirm else "❌")
    status_text = f"{status_icon} {'成功' if result.success else ('需确认' if result.need_confirm else '失败')}"
    if result.retry_count > 0:
        status_text += f"（重试 {result.retry_count} 次）"
    error_info = result.error if result.error else ""
    table_output = result.formatted_table if result.success else ""
    return result.sql, status_text, table_output, error_info


# ===== Few-shot =====

def add_fewshot(question: str, sql: str):
    from sql_agent.fewshot.store import FewShotStore
    store = FewShotStore()
    store.add(question.strip(), sql.strip())
    return f"✅ 已添加示例：{question}"


# ===== 配置管理 =====

def load_config_defaults():
    env = read_env()
    # 优先级：bailian > siliconflow > qwen > openai
    provider = "openai"
    if env.get("OPENAI_API_KEY"):
        provider = "openai"
    if env.get("DASHSCOPE_API_KEY"):
        provider = "qwen"
    if env.get("SILICONFLOW_API_KEY"):
        provider = "siliconflow"
    if env.get("BAILIAN_API_KEY"):
        provider = "bailian"

    # 从 settings.yaml 读取当前 provider
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

def load_query_history():
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
                rows.append([
                    d.get("timestamp", ""),
                    d.get("question", ""),
                    d.get("sql", ""),
                    "✅" if d.get("success") else "❌",
                    str(d.get("rows_count", "")),
                    str(d.get("retry_count", 0)),
                    conf_str,
                ])
            except Exception:
                continue
    rows.reverse()
    return rows


# ===== 表白名单 =====

def load_tables():
    with open(TABLES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return "\n".join(data.get("allowed_tables", []))


def save_tables(text: str):
    tables = [t.strip() for t in text.strip().splitlines() if t.strip()]
    with open(TABLES_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"allowed_tables": tables}, f, allow_unicode=True, default_flow_style=False)
    reset_agent()
    return f"✅ 已保存 {len(tables)} 张表到白名单"


# ===== Schema 注释 =====

def load_annotations():
    with open(ANNOTATIONS_PATH, "r", encoding="utf-8") as f:
        return f.read()


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

def load_agent_params():
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        s = yaml.safe_load(f)
    return (
        s["agent"]["max_retry"],
        s["agent"]["confidence_threshold"],
        s["agent"]["max_tables_in_prompt"],
        s["executor"]["query_timeout"],
        s["executor"]["max_rows"],
    )


def save_agent_params(max_retry, confidence_threshold, max_tables, query_timeout, max_rows):
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        s = yaml.safe_load(f)
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
with gr.Blocks(title="sql-agent-kit") as demo:
    gr.Markdown("# 🤖 sql-agent-kit\n**生产级 Text-to-SQL Agent 演示**")

    with gr.Tab("💬 查询"):
        with gr.Row():
            question_input = gr.Textbox(
                label="输入你的问题（自然语言）",
                placeholder="例如：上个月销售额最高的商品是什么？",
                lines=2,
            )
        query_btn = gr.Button("查询", variant="primary")
        with gr.Row():
            sql_output = gr.Code(label="生成的 SQL", language="sql")
            status_output = gr.Textbox(label="执行状态", interactive=False)
        table_output = gr.Markdown(label="查询结果")
        error_output = gr.Textbox(label="错误信息", interactive=False)
        query_btn.click(
            fn=run_query,
            inputs=[question_input],
            outputs=[sql_output, status_output, table_output, error_output],
        )

    with gr.Tab("⚙️ 配置管理"):
        gr.Markdown("### 大模型 API")
        cfg_provider = gr.Dropdown(
            choices=["openai", "qwen", "siliconflow", "bailian"],
            value=_defaults[0], label="LLM Provider"
        )

        with gr.Group() as openai_group:
            gr.Markdown("**OpenAI / 兼容接口**")
            cfg_openai_key = gr.Textbox(label="API Key", value=_defaults[1], type="password")
            cfg_openai_base_url = gr.Textbox(label="Base URL（兼容接口，可选）", value=_defaults[2])
            cfg_openai_model = gr.Textbox(label="模型名称", value=_defaults[3])

        with gr.Group() as qwen_group:
            gr.Markdown("**通义千问（DashScope）**")
            cfg_dashscope_key = gr.Textbox(label="DashScope API Key", value=_defaults[4], type="password")
            cfg_qwen_model = gr.Textbox(label="Qwen 模型名称", value=_defaults[5])

        with gr.Group() as sf_group:
            gr.Markdown("**硅基流动（SiliconFlow）**")
            cfg_sf_key = gr.Textbox(label="SiliconFlow API Key", value=_defaults[6], type="password")
            cfg_sf_model = gr.Textbox(label="模型名称", value=_defaults[7])

        with gr.Group() as bailian_group:
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

        # 模型连接测试
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

        gr.Markdown("### 数据库连接")
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

    with gr.Tab("📋 查询历史"):
        refresh_btn = gr.Button("🔄 刷新", variant="secondary")
        history_table = gr.Dataframe(
            headers=["时间", "问题", "SQL", "状态", "行数", "重试", "置信度"],
            datatype=["str", "str", "str", "str", "str", "str", "str"],
            value=load_query_history(),
            wrap=True,
        )
        refresh_btn.click(fn=load_query_history, outputs=[history_table])

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

    with gr.Tab("📚 Few-shot 管理"):
        gr.Markdown("添加正确的问题-SQL示例对，提升查询准确率")
        fs_question = gr.Textbox(label="问题", placeholder="用户的自然语言问题")
        fs_sql = gr.Code(label="正确的 SQL", language="sql")
        fs_btn = gr.Button("添加示例", variant="secondary")
        fs_result = gr.Textbox(label="结果", interactive=False)
        fs_btn.click(fn=add_fewshot, inputs=[fs_question, fs_sql], outputs=[fs_result])

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
- ✅ **Few-shot 管理**：持续积累正确示例，提升准确率
- ✅ **查询日志**：完整记录每次查询，支持问题溯源
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
    # 绕过系统代理，避免 all_proxy/socks5 代理拦截 localhost 自检请求
    os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
    os.environ.setdefault("no_proxy", "localhost,127.0.0.1")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
