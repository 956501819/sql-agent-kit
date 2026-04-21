"""
QuickStart：5 分钟跑通 sql-agent-kit

步骤：
1. cp .env.example .env  → 填入你的 API Key 和数据库配置
2. 修改 config/tables.yaml → 添加你的表名
3. 修改 config/schema_annotations.yaml → 填写字段业务含义（可选但强烈推荐）
4. python examples/quickstart.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from sql_agent import build_agent

console = Console()


def run_demo():
    console.print(Panel(
        "[bold cyan]sql-agent-kit QuickStart[/bold cyan]\n"
        "Text-to-SQL Agent 演示",
        border_style="cyan"
    ))

    # 构建 Agent（自动读取 config/ 目录配置）
    console.print("\n[yellow]正在初始化 Agent...[/yellow]")
    try:
        agent = build_agent()
        console.print("[green]✓ Agent 初始化成功[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ 初始化失败: {e}[/red]")
        console.print("[dim]请检查 .env 文件中的数据库连接和 API Key 配置[/dim]")
        return

    # 示例问题列表（根据你的数据库调整）
    questions = [
        "查询所有用户的数量",
        "过去7天内每天的订单数量是多少？",
        "销售额最高的前5个商品是什么？",
        "有哪些用户下单超过3次？",
    ]

    for question in questions:
        console.print(f"[bold]问题:[/bold] {question}")

        result = agent.query(question)

        if result.need_confirm:
            console.print(f"[yellow]⚠ {result.error}[/yellow]")
            console.print(f"[dim]生成的 SQL:[/dim]\n{result.sql}\n")

        elif result.success:
            console.print(f"[dim]生成的 SQL:[/dim]\n[cyan]{result.sql}[/cyan]")
            if result.retry_count > 0:
                console.print(f"[yellow]（经过 {result.retry_count} 次重试）[/yellow]")
            console.print(f"\n[bold]查询结果:[/bold]")
            console.print(result.formatted_table)
            console.print(f"[dim]置信度: {result.confidence:.0%}[/dim]\n")

        else:
            console.print(f"[red]✗ 查询失败: {result.error}[/red]")
            if result.sql:
                console.print(f"[dim]最后生成的 SQL:[/dim]\n{result.sql}\n")

        console.print("─" * 60)

    # 交互模式
    console.print("\n[bold cyan]进入交互模式，输入问题直接查询（输入 exit 退出）[/bold cyan]\n")
    while True:
        try:
            question = console.input("[bold]> [/bold]").strip()
            if question.lower() in ("exit", "quit", "q"):
                break
            if not question:
                continue

            result = agent.query(question)

            if result.need_confirm:
                console.print(f"[yellow]置信度较低，建议确认以下 SQL 再手动执行:[/yellow]")
                console.print(f"[cyan]{result.sql}[/cyan]\n")
            elif result.success:
                console.print(f"[dim]SQL:[/dim] [cyan]{result.sql}[/cyan]")
                console.print(result.formatted_table + "\n")
            else:
                console.print(f"[red]失败: {result.error}[/red]\n")

        except KeyboardInterrupt:
            break

    console.print("\n[dim]再见！[/dim]")


if __name__ == "__main__":
    run_demo()
