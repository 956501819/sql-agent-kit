import yaml
from pathlib import Path


class SchemaAnnotator:
    """
    语义注释层：将 schema_annotations.yaml 中的业务含义注入到表结构中
    这是提升 SQL 生成准确率的核心差异化功能

    解决的问题：
    - 企业数据库字段名语义模糊（如 ord_stat_cd、usr_id）
    - 枚举值含义不明（如 status=1/2/3/4/5 各代表什么）
    - 多表关联关系不直观
    """

    def __init__(self, annotation_path: str):
        self._annotations = {}
        path = Path(annotation_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self._annotations = data.get("tables", {})

    def annotate(self, schema: dict[str, dict]) -> dict[str, dict]:
        """
        将注释信息合并到 schema 中
        :param schema: SchemaLoader 返回的原始表结构
        :return: 注入业务语义后的增强表结构
        """
        enriched = {}
        for table_name, table_info in schema.items():
            table_annotation = self._annotations.get(table_name, {})
            col_annotations = table_annotation.get("columns", {})

            enriched_columns = []
            for col in table_info["columns"]:
                col_name = col["name"]
                annotation = col_annotations.get(col_name, {})
                enriched_col = dict(col)
                # 如果有注释，追加到字段描述中
                if annotation:
                    desc = annotation if isinstance(annotation, str) else annotation.get("description", "")
                    enriched_col["description"] = desc
                enriched_columns.append(enriched_col)

            enriched[table_name] = {
                "description": table_annotation.get("description", ""),
                "columns": enriched_columns,
                "foreign_keys": table_info.get("foreign_keys", []),
            }

        return enriched

    def format_for_prompt(self, enriched_schema: dict[str, dict]) -> str:
        """
        将增强后的 schema 格式化为适合注入 Prompt 的文本
        """
        lines = []
        for table_name, info in enriched_schema.items():
            desc = info.get("description", "")
            header = f"表名: {table_name}"
            if desc:
                header += f"  // {desc}"
            lines.append(header)

            for col in info["columns"]:
                nullable = "可空" if col.get("nullable") else "非空"
                col_line = f"  - {col['name']} ({col['type']}, {nullable})"
                if col.get("description"):
                    col_line += f"  -- {col['description']}"
                lines.append(col_line)

            if info.get("foreign_keys"):
                for fk in info["foreign_keys"]:
                    lines.append(f"  [外键] {fk['column']} -> {fk['references']}")

            lines.append("")  # 表之间空一行

        return "\n".join(lines)
