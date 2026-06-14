# routes/search_routes.py

from flask import Blueprint, request, jsonify, Response

import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.pan_operator import create_share, del_share
from src.services.search_service import (
    generate_search_stream_events,
    search_resources,
)
from utils.validation_utils import validate_keyword, validate_url, validate_title, validate_integer
from utils.auth_utils import api_token_required

logger = logging.getLogger(__name__)

search_bp = Blueprint("search", __name__)

_search_history_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="search_history")


def get_client_ip():
    """获取客户端 IP 地址"""
    # 优先从 X-Forwarded-For 获取（仅在反向代理后面时有效）
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr


@search_bp.route("/api/search_stream", methods=["GET"])
def search_stream():
    """
    使用 Server-Sent Events (SSE) 实时流式返回搜索结果。
    """
    keyword = request.args.get("keyword")
    # 验证关键词
    validated_keyword = validate_keyword(keyword)
    if not validated_keyword:
        return jsonify({"error": "请提供有效的搜索关键词"}), 400

    logger.info(f"用户 SSE 搜索关键词: {validated_keyword}")

    # 获取用户 IP 地址
    ip_address = get_client_ip()
    logger.info(f"客户端 IP 地址: {ip_address}")

    # 记录搜索历史（异步，不影响搜索速度）
    try:
        from src.db.search_history_dao import add_search_history
        _search_history_executor.submit(add_search_history, ip_address, validated_keyword)
    except Exception as e:
        logger.warning(f"记录搜索历史失败: {e}")

    def generate_events():
        for payload in generate_search_stream_events(validated_keyword):
            yield f"data: {payload}\n\n"

    response = Response(generate_events(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Accel-Buffering'] = 'no'  # 禁用 Nginx 缓冲
    return response


@search_bp.route("/api", methods=["GET"])
def search_api():
    """
    通过名称、云名称或类型搜索资源的API接口
    """
    name = request.args.get("name", "", type=str)
    cloud_name = request.args.get("cloud_name", "", type=str)
    resource_type = request.args.get("type", "", type=str)
    limit = request.args.get("limit", 100, type=int)
    sort = request.args.get("sort", "default")

    # 验证输入
    validated_name = validate_keyword(name)
    validated_cloud_name = validate_keyword(cloud_name)
    validated_resource_type = validate_keyword(resource_type)
    validated_limit = validate_integer(limit, min_value=1, max_value=100)

    # 验证排序参数
    valid_sort_values = ["default", "asc", "desc", "random"]
    if sort not in valid_sort_values:
        sort = "default"

    success, message, results = search_resources(
        name=validated_name or "", cloud_name=validated_cloud_name or "", resource_type=validated_resource_type or "",
        limit=validated_limit or 100, sort=sort
    )

    if not success:
        status_code = 400 if "至少需要提供" in message else 500
        return jsonify({"success": False, "message": message}), status_code

    return jsonify({"success": True, "total": len(results), "results": results})


@search_bp.route("/create_share", methods=["POST"])
def create_share_route():
    try:
        share_data = request.get_json()
        if not share_data:
            return jsonify({"error": "缺少参数"}), 400
        
        # 验证输入
        if "share_url" in share_data:
            share_data["share_url"] = validate_url(share_data["share_url"])
            if not share_data["share_url"]:
                return jsonify({"error": "无效的分享链接"}), 400
        
        if "title" in share_data:
            share_data["title"] = validate_title(share_data["title"])
            if not share_data["title"]:
                return jsonify({"error": "无效的标题"}), 400
        
        result = create_share(share_data)
        if result:
            logger.info(f"分享创建成功: {share_data.get('title')}")
            return jsonify({"message": '分享创建成功', "success": True, "data": result}), 200
        else:
            logger.warning(f"分享创建失败: {share_data.get('title')}")
            return jsonify({"error": "分享创建失败"}), 500
    except Exception as e:
        logger.error(f"创建分享时发生未知错误: {str(e)}", exc_info=True)
        return jsonify({"error": "服务器内部错误，请稍后重试"}), 500


@search_bp.route("/api/wash", methods=["POST"])
def wash_single_link():
    """手动洗白单条链接"""
    try:
        data = request.get_json()
        url = data.get("url") or data.get("share_url")
        title = data.get("title", "")
        
        # 验证输入
        validated_url = validate_url(url)
        if not validated_url:
            return jsonify({"success": False, "message": "无效的链接参数"}), 400
        
        validated_title = validate_title(title)
        if title and not validated_title:
            return jsonify({"success": False, "message": "无效的标题"}), 400
        
        from utils.netdisk_utils import match_netdisk_link
        netdisk_name = match_netdisk_link(validated_url)
        
        share_data = {
            "share_url": validated_url,
            "title": validated_title or "",
            "cloud_name": netdisk_name,
            "save_to_netdisk": {"quark": True, "baidu": True}
        }
        
        result = create_share(share_data)
        
        if result and result.get("share_url"):
            logger.info(f"[手动洗白] 成功: {validated_title or '无标题'} -> {result['share_url']}")
            return jsonify({
                "success": True,
                "message": "洗白成功",
                "data": {
                    "original_url": validated_url,
                    "washed_url": result["share_url"],
                    "file_id": result.get("file_id"),
                    "netdisk_name": netdisk_name
                }
            })
        else:
            # 如果洗白失败，返回原始链接
            return jsonify({
                "success": False,
                "message": "不支持洗白，返回原始链接",
                "data": {
                    "original_url": validated_url,
                    "washed_url": validated_url,
                    "file_id": None,
                    "netdisk_name": netdisk_name
                }
            })
            
    except Exception as e:
        logger.error(f"手动洗白失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "服务器内部错误，请稍后重试"}), 500


@search_bp.route("/del_share", methods=["POST"])
def del_share_route():
    try:
        share_data = request.get_json()
        if not share_data:
            return jsonify({"error": "缺少参数"}), 400
        
        # 验证输入
        if "share_url" in share_data:
            share_data["share_url"] = validate_url(share_data["share_url"])
            if not share_data["share_url"]:
                return jsonify({"error": "无效的分享链接"}), 400
        
        result = del_share(share_data)
        if result:
            logger.info(f"分享删除成功: URL={share_data.get('share_url')}")
            return jsonify({"message": "分享删除成功", "success": True}), 200
        else:
            logger.warning(f"分享删除失败: URL={share_data.get('share_url')}")
            return jsonify({"error": "分享删除失败"}), 500
    except Exception as e:
        logger.error(f"删除分享时发生未知错误: {str(e)}", exc_info=True)
        return jsonify({"error": "服务器内部错误，请稍后重试"}), 500


@search_bp.route("/api/check_validity", methods=["POST"])
def check_validity():
    """检查单个链接的有效性"""
    try:
        data = request.get_json()
        url = data.get("url")
        
        # 验证输入
        validated_url = validate_url(url)
        if not validated_url:
            return jsonify({"success": False, "message": "无效的链接参数"}), 400
        
        from utils.netdisk_utils import check_link_validity
        is_valid = check_link_validity(validated_url)
        
        return jsonify({
            "success": True,
            "data": {
                "url": validated_url,
                "is_valid": is_valid
            }
        })
    except Exception as e:
        logger.error(f"检查链接有效性失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "服务器内部错误，请稍后重试"}), 500


@search_bp.route("/api/check_validity_batch", methods=["POST"])
def check_validity_batch():
    """批量检查链接的有效性（使用线程池并行检测）"""
    try:
        data = request.get_json()
        urls = data.get("urls", [])
        
        if not urls or not isinstance(urls, list):
            return jsonify({"success": False, "message": "缺少链接参数或参数格式错误"}), 400
        
        # 验证输入
        validated_urls = []
        for url in urls:
            validated_url = validate_url(url)
            if validated_url:
                validated_urls.append(validated_url)
        
        if not validated_urls:
            return jsonify({"success": False, "message": "没有有效的链接参数"}), 400
        
        from utils.netdisk_utils import check_link_validity
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        results_dict = {}
        
        # 最多处理50个链接，避免服务器负载过高
        batch_urls = validated_urls[:50]
        
        # 使用线程池并行检测，最多10个线程
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(check_link_validity, url): url for url in batch_urls}
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    is_valid = future.result()
                    results_dict[url] = is_valid
                except Exception as e:
                    logger.error(f"检查链接有效性失败: {url} (错误: {e})")
                    results_dict[url] = False
        
        # 按原始顺序返回结果
        for url in batch_urls:
            results.append({
                "url": url,
                "is_valid": results_dict.get(url, False)
            })
        
        return jsonify({
            "success": True,
            "data": results
        })
    except Exception as e:
        logger.error(f"批量检查链接有效性失败: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "服务器内部错误，请稍后重试"}), 500