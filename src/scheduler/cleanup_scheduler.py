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
    
    # 启动桃白白影视目录清理调度器
    start_taobai_scheduler()


def clean_taobai_files_by_time(expire_minutes: int = 20):
    """
    基于文件名时间戳清理桃白白影视目录下的过期文件
    :param expire_minutes: 过期时间（分钟）
    """
    logger.info(f"[定时清理] 开始清理桃白白影视目录下 {expire_minutes} 分钟前的文件...")
    
    quark_cookie = get_cookie_by_cloud_name("夸克网盘")
    baidu_cookie = get_cookie_by_cloud_name("百度网盘")
    
    quark_client = Quark(quark_cookie) if quark_cookie else None
    baidu_client = Baidu(baidu_cookie) if baidu_cookie else None
    
    quark_deleted_files = 0
    baidu_deleted_files = 0
    
    # 计算过期时间
    cutoff_time = datetime.now() - timedelta(minutes=expire_minutes)
    
    # 清理夸克网盘
    if quark_client:
        try:
            # 获取桃白白影视目录的ID
            taobai_dir_id = quark_client._get_or_create_dir("/桃白白影视/")
            if taobai_dir_id != '0':
                # 获取桃白白影视目录下的所有文件
                taobai_files = quark_client.get_dir_file(taobai_dir_id)
                for file in taobai_files:
                    if file.get('file_type') == 1:  # 1表示文件
                        file_id = file.get('fid')
                        file_name = file.get('file_name')
                        # 尝试从文件名中提取时间戳
                        if file_name:
                            try:
                                # 匹配文件名格式：[原始文件名]_[YYYYMMDDHHMMSS].[文件扩展名]
                                import re
                                match = re.search(r'_(\d{14})\.[^.]+$', file_name)
                                if match:
                                    timestamp_str = match.group(1)
                                    file_time = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                                    # 检查是否过期
                                    if file_time < cutoff_time:
                                        # 删除文件
                                        delete_success = quark_client.del_file(file_id)
                                        if delete_success:
                                            quark_deleted_files += 1
                                            logger.debug(f"[定时清理] 成功删除过期文件: {file_name}")
                            except Exception as e:
                                logger.debug(f"[定时清理] 解析夸克文件名时间戳时出错: {e}")
        except Exception as e:
            logger.error(f"[定时清理] 清理夸克网盘桃白白影视目录时出错: {e}")
    
    # 清理百度网盘
    if baidu_client:
        try:
            # 获取桃白白影视目录下的所有文件
            # 使用百度客户端的API获取文件列表
            url = "https://pan.baidu.com/api/list"
            params = {
                "dir": "/桃白白影视",
                "bdstoken": baidu_client.bdstoken,
                "clienttype": 0,
                "web": 1,
                "page": 1,
                "num": 1000,
                "order": "time",
                "desc": 1
            }
            res = baidu_client.session.get(url, params=params)
            js = res.json()
            if js.get("errno") == 0:
                file_list = js.get("list", [])
                for file in file_list:
                    if file.get("isdir") == 0:  # 0表示文件
                        path = file.get("path")
                        file_name = file.get("server_filename")
                        # 尝试从文件名中提取时间戳
                        if file_name:
                            try:
                                # 匹配文件名格式：[原始文件名]_[YYYYMMDDHHMMSS].[文件扩展名]
                                import re
                                match = re.search(r'_(\d{14})\.[^.]+$', file_name)
                                if match:
                                    timestamp_str = match.group(1)
                                    file_time = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                                    # 检查是否过期
                                    if file_time < cutoff_time:
                                        # 删除文件
                                        delete_success = baidu_client.del_file([path])
                                        if delete_success:
                                            baidu_deleted_files += 1
                                            logger.debug(f"[定时清理] 成功删除过期文件: {file_name}")
                            except Exception as e:
                                logger.debug(f"[定时清理] 解析百度文件名时间戳时出错: {e}")
        except Exception as e:
            logger.error(f"[定时清理] 清理百度网盘桃白白影视目录时出错: {e}")
    
    total_deleted_files = quark_deleted_files + baidu_deleted_files
    logger.info(f"[定时清理] 桃白白影视目录清理完成: 夸克网盘删除 {quark_deleted_files} 个文件, 百度网盘删除 {baidu_deleted_files} 个文件, 共删除 {total_deleted_files} 个文件")


# 全局变量用于存储新的调度线程
_taobai_scheduler_thread = None
_taobai_stop_event = threading.Event()


def _taobai_scheduler_loop():
    """
    桃白白影视目录清理任务循环，每天0点执行一次
    """
    while not _taobai_stop_event.is_set():
        try:
            # 获取当前时间
            now = datetime.now()
            # 计算到第二天0点的时间差
            tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
            seconds_until_midnight = (tomorrow - now).total_seconds()
            
            logger.info(f"[定时清理] 等待到明天0点执行桃白白影视目录清理，需要等待 {seconds_until_midnight:.2f} 秒")
            
            # 等待到第二天0点
            if _taobai_stop_event.wait(seconds_until_midnight):
                # 如果事件被设置，退出循环
                break
            
            # 执行清理任务
            clean_taobai_files_by_time(expire_minutes=20)
            
        except Exception as e:
            logger.error(f"[定时清理] 桃白白影视目录清理任务执行异常: {e}")
            # 出错后等待1小时再继续
            _taobai_stop_event.wait(3600)


def start_taobai_scheduler():
    """
    启动桃白白影视目录清理定时任务，每天0点执行一次
    """
    global _taobai_scheduler_thread, _taobai_stop_event
    
    if _taobai_scheduler_thread and _taobai_scheduler_thread.is_alive():
        logger.warning("[定时清理] 桃白白影视目录清理调度器已在运行中")
        return
    
    _taobai_stop_event.clear()
    _taobai_scheduler_thread = threading.Thread(
        target=_taobai_scheduler_loop,
        daemon=True
    )
    _taobai_scheduler_thread.start()
    logger.info("[定时清理] 桃白白影视目录清理调度器已启动: 每天0点执行一次")


def stop_taobai_scheduler():
    """
    停止桃白白影视目录清理定时任务
    """
    global _taobai_stop_event
    
    _taobai_stop_event.set()
    logger.info("[定时清理] 桃白白影视目录清理调度器已停止")


def stop_scheduler():
    """
    停止定时清理任务
    """
    global _stop_event
    
    _stop_event.set()
    stop_taobai_scheduler()
    logger.info("[定时清理] 调度器已停止")
