from flask import Blueprint, jsonify, request, render_template, send_file
import logging
import os

from werkzeug.utils import secure_filename

from utils.auth_utils import token_required, api_token_required
from src.services.hot_resource_service import (
    list_resources,
    get_resource_detail,
    add_resource_and_share,
    update_resource_info,
    delete_resource_and_share,
)
from src.db.cookie_config_dao import get_cookie_by_cloud_name, save_cookie
from src.clients.quark_client import Quark
from src.clients.baidu_client import Baidu
from src.pan_operator import clear_cookie_cache

logger = logging.getLogger(__name__)

resources_bp = Blueprint("resources", __name__)


@resources_bp.route("/hot_resource")
@token_required
def resources_page():
    """资源管理页面，需要JWT验证"""
    return render_template("hot_resource.html")


@resources_bp.route("/api/resources", methods=["GET"])
@api_token_required
def get_resources():
    """获取资源列表，支持分页和搜索功能"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 10, type=int)
    search = request.args.get("search", "", type=str)

    success, message, data = list_resources(page=page, page_size=page_size, search=search)
    if not success:
        return jsonify({"success": False, "message": message}), 500
    return jsonify({"success": True, "data": data})


@resources_bp.route("/api/resources/<int:resource_id>", methods=["GET"])
@token_required
def get_resource(resource_id):
    """获取单个资源详情"""
    success, message, resource = get_resource_detail(resource_id)
    if not success:
        status = 404 if message == "资源不存在" else 500
        return jsonify({"success": False, "message": message}), status
    return jsonify({"success": True, "data": resource})


@resources_bp.route("/api/resources", methods=["POST"])
@api_token_required
def add_resource():
    """添加新资源"""
    resource_data = request.get_json()
    success, message, new_id = add_resource_and_share(resource_data)
    if not success:
        status = 400 if "必填项" in message else 500 if "数据库" in message else 500
        return jsonify({"success": False, "message": message}), status
    return jsonify({"success": True, "message": message, "id": new_id}), 201


@resources_bp.route("/api/resources/<int:resource_id>", methods=["PUT"])
@api_token_required
def update_resource(resource_id):
    """更新资源信息"""
    resource_data = request.get_json()
    success, message = update_resource_info(resource_id, resource_data)
    if not success:
        status = 400 if "必填项" in message else 404 if message == "资源不存在" else 500
        return jsonify({"success": False, "message": message}), status
    return jsonify({"success": True, "message": message})


@resources_bp.route("/api/resources/<int:resource_id>", methods=["DELETE"])
@api_token_required
def delete_resource(resource_id):
    """删除资源"""
    success, message = delete_resource_and_share(resource_id)
    if not success:
        status = 404 if message == "资源不存在" else 500
        return jsonify({"success": False, "message": message}), status
    return jsonify({"success": True, "message": message})


@resources_bp.route("/cookie-config", methods=["GET"])
@api_token_required
def get_cookie_config():
    """获取Cookie配置"""
    baidu_cookie = get_cookie_by_cloud_name("百度网盘")
    quark_cookie = get_cookie_by_cloud_name("夸克网盘")

    # 掩码处理 Cookie 值，不返回实际内容
    def mask_cookie(cookie_value):
        if not cookie_value:
            return None
        if len(cookie_value) <= 8:
            return "***"
        return cookie_value[:4] + "***" + cookie_value[-4:]

    return jsonify({"baidu_cookie": mask_cookie(baidu_cookie), "quark_cookie": mask_cookie(quark_cookie)})


@resources_bp.route("/cookie-config", methods=["POST"])
@api_token_required
def save_cookie_config():
    """保存Cookie配置"""
    data = request.get_json()
    baidu_cookie = data.get("baidu_cookie", "")
    quark_cookie = data.get("quark_cookie", "")
    
    messages = []
    
    logger.info(f"保存Cookie请求 - 百度Cookie长度: {len(baidu_cookie) if baidu_cookie else 0}, 夸克Cookie长度: {len(quark_cookie) if quark_cookie else 0}")
    
    # 保存百度网盘Cookie（如果提供）
    if baidu_cookie and baidu_cookie.strip():
        logger.info("开始验证百度网盘Cookie")
        try:
            client = Baidu(baidu_cookie)
            quota = client.get_quota()
            if not quota:
                return jsonify({"success": False, "message": "百度网盘Cookie无效，请检查后重新输入"}), 400
            used_gb = round(quota['used'] / (1024**3), 2)
            total_gb = round(quota['total'] / (1024**3), 2)
            messages.append(f"百度网盘Cookie验证成功（已用{used_gb}GB/{total_gb}GB）")
        except Exception as e:
            logger.error(f"验证百度网盘Cookie失败: {e}")
            return jsonify({"success": False, "message": "百度网盘Cookie验证失败，请检查后重新输入"}), 400
        
        success, message = save_cookie("百度网盘", baidu_cookie)
        if not success:
            return jsonify({"success": False, "message": message}), 500
        clear_cookie_cache("百度网盘")
    else:
        logger.info("百度网盘Cookie为空，跳过验证和保存")
    
    # 保存夸克网盘Cookie（如果提供）
    if quark_cookie and quark_cookie.strip():
        logger.info("开始验证夸克网盘Cookie")
        try:
            client = Quark(quark_cookie)
            quota = client.get_quota()
            if not quota:
                return jsonify({"success": False, "message": "夸克网盘Cookie无效，请检查后重新输入"}), 400
            used_gb = round(quota['used'] / (1024**3), 2)
            total_gb = round(quota['total'] / (1024**3), 2)
            messages.append(f"夸克网盘Cookie验证成功（已用{used_gb}GB/{total_gb}GB）")
        except Exception as e:
            logger.error(f"验证夸克网盘Cookie失败: {e}")
            return jsonify({"success": False, "message": "夸克网盘Cookie验证失败，请检查后重新输入"}), 400
        
        success, message = save_cookie("夸克网盘", quark_cookie)
        if not success:
            return jsonify({"success": False, "message": message}), 500
        clear_cookie_cache("夸克网盘")
    else:
        logger.info("夸克网盘Cookie为空，跳过验证和保存")
    
    return jsonify({"success": True, "message": "；".join(messages) if messages else "Cookie配置保存成功"})


@resources_bp.route("/upload-qr-code", methods=["POST"])
@api_token_required
def upload_qr_code():
    """上传二维码图片"""
    try:
        if "qr_code" not in request.files:
            return jsonify({"success": False, "message": "没有选择文件"}), 400
        
        file = request.files["qr_code"]
        if file.filename == "":
            return jsonify({"success": False, "message": "没有选择文件"}), 400
        
        # 检查文件大小（限制为 5MB）
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({"success": False, "message": "文件大小不能超过 5MB"}), 400
        
        # 检查文件类型
        allowed_extensions = {"png", "jpg", "jpeg", "gif", "bmp"}
        filename = secure_filename(file.filename)
        if not filename or not ("." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions):
            return jsonify({"success": False, "message": "不支持的文件类型，仅支持 png, jpg, jpeg, gif, bmp"}), 400
        
        # 保存文件到固定路径
        upload_path = os.path.join("static", "images", "qr_code_upload.png")
        file.save(upload_path)
        
        # 计算过期时间（当前时间 + 5天）
        from datetime import datetime, timedelta
        upload_time = datetime.now()
        expires_at = upload_time + timedelta(days=5)
        
        # 记录到数据库 - 更新或插入（只保留一条记录）
        from src.db.qr_code_dao import upsert_qr_code
        qr_code_data = {
            "file_name": filename,
            "file_path": upload_path,
            "file_size": file_size,
            "expires_at": expires_at
        }
        upsert_qr_code(qr_code_data)
        
        logger.info(f"二维码上传成功: {upload_path}, 大小: {file_size} bytes, 过期时间: {expires_at}")
        return jsonify({"success": True, "message": "二维码上传成功"})
    
    except Exception as e:
        logger.error(f"上传二维码失败: {str(e)}")
        return jsonify({"success": False, "message": f"上传失败: {str(e)}"}), 500


@resources_bp.route("/get-qr-code", methods=["GET"])
def get_qr_code():
    """获取二维码图片，不使用缓存"""
    try:
        qr_path = os.path.join("static", "images", "qr_code_upload.png")
        
        # 如果上传的图片不存在，返回默认图片
        if not os.path.exists(qr_path):
            qr_path = os.path.join("static", "images", "code.png")
        
        # 返回图片，禁用所有缓存
        response = send_file(qr_path, mimetype='image/png')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        response.headers['Last-Modified'] = '0'
        
        return response
    except Exception as e:
        logger.error(f"获取二维码失败: {str(e)}")
        # 如果出错，返回默认图片
        return send_file(os.path.join("static", "images", "code.png"), mimetype='image/png')


@resources_bp.route("/api/quota", methods=["GET"])
@api_token_required
def get_quota_info():
    """获取网盘空间信息"""
    try:
        cloud_name = request.args.get("cloud", "夸克网盘")  # 默认夸克网盘
        
        cookie = get_cookie_by_cloud_name(cloud_name)
        if not cookie:
            return jsonify({"success": False, "message": f"未配置{cloud_name}Cookie"}), 400
        
        if cloud_name == "夸克网盘":
            client = Quark(cookie)
        elif cloud_name == "百度网盘":
            client = Baidu(cookie)
        else:
            return jsonify({"success": False, "message": "不支持的网盘类型"}), 400
        
        quota = client.get_quota()
        
        if quota:
            # 转换字节为GB显示
            quota['used_gb'] = round(quota['used'] / (1024**3), 2)
            quota['total_gb'] = round(quota['total'] / (1024**3), 2)
            quota['free_gb'] = round(quota['free'] / (1024**3), 2)
            return jsonify({"success": True, "data": quota})
        else:
            return jsonify({"success": False, "message": "获取空间信息失败"}), 500
    except Exception as e:
        logger.error(f"获取空间信息时出错: {e}")
        return jsonify({"success": False, "message": f"获取空间信息失败: {str(e)}"}), 500


@resources_bp.route("/api/clean", methods=["POST"])
@api_token_required
def clean_old_files():
    """自动清理旧文件"""
    try:
        data = request.get_json() or {}
        cloud_name = data.get("cloud", "夸克网盘")  # 默认夸克网盘
        threshold = data.get("threshold", 80)  # 默认80%触发清理
        count = data.get("count", 20)  # 默认清理20个文件
        
        cookie = get_cookie_by_cloud_name(cloud_name)
        if not cookie:
            return jsonify({"success": False, "message": f"未配置{cloud_name}Cookie"}), 400
        
        if cloud_name == "夸克网盘":
            client = Quark(cookie)
        elif cloud_name == "百度网盘":
            client = Baidu(cookie)
        else:
            return jsonify({"success": False, "message": "不支持的网盘类型"}), 400
        
        success, deleted_count, used_percent = client.clean_old_files(threshold, count)
        
        if success:
            if deleted_count > 0:
                return jsonify({
                    "success": True, 
                    "message": f"成功清理 {deleted_count} 个旧文件，清理前使用率: {used_percent}%",
                    "deleted_count": deleted_count,
                    "used_percent_before": used_percent
                })
            else:
                return jsonify({
                    "success": True, 
                    "message": f"当前空间使用率 {used_percent}% 低于阈值 {threshold}%，无需清理",
                    "deleted_count": 0,
                    "used_percent": used_percent
                })
        else:
            return jsonify({"success": False, "message": "清理失败"}), 500
    except Exception as e:
        logger.error(f"清理文件时出错: {e}")
        return jsonify({"success": False, "message": f"清理失败: {str(e)}"}), 500



