import logging
from functools import wraps
from flask import jsonify

logger = logging.getLogger(__name__)


class AppException(Exception):
    """应用基础异常类"""
    
    def __init__(self, message, status_code=500, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}
    
    def to_dict(self):
        result = dict(self.payload)
        result['success'] = False
        result['message'] = self.message
        return result


class ValidationError(AppException):
    """验证错误"""
    
    def __init__(self, message, payload=None):
        super().__init__(message, status_code=400, payload=payload)


class NotFoundError(AppException):
    """资源未找到错误"""
    
    def __init__(self, message, payload=None):
        super().__init__(message, status_code=404, payload=payload)


class AuthenticationError(AppException):
    """认证错误"""
    
    def __init__(self, message, payload=None):
        super().__init__(message, status_code=401, payload=payload)


class DatabaseError(AppException):
    """数据库错误"""
    
    def __init__(self, message, payload=None):
        super().__init__(message, status_code=500, payload=payload)


def handle_exceptions(f):
    """
    统一异常处理装饰器
    
    用法：
        @handle_exceptions
        def my_route():
            # 你的代码
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AppException as e:
            logger.error(f"应用异常: {e.message}", exc_info=True)
            return jsonify(e.to_dict()), e.status_code
        except Exception as e:
            logger.error(f"未处理的异常: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': '服务器内部错误'
            }), 500
    
    return decorated_function


def log_function_call(f):
    """
    函数调用日志装饰器
    
    用法：
        @log_function_call
        def my_function():
            # 你的代码
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        function_name = f.__name__
        logger.info(f"调用函数: {function_name}")
        
        try:
            result = f(*args, **kwargs)
            logger.info(f"函数 {function_name} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {function_name} 执行失败: {str(e)}", exc_info=True)
            raise
    
    return decorated_function
