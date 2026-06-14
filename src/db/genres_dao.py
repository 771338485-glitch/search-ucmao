import logging
from typing import Any, Dict, List, Optional

from src.db.db import db_cursor

logger = logging.getLogger(__name__)


def init_genres_table():
    """初始化类型标签表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS genres (
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_genres_name ON genres(name)")
            logger.info("genres 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 genres 表失败: {e}")


def init_movie_genres_table():
    """初始化影视-类型关联表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS movie_genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        genre_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
        FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE,
        UNIQUE(movie_id, genre_id)
    )
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return
        
        try:
            cursor.execute(create_table_sql)
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movie_genres_movie_id ON movie_genres(movie_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movie_genres_genre_id ON movie_genres(genre_id)")
            logger.info("movie_genres 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 movie_genres 表失败: {e}")


def insert_genre(name: str) -> Optional[int]:
    """
    插入一个类型标签，返回新记录的 ID
    """
    sql = "INSERT INTO genres (name) VALUES (%s)"
    params = (name,)

    with db_cursor() as cursor:
        if cursor is None:
            return None
        
        try:
            cursor.execute(sql, params)
            new_id = cursor.lastrowid
            logger.info(f"成功插入类型标签: {name}, ID: {new_id}")
            return new_id
        except Exception as e:
            logger.error(f"插入类型标签 {name} 失败: {e}")
            return None


def get_genre_by_name(name: str) -> Optional[Dict[str, Any]]:
    """根据名称获取类型标签"""
    sql = "SELECT id, name, created_at FROM genres WHERE name = %s"
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
            logger.error(f"获取类型标签失败: {e}")
            return None


def get_genre_by_id(genre_id: int) -> Optional[Dict[str, Any]]:
    """根据ID获取类型标签"""
    sql = "SELECT id, name, created_at FROM genres WHERE id = %s"
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return None
        try:
            cursor.execute(sql, (genre_id,))
            row = cursor.fetchone()
            if row:
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
                return row
            return None
        except Exception as e:
            logger.error(f"获取类型标签失败: {e}")
            return None


def get_all_genres() -> List[Dict[str, Any]]:
    """获取所有类型标签"""
    sql = "SELECT id, name, created_at FROM genres"
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
            logger.error(f"获取所有类型标签失败: {e}")
            return []


def insert_movie_genre(movie_id: int, genre_id: int) -> bool:
    """
    插入影视-类型关联
    """
    sql = "INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (%s, %s)"
    params = (movie_id, genre_id)

    with db_cursor() as cursor:
        if cursor is None:
            return False
        
        try:
            cursor.execute(sql, params)
            logger.info(f"成功插入影视-类型关联: movie_id={movie_id}, genre_id={genre_id}")
            return True
        except Exception as e:
            logger.error(f"插入影视-类型关联失败: {e}")
            return False


def get_movie_genres(movie_id: int) -> List[Dict[str, Any]]:
    """
    获取影视的类型标签
    """
    sql = """
    SELECT g.id, g.name, g.created_at
    FROM genres g
    JOIN movie_genres mg ON g.id = mg.genre_id
    WHERE mg.movie_id = %s
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
            logger.error(f"获取影视类型标签失败: {e}")
            return []


def get_movies_by_genre(genre_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """
    获取指定类型的影视
    """
    sql = """
    SELECT m.id, m.title, m.original_title, m.description, m.release_date, m.rating, m.vote_count, m.cover_url, m.backdrop_url, m.source, m.source_id, m.url, m.query_count, m.last_query_at, m.created_at, m.updated_at
    FROM movies m
    JOIN movie_genres mg ON m.id = mg.movie_id
    WHERE mg.genre_id = %s
    ORDER BY m.query_count DESC, m.last_query_at DESC
    LIMIT %s
    """
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []
        try:
            cursor.execute(sql, (genre_id, limit))
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
            logger.error(f"获取指定类型的影视失败: {e}")
            return []


def delete_movie_genres(movie_id: int) -> bool:
    """
    删除影视的所有类型关联
    """
    sql = "DELETE FROM movie_genres WHERE movie_id = %s"
    with db_cursor() as cursor:
        if cursor is None:
            return False
        try:
            cursor.execute(sql, (movie_id,))
            logger.info(f"成功删除影视ID {movie_id} 的所有类型关联")
            return True
        except Exception as e:
            logger.error(f"删除影视类型关联失败: {e}")
            return False
