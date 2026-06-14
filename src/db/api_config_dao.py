import logging
from typing import Any, Dict, List, Optional, Tuple

from src.db.db import db_cursor

logger = logging.getLogger(__name__)


def init_api_config_table():
    """初始化API配置表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS api_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        url TEXT NOT NULL,
        method TEXT DEFAULT 'GET',
        request TEXT,
        response TEXT,
        status INTEGER DEFAULT 1,
        is_enabled INTEGER DEFAULT 1,
        response_time_ms INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return
        
        try:
            cursor.execute(create_table_sql)
            logger.info("api_config 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 api_config 表失败: {e}")


def get_all_configs(order_by_created: bool = True) -> List[Dict[str, Any]]:
    """
    从数据库中读取所有 API 配置。
    order_by_created=True: 按创建时间倒序（用于后台管理）
    order_by_created=False: 不排序（用于搜索服务）
    """
    if order_by_created:
        query = (
            "SELECT id, name, url, method, request, response, status, "
            "is_enabled, response_time_ms, created_at, updated_at "
            "FROM api_config ORDER BY created_at DESC"
        )
    else:
        query = (
            "SELECT id, name, url, method, request, response, status, "
            "is_enabled, response_time_ms FROM api_config"
        )

    try:
        with db_cursor(dictionary=True) as cursor:
            if cursor is None:
                return []
                
            cursor.execute(query)
            results = cursor.fetchall()
            
            configs = []
            for row in results:
                config = {
                    "id": row["id"],
                    "name": row["name"],
                    "url": row["url"],
                    "method": row["method"],
                    "request": row["request"] if row["request"] is not None else "{}",
                    "response": row["response"] if row["response"] is not None else "[]",
                    "status": bool(row["status"]),
                    "is_enabled": bool(row["is_enabled"]),
                    "response_time_ms": row["response_time_ms"] if row["response_time_ms"] is not None else (0 if order_by_created else 9999),
                }
                if order_by_created:
                    config["created_at"] = str(row["created_at"])
                    config["updated_at"] = str(row["updated_at"])
                configs.append(config)
                
            return configs
    except Exception as err:
        logger.error(f"查询 API 配置时出错: {err}")
        return []


def get_config_by_id(api_id: int) -> Optional[Dict[str, Any]]:
    """根据 ID 获取单个 API 配置（用于测试）。"""
    try:
        with db_cursor(dictionary=True) as cursor:
            if cursor is None:
                return None
                
            cursor.execute("SELECT * FROM api_config WHERE id = %s", (api_id,))
            config = cursor.fetchone()
            return config
    except Exception as err:
        logger.error(f"查询 API 配置时出错: {err}")
        return None


def get_config_status(api_id: int) -> Optional[Dict[str, bool]]:
    """从数据库中获取单个 API 的 status 和 is_enabled 状态"""
    query = "SELECT status, is_enabled FROM api_config WHERE id = %s"
    try:
        with db_cursor(dictionary=True) as cursor:
            if cursor is None:
                return None
                
            cursor.execute(query, (api_id,))
            result = cursor.fetchone()
            if result:
                result["status"] = bool(result["status"])
                result["is_enabled"] = bool(result["is_enabled"])
            return result
    except Exception as err:
        logger.error(f"查询 API 状态时出错: {err}")
        return None


def insert_config(new_config: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
    """向数据库中添加一条 API 配置记录"""
    query = (
        "INSERT INTO api_config (name, url, method, request, response, status, "
        "is_enabled, response_time_ms) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    )
    status = new_config.get("status")
    if status is None:
        status_value = 1
    else:
        status_value = 1 if status else 0
    
    is_enabled = new_config.get("is_enabled")
    if is_enabled is None:
        is_enabled_value = 1
    else:
        is_enabled_value = 1 if is_enabled else 0
    
    params = (
        new_config["name"],
        new_config["url"],
        new_config["method"],
        new_config.get("request", "{}"),
        new_config.get("response", "[]"),
        status_value,
        is_enabled_value,
        0,
    )

    try:
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return False, "数据库连接失败", None
                
            cursor.execute(query, params)
            new_id = cursor.lastrowid
            logger.info(f"成功添加新的 API 配置 ID: {new_id}")
            return True, "API 配置添加成功", new_id
    except Exception as err:
        logger.error(f"添加 API 配置时出错: {err}")
        return False, f"API 配置添加失败: {err}", None


def copy_config(api_id: int) -> Tuple[bool, str, Optional[int]]:
    """在数据库中复制一条 API 配置记录"""
    select_query = (
        "SELECT name, url, method, request, response, status, is_enabled, response_time_ms "
        "FROM api_config WHERE id = %s"
    )

    try:
        with db_cursor(dictionary=True) as cursor:
            if cursor is None:
                return False, "数据库连接失败", None
                
            cursor.execute(select_query, (api_id,))
            original_config = cursor.fetchone()

            if not original_config:
                logger.warning(f"尝试复制 ID 为 {api_id} 的 API 配置，但未找到该配置")
                return False, "未找到该 API 配置", None

            new_name = f"{original_config['name']}_副本"
            insert_query = (
                "INSERT INTO api_config (name, url, method, request, response, status, "
                "is_enabled, response_time_ms) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            )
            insert_params = (
                new_name,
                original_config["url"],
                original_config["method"],
                original_config["request"],
                original_config["response"],
                original_config["status"],
                original_config["is_enabled"],
                original_config["response_time_ms"],
            )

            cursor.execute(insert_query, insert_params)
            new_id = cursor.lastrowid
            logger.info(f"成功复制 ID 为 {api_id} 的 API 配置，新 ID: {new_id}")
            return True, "API 配置复制成功", new_id
    except Exception as err:
        logger.error(f"复制 API 配置时出错: {err}")
        return False, f"API 配置复制失败: {err}", None


def update_config(api_id: int, updated_config: Dict[str, Any]) -> Tuple[bool, str]:
    """更新一条 API 配置记录"""
    new_is_enabled = bool(updated_config.get("is_enabled"))

    if new_is_enabled:
        current_api_status = get_config_status(api_id)
        if current_api_status is None:
            return False, "未找到该 API 配置"

        if not current_api_status["status"]:
            logger.warning(f"尝试修改 API ID:{api_id}，但无法在异常状态下启用")
            return False, "API 状态异常，无法启用。请先测试并修复。"

    status = updated_config.get("status")
    if status is None:
        status_value = 1
    else:
        status_value = 1 if status else 0
    
    query = """
    UPDATE api_config 
    SET name = %s, url = %s, method = %s, request = %s, response = %s, status = %s, is_enabled = %s
    WHERE id = %s
    """
    params = (
        updated_config["name"],
        updated_config["url"],
        updated_config["method"],
        updated_config.get("request", "{}"),
        updated_config.get("response", "[]"),
        status_value,
        1 if new_is_enabled else 0,
        api_id,
    )

    try:
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return False, "数据库连接失败"
                
            cursor.execute(query, params)
            if cursor.rowcount > 0:
                logger.info(f"成功修改 ID 为 {api_id} 的 API 配置")
                return True, "API 配置修改成功"
            logger.warning(f"尝试修改 ID 为 {api_id} 的 API 配置，但未找到或数据未变化")
            return False, "未找到该 API 配置或数据未变化"
    except Exception as err:
        logger.error(f"修改 API 配置时出错: {err}")
        return False, f"API 配置修改失败: {err}"


def delete_config(api_id: int) -> Tuple[bool, str]:
    """删除一条 API 配置记录"""
    query = "DELETE FROM api_config WHERE id = %s"

    try:
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return False, "数据库连接失败"
                
            cursor.execute(query, (api_id,))
            if cursor.rowcount > 0:
                logger.info(f"成功删除 ID 为 {api_id} 的 API 配置")
                return True, "API 配置删除成功"
            logger.warning(f"尝试删除 ID 为 {api_id} 的 API 配置，但未找到该配置")
            return False, "未找到该 API 配置"
    except Exception as err:
        logger.error(f"删除 API 配置时出错: {err}")
        return False, f"API 配置删除失败: {err}"


def update_status(api_id: int, new_status: bool, response_time_ms: int = 0) -> bool:
    """更新 API 配置的状态和响应时间 (不修改 is_enabled)"""
    query = "UPDATE api_config SET status = %s, response_time_ms = %s WHERE id = %s"
    status_int = 1 if new_status else 0

    try:
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return False
                
            cursor.execute(query, (status_int, response_time_ms, api_id))
            logger.info(f"更新 API ID:{api_id} 的状态为 {new_status}，耗时: {response_time_ms}ms")
            return True
    except Exception as err:
        logger.error(f"更新 API 状态时出错: {err}")
        return False


def update_enabled_status(
    api_id: int, is_enabled: bool, new_status: Optional[bool] = None, response_time_ms: Optional[int] = None
) -> bool:
    """
    更新 API 配置的启用状态，可同时更新 status 和 response_time_ms。
    用于测试失败后，强制禁用 API。
    """
    fields = ["is_enabled = %s"]
    params = [1 if is_enabled else 0]

    if new_status is not None:
        fields.append("status = %s")
        params.append(1 if new_status else 0)

    if response_time_ms is not None:
        fields.append("response_time_ms = %s")
        params.append(response_time_ms)

    query = f"UPDATE api_config SET {', '.join(fields)} WHERE id = %s"
    params.append(api_id)

    try:
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return False
                
            cursor.execute(query, params)
            logger.info(f"更新 API ID:{api_id} 的 is_enabled={is_enabled}，status={new_status} (如果提供)")
            return True
    except Exception as err:
        logger.error(f"更新 API 启用状态时出错: {err}")
        return False


def set_enabled(api_id: int, is_enabled: bool) -> Tuple[bool, str]:
    """切换单个 API 的启用状态，限制异常状态下启用"""
    is_enabled = bool(is_enabled)

    if is_enabled:
        current_api_status = get_config_status(api_id)
        if current_api_status is None:
            return False, "未找到该 API 配置"

        if not current_api_status["status"]:
            logger.warning(f"尝试启用 API ID:{api_id} 失败，状态异常")
            return False, "API 状态异常，无法启用。请先测试并修复。"

    query = "UPDATE api_config SET is_enabled = %s WHERE id = %s"
    status_int = 1 if is_enabled else 0

    try:
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return False, "数据库连接失败"
                
            cursor.execute(query, (status_int, api_id))
            if cursor.rowcount > 0:
                logger.info(f"成功将 API ID:{api_id} 的启用状态设置为 {is_enabled}")
                return True, "API 启用状态更新成功"
            logger.warning(f"尝试更新 ID 为 {api_id} 的 API 启用状态，但未找到该配置")
            return False, "未找到该 API 配置"
    except Exception as err:
        logger.error(f"更新 API 启用状态时出错: {err}")
        return False, f"API 启用状态更新失败: {err}"


def enable_all_normal() -> Tuple[bool, str, int]:
    """一键启用所有【状态正常 (status=1)】的 API"""
    query = "UPDATE api_config SET is_enabled = 1 WHERE status = 1"

    try:
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return False, "数据库连接失败", 0
                
            cursor.execute(query)
            logger.info(f"成功一键启用所有【正常状态】的 API 配置，共更新 {cursor.rowcount} 条")
            return True, f"成功一键启用 {cursor.rowcount} 条【正常状态】的 API 配置", cursor.rowcount
    except Exception as err:
        logger.error(f"一键启用所有 API 时出错: {err}")
        return False, f"一键启用失败: {err}", 0


def disable_all() -> Tuple[bool, str, int]:
    """一键禁用所有 API"""
    query = "UPDATE api_config SET is_enabled = 0"

    try:
        with db_cursor(commit=True) as cursor:
            if cursor is None:
                return False, "数据库连接失败", 0
                
            cursor.execute(query)
            logger.info(f"成功一键禁用所有 API 配置，共更新 {cursor.rowcount} 条")
            return True, f"成功一键禁用 {cursor.rowcount} 条 API 配置", cursor.rowcount
    except Exception as err:
        logger.error(f"一键禁用所有 API 时出错: {err}")
        return False, f"一键禁用失败: {err}", 0
