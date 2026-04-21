import re


# 危险操作关键词（只允许 SELECT）
_FORBIDDEN_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bxp_\w+",        # SQL Server 扩展存储过程
    r"\bINTO\s+OUTFILE", # MySQL 写文件
    r"\bLOAD_FILE\b",
]

_FORBIDDEN_RE = re.compile(
    "|".join(_FORBIDDEN_PATTERNS),
    re.IGNORECASE,
)


class SafetyValidator:
    """
    SQL 安全校验器
    只允许 SELECT 查询，过滤所有写操作和危险函数
    防止 SQL 注入和数据泄露
    """

    def validate(self, sql: str) -> tuple[bool, str]:
        """
        :return: (is_safe, reason)
        """
        sql_stripped = sql.strip()

        # 必须以 SELECT 开头（允许前置注释）
        sql_no_comment = re.sub(r"/\*.*?\*/", "", sql_stripped, flags=re.DOTALL)
        sql_no_comment = re.sub(r"--[^\n]*", "", sql_no_comment)
        first_token = sql_no_comment.strip().split()[0].upper() if sql_no_comment.strip() else ""

        if first_token != "SELECT":
            return False, f"只允许 SELECT 查询，检测到操作类型: {first_token}"

        # 检查危险关键词
        match = _FORBIDDEN_RE.search(sql)
        if match:
            return False, f"检测到危险操作关键词: {match.group()}"

        # 检查分号（防止多语句注入）
        # 允许最后一个分号，但不允许中间有分号
        sql_no_strings = re.sub(r"'[^']*'", "''", sql)
        semicolons = [i for i, c in enumerate(sql_no_strings) if c == ";"]
        if len(semicolons) > 1 or (
            len(semicolons) == 1 and semicolons[0] < len(sql_no_strings.rstrip()) - 1
        ):
            return False, "检测到多语句注入风险（多个分号）"

        return True, "OK"
