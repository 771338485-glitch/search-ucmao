from flask import Blueprint, request, jsonify, Response
from src.services.douban_service import douban_service
import requests
from urllib.parse import urlparse, unquote
import re
import logging

logger = logging.getLogger(__name__)

douban_bp = Blueprint('douban', __name__)

ALLOWED_HOSTS = re.compile(r'^img\d+\.doubanio\.com$')
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

@douban_bp.route('/api/img')
def proxy_image():
    """代理豆瓣图片接口，绕过反爬"""
    try:
        raw_url = request.args.get('url', '')
        if not raw_url:
            return Response('Missing url', status=400)
        
        url = unquote(raw_url)
        
        if not url or not url.startswith('https://'):
            return Response('Invalid url', status=400)
        
        try:
            parsed_url = urlparse(url)
            host = parsed_url.hostname
        except Exception:
            return Response('Invalid url', status=400)
        
        if not ALLOWED_HOSTS.match(host):
            return Response('Host not allowed', status=403)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Referer": "https://movie.douban.com/",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
        
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()

        # 检查 Content-Length
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_IMAGE_SIZE:
            return Response('Image too large', status=413)
        
        # 流式生成响应
        def generate():
            chunk_size = 8192
            total_size = 0
            for chunk in response.iter_content(chunk_size=chunk_size):
                total_size += len(chunk)
                if total_size > MAX_IMAGE_SIZE:
                    break
                yield chunk
        
        return Response(generate(), content_type=response.headers.get('Content-Type', 'image/jpeg'))
        
    except Exception as e:
        logger.error(f"代理图片失败: {e}")
        return Response('Image fetch failed', status=503)

@douban_bp.route('/api/douban-hot')
def api_douban_hot():
    """
    获取豆瓣热门榜单数据的API
    """
    try:
        category = request.args.get('category', 'douban-movie')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 25, type=int)
        
        data = douban_service.get_hot_movies(category, page, limit)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'category': category,
                'items': data['items'],
                'hasMore': data['hasMore'],
                'page': page,
                'limit': limit
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': -1,
            'message': f'获取豆瓣榜单失败: {str(e)}',
            'data': {
                'category': category,
                'items': [],
                'hasMore': False,
                'page': page,
                'limit': limit
            }
        })
