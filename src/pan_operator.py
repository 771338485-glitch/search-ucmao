import logging
import os
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from src.clients.quark_client import Quark
from src.clients.baidu_client import Baidu
from src.db.resources_dao import insert_resource, delete_by_share_link, update_share_link
from src.db.cookie_config_dao import get_cookie_by_cloud_name
from src.db.stored_files_dao import insert_stored_file, get_washed_link_by_original
from src.scheduler.email_scheduler import send_wash_failed_email
from utils.netdisk_utils import match_netdisk_link

logger = logging.getLogger(__name__)

_email_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="email_notify")

# --- 缓存机制 ---# Cookie 有效性缓存
COOKIE_CACHE = {}
COOKIE_CACHE_TTL = 300  # 5分钟缓存

# 目录结构缓存
DIRECTORY_CACHE = {}
DIRECTORY_CACHE_TTL = 600  # 10分钟缓存

# 缓存锁
COOKIE_CACHE_LOCK = threading.RLock()
DIRECTORY_CACHE_LOCK = threading.RLock()

# --- 工具函数：Cookie 校验 ---

def clear_cookie_cache(netdisk_type: str = None):
    """
    清除Cookie缓存
    :param netdisk_type: 指定云盘类型，None则清除所有
    """
    with COOKIE_CACHE_LOCK:
        if netdisk_type:
            if netdisk_type in COOKIE_CACHE:
                del COOKIE_CACHE[netdisk_type]
                logger.info(f"[{netdisk_type}] 已清除Cookie缓存")
        else:
            COOKIE_CACHE.clear()
            logger.info("已清除所有Cookie缓存")

def get_and_validate_cookie(netdisk_type: str) -> str:
    """
    统一获取并校验 Cookie。
    :param netdisk_type: "夸克网盘" 或 "百度网盘"
    :return: 有效的 cookie 字符串，无效则返回空字符串
    """
    current_time = time.time()
    
    with COOKIE_CACHE_LOCK:
        # 检查缓存
        if netdisk_type in COOKIE_CACHE:
            cached_data = COOKIE_CACHE[netdisk_type]
            if current_time - cached_data['timestamp'] < COOKIE_CACHE_TTL:
                logger.debug(f"[{netdisk_type}] 使用缓存的 Cookie")
                return cached_data['cookie']
        
        # 缓存未命中，从数据库获取
        cookie = get_cookie_by_cloud_name(netdisk_type)
        
        if not cookie:
            logger.error(f"[{netdisk_type}] 操作失败：数据库中未配置 Cookie。")
            return ""
        
        if len(cookie) < 300:
            logger.error(f"[{netdisk_type}] 操作失败：Cookie 长度不足({len(cookie)})，可能已失效。")
            return ""
        
        # 缓存有效 Cookie
        COOKIE_CACHE[netdisk_type] = {
            'cookie': cookie,
            'timestamp': current_time
        }
        logger.debug(f"[{netdisk_type}] 缓存新的 Cookie")
        return cookie

# --- 核心逻辑：通用网盘操作处理器 ---

def _handle_netdisk_operation(client_class, client_cookie, share_url, to_pdir_path: str = '/', 
                              operation: str = 'store', file_id: str = None):
    """
    通用网盘操作处理器（转存或删除）。
    """
    client = client_class(client_cookie)
    try:
        if operation == 'store':
            # 执行转存流程
            new_file_id, file_name, new_share_url = client.store(share_url, to_pdir_path)

            if not new_file_id or not new_share_url:
                logger.error(f"[{client_class.__name__}] 转存或分享接口返回空数据")
                return None, None, None

            logger.debug(f"[{client_class.__name__}] 处理成功: {file_name}")
            return new_file_id, file_name, new_share_url

        elif operation == 'delete':
            if not file_id:
                logger.error(f"[{client_class.__name__}] 删除操作缺失 file_id")
                return False

            # 百度删除通常需要路径列表，夸克通常是 ID
            target = [file_id] if client_class == Baidu else file_id
            status = client.del_file(target)
            return status

    except Exception as e:
        logger.exception(f"[{client_class.__name__}] 接口调用异常: {e}")
        return (None, None, None) if operation == 'store' else False

# --- 业务接口：创建分享 ---

