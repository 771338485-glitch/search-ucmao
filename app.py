# 在所有其他 import 之前清除代理环境变量
# 系统 SOCKS5 代理会导致 requests 通过代理连接外部 HTTPS API，严重超时
import os as _os
for _pk in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
            'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    _os.environ.pop(_pk, None)
# 禁止 requests 自动读取代理
_os.environ['NO_PROXY'] = '*'

import logging
from functools import wraps
from flask import Flask, render_template, request, abort, jsonify
from flask_compress import Compress
from configs.logging_setup import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

from routes.api_config_routes import api_config_bp
from routes.search_routes import search_bp
from routes.hot_resource_routes import resources_bp
from routes.auth_routes import auth_bp
from routes.search_history_routes import search_history_bp

from routes.email_config_routes import email_config_bp
from routes.douban_routes import douban_bp
from routes.movie_routes import movie_bp
from configs.app_config import SECRET_KEY, API_KEY

# 检查环境变量（在加载配置之后）
from utils.env_checker import validate_environment
validate_environment()

app = Flask(__name__)

app.secret_key = SECRET_KEY
app.config['API_KEY'] = API_KEY

# 启用Gzip压缩
Compress(app)

# API密钥认证装饰器
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if not api_key:
            abort(401, description='Missing API key')
        if api_key != app.config['API_KEY']:
            abort(403, description='Invalid API key')
        return f(*args, **kwargs)
    return decorated_function

# 防止恶意请求的装饰器
from collections import defaultdict
import time

_request_counts = defaultdict(list)
_last_cleanup = time.time()
_CLEANUP_INTERVAL = 300  # 5 分钟清理一次

def rate_limit(max_requests=60, window_seconds=60):
    """速率限制装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            global _last_cleanup
            client_ip = request.remote_addr
            now = time.time()

            # 定期清理空列表条目
            if now - _last_cleanup > _CLEANUP_INTERVAL:
                _last_cleanup = now
                empty_ips = [ip for ip, times in _request_counts.items() if not times]
                for ip in empty_ips:
                    del _request_counts[ip]

            # 清理过期记录
            _request_counts[client_ip] = [
                t for t in _request_counts[client_ip] if now - t < window_seconds
            ]
            if len(_request_counts[client_ip]) >= max_requests:
                return jsonify({"code": 429, "message": "请求过于频繁，请稍后再试", "data": None}), 429
            _request_counts[client_ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 静态文件缓存策略
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 24小时缓存

# 添加 seedhub_images 目录作为静态文件目录
import os
from flask import send_from_directory

seedhub_images_dir = os.path.join(os.path.dirname(__file__), 'seedhub_images')

@app.route('/seedhub_images/<path:filename>')
def serve_seedhub_images(filename):
    return send_from_directory(seedhub_images_dir, filename)

# 针对二维码等动态文件的特殊处理
@app.after_request
def add_header(response):
    # 对于图片文件，设置较短的缓存时间
    if response.content_type and ('image' in response.content_type):
        response.headers['Cache-Control'] = 'public, max-age=3600'  # 1小时
    return response

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(api_config_bp)
app.register_blueprint(search_bp)
app.register_blueprint(resources_bp)
app.register_blueprint(search_history_bp)

app.register_blueprint(email_config_bp)
app.register_blueprint(douban_bp)
app.register_blueprint(movie_bp)

# 上下文处理器，将登录状态传递给所有模板
@app.context_processor
def inject_login_status():
    from flask import request
    import jwt
    token = request.cookies.get('token')
    is_logged_in = False
    try:
        if token:
            jwt.decode(token, app.secret_key, algorithms=['HS256'])
            is_logged_in = True
    except jwt.ExpiredSignatureError:
        pass
    except jwt.InvalidTokenError:
        pass
    return {'is_logged_in': is_logged_in}


# 首页，返回 HTML 文件
@app.route('/')
def search_index():
    return render_template('index.html')


def init_app():
    """初始化应用：创建表、启动定时任务等"""
    from src.db.stored_files_dao import init_stored_files_table
    from src.db.search_history_dao import init_search_history_table
    from src.db.resources_dao import init_resources_table
    from src.db.api_config_dao import init_api_config_table
    from src.db.cookie_config_dao import init_cookie_config_table
    from src.db.movies_dao import init_movies_table
    from src.db.genres_dao import init_genres_table, init_movie_genres_table
    from src.db.tags_dao import init_tags_table, init_movie_tags_table
    from src.db.qr_code_dao import init_qr_code_table
    from src.scheduler.cleanup_scheduler import start_scheduler
    from src.scheduler.email_scheduler import start_email_scheduler
    from src.scheduler.movie_crawl_scheduler import start_movie_crawl_scheduler
    
    logger.info("初始化应用...")
    init_resources_table()
    init_api_config_table()
    init_cookie_config_table()
    init_stored_files_table()
    init_search_history_table()
    init_qr_code_table()
    # 初始化电影相关表
    init_movies_table()
    init_genres_table()
    init_movie_genres_table()
    init_tags_table()
    init_movie_tags_table()
    start_scheduler(interval_minutes=5, expire_minutes=5)
    start_email_scheduler()  # 启动邮件通知调度器
    start_movie_crawl_scheduler()  # 启动电影采集调度器
    logger.info("应用初始化完成")


def start_async_init():
    """异步初始化应用"""
    import threading
    thread = threading.Thread(target=init_app)
    thread.daemon = True
    thread.start()


if __name__ == '__main__':
    import os
    import argparse
    from dotenv import load_dotenv
    load_dotenv()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='启动Flask应用')
    parser.add_argument('--port', type=int, help='指定服务器端口')
    args = parser.parse_args()
    
    # 优先使用命令行参数，然后是环境变量，最后是默认值
    if args.port:
        port = args.port
    else:
        port = int(os.getenv('PORT', 5004))
    
    # 异步初始化应用，让 Flask 应用先启动
    start_async_init()
    
    logger.info("启动 Flask 应用")
    app.run(host='0.0.0.0', port=port, debug=False)

