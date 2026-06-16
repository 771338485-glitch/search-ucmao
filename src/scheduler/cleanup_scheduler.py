import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path

from src.db.stored_files_dao import get_expired_files, delete_stored_files_by_ids, update_delete_status
from src.db.cookie_config_dao import get_cookie_by_cloud_name
from src.db.search_history_dao import delete_old_search_history
from src.db.movies_dao import get_expired_movies, delete_movies_by_ids
from src.clients.quark_client import Quark
from src.clients.baidu_client import Baidu

logger = logging.getLogger(__name__)

_scheduler_thread = None
_stop_event = threading.Event()


def clean_expired_files(expire_minutes: int = 5):
    """
    清理过期的转存文件
    """
    logger.info(f"[定时清理] 开始检查 {expire_minutes} 分钟前转存的文件...")
    
    expired_files = get_expired_files(expire_minutes)
    
    if not expired_files:
        logger.info("[定时清理] 没有需要清理的过期文件")
        return
    
    quark_cookie = get_cookie_by_cloud_name("夸克网盘")
    baidu_cookie = get_cookie_by_cloud_name("百度网盘")
    
    quark_client = Quark(quark_cookie) if quark_cookie else None
    baidu_client = Baidu(baidu_cookie) if baidu_cookie else None
    
    deleted_record_ids = []
    deleted_count = 0
    failed_count = 0
    deleted_folders = 0
    
    processed_file_ids = set()
    processed_folders = set()
    
    for file_record in expired_files:
        file_id = file_record.get('file_id')
        cloud_name = file_record.get('cloud_name', '')
        record_id = file_record.get('id')
        delete_attempts = file_record.get('delete_attempts', 0)
        
        if file_id in processed_file_ids:
            continue
        
        processed_file_ids.add(file_id)
        
        try:
            if cloud_name == "夸克网盘" and quark_client:
                success = quark_client.del_file(file_id)
            elif cloud_name == "百度网盘" and baidu_client:
                success = baidu_client.del_file([file_id])
            else:
                continue
            
            if success:
                deleted_count += 1
                deleted_record_ids.append(record_id)
                # 更新删除状态为成功
                update_delete_status(record_id, 'success', delete_attempts)
                
                # 不再处理文件夹删除，因为我们已经不再创建子目录
                pass
            else:
                failed_count += 1
                # 更新删除状态为失败，增加尝试次数
                update_delete_status(record_id, 'failed', delete_attempts + 1)
                
        except Exception as e:
            failed_count += 1
            # 更新删除状态为失败，增加尝试次数
            update_delete_status(record_id, 'failed', delete_attempts + 1)
    
    if deleted_record_ids:
        delete_stored_files_by_ids(deleted_record_ids)
    
    logger.info(f"[定时清理] 清理完成: 成功删除 {deleted_count} 个文件, 失败 {failed_count} 个, 清理 {len(deleted_record_ids)} 条记录, 删除 {deleted_folders} 个空文件夹")


def clean_old_search_history(days: int = 30):
    """
    清理30天前的搜索历史记录
    """
    logger.info(f"[定时清理] 开始清理 {days} 天前的搜索历史记录...")
    deleted_count = delete_old_search_history(days=days)
    logger.info(f"[定时清理] 搜索历史清理完成: 共删除 {deleted_count} 条记录")


def clean_old_logs(days: int = 7):
    """
    清理7天前的日志文件
    """
    logger.info(f"[定时清理] 开始清理 {days} 天前的日志文件...")
    
    log_dir = Path("logs")
    if not log_dir.exists():
        logger.info("[定时清理] 日志目录不存在，跳过清理")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0
    
    # 清理主日志文件的备份
    for log_file in log_dir.glob("search_ucmao.log.*"):
        try:
            # 尝试从文件名中提取日期
            file_stat = log_file.stat()
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            
            if file_mtime < cutoff_date:
                log_file.unlink()
                deleted_count += 1
                logger.info(f"[定时清理] 删除过期日志文件: {log_file}")
        except Exception as e:
            logger.error(f"[定时清理] 删除日志文件 {log_file} 时出错: {e}")
    
    logger.info(f"[定时清理] 日志文件清理完成: 共删除 {deleted_count} 个文件")


def clean_expired_movies(days: int = 30):
    """
    清理指定天数前的影视数据及对应的图片
    :param days: 天数
    """
    logger.info(f"[定时清理] 开始清理 {days} 天前的影视数据及对应的图片...")
    
    # 获取过期的影视记录
    expired_movies = get_expired_movies(days=days)
    
    if not expired_movies:
        logger.info("[定时清理] 没有需要清理的过期影视数据")
        return
    
    # 图片存储目录
    images_dir = Path("seedhub_images")
    
    deleted_movies = 0
    deleted_images = 0
    failed_images = 0
    movie_ids_to_delete = []
    
    for movie in expired_movies:
        movie_id = movie.get('id')
        title = movie.get('title')
        cover_url = movie.get('cover_url')
        
        # 记录要删除的电影ID
        movie_ids_to_delete.append(movie_id)
        
        # 删除对应的图片文件
        if cover_url and not cover_url.startswith('http'):
            # 提取图片文件名
            image_filename = cover_url.split('/')[-1]
            image_path = images_dir / image_filename
            
            if image_path.exists():
                try:
                    image_path.unlink()
                    deleted_images += 1
                    logger.debug(f"[定时清理] 删除影视图片: {image_path}")
                except Exception as e:
                    failed_images += 1
                    logger.error(f"[定时清理] 删除影视图片 {image_path} 时出错: {e}")
    
    # 批量删除影视记录
    if movie_ids_to_delete:
        success = delete_movies_by_ids(movie_ids_to_delete)
        if success:
            deleted_movies = len(movie_ids_to_delete)
            logger.info(f"[定时清理] 成功删除 {deleted_movies} 部过期影视记录")
        else:
            logger.error("[定时清理] 删除过期影视记录失败")
    
    logger.info(f"[定时清理] 影视数据清理完成: 成功删除 {deleted_movies} 部影视, {deleted_images} 张图片, 失败 {failed_images} 张图片")


def _scheduler_loop(interval_minutes: int = 5, expire_minutes: int = 5):
    """
    定时任务循环
    """
    # 启动时先等待一个时间间隔，避免每次启动都执行清理操作
    _stop_event.wait(interval_minutes * 60)
    
    while not _stop_event.is_set():
        try:
            clean_expired_files(expire_minutes)
            clean_old_search_history(days=30)
            clean_old_logs(days=7)
            clean_expired_movies(days=30)
        except Exception as e:
            logger.error(f"[定时清理] 清理任务执行异常: {e}")
        
        _stop_event.wait(interval_minutes * 60)


def start_scheduler(interval_minutes: int = 5, expire_minutes: int = 5):
    """
    启动定时清理任务
    :param interval_minutes: 检查间隔（分钟）
    :param expire_minutes: 文件过期时间（分钟）
    """
    global _scheduler_thread, _stop_event
    
    if _scheduler_thread and _scheduler_thread.is_alive():
        logger.warning("[定时清理] 调度器已在运行中")
        return
    
    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(interval_minutes, expire_minutes),
        daemon=True
    )
    _scheduler_thread.start()
    logger.info(f"[定时清理] 调度器已启动: 每 {interval_minutes} 分钟检查一次, 清理 {expire_minutes} 分钟前的文件")



def stop_scheduler():
    """
    停止定时清理任务
    """
    global _stop_event

    _stop_event.set()
    logger.info("[定时清理] 调度器已停止")
