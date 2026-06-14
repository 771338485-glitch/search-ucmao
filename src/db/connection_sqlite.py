import logging
from contextlib import contextmanager
from typing import Generator, Optional
import sqlite3
import os

from configs.app_config import sqlite_db_path

logger = logging.getLogger(__name__)


def get_db_connection() -> Optional[sqlite3.Connection]:
    """
    获取SQLite数据库连接
    """
    try:
        # 移除 check_same_thread=False，因为每次都是新连接
        conn = sqlite3.connect(sqlite_db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as err:
        logger.error(f"SQLite数据库连接失败: {err}")
        return None


@contextmanager
def db_cursor(dictionary: bool = False):
    """
    提供一个上下文管理器，统一管理连接与游标生命周期。
    使用示例：

        with db_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT ...")
            rows = cursor.fetchall()
    """
    conn = get_db_connection()
    if not conn:
        yield None
        return

    # 保存原始的 row_factory
    original_row_factory = conn.row_factory
    
    try:
        # 如果需要返回字典，设置 row_factory 为 sqlite3.Row 或自定义函数
        if dictionary:
            # 定义一个函数，将 sqlite3.Row 转换为字典
            def dict_factory(cursor, row):
                d = {}
                for idx, col in enumerate(cursor.description):
                    d[col[0]] = row[idx]
                return d
            conn.row_factory = dict_factory
        
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as err:
            logger.error(f"SQLite数据库操作出错: {err}")
            conn.rollback()
            raise
    finally:
        # 恢复原始的 row_factory
        if conn:
            conn.row_factory = original_row_factory
        # 安全关闭 cursor
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                logger.error(f"关闭 cursor 失败: {e}")
        # 关闭连接
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"关闭数据库连接失败: {e}")
