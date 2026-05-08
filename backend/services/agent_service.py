"""
Thread-safe singleton for SQLAgent.
Reset after any config change so the next request picks up new settings.
"""

import os
import threading

_agent = None
_agent_lock = threading.Lock()

# Absolute paths so the agent works regardless of cwd
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_DIR = os.path.join(_REPO_ROOT, "config")
DATA_DIR = os.path.join(_REPO_ROOT, "data")
ENV_PATH = os.path.join(_REPO_ROOT, ".env")


def get_agent():
    global _agent
    with _agent_lock:
        if _agent is None:
            from sql_agent import build_agent
            _agent = build_agent(config_dir=CONFIG_DIR, data_dir=DATA_DIR, env_file=ENV_PATH)
    return _agent


def reset_agent():
    global _agent
    with _agent_lock:
        _agent = None
