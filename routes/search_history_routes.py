from flask import Blueprint, render_template, request, jsonify
import logging

from src.db.search_history_dao import (
    get_search_history,
    get_search_history_count,
    get_search_keyword_stats,
    delete_old_search_history,
    get_daily_visitor_count,
    get_yesterday_visitor_count,
    get_last_7_days_visitor_count,
    get_last_30_days_visitor_count
)
from utils.auth_utils import token_required, api_token_required

logger = logging.getLogger(__name__)

search_history_bp = Blueprint("search_history", __name__)


@search_history_bp.route("/search_history", methods=["GET"])
@token_required
def search_history_page():
    """搜索历史页面（需要认证）"""
    return render_template("search_history.html")


@search_history_bp.route("/api/search_history", methods=["GET"])
@api_token_required
def api_search_history():
    """获取搜索历史 API（需要认证）"""
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 50, type=int)
        limit = min(limit, 100)
        offset = (page - 1) * limit

        history = get_search_history(limit=limit, offset=offset)
        total_count = get_search_history_count()

        # 格式化数据
        formatted_history = []
        for item in history:
            search_time = item[3]
            # 检查search_time的类型
            if isinstance(search_time, str):
                # 已经是字符串，直接使用
                formatted_time = search_time
            else:
                # 是datetime对象，调用strftime
                formatted_time = search_time.strftime("%Y-%m-%d %H:%M:%S") if search_time else ""
            
            formatted_history.append({
                "id": item[0],
                "ip_address": item[1],
                "search_keyword": item[2],
                "search_time": formatted_time
            })

        return jsonify({
            "success": True,
            "data": formatted_history,
            "total": total_count,
            "page": page,
            "limit": limit
        })
    except Exception as e:
        logger.error(f"获取搜索历史失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"}), 500


@search_history_bp.route("/api/search_history/stats", methods=["GET"])
def api_search_history_stats():
    """获取搜索关键词统计 API"""
    try:
        limit = request.args.get("limit", 20, type=int)
        limit = min(limit, 100)
        stats = get_search_keyword_stats(limit=limit)

        formatted_stats = []
        for item in stats:
            formatted_stats.append({
                "search_keyword": item[0],
                "count": item[1]
            })

        return jsonify({
            "success": True,
            "data": formatted_stats
        })
    except Exception as e:
        logger.error(f"获取搜索关键词统计失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"}), 500


@search_history_bp.route("/api/search_history/cleanup", methods=["POST"])
@api_token_required
def api_cleanup_search_history():
    """清理旧搜索历史 API"""
    try:
        days = request.json.get("days", 30) if request.is_json else 30
        try:
            days = int(days)
            if days < 1 or days > 365:
                return jsonify({"code": 400, "message": "保留天数必须在 1-365 之间", "data": None}), 400
        except (ValueError, TypeError):
            return jsonify({"code": 400, "message": "保留天数必须是有效整数", "data": None}), 400
        deleted_count = delete_old_search_history(days=days)

        return jsonify({
            "success": True,
            "message": f"成功清理 {deleted_count} 条记录",
            "deleted_count": deleted_count
        })
    except Exception as e:
        logger.error(f"清理搜索历史失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"清理失败: {str(e)}"}), 500


@search_history_bp.route("/api/visitor/stats", methods=["GET"])
def api_visitor_stats():
    """获取访客统计 API"""
    try:
        daily = get_daily_visitor_count()
        yesterday = get_yesterday_visitor_count()
        last_7_days = get_last_7_days_visitor_count()
        last_30_days = get_last_30_days_visitor_count()

        return jsonify({
            "success": True,
            "data": {
                "today": daily,
                "yesterday": yesterday,
                "last_7_days": last_7_days,
                "last_30_days": last_30_days
            }
        })
    except Exception as e:
        logger.error(f"获取访客统计失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"获取失败: {str(e)}"}), 500
