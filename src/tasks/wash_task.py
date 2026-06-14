import logging
import time
import threading
from src.pan_operator import sync_create_share

logger = logging.getLogger(__name__)

# 内存队列作为回退方案
class MemoryQueue:
    def __init__(self):
        self.jobs = []
        self.job_id_counter = 1
    
    def enqueue(self, func, *args, **kwargs):
        job_id = f"job_{self.job_id_counter}"
        self.job_id_counter += 1
        
        def run_job():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"[内存队列] 任务执行失败: {e}")
        
        thread = threading.Thread(target=run_job)
        thread.daemon = True
        thread.start()
        
        logger.info(f"[内存队列] 任务已加入队列，ID: {job_id}")
        return job_id

# 尝试使用Redis队列，如果失败则使用内存队列
try:
    from rq import Queue
    from redis import Redis
    import os

    # 从环境变量读取 Redis 配置
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_password = os.getenv('REDIS_PASSWORD', '')

    # 连接到Redis
    redis_conn = Redis(host=redis_host, port=redis_port, db=0, password=redis_password, socket_connect_timeout=2)
    redis_conn.ping()

    # 创建任务队列
    wash_queue = Queue('wash', connection=redis_conn)
    logger.info("[洗白队列] 成功连接到Redis队列")
except Exception as e:
    logger.warning(f"[洗白队列] Redis连接失败，使用内存队列: {e}")
    wash_queue = MemoryQueue()

def create_share_async(share_data):
    """
    异步创建分享链接
    """
    try:
        logger.info(f"[异步洗白] 开始处理: {share_data.get('title')}, URL: {share_data.get('share_url')}")
        start_time = time.time()
        
        # 调用同步的创建分享函数
        result = sync_create_share(share_data)
        
        end_time = time.time()
        logger.info(f"[异步洗白] 处理完成，耗时: {end_time - start_time:.2f}秒")
        
        return result
    except Exception as e:
        logger.exception(f"[异步洗白] 处理失败: {e}")
        return None

def enqueue_wash_task(share_data):
    """
    将洗白任务加入队列
    """
    job = wash_queue.enqueue(create_share_async, share_data)
    logger.info(f"[洗白队列] 任务已加入队列，ID: {job}")
    return job
