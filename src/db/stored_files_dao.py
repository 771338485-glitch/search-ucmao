import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from src.db.db import db_cursor, get_db_connection

logger = logging.getLogger(__name__)


def init_stored_files_table():
    """初始化存储文件表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS stored_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT NOT NULL,
        file_name TEXT NOT NULL,
        original_share_link TEXT NOT NULL,
        share_link TEXT NOT NULL,
        cloud_name TEXT NOT NULL,
        delete_status TEXT DEFAULT 'pending',
        delete_attempts INTEGER DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return
        
        try:
            cursor.execute(create_table_sql)
            logger.info("stored_files 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 stored_files 表失败: {e}")


def insert_stored_file(data: Dict) -> bool:
    """
    插入存储文件记录
    
    Args:
        data: 文件数据，包含 file_id, file_name, original_share_link, share_link, cloud_name
        
    Returns:
        是否插入成功
    """
    insert_sql = """
    INSERT INTO stored_files (file_id, file_name, original_share_link, share_link, cloud_name, delete_status, delete_attempts, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return False
        
        try:
            now = datetime.now()
            cursor.execute(insert_sql, (
                data.get('file_id'),
                data.get('file_name'),
                data.get('original_share_link'),
                data.get('share_link'),
                data.get('cloud_name'),
                'pending',
                0,
                now,
                now
            ))
            logger.info(f"成功插入存储文件: {data.get('file_name')}")
            return True
        except Exception as e:
            logger.error(f"插入存储文件失败: {e}")
            return False


def get_washed_link_by_original(original_share_link: str) -> Optional[Dict]:
    """
    根据原始分享链接获取已洗白的链接
    
    Args:
        original_share_link: 原始分享链接
        
    Returns:
        包含 share_link 和 file_id 的字典，或 None
    """
    select_sql = """
    SELECT share_link, file_id
    FROM stored_files
    WHERE original_share_link = %s
    ORDER BY created_at DESC
    LIMIT 1
    """
    
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return None
        
        try:
            cursor.execute(select_sql, (original_share_link,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"查询洗白链接失败: {e}")
            return None


def get_expired_files(expire_minutes: int = 15) -> List[Dict]:
    """
    获取过期的文件记录

    Args:
        expire_minutes: 过期时间（分钟）

    Returns:
        过期文件记录列表
    """
    # 使用参数化查询避免 SQL 注入风险
    # 包含 pending 和 failed（重试次数<3）的记录，避免 failed 记录永远不被重试
    select_sql = """
    SELECT id, file_id, file_name, cloud_name, delete_status, delete_attempts
    FROM stored_files
    WHERE delete_status IN ('pending', 'failed') AND delete_attempts < 3
      AND created_at < datetime('now', 'localtime', ?)
    ORDER BY created_at ASC
    """

    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []

        try:
            # 传递参数化的过期时间
            expire_param = f'-{expire_minutes} minutes'
            cursor.execute(select_sql, (expire_param,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"获取过期文件失败: {e}")
            return []


def delete_stored_files_by_ids(ids: List[int]) -> int:
    """
    根据ID列表删除存储文件记录
    
    Args:
        ids: ID列表
        
    Returns:
        删除的记录数
    """
    if not ids:
        return 0
    
    placeholders = ', '.join(['%s'] * len(ids))
    delete_sql = f"DELETE FROM stored_files WHERE id IN ({placeholders})"
    
    with db_cursor() as cursor:
        if cursor is None:
            return 0
        
        try:
            cursor.execute(delete_sql, ids)
            deleted_count = cursor.rowcount
            logger.info(f"删除了 {deleted_count} 条存储文件记录")
            return deleted_count
        except Exception as e:
            logger.error(f"删除存储文件记录失败: {e}")
            return 0


def delete_stored_file_by_original_link(original_share_link: str) -> int:
    """
    根据分享链接删除 stored_files 记录（同时匹配原始链接和洗白链接）。
    因为 del_share 可能接收到新链接或原链接，需要两边都查。
    """
    delete_sql = "DELETE FROM stored_files WHERE original_share_link = %s OR share_link = %s"

    with db_cursor(commit=True) as cursor:
        if cursor is None:
            return 0
        try:
            cursor.execute(delete_sql, (original_share_link, original_share_link))
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                logger.info(f"已清理 stored_files 缓存记录: {original_share_link}, 共 {deleted_count} 条")
            return deleted_count
        except Exception as e:
            logger.error(f"删除 stored_files 缓存记录失败: {e}")
            return 0


def update_delete_status(record_id: int, status: str, attempts: Optional[int] = None) -> bool:
    """
    更新删除状态
    
    Args:
        record_id: 记录ID
        status: 新状态
        attempts: 尝试次数（可选）
        
    Returns:
        是否更新成功
    """
    if attempts is not None:
        update_sql = """
        UPDATE stored_files
        SET delete_status = %s, delete_attempts = %s, updated_at = %s
        WHERE id = %s
        """
        params = (status, attempts, datetime.now(), record_id)
    else:
        update_sql = """
        UPDATE stored_files
        SET delete_status = %s, updated_at = %s
        WHERE id = %s
        """
        params = (status, datetime.now(), record_id)
    
    with db_cursor() as cursor:
        if cursor is None:
            return False
        
        try:
            cursor.execute(update_sql, params)
            if cursor.rowcount > 0:
                logger.info(f"成功更新记录 {record_id} 的删除状态为 {status}")
                return True
            return False
        except Exception as e:
            logger.error(f"更新删除状态失败: {e}")
            return False
