import logging
from typing import Any, Dict, List, Optional, Tuple

from src.db.db import db_cursor

logger = logging.getLogger(__name__)


def init_movies_table():
    """初始化影视表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(255) NOT NULL,
        original_title VARCHAR(255),
        description TEXT,
        release_date DATE,
        rating DECIMAL(3,1),
        vote_count INTEGER,
        cover_url VARCHAR(512),
        backdrop_url VARCHAR(512),
        source VARCHAR(100) NOT NULL,
        source_id VARCHAR(100),
        url VARCHAR(512),
        category VARCHAR(50),
        query_count INTEGER DEFAULT 0,
        last_query_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    with db_cursor() as cursor:
        if cursor is None:
            return
        
        try:
            cursor.execute(create_table_sql)
            # 添加 category 字段（如果不存在）
            try:
                cursor.execute("ALTER TABLE movies ADD COLUMN category VARCHAR(50)")
                logger.info("添加 category 字段到 movies 表")
            except Exception as e:
                # 字段可能已存在，忽略错误
                pass
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_source_source_id ON movies(source, source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_updated_at ON movies(updated_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_query_count ON movies(query_count)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_last_query_at ON movies(last_query_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_category ON movies(category)")
            logger.info("movies 表初始化完成")
        except Exception as e:
            logger.error(f"初始化 movies 表失败: {e}")


def insert_movie(record: Dict[str, Any]) -> Optional[int]:
    """
    插入一条影视记录，返回新记录的 ID
    """
    title = record.get("title")
    original_title = record.get("original_title")
    description = record.get("description")
    release_date = record.get("release_date")
    rating = record.get("rating")
    vote_count = record.get("vote_count")
    cover_url = record.get("cover_url")
    backdrop_url = record.get("backdrop_url")
    source = record.get("source")
    source_id = record.get("source_id")
    url = record.get("url")
    category = record.get("category")

    sql = """
    INSERT INTO movies (title, original_title, description, release_date, rating, vote_count, cover_url, backdrop_url, source, source_id, url, category)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (title, original_title, description, release_date, rating, vote_count, cover_url, backdrop_url, source, source_id, url, category)

    with db_cursor() as cursor:
        if cursor is None:
            return None
        
        try:
            cursor.execute(sql, params)
            new_id = cursor.lastrowid
            logger.info(f"成功插入影视记录: {title}, ID: {new_id}")
            return new_id
        except Exception as e:
            logger.error(f"插入影视记录 {title} 失败: {e}")
            return None


def get_movie_by_id(movie_id: int) -> Optional[Dict[str, Any]]:
    """根据ID获取影视记录"""
    sql = """
    SELECT id, title, original_title, description, release_date, rating, vote_count, cover_url, backdrop_url, source, source_id, url, category, query_count, last_query_at, created_at, updated_at
    FROM movies WHERE id = %s
    """
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return None
        try:
            cursor.execute(sql, (movie_id,))
            row = cursor.fetchone()
            if row:
                # 转换时间格式
                if "release_date" in row:
                    row["release_date"] = str(row["release_date"])
                if "last_query_at" in row:
                    row["last_query_at"] = str(row["last_query_at"])
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
                if "updated_at" in row:
                    row["updated_at"] = str(row["updated_at"])
                return row
            return None
        except Exception as e:
            logger.error(f"获取影视记录失败: {e}")
            return None


def get_movie_by_source(source: str, title: str) -> Optional[Dict[str, Any]]:
    """根据来源和标题获取影视记录"""
    sql = """
    SELECT id, title, original_title, description, release_date, rating, vote_count, cover_url, backdrop_url, source, source_id, url, category, query_count, last_query_at, created_at, updated_at
    FROM movies WHERE source = %s AND title = %s
    """
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return None
        try:
            cursor.execute(sql, (source, title))
            row = cursor.fetchone()
            if row:
                # 转换时间格式
                if "release_date" in row:
                    row["release_date"] = str(row["release_date"])
                if "last_query_at" in row:
                    row["last_query_at"] = str(row["last_query_at"])
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
                if "updated_at" in row:
                    row["updated_at"] = str(row["updated_at"])
                return row
            return None
        except Exception as e:
            logger.error(f"获取影视记录失败: {e}")
            return None