def create_share(share_data):
    """
    创建/转存分享链接
    """
    try:
        share_url = share_data.get('share_url')
        title = share_data.get('title', f"资源_{int(time.time())}")
        save_to_netdisk = share_data.get('save_to_netdisk', {})
        has_id = 'id' in share_data
        share_id = share_data.get('id')

        logger.info(f"[洗白] 开始处理资源: {title}, URL: {share_url}")
        logger.info(f"[洗白] 转存配置: {save_to_netdisk}")

        # 特殊处理：跳过特定夸克网盘链接的洗白操作
        # 解码URL并检查是否包含特定路径
        # 注意：这里硬编码了跳过逻辑，实际项目中应该从配置中读取
        decoded_url = urllib.parse.unquote(share_url)
        if 'pan.quark.cn/s/6176e44c7c0a' in decoded_url:
            logger.info(f"[洗白] 跳过特定夸克网盘链接的洗白操作: {share_url}")
            return share_data if not has_id else None

        # 1. 匹配网盘类型
        netdisk_type = match_netdisk_link(share_url)
        logger.info(f"[洗白] 识别网盘类型: {netdisk_type}")

        config_map = {
            "夸克网盘": {"class": Quark, "enabled": save_to_netdisk.get('quark', False)},
            "百度网盘": {"class": Baidu, "enabled": save_to_netdisk.get('baidu', False)}
        }

        conf = config_map.get(netdisk_type)

        # 2. 判断是否需要转存
        if not conf:
            logger.warning(f"[洗白] 不支持的网盘类型或无法识别: {netdisk_type}")
            return share_data if not has_id else None

        if not conf["enabled"]:
            logger.warning(f"[洗白] 转存开关未开启: {netdisk_type}, save_to_netdisk={save_to_netdisk}")
            return share_data if not has_id else None

        # 3. 检查是否已经洗白过（去重）
        logger.info(f"[洗白] 检查是否已洗白过: {share_url}")
        existing = get_washed_link_by_original(share_url)
        logger.info(f"[洗白] 查询结果: {existing}")
        if existing and existing.get('share_link'):
            logger.info(f"[洗白] 该链接已洗白过，直接返回: {existing['share_link']}")
            return {
                "share_url": existing['share_link'],
                "file_id": existing['file_id']
            }

        # 4. 直接使用同步处理
        logger.info("[洗白] 使用同步处理洗白操作")
        return sync_create_share(share_data)

    except Exception as e:
        logger.exception(f"create_share 运行异常: {e}")
        return share_data if 'id' not in share_data else None

