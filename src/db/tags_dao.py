import logging
from typing import Any, Dict, List, Optional

from src.db.db import db_cursor

logger = logging.getLogger(__name__)


def init_tags_table():
    """初始化标签表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return
        
        try:
            cursor.execute(create_table_sql)
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
            logger.info("tags 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 tags 表失败: {e}")


def init_movie_tags_table():
    """初始化影视-标签关联表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS movie_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
        UNIQUE(movie_id, tag_id)
    )
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return
        
        try:
            cursor.execute(create_table_sql)
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movie_tags_movie_id ON movie_tags(movie_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movie_tags_tag_id ON movie_tags(tag_id)")
            logger.info("movie_tags 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 movie_tags 表失败: {e}")


def insert_tag(name: str) -> Optional[int]:
    """
    插入一个标签，返回新记录的 ID
    """
    sql = "INSERT INTO tags (name) VALUES (%s)"
    params = (name,)

    with db_cursor() as cursor:
        if cursor is None:
            return None
        
        try:
            cursor.execute(sql, params)
            new_id = cursor.lastrowid
            logger.info(f"成功插入标签: {name}, ID: {new_id}")
            return new_id
        except Exception as e:
            logger.error(f"插入标签 {name} 失败: {e}")
            return None


def get_tag_by_name(name: str) -> Optional[Dict[str, Any]]:
    """根据名称获取标签"""
    sql = "SELECT id, name, created_at FROM tags WHERE name = %s"
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return None
        try:
            cursor.execute(sql, (name,))
            row = cursor.fetchone()
            if row:
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
                return row
            return None
        except Exception as e:
            logger.error(f"获取标签失败: {e}")
            return None


def get_tag_by_id(tag_id: int) -> Optional[Dict[str, Any]]:
    """根据ID获取标签"""
    sql = "SELECT id, name, created_at FROM tags WHERE id = %s"
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return None
        try:
            cursor.execute(sql, (tag_id,))
            row = cursor.fetchone()
            if row:
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
                return row
            return None
        except Exception as e:
            logger.error(f"获取标签失败: {e}")
            return None


def get_all_tags() -> List[Dict[str, Any]]:
    """获取所有标签"""
    sql = "SELECT id, name, created_at FROM tags"
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            # 转换时间格式
            for row in rows:
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
            return rows
        except Exception as e:
            logger.error(f"获取所有标签失败: {e}")
            return []


def insert_movie_tag(movie_id: int, tag_id: int) -> bool:
    """
    插入影视-标签关联
    """
    sql = "INSERT OR IGNORE INTO movie_tags (movie_id, tag_id) VALUES (%s, %s)"
    params = (movie_id, tag_id)

    with db_cursor() as cursor:
        if cursor is None:
            return False
        
        try:
            cursor.execute(sql, params)
            logger.info(f"成功插入影视-标签关联: movie_id={movie_id}, tag_id={tag_id}")
            return True
        except Exception as e:
            logger.error(f"插入影视-标签关联失败: {e}")
            return False


def get_movie_tags(movie_id: int) -> List[Dict[str, Any]]:
    """
    获取影视的标签
    """
    sql = """
    SELECT t.id, t.name, t.created_at
    FROM tags t
    JOIN movie_tags mt ON t.id = mt.tag_id
    WHERE mt.movie_id = %s
    """
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []
        try:
            cursor.execute(sql, (movie_id,))
            rows = cursor.fetchall()
            # 转换时间格式
            for row in rows:
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
            return rows
        except Exception as e:
            logger.error(f"获取影视标签失败: {e}")
            return []


def count_movies_by_tag(tag_id: int) -> int:
    """
    统计指定标签的影视总数
    """
    sql = """
    SELECT COUNT(*) as total
    FROM movies m
    JOIN movie_tags mt ON m.id = mt.movie_id
    WHERE mt.tag_id = %s
    """
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return 0
        try:
            cursor.execute(sql, (tag_id,))
            row = cursor.fetchone()
            return row.get("total", 0) if row else 0
        except Exception as e:
            logger.error(f"统计指定标签的影视数量失败: {e}")
            return 0


def get_movies_by_tag(tag_id: int, page: int = 1, limit: int = 12) -> List[Dict[str, Any]]:
    """
    获取指定标签的影视
    """
    offset = (page - 1) * limit
    sql = """
    SELECT m.id, m.title, m.original_title, m.description, m.release_date, m.rating, m.vote_count, m.cover_url, m.backdrop_url, m.source, m.source_id, m.url, m.query_count, m.last_query_at, m.created_at, m.updated_at
    FROM movies m
    JOIN movie_tags mt ON m.id = mt.movie_id
    WHERE mt.tag_id = %s
    ORDER BY m.created_at DESC
    LIMIT %s OFFSET %s
    """
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []
        try:
            cursor.execute(sql, (tag_id, limit, offset))
            rows = cursor.fetchall()
            # 转换时间格式
            for row in rows:
                if row.get("release_date"):
                    row["release_date"] = str(row["release_date"])
                if row.get("last_query_at"):
                    row["last_query_at"] = str(row["last_query_at"])
                if row.get("created_at"):
                    row["created_at"] = str(row["created_at"])
                if row.get("updated_at"):
                    row["updated_at"] = str(row["updated_at"])
            return rows
        except Exception as e:
            logger.error(f"获取指定标签的影视失败: {e}")
            return []


def delete_movie_tags(movie_id: int) -> bool:
    """
    删除影视的所有标签关联
    """
    sql = "DELETE FROM movie_tags WHERE movie_id = %s"
    with db_cursor() as cursor:
        if cursor is None:
            return False
        try:
            cursor.execute(sql, (movie_id,))
            logger.info(f"成功删除影视ID {movie_id} 的所有标签关联")
            return True
        except Exception as e:
            logger.error(f"删除影视标签关联失败: {e}")
            return False