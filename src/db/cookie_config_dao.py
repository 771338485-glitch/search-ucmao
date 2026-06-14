import logging
from typing import Any, Dict, List, Optional, Tuple

from src.db.db import db_cursor
from utils.encryption import encryption_utils

logger = logging.getLogger(__name__)


def init_cookie_config_table():
    """初始化Cookie配置表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS cookie_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cloud_name TEXT NOT NULL UNIQUE,
        cookie TEXT,
        cookie_encrypted TEXT,
        encryption_method TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return
        
        try:
            cursor.execute(create_table_sql)
            logger.info("cookie_config 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 cookie_config 表失败: {e}")


def get_all_cookies() -> List[Dict[str, Any]]:
    """
    从数据库中读取所有云盘Cookie配置。
    返回解密后的Cookie数据，隐藏加密信息。
    """
    try:
        with db_cursor(dictionary=True) as cursor:
            if cursor is None:
                return []
                
            cookies = []
            query = "SELECT id, cloud_name, cookie, cookie_encrypted, encryption_method, created_at, updated_at FROM cookie_config ORDER BY created_at DESC"
            cursor.execute(query)
            results = cursor.fetchall()

            for row in results:
                cookie = row["cookie"]
                if row.get("cookie_encrypted"):
                    decrypted_cookie = encryption_utils.decrypt(row["cookie_encrypted"])
                    if decrypted_cookie:
                        cookie = decrypted_cookie
                
                cookie_config = {
                    "id": row["id"],
                    "cloud_name": row["cloud_name"],
                    "cookie": cookie,
                    "encryption_method": row.get("encryption_method"),
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"])
                }
                cookies.append(cookie_config)
                
            return cookies
    except Exception as err:
        logger.error(f"查询云盘Cookie配置时出错: {err}")
        return []


def get_cookie_by_cloud_name(cloud_name: str) -> Optional[str]:
    """
    根据云盘名称获取对应的Cookie内容。
    优先使用加密的Cookie数据。
    """
    try:
        with db_cursor(dictionary=True) as cursor:
            if cursor is None:
                return None
                
            query = "SELECT cookie, cookie_encrypted FROM cookie_config WHERE cloud_name = %s"
            cursor.execute(query, (cloud_name,))
            result = cursor.fetchone()
            if not result:
                return None
            
            if result.get("cookie_encrypted"):
                decrypted_cookie = encryption_utils.decrypt(result["cookie_encrypted"])
                if decrypted_cookie:
                    return decrypted_cookie
            
            return result.get("cookie")
    except Exception as err:
        logger.error(f"根据云盘名称查询Cookie时出错: {err}")
        return None


def save_cookie(cloud_name: str, cookie: str) -> Tuple[bool, str]:
    """
    保存或更新云盘Cookie配置。
    如果存在相同的cloud_name，则更新；否则插入新记录。
    同时保存明文和加密的Cookie数据。
    """
    try:
        with db_cursor(dictionary=True) as cursor:
            if cursor is None:
                return False, "数据库连接失败"
                
            query = "SELECT id FROM cookie_config WHERE cloud_name = %s"
            cursor.execute(query, (cloud_name,))
            existing_record = cursor.fetchone() is not None
            
            encrypted_cookie = encryption_utils.encrypt(cookie)
            action = "添加"
            
            if existing_record:
                query = "UPDATE cookie_config SET cookie = %s, cookie_encrypted = %s, encryption_method = %s, updated_at = CURRENT_TIMESTAMP WHERE cloud_name = %s"
                params = (cookie, encrypted_cookie, "AES-256-CBC", cloud_name)
                action = "更新"
            else:
                query = "INSERT INTO cookie_config (cloud_name, cookie, cookie_encrypted, encryption_method) VALUES (%s, %s, %s, %s)"
                params = (cloud_name, cookie, encrypted_cookie, "AES-256-CBC")
                action = "添加"
            
            cursor.execute(query, params)
            logger.info(f"成功{action}云盘'{cloud_name}'的Cookie配置")
            return True, f"云盘Cookie配置{action}成功"
    except Exception as err:
        logger.error(f"保存云盘Cookie配置时出错: {err}")
        return False, f"云盘Cookie配置保存失败: {err}"


def delete_cookie(cloud_name: str) -> Tuple[bool, str]:
    """
    根据云盘名称删除Cookie配置。
    """
    try:
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return False, "数据库连接失败"
                
            query = "DELETE FROM cookie_config WHERE cloud_name = %s"
            cursor.execute(query, (cloud_name,))
            
            if cursor.rowcount > 0:
                logger.info(f"成功删除云盘'{cloud_name}'的Cookie配置")
                return True, "云盘Cookie配置删除成功"
            else:
                logger.warning(f"尝试删除云盘'{cloud_name}'的Cookie配置，但未找到该记录")
                return False, "未找到该云盘的Cookie配置"
    except Exception as err:
        logger.error(f"删除云盘Cookie配置时出错: {err}")
        return False, f"云盘Cookie配置删除失败: {err}"
