# sql-agent-kit

**生产级 Text-to-SQL Agent 工具包** — 让自然语言直接查询你的数据库。
作者联系邮箱：ly956501819@foxmail.com
作者联系微信：ly956501819
> 输入"上个月销售额最高的商品是什么？"，自动生成并执行 SQL，返回结果。

- **自然语言转 SQL**：用中文提问，自动生成对应的 SQL 查询
- **多模型支持**：兼容 OpenAI、Qwen（通义千问）、硅基流动等 LLM 接口
- **SQL 安全验证**：白名单表过滤、语法校验、置信度评估
- **Schema 语义增强**：支持字段语义注释，提升 SQL 生成准确率
- **Few-shot 学习**：积累优秀问答对，持续优化生成效果
- **多种输出格式**：终端交互、Web UI

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🛡️ 表名白名单 | 只允许查询指定的表，防止越权访问 |
| 🏷️ 语义注释层 | 给字段加业务含义，解决企业数据库字段名模糊问题 |
| 🔒 SQL 安全校验 | 只允许 SELECT，过滤所有写操作 |
| 🔄 错误自愈重试 | 执行失败自动把错误反馈给 LLM 重试（最多 N 次） |
| 📊 置信度评估 | 低置信度时提示用户确认，不静默执行 |
| 📚 Few-shot 管理 | 持续积累正确示例，提升准确率 |
| 📋 查询日志 | 完整记录每次查询，支持问题溯源 |
| 🌐 Web 配置界面 | 无需手动编辑文件，网页端完成所有配置 |

---

## 🗄️ 支持的数据库

- MySQL
- PostgreSQL
- SQLite

## 🤖 支持的 LLM

- OpenAI（及所有兼容接口，如 Ollama、vLLM）
- 通义千问（阿里云 DashScope）
- 硅基流动 SiliconFlow（Qwen、DeepSeek、GLM 等开源模型）

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

> 数据库驱动按需安装：MySQL 需要 `pymysql`，PostgreSQL 需要 `psycopg2-binary`，SQLite 无需额外安装。

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入你的数据库连接信息和 LLM API Key：

```env
# 选择一个 LLM Provider 填写
SILICONFLOW_API_KEY=sk-xxx
# OPENAI_API_KEY=sk-xxx
# DASHSCOPE_API_KEY=sk-xxx

# 数据库配置
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=your_database
```

### 3. 配置白名单表

编辑 `config/tables.yaml`，填入允许查询的表名：

```yaml
allowed_tables:
  - users
  - orders
  - products
```

### 4. 启动 Web UI

```bash
python web/app.py
```

访问 [http://localhost:7860](http://localhost:7860)，在网页端完成所有配置并开始查询。

### 或者：命令行快速体验

```bash
python examples/quickstart.py
```

---

## 🌐 Web UI 功能

启动后提供以下管理界面：

- **💬 查询** — 输入自然语言，查看生成的 SQL 和执行结果
- **⚙️ 配置管理** — 网页端修改数据库连接和 LLM API Key，支持一键测试连接
- **📋 查询历史** — 查看历史查询记录、SQL 和执行状态
- **🗂️ 表白名单** — 增删允许查询的表
- **🏷️ Schema 注释** — 编辑字段业务含义，提升 LLM 理解准确率
- **🔧 Agent 参数** — 调整重试次数、置信度阈值等行为参数
- **📚 Few-shot 管理** — 添加问题-SQL 示例对，持续提升准确率

---

## 📁 项目结构

```
sql-agent-kit/
├── config/
│   ├── settings.yaml          # 全局参数配置
│   ├── tables.yaml            # 白名单表配置
│   └── schema_annotations.yaml # 字段语义注释
├── sql_agent/
│   ├── agent/                 # Agent 主链路
│   ├── llm/                   # LLM 客户端（OpenAI / Qwen / SiliconFlow）
│   ├── schema/                # Schema 加载、注释、筛选
│   ├── executor/              # SQL 执行器
│   ├── validator/             # 安全、语法、置信度校验
│   ├── fewshot/               # Few-shot 存储与检索
│   └── feedback/              # 查询日志
├── web/
│   └── app.py                 # Gradio Web UI
├── examples/
│   └── quickstart.py          # 命令行快速体验
├── .env.example               # 环境变量模板
└── requirements.txt
```

---

## ⚙️ 配置说明

### config/settings.yaml

```yaml
llm:
  provider: siliconflow   # openai | qwen | siliconflow

agent:
  max_retry: 3            # SQL 执行失败最大重试次数
  confidence_threshold: 0.6  # 低于此值时提示用户确认

executor:
  query_timeout: 30       # SQL 查询超时（秒）
  max_rows: 500           # 单次查询最大返回行数
```

### config/schema_annotations.yaml

给模糊的字段名加上业务含义，显著提升 LLM 生成 SQL 的准确率：

```yaml
tables:
  orders:
    description: "订单主表，记录每一笔交易"
    columns:
      status:
        description: "订单状态: pending=待付款, paid=已付款, completed=已完成"
      total_amount:
        description: "订单总金额，单位：元"
```

---

## 💡 Python SDK 用法

```python
from sql_agent import build_agent

agent = build_agent()
result = agent.query("上个月销售额最高的商品是什么？")

if result.success:
    print(result.sql)
    print(result.formatted_table)
elif result.need_confirm:
    print(f"置信度较低，请确认 SQL：\n{result.sql}")
else:
    print(f"查询失败：{result.error}")
```

---

## 📄 License

MIT License — 自由使用、修改和分发。
