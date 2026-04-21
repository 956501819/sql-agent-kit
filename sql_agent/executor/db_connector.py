import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from urllib.parse import quote_plus


def create_db_engine() -> Engine:
    """
    根据环境变量创建数据库连接引擎
    支持 MySQL、PostgreSQL、SQLite
    """
    db_type = os.getenv("DB_TYPE", "mysql").lower()

    if db_type == "sqlite":
        path = os.getenv("DB_SQLITE_PATH", "./data/local.db")
        return create_engine(f"sqlite:///{path}")

    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    # 对密码中的特殊字符进行 URL 编码
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    database = os.getenv("DB_NAME", "")

    if db_type == "postgresql":
        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    else:  # mysql (default)
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"

    return create_engine(
        url,
        pool_pre_ping=True,    # 自动检测连接是否存活
        pool_recycle=3600,     # 1小时回收连接，避免 MySQL 8小时断开
    )
