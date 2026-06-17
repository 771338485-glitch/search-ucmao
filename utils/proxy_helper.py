"""代理环境变量保存/恢复工具"""
import os

_PROXY_KEYS = [
    "http_proxy", "HTTP_PROXY",
    "https_proxy", "HTTPS_PROXY",
    "all_proxy", "ALL_PROXY",
]

# 模块加载时快照当前代理环境变量
_saved: dict[str, str] = {}
for _k in _PROXY_KEYS:
    _v = os.environ.get(_k)
    if _v is not None:
        _saved[_k] = _v


def restore_proxy_env():
    """将代理环境变量恢复为进程启动时的值"""
    for k in _PROXY_KEYS:
        if k in _saved:
            os.environ[k] = _saved[k]
        else:
            os.environ.pop(k, None)
