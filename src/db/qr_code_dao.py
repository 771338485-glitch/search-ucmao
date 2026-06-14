import logging
from typing import Dict, Optional, Tuple

from src.db.db import db_cursor

logger = logging.getLogger(__name__)

def init_qr_code_table():
    """初始化二维码表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS qr_code (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        expires_at DATETIME,
        notified INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return
        
        try:
            cursor.execute(create_table_sql)
            logger.info("qr_code 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 qr_code 表失败: {e}")


def insert_qr_code(record: Dict) -> Optional[int]:
    """
    插入二维码记录
    """
    file_name = record.get("file_name")
    file_path = record.get("file_path")
    file_size = record.get("file_size")
    expires_at = record.get("expires_at")

    sql = """
    INSERT INTO qr_code (file_name, file_path, file_size, expires_at)
    VALUES (%s, %s, %s, %s)
    """
    params = (file_name, file_path, file_size, expires_at)

    with db_cursor(commit=True) as cursor:
        if cursor is None:
            return None
        
        try:
            cursor.execute(sql, params)
            new_id = cursor.lastrowid
            logger.info(f"成功插入二维码记录: {file_name}, ID: {new_id}")
            return new_id
        except Exception as e:
            logger.error(f"插入二维码记录 {file_name} 失败: {e}")
            return None


def get_latest_qr_code() -> Optional[Dict]:
    """
    获取最新的二维码记录
    """
    sql = """
    SELECT id, upload_time, file_name, file_path, file_size, expires_at, notified
    FROM qr_code
    ORDER BY upload_time DESC
    LIMIT 1
    """
    
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return None
        
        try:
            cursor.execute(sql)
            row = cursor.fetchone()
            if row:
                logger.info(f"获取到最新二维码记录: {row}")
                return row
            logger.warning("qr_code 表中未找到任何记录")
            return None
        except Exception as e:
            logger.error(f"获取二维码记录失败: {e}")
            return None


def get_expiring_qr_codes(days: int = 5) -> list:
    """
    获取过期或已过期的二维码记录（过期当天或已过期）
    """
    sql = """
    SELECT id, upload_time, file_name, file_path, file_size, expires_at, notified
    FROM qr_code
    WHERE date(expires_at) <= date('now')
    """
    
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []
        
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            logger.info(f"获取到 {len(rows)} 条过期或已过期的二维码记录")
            return rows
        except Exception as e:
            logger.error(f"获取过期二维码记录失败: {e}")
            return []


def mark_as_notified(qr_code_id: int) -> bool:
    """
    标记二维码记录为已通知
    """
    sql = """
    UPDATE qr_code
    SET notified = 1, updated_at = CURRENT_TIMESTAMP
    WHERE id = %s
    """
    
    with db_cursor(commit=True) as cursor:
        if cursor is None:
            return False
        
        try:
            cursor.execute(sql, (qr_code_id,))
            if cursor.rowcount > 0:
                logger.info(f"成功标记二维码记录 {qr_code_id} 为已通知")
                return True
            logger.warning(f"未找到二维码记录 {qr_code_id}")
            return False
        except Exception as e:
            logger.error(f"标记二维码记录为已通知失败: {e}")
            return False


def update_qr_code_expiry(qr_code_id: int, expires_at) -> bool:
    """
    更新二维码过期时间
    """
    sql = """
    UPDATE qr_code
    SET expires_at = %s, updated_at = CURRENT_TIMESTAMP
    WHERE id = %s
    """
    
    with db_cursor(commit=True) as cursor:
        if cursor is None:
            return False
        
        try:
            cursor.execute(sql, (expires_at, qr_code_id))
            if cursor.rowcount > 0:
                logger.info(f"成功更新二维码记录 {qr_code_id} 的过期时间")
                return True
            logger.warning(f"未找到二维码记录 {qr_code_id}")
            return False
        except Exception as e:
            logger.error(f"更新二维码过期时间失败: {e}")
            return False


def upsert_qr_code(record: Dict) -> Optional[int]:
    """
    更新或插入二维码记录（如果有最新记录则更新，否则插入）
    """
    file_name = record.get("file_name")
    file_path = record.get("file_path")
    file_size = record.get("file_size")
    expires_at = record.get("expires_at")
    
    # 先获取最新的记录
    latest = get_latest_qr_code()
    
    if latest:
        # 更新现有记录
        sql = """
        UPDATE qr_code
        SET file_name = %s, file_path = %s, file_size = %s, expires_at = %s, 
            notified = 0, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """
        params = (file_name, file_path, file_size, expires_at, latest['id'])
        
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return None
            
            try:
                cursor.execute(sql, params)
                logger.info(f"成功更新二维码记录: {file_name}, ID: {latest['id']}")
                return latest['id']
            except Exception as e:
                logger.error(f"更新二维码记录 {file_name} 失败: {e}")
                return None
    else:
        # 插入新记录
        return insert_qr_code(record)
