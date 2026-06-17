# configs/app_config.py

import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 设置 SECRET_KEY，用于会话管理和 JWT（必需）
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY 环境变量必须配置")

# 网盘信息
QUARK_PAN_COOKIE = os.getenv('QUARK_PAN_COOKIE')
BAIDU_PAN_COOKIE = os.getenv('BAIDU_PAN_COOKIE')
DEFAULT_SAVE_DIR = os.getenv('DEFAULT_SAVE_DIR')

# 管理员账号密码（必需）
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# API密钥（不允许硬编码默认值，必须通过环境变量配置）（必需）
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY 环境变量必须配置")

# 加密密钥（必需，至少 32 字节）
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY 环境变量必须配置")
if len(ENCRYPTION_KEY.encode()) < 32:
    raise ValueError("ENCRYPTION_KEY 长度必须至少 32 字节")

# SQLite数据库配置
sqlite_db_path = os.path.join(os.path.dirname(current_dir), 'data', 'search_ucmao.db')

# User-Agent 列表配置
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.203',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.203',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.203'
]

# 搜索配置
SEARCH_MAX_CONCURRENCY = int(os.getenv('SEARCH_MAX_CONCURRENCY', '8'))  # 最大并发数
SEARCH_VARIANT_TRIGGER = int(os.getenv('SEARCH_VARIANT_TRIGGER', '25'))  # 触发变体搜索的结果阈值
SEARCH_PLUGIN_TIMEOUT_MS = int(os.getenv('SEARCH_PLUGIN_TIMEOUT_MS', '20000'))  # API超时时间（毫秒）
    
