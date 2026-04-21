import sqlparse


class SyntaxValidator:
    """
    SQL 语法检查器
    利用 sqlparse 做基础语法解析，快速发现明显的语法错误
    注意：sqlparse 不做完整语义校验，真正的错误会在执行时暴露
    """

    def validate(self, sql: str) -> tuple[bool, str]:
        """
        :return: (is_valid, reason)
        """
        sql = sql.strip()
        if not sql:
            return False, "SQL 为空"

        try:
            statements = sqlparse.parse(sql)
            if not statements:
                return False, "无法解析 SQL"

            stmt = statements[0]

            # 检查是否有未闭合的括号
            open_parens = sql.count("(")
            close_parens = sql.count(")")
            if open_parens != close_parens:
                return False, f"括号不匹配：左括号 {open_parens} 个，右括号 {close_parens} 个"

            # 检查是否有未闭合的单引号（粗略检测）
            # 去掉转义的引号后计数
            cleaned = sql.replace("\\'", "").replace("''", "")
            if cleaned.count("'") % 2 != 0:
                return False, "单引号未正确闭合"

            return True, "OK"

        except Exception as e:
            return False, f"语法解析异常: {e}"
