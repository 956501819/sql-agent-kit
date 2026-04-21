from tabulate import tabulate


class ResultFormatter:
    """结果格式化器，将查询结果转换为可读的文本或表格"""

    def to_table(self, rows: list[dict], max_rows: int = 50) -> str:
        """格式化为 Markdown 表格"""
        if not rows:
            return "查询成功，返回 0 条记录。"

        display_rows = rows[:max_rows]
        headers = list(display_rows[0].keys())
        data = [[str(row.get(h, "")) for h in headers] for row in display_rows]

        table = tabulate(data, headers=headers, tablefmt="github")
        suffix = f"\n\n> 共 {len(rows)} 条记录" + (
            f"，已显示前 {max_rows} 条" if len(rows) > max_rows else ""
        )
        return table + suffix

    def to_summary(self, rows: list[dict]) -> str:
        """生成数据简要摘要（行数、列名）"""
        if not rows:
            return "查询成功，返回 0 条记录。"
        cols = list(rows[0].keys())
        return f"返回 {len(rows)} 条记录，字段：{', '.join(cols)}"
