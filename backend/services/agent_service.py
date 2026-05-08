"""
SQL Agent 单例管理模块

本模块提供线程安全的全局 SQL Agent 单例实例，确保：
1. 全局只有一个 Agent 实例，避免重复初始化带来的资源消耗
2. 线程安全，支持多线程/多请求并发访问
3. 配置变更时可重置实例，下次请求自动加载新配置

使用场景：
- FastAPI 应用启动时，通过 get_agent() 获取 Agent 实例处理用户查询
- 管理员修改配置后，调用 reset_agent() 重置实例
"""

import os
import threading

# -----------------------------------------------------------------------------
# 全局变量：Agent 实例与线程锁
# -----------------------------------------------------------------------------

# 全局唯一的 Agent 实例，初始化为 None（懒加载模式）
_agent = None

# 线程锁，用于保证 get_agent() 和 reset_agent() 的线程安全性
# 使用 with _agent_lock 语句确保同一时刻只有一个线程能修改 _agent
_agent_lock = threading.Lock()

# -----------------------------------------------------------------------------
# 路径配置：使用绝对路径确保无论当前工作目录在哪都能正确找到文件
# -----------------------------------------------------------------------------

# _REPO_ROOT：计算项目根目录的绝对路径
# __file__ 是当前文件路径 (backend/services/agent_service.py)
# 通过两次向上查找 (services -> backend -> 项目根目录) 得到项目根目录
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

# CONFIG_DIR：配置文件目录，用于存放数据库连接配置、LLM 配置等
CONFIG_DIR = os.path.join(_REPO_ROOT, "config")

# DATA_DIR：数据文件目录，用于存放数据库文件、示例数据等
DATA_DIR = os.path.join(_REPO_ROOT, "data")

# ENV_PATH：环境变量文件路径，用于存放 API Key 等敏感配置
ENV_PATH = os.path.join(_REPO_ROOT, ".env")


# -----------------------------------------------------------------------------
# 核心函数
# -----------------------------------------------------------------------------

def get_agent():
    """
    获取全局唯一的 SQL Agent 实例。

    采用懒加载模式：
    - 首次调用时检查实例是否存在
    - 若不存在，则创建新实例并缓存到全局变量
    - 后续调用直接返回缓存的实例

    线程安全：
    - 使用 _agent_lock 锁保护实例创建过程
    - 确保多线程并发时不会创建多个实例

    Returns:
        Agent: 已初始化的 SQL Agent 实例

    Example:
        agent = get_agent()
        result = agent.run("查询销售总额")
    """
    global _agent
    with _agent_lock:  # 加锁：确保线程安全
        if _agent is None:  # 双重检查锁定（Double-Checked Locking）
            # 动态导入 build_agent 函数，避免循环导入
            from sql_agent import build_agent
            # 使用项目根目录下的配置和数据目录初始化 Agent
            _agent = build_agent(
                config_dir=CONFIG_DIR,  # 配置文件目录
                data_dir=DATA_DIR,      # 数据文件目录
                env_file=ENV_PATH       # 环境变量文件
            )
    return _agent


def reset_agent():
    """
    重置全局 Agent 实例。

    调用此函数后：
    - 将全局 _agent 置为 None
    - 下次调用 get_agent() 时会重新创建实例

    使用场景：
    - 配置文件发生变更（如数据库连接信息改变）
    - 需要重新加载 Agent 的某些运行时状态
    - 调试时强制重新初始化

    注意：不会立即销毁旧实例，旧实例会被 Python 垃圾回收
    """
    global _agent
    with _agent_lock:  # 加锁：确保线程安全
        _agent = None  # 重置为 None，下次 get_agent() 会重新创建