def sync_create_share(share_data):
    """
    同步创建分享链接（用于异步任务或回退）
    """
    try:
        share_url = share_data.get('share_url')
        title = share_data.get('title', f"资源_{int(time.time())}")
        save_to_netdisk = share_data.get('save_to_netdisk', {})
        has_id = 'id' in share_data
        share_id = share_data.get('id')

        # 1. 匹配网盘类型
        netdisk_type = match_netdisk_link(share_url)
        
        config_map = {
            "夸克网盘": {"class": Quark, "enabled": save_to_netdisk.get('quark', False)},
            "百度网盘": {"class": Baidu, "enabled": save_to_netdisk.get('baidu', False)}
        }
        
        conf = config_map.get(netdisk_type)

        # 2. 获取并校验 Cookie
        client_cookie = get_and_validate_cookie(netdisk_type)
        if not client_cookie:
            logger.error(f"[洗白] Cookie 校验失败: {netdisk_type}")
            # 异步发送邮件通知
            try:
                _email_executor.submit(
                    send_wash_failed_email,
                    reason=f"{netdisk_type} Cookie已过期或未配置，请及时更新",
                    url=share_url,
                    title=title
                )
            except Exception as email_error:
                logger.warning(f"[洗白] 发送邮件通知失败: {email_error}")
            return share_data if not has_id else None
        
        logger.debug(f"[洗白] Cookie 校验通过, 长度: {len(client_cookie)}")

        # 3. 执行转存
        # 使用环境变量配置的默认保存目录，默认为"/桃白白影视/"
        base_dir = os.getenv('DEFAULT_SAVE_DIR', '/桃白白影视/')
        # 确保路径以/开头（百度API要求绝对路径）
        if not base_dir.startswith('/'):
            base_dir = '/' + base_dir
        # 直接使用根目录，不创建子目录
        default_save_dir = base_dir.rstrip('/') + '/'
        logger.info(f"[洗白] 开始执行转存操作，目标路径: {default_save_dir}")
        logger.info(f"[洗白] 网盘类型: {netdisk_type}, 分享链接: {share_url}")
        new_file_id, file_name, new_share_url = _handle_netdisk_operation(
            client_class=conf["class"],
            client_cookie=client_cookie,
            share_url=share_url,
            to_pdir_path=default_save_dir,
            operation='store'
        )

        logger.info(f"[洗白] 转存结果: file_id={new_file_id}, file_name={file_name}, share_url={new_share_url}")

        if not new_share_url:
            logger.warning(f"[洗白] 转存失败，链接可能已失效: {share_url}")
            # 异步发送邮件通知
            try:
                _email_executor.submit(
                    send_wash_failed_email,
                    reason=f"{netdisk_type} 转存失败，请检查链接是否有效或Cookie是否过期",
                    url=share_url,
                    title=title
                )
            except Exception as email_error:
                logger.warning(f"[洗白] 发送邮件通知失败: {email_error}")
            # 转存失败时，直接返回原始链接，标记为无效
            if has_id:
                # 如果有ID，返回None表示不处理
                return None
            else:
                # 如果没有ID，直接返回原始数据
                return share_data
        
        logger.debug(f"[洗白] 转存成功: {file_name}, 新链接: {new_share_url}")
        
        # 记录转存文件（用于定时清理）
        insert_stored_file({
            'file_id': new_file_id,
            'file_name': file_name,
            'original_share_link': share_url,
            'share_link': new_share_url,
            'cloud_name': netdisk_type
        })
        logger.debug(f"[洗白] 已记录转存文件，将在15分钟后自动清理")

        # 4. 数据库同步
        if has_id:
            # 场景 A: 已有记录更新链接
            logger.debug(f"[洗白] 更新数据库记录 ID={share_id}")
            update_share_link(share_id, new_share_url, new_file_id)
            logger.debug(f"[洗白] 数据库更新完成")
            return None
        else:
            # 场景 B: 搜索发现新资源，入库并返回新对象
            logger.debug(f"[洗白] 无需更新数据库(无ID)")
            # 返回洗白后的新链接（无论是否入库成功）
            result = {"share_url": new_share_url, "file_id": new_file_id}
            
            # 只有在有完整资源信息时才尝试入库
            if share_data.get('name'):
                new_record = {
                    'file_id': new_file_id,
                    'name': share_data.get('name', file_name or title),
                    'share_link': new_share_url,
                    'cloud_name': netdisk_type,
                    'type': share_data.get('resource_type'),
                    'remarks': share_data.get('remark')
                }
                try:
                    insert_resource(new_record)
                    logger.debug(f"[洗白] 新资源已入库: {new_record['name']}")
                except Exception as e:
                    logger.debug(f"[洗白] 入库失败(可能已存在): {e}")
            
            return result

    except Exception as e:
        logger.exception(f"sync_create_share 运行异常: {e}")
        return share_data if 'id' not in share_data else None

# --- 业务接口：删除分享 ---

def del_share(share_data):
    """
    删除分享及其对应的网盘文件
    """
    try:
        share_url = share_data.get('share_url')
        file_id = share_data.get('file_id')

        if not share_url:
            return False

        # 1. 获取 Cookie
        netdisk_type = match_netdisk_link(share_url)
        client_cookie = get_and_validate_cookie(netdisk_type)
        if not client_cookie:
            return False

        # 2. 执行物理删除
        # 直接使用已获取的 client_cookie，不依赖未定义的全局变量
        config = {
            "百度网盘": Baidu,
            "夸克网盘": Quark,
        }
        client_class = config.get(netdisk_type)
        if not client_class:
            return {"success": False, "message": f"不支持的网盘类型: {netdisk_type}"}

        status = _handle_netdisk_operation(
            client_class=client_class,
            client_cookie=client_cookie,
            share_url=share_url,
            operation='delete',
            file_id=file_id
        )

        # 3. 逻辑删除（数据库记录清理）
        if status:
            delete_by_share_link(share_url)
            logger.info(f"成功清理 {netdisk_type} 资源及其数据库记录")
            return True

        return False

    except Exception as e:
        logger.exception(f"del_share 运行异常: {e}")
        return False
