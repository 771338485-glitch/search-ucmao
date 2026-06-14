import logging
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from src.db.db import db_cursor

logger = logging.getLogger(__name__)


def init_search_history_table():
    """初始化搜索历史表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip_address TEXT NOT NULL,
        search_keyword TEXT NOT NULL,
        search_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return

        try:
            cursor.execute(create_table_sql)
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_search_time ON search_history(search_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_search_keyword ON search_history(search_keyword)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_ip_address ON search_history(ip_address)")
            logger.info("search_history 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 search_history 表失败: {e}")


def add_search_history(ip_address: str, search_keyword: str) -> bool:
    """
    添加搜索历史记录
    
    Args:
        ip_address: 用户 IP 地址
        search_keyword: 搜索关键词
        
    Returns:
        是否添加成功
    """
    insert_sql = """
    INSERT INTO search_history (ip_address, search_keyword, search_time)
    VALUES (%s, %s, %s)
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return False

        try:
            cursor.execute(insert_sql, (ip_address, search_keyword, datetime.now()))
            logger.info(f"添加搜索历史成功: IP={ip_address}, 关键词={search_keyword}")
            return True
        except Exception as e:
            logger.error(f"添加搜索历史失败: {e}")
            return False


def get_search_history(
    limit: int = 100,
    offset: int = 0
) -> List[Tuple[int, str, str, datetime]]:
    """
    获取搜索历史记录
    
    Args:
        limit: 返回记录数限制
        offset: 偏移量
        
    Returns:
        搜索历史记录列表 [(id, ip_address, search_keyword, search_time), ...]
    """
    select_sql = """
    SELECT id, ip_address, search_keyword, search_time
    FROM search_history
    ORDER BY search_time DESC
    LIMIT %s OFFSET %s
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return []

        try:
            cursor.execute(select_sql, (limit, offset))
            results = cursor.fetchall()
            return results
        except Exception as e:
            logger.error(f"获取搜索历史失败: {e}")
            return []


def get_search_history_count() -> int:
    """
    获取搜索历史记录总数
    
    Returns:
        记录总数
    """
    with db_cursor() as cursor:
        if cursor is None:
            return 0

        try:
            count_sql = "SELECT COUNT(*) FROM search_history"
            cursor.execute(count_sql)
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"获取搜索历史总数失败: {e}")
            return 0


def get_search_keyword_stats(limit: int = 20) -> List[Tuple[str, int]]:
    """
    获取搜索关键词统计（按搜索次数排序）
    
    Args:
        limit: 返回关键词数量限制
        
    Returns:
        关键词统计列表 [(search_keyword, count), ...]
    """
    stats_sql = """
    SELECT search_keyword, COUNT(*) as count
    FROM search_history
    GROUP BY search_keyword
    ORDER BY count DESC
    LIMIT %s
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return []

        try:
            cursor.execute(stats_sql, (limit,))
            results = cursor.fetchall()
            return results
        except Exception as e:
            logger.error(f"获取搜索关键词统计失败: {e}")
            return []


def delete_old_search_history(days: int = 30) -> int:
    """
    删除指定天数前的搜索历史记录
    
    Args:
        days: 保留天数
        
    Returns:
        删除的记录数
    """
    delete_sql = """
    DELETE FROM search_history
    WHERE search_time < %s
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return 0

        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            cursor.execute(delete_sql, (cutoff_time,))
            deleted_count = cursor.rowcount
            logger.info(f"删除 {days} 天前的搜索历史，共删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            logger.error(f"删除旧搜索历史失败: {e}")
            return 0


def get_daily_visitor_count() -> int:
    """
    获取当日去重访客数（按IP统计）
    
    Returns:
        当日访客数
    """
    count_sql = """
    SELECT COUNT(DISTINCT ip_address) 
    FROM search_history 
    WHERE date(search_time) = date('now')
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return 0

        try:
            cursor.execute(count_sql)
            result = cursor.fetchone()
            count = result[0] if result else 0
            logger.info(f"今日访客数: {count}")
            return count
        except Exception as e:
            logger.error(f"获取今日访客数失败: {e}")
            return 0


def get_yesterday_visitor_count() -> int:
    """
    获取昨日去重访客数（按IP统计）
    
    Returns:
        昨日访客数
    """
    count_sql = """
    SELECT COUNT(DISTINCT ip_address) 
    FROM search_history 
    WHERE date(search_time) = date('now', '-1 day')
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return 0

        try:
            cursor.execute(count_sql)
            result = cursor.fetchone()
            count = result[0] if result else 0
            logger.info(f"昨日访客数: {count}")
            return count
        except Exception as e:
            logger.error(f"获取昨日访客数失败: {e}")
            return 0


def get_last_7_days_visitor_count() -> int:
    """
    获取近7天去重访客数（按IP统计）
    
    Returns:
        近7天访客数
    """
    count_sql = """
    SELECT COUNT(DISTINCT ip_address) 
    FROM search_history 
    WHERE date(search_time) >= date('now', '-6 days')
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return 0

        try:
            cursor.execute(count_sql)
            result = cursor.fetchone()
            count = result[0] if result else 0
            logger.info(f"近7天访客数: {count}")
            return count
        except Exception as e:
            logger.error(f"获取近7天访客数失败: {e}")
            return 0


def get_last_30_days_visitor_count() -> int:
    """
    获取近30天去重访客数（按IP统计）
    
    Returns:
        近30天访客数
    """
    count_sql = """
    SELECT COUNT(DISTINCT ip_address) 
    FROM search_history 
    WHERE date(search_time) >= date('now', '-29 days')
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return 0

        try:
            cursor.execute(count_sql)
            result = cursor.fetchone()
            count = result[0] if result else 0
            logger.info(f"近30天访客数: {count}")
            return count
        except Exception as e:
            logger.error(f"获取近30天访客数失败: {e}")
            return 0
