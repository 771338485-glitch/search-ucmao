import logging
from typing import Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

from src.db.connection_sqlite import db_cursor as _db_cursor, get_db_connection
logger.info("使用SQLite数据库")


def adapt_sql(query: str, params: tuple = ()) -> tuple[str, tuple]:
    """
    适配SQL语法（SQLite使用?）
    """
    query = query.replace('%s', '?')
    return query, params


def adapt_random() -> str:
    """
    SQLite随机函数
    """
    return 'RANDOM()'


def get_last_insert_id(cursor) -> Any:
    """
    获取最后插入的ID
    """
    return cursor.lastrowid


class CursorWrapper:
    """游标包装器，自动适配SQL语法"""
    def __init__(self, cursor):
        self.cursor = cursor
    
    def execute(self, query, params=None):
        if params is None:
            params = ()
        adapted_query, adapted_params = adapt_sql(query, params)
        return self.cursor.execute(adapted_query, adapted_params)
    
    def executemany(self, query, param_list):
        adapted_query, _ = adapt_sql(query, ())
        return self.cursor.executemany(adapted_query, param_list)
    
    def __getattr__(self, name):
        return getattr(self.cursor, name)


@contextmanager
def db_cursor(dictionary: bool = False, commit: bool = True):
    """
    提供一个上下文管理器，统一管理连接与游标生命周期，并自动适配SQL语法
    """
    with _db_cursor(dictionary=dictionary) as cursor:
        if cursor is None:
            yield None
        else:
            yield CursorWrapper(cursor)


__all__ = ['db_cursor', 'get_db_connection', 'adapt_sql', 'adapt_random', 'get_last_insert_id']
