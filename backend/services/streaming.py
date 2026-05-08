"""
SSE streaming runner for the multi-agent pipeline.

Strategy: rebuild the LangGraph graph with each node function wrapped.
The wrapper diffs process_log before/after each node call and pushes
new entries into an asyncio.Queue via run_coroutine_threadsafe.
The pipeline runs in a ThreadPoolExecutor thread; the FastAPI endpoint
drains the queue and yields SSE chunks.

Zero changes to sql_agent/ package required.
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator

from sql_agent.multi.planner import planner_node
from sql_agent.multi.sql_node import sql_node
from sql_agent.multi.chart import chart_node
from sql_agent.multi.summary import summary_node
from sql_agent.multi.judge import judge_node
from sql_agent.multi.state import GraphState
from sql_agent.graph.pipeline import _route_after_sql

_executor = ThreadPoolExecutor(max_workers=4)
logger = logging.getLogger(__name__)

PIPELINE_TIMEOUT = 120  # 整个管道最长允许运行秒数


def _wrap_node(node_fn, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop, source: str = ""):
    """Wrap a LangGraph node to emit new process_log entries as SSE log events."""
    def wrapped(state: GraphState) -> GraphState:
        prev_len = len(state.get("process_log") or [])
        new_state = node_fn(state)
        new_log = new_state.get("process_log") or []
        for entry in new_log[prev_len:]:
            asyncio.run_coroutine_threadsafe(
                queue.put({"type": "log", "text": entry, "source": source}),
                loop,
            )
        return new_state
    return wrapped


def _build_streaming_pipeline(queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    from langgraph.graph import StateGraph, END

    graph = StateGraph(GraphState)
    graph.add_node("planner",      _wrap_node(planner_node,  queue, loop, source="planner"))
    graph.add_node("sql_agent",    _wrap_node(sql_node,      queue, loop, source="sql"))
    graph.add_node("chart_agent",  _wrap_node(chart_node,    queue, loop, source="chart"))
    graph.add_node("summary_agent",_wrap_node(summary_node,  queue, loop, source="summary"))
    graph.add_node("judge_agent",  _wrap_node(judge_node,    queue, loop, source="judge"))

    graph.set_entry_point("planner")
    graph.add_edge("planner", "sql_agent")
    graph.add_conditional_edges(
        "sql_agent",
        _route_after_sql,
        {"ok": "chart_agent", "error": END},
    )
    graph.add_edge("chart_agent", "summary_agent")
    graph.add_edge("summary_agent", "judge_agent")
    graph.add_edge("judge_agent", END)
    return graph.compile()


async def run_pipeline_streaming(question: str) -> AsyncGenerator[dict, None]:
    """
    Runs the multi-agent pipeline in a thread pool, yielding SSE-compatible dicts:
      {"type": "log",    "text": str}
      {"type": "result", "sql": ..., "data": ..., "chart_json": ..., "summary": ..., "judge_scores": ..., "error": ...}
      {"type": "error",  "message": str}
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    result_holder: dict = {}
    thread_done = asyncio.Event()

    pipeline = _build_streaming_pipeline(queue, loop)

    def run_in_thread():
        try:
            state = pipeline.invoke({"question": question, "process_log": []})
            result_holder["state"] = state
            logger.info(f"[pipeline] done, sql_results={len(state.get('sql_results') or [])}, chart_json={'yes' if state.get('chart_json') else 'no'}")
        except Exception as e:
            logger.exception(f"[pipeline] error: {e}")
            result_holder["error"] = str(e)
        finally:
            asyncio.run_coroutine_threadsafe(queue.put({"type": "_done"}), loop)
            loop.call_soon_threadsafe(thread_done.set)

    future = loop.run_in_executor(_executor, run_in_thread)
    deadline = loop.time() + PIPELINE_TIMEOUT

    # Drain queue until sentinel or timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            logger.warning("[pipeline] global timeout reached, aborting")
            future.cancel()
            yield {"type": "error", "message": f"分析超时（超过 {PIPELINE_TIMEOUT} 秒），请简化问题后重试"}
            return

        try:
            item = await asyncio.wait_for(queue.get(), timeout=min(15.0, remaining))
        except asyncio.TimeoutError:
            # 心跳前先检查线程是否已结束（防止线程崩溃后无限心跳）
            if thread_done.is_set():
                break
            yield {"type": "_heartbeat"}
            continue

        if item["type"] == "_done":
            break
        yield item

    await future  # ensure thread cleanup

    if "error" in result_holder:
        yield {"type": "error", "message": result_holder["error"]}
        return

    state = result_holder.get("state", {})
    sql_results = state.get("sql_results") or []
    chart_source_index = state.get("chart_source_index", 0)

    # 构建每个子问题的结果，截断超大数据
    results_payload = []
    for r in sql_results:
        data = r.get("data", [])
        truncated = len(data) > 500
        results_payload.append({
            "question": r.get("question", ""),
            "sql": r.get("sql", ""),
            "success": r.get("success", False),
            "data": data[:500] if truncated else data,
            "truncated": truncated,
            "error": r.get("error", ""),
            "confidence": r.get("confidence", 0.0),
        })

    # Send chart as a separate event
    chart_json_str = state.get("chart_json", "")
    if chart_json_str:
        try:
            chart_obj = json.loads(chart_json_str)
            yield {"type": "chart", "chart": chart_obj, "chart_source_index": chart_source_index}
        except Exception as e:
            logger.warning(f"[pipeline] chart JSON parse failed: {e}")

    yield {
        "type": "result",
        "sql_results": results_payload,
        "chart_source_index": chart_source_index,
        "chart_hint": state.get("chart_hint", {}),
        "summary": state.get("summary", ""),
        "judge_scores": state.get("judge_scores", {}),
        "error": state.get("error", ""),
    }
