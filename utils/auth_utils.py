import datetime
from functools import wraps

import jwt
from flask import request, redirect, url_for, jsonify

from configs.app_config import SECRET_KEY


def create_jwt_token():
    """创建 JWT 令牌，有效期 24 小时"""
    now = datetime.datetime.now(datetime.timezone.utc)
    expiration = now + datetime.timedelta(hours=24)
    payload = {
        "exp": expiration,
        "iat": now,
        "sub": "admin",
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def _verify_token():
    """验证 JWT Token，返回 (is_valid, error_response)"""
    token = request.cookies.get("token")
    # 同时支持 Authorization Bearer 头
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return False, None

    try:
        jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return True, None
    except jwt.ExpiredSignatureError:
        return False, None
    except jwt.InvalidTokenError:
        return False, None


def token_required(f):
    """JWT 令牌验证装饰器（用于页面路由，未授权时重定向到登录页）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        is_valid, _ = _verify_token()
        if not is_valid:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def api_token_required(f):
    """JWT 令牌验证装饰器（用于 API 路由，未授权时返回 401 JSON）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        is_valid, _ = _verify_token()
        if not is_valid:
            return jsonify({"code": 401, "message": "未授权，请先登录", "data": None}), 401
        return f(*args, **kwargs)
    return decorated