def increment_query_count(movie_id: int) -> bool:
    """增加影视的查询次数"""
    sql = """
    UPDATE movies
    SET query_count = query_count + 1, last_query_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
    WHERE id = %s
    """
    with db_cursor() as cursor:
        if cursor is None:
            return False
        try:
            cursor.execute(sql, (movie_id,))
            if cursor.rowcount > 0:
                logger.info(f"成功增加影视ID {movie_id} 的查询次数")
                return True
            return False
        except Exception as e:
            logger.error(f"增加查询次数失败: {e}")
            return False


def get_movies_count(category: Optional[str] = None) -> int:
    """获取电影总数"""
    sql = """
    SELECT COUNT(*) as count
    FROM movies
    """
    params = []
    if category:
        sql += " WHERE category = %s"
        params.append(category)
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return 0
        try:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            if row:
                return row.get("count", 0)
            return 0
        except Exception as e:
            logger.error(f"获取电影总数失败: {e}")
            return 0


def get_movies_by_query_count(page: int = 1, limit: int = 20, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """根据查询次数获取热门影视"""
    offset = (page - 1) * limit
    # 修改排序逻辑，当 query_count 相同时，按照 ID 降序排序，确保有结果
    sql = """
    SELECT id, title, original_title, description, release_date, rating, vote_count, cover_url, backdrop_url, source, source_id, url, category, query_count, last_query_at, created_at, updated_at
    FROM movies
    """
    params = []
    if category:
        sql += " WHERE category = %s"
        params.append(category)
    sql += " ORDER BY query_count DESC, id DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            logger.info(f"获取热门影视成功，共 {len(rows)} 部")
            # 转换时间格式
            for row in rows:
                if "release_date" in row:
                    row["release_date"] = str(row["release_date"])
                if "last_query_at" in row:
                    row["last_query_at"] = str(row["last_query_at"])
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
                if "updated_at" in row:
                    row["updated_at"] = str(row["updated_at"])
            return rows
        except Exception as e:
            logger.error(f"获取热门影视失败: {e}")
            return []


def update_movie(movie_id: int, record: Dict[str, Any]) -> bool:
    """
    更新影视记录
    """
    # 构建更新字段
    update_fields = []
    params = []
    
    if "title" in record:
        update_fields.append("title = %s")
        params.append(record["title"])
    if "original_title" in record:
        update_fields.append("original_title = %s")
        params.append(record["original_title"])
    if "description" in record:
        update_fields.append("description = %s")
        params.append(record["description"])
    if "release_date" in record:
        update_fields.append("release_date = %s")
        params.append(record["release_date"])
    if "rating" in record:
        update_fields.append("rating = %s")
        params.append(record["rating"])
    if "vote_count" in record:
        update_fields.append("vote_count = %s")
        params.append(record["vote_count"])
    if "cover_url" in record:
        update_fields.append("cover_url = %s")
        params.append(record["cover_url"])
    if "backdrop_url" in record:
        update_fields.append("backdrop_url = %s")
        params.append(record["backdrop_url"])
    if "source" in record:
        update_fields.append("source = %s")
        params.append(record["source"])
    if "source_id" in record:
        update_fields.append("source_id = %s")
        params.append(record["source_id"])
    if "url" in record:
        update_fields.append("url = %s")
        params.append(record["url"])
    if "category" in record:
        update_fields.append("category = %s")
        params.append(record["category"])
    
    # 添加更新时间
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    
    if not update_fields:
        return False
    
    sql = f"""
    UPDATE movies
    SET {', '.join(update_fields)}
    WHERE id = %s
    """
    params.append(movie_id)
    
    with db_cursor() as cursor:
        if cursor is None:
            return False
        try:
            cursor.execute(sql, params)
            if cursor.rowcount > 0:
                logger.info(f"成功更新影视ID {movie_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"更新影视记录失败: {e}")
            return False


def delete_movie(movie_id: int) -> bool:
    """删除影视记录"""
    sql = "DELETE FROM movies WHERE id = %s"
    with db_cursor() as cursor:
        if cursor is None:
            return False
        try:
            cursor.execute(sql, (movie_id,))
            if cursor.rowcount > 0:
                logger.info(f"成功删除影视ID {movie_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除影视记录失败: {e}")
            return False


def search_movies(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """搜索影视"""
    sql = """
    SELECT id, title, original_title, description, release_date, rating, vote_count, cover_url, backdrop_url, source, source_id, url, category, query_count, last_query_at, created_at, updated_at
    FROM movies
    WHERE title LIKE %s OR original_title LIKE %s
    ORDER BY query_count DESC, last_query_at DESC
    LIMIT %s
    """
    params = (f"%{keyword}%", f"%{keyword}%", limit)
    
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            # 转换时间格式
            for row in rows:
                if "release_date" in row:
                    row["release_date"] = str(row["release_date"])
                if "last_query_at" in row:
                    row["last_query_at"] = str(row["last_query_at"])
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
                if "updated_at" in row:
                    row["updated_at"] = str(row["updated_at"])
            return rows
        except Exception as e:
            logger.error(f"搜索影视失败: {e}")
            return []


def get_latest_movies(page: int = 1, limit: int = 20) -> List[Dict[str, Any]]:
    """根据创建时间获取最新影视"""
    offset = (page - 1) * limit
    sql = """
    SELECT id, title, original_title, description, release_date, rating, vote_count, cover_url, backdrop_url, source, source_id, url, category, query_count, last_query_at, created_at, updated_at
    FROM movies
    ORDER BY created_at DESC, id DESC
    LIMIT %s OFFSET %s
    """
    params = [limit, offset]
    
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            logger.info(f"获取最新影视成功，共 {len(rows)} 部")
            # 转换时间格式
            for row in rows:
                if "release_date" in row:
                    row["release_date"] = str(row["release_date"])
                if "last_query_at" in row:
                    row["last_query_at"] = str(row["last_query_at"])
                if "created_at" in row:
                    row["created_at"] = str(row["created_at"])
                if "updated_at" in row:
                    row["updated_at"] = str(row["updated_at"])
            return rows
        except Exception as e:
            logger.error(f"获取最新影视失败: {e}")
            return []


def get_expired_movies(days: int = 30) -> List[Dict[str, Any]]:
    """
    获取指定天数前的影视记录
    :param days: 天数
    :return: 影视记录列表
    """
    sql = """
    SELECT id, title, cover_url
    FROM movies
    WHERE created_at < datetime('now', '-' || ? || ' days')
    """
    params = [days]
    
    with db_cursor(dictionary=True) as cursor:
        if cursor is None:
            return []
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            logger.info(f"获取 {days} 天前的影视记录成功，共 {len(rows)} 部")
            return rows
        except Exception as e:
            logger.error(f"获取过期影视记录失败: {e}")
            return []


def delete_movies_by_ids(movie_ids: List[int]) -> bool:
    """
    批量删除影视记录
    :param movie_ids: 影视ID列表
    :return: 是否成功
    """
    if not movie_ids:
        return True
    
    placeholders = ','.join(['%s'] * len(movie_ids))
    sql = f"DELETE FROM movies WHERE id IN ({placeholders})"
    
    with db_cursor() as cursor:
        if cursor is None:
            return False
        try:
            cursor.execute(sql, movie_ids)
            deleted_count = cursor.rowcount
            logger.info(f"成功删除 {deleted_count} 部影视记录")
            return True
        except Exception as e:
            logger.error(f"批量删除影视记录失败: {e}")
            return False
