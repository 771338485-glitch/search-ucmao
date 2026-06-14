import logging
from flask import Blueprint, request, jsonify

from src.services.movie_service import movie_service
from utils.validation_utils import validate_keyword, validate_category, validate_integer, validate_page, validate_limit, validate_tag_name
from utils.auth_utils import api_token_required

logger = logging.getLogger(__name__)

# 创建蓝图
movie_bp = Blueprint('movie', __name__)


@movie_bp.route('/api/movies/hot')
def api_hot_movies():
    """
    获取热门电影API
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 12, type=int)
        category = request.args.get('category', None, type=str)
        
        # 验证输入
        validated_page = validate_page(page)
        validated_limit = validate_limit(limit)
        validated_category = validate_category(category)
        
        # 打印接收到的参数，用于调试
        logger.debug(f"接收到的参数: page={validated_page}, limit={validated_limit}, category={validated_category}")
        result = movie_service.get_hot_movies(validated_page, validated_limit, validated_category)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
    except Exception as e:
        logger.error(f"获取热门电影失败: {e}")
        return jsonify({
            'code': -1,
            'message': f'获取热门电影失败: {str(e)}',
            'data': {
                'items': [],
                'page': 1,
                'limit': 12,
                'total': 0,
                'hasMore': False
            }
        })


@movie_bp.route('/api/movies/detail/<int:movie_id>')
def api_movie_detail(movie_id):
    """
    获取电影详情API
    """
    try:
        movie = movie_service.get_movie_detail(movie_id)
        
        if movie:
            return jsonify({
                'code': 0,
                'message': 'success',
                'data': movie
            })
        else:
            return jsonify({
                'code': -1,
                'message': '电影不存在',
                'data': None
            })
    except Exception as e:
        logger.error(f"获取电影详情失败: {e}")
        return jsonify({
            'code': -1,
            'message': f'获取电影详情失败: {str(e)}',
            'data': None
        })


@movie_bp.route('/api/movies/search')
def api_search_movies():
    """
    搜索电影API
    """
    try:
        keyword = request.args.get('keyword', '', type=str)
        limit = request.args.get('limit', 20, type=int)
        
        # 验证输入
        validated_keyword = validate_keyword(keyword)
        validated_limit = validate_limit(limit)
        
        if not validated_keyword:
            return jsonify({
                'code': -1,
                'message': '搜索关键词不能为空或包含无效字符',
                'data': {
                    'items': []
                }
            })
        
        movies = movie_service.search_movies(validated_keyword, validated_limit)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'items': movies,
                'keyword': validated_keyword,
                'limit': validated_limit
            }
        })
    except Exception as e:
        logger.error(f"搜索电影失败: {e}")
        return jsonify({
            'code': -1,
            'message': f'搜索电影失败: {str(e)}',
            'data': {
                'items': []
            }
        })


@movie_bp.route('/api/movies/crawl')
@api_token_required
def api_crawl_movies():
    """
    爬取电影数据API
    """
    try:
        pages = request.args.get('pages', 2, type=int)
        category = request.args.get('category', '电影', type=str)
        
        # 验证输入
        validated_pages = validate_integer(pages, min_value=1, max_value=10)
        validated_category = validate_category(category)
        
        saved_count = movie_service.schedule_seedhub_crawl(validated_pages or 2, validated_category or '电影')
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'saved_count': saved_count,
                'pages': validated_pages or 2,
                'category': validated_category or '电影'
            }
        })
    except Exception as e:
        logger.error(f"爬取电影数据失败: {e}")
        return jsonify({
            'code': -1,
            'message': f'爬取电影数据失败: {str(e)}',
            'data': {
                'saved_count': 0,
                'pages': 0,
                'category': '电影'
            }
        })


@movie_bp.route('/api/movies/latest')
def api_latest_movies():
    """
    获取最新电影API
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 12, type=int)
        
        # 验证输入
        validated_page = validate_page(page)
        validated_limit = validate_limit(limit)
        
        # 打印接收到的参数，用于调试
        logger.debug(f"接收到的参数: page={validated_page}, limit={validated_limit}")
        result = movie_service.get_latest_movies(validated_page, validated_limit)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
    except Exception as e:
        logger.error(f"获取最新电影失败: {e}")
        return jsonify({
            'code': -1,
            'message': f'获取最新电影失败: {str(e)}',
            'data': {
                'items': [],
                'page': 1,
                'limit': 12,
                'total': 0,
                'hasMore': False
            }
        })


@movie_bp.route('/api/movies/tag/<tag_name>')
def api_movies_by_tag(tag_name):
    """
    根据标签获取电影API
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 12, type=int)
        
        # 验证输入
        validated_tag_name = validate_tag_name(tag_name)
        validated_page = validate_page(page)
        validated_limit = validate_limit(limit)
        
        if not validated_tag_name:
            return jsonify({
                'code': -1,
                'message': '无效的标签名称',
                'data': {
                    'items': [],
                    'page': 1,
                    'limit': 12,
                    'total': 0,
                    'hasMore': False
                }
            })
        
        # 打印接收到的参数，用于调试
        logger.debug(f"接收到的参数: tag_name={validated_tag_name}, page={validated_page}, limit={validated_limit}")
        result = movie_service.get_movies_by_tag(validated_tag_name, validated_page, validated_limit)
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': result
        })
    except Exception as e:
        logger.error(f"根据标签获取电影失败: {e}")
        return jsonify({
            'code': -1,
            'message': f'根据标签获取电影失败: {str(e)}',
            'data': {
                'items': [],
                'page': 1,
                'limit': 12,
                'total': 0,
                'hasMore': False
            }
        })


@movie_bp.route('/api/movies/crawl/hot')
@api_token_required
def api_crawl_hot_movies():
    """
    爬取热门电影数据API
    """
    try:
        pages = request.args.get('pages', 1, type=int)
        
        # 验证输入
        validated_pages = validate_integer(pages, min_value=1, max_value=10)
        
        saved_count = 0
        for page in range(1, (validated_pages or 1) + 1):
            movies = movie_service.crawl_seedhub_hot_movies(page)
            for movie in movies:
                movie_service.save_movie(movie)
                saved_count += 1
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'saved_count': saved_count,
                'pages': validated_pages or 1
            }
        })
    except Exception as e:
        logger.error(f"爬取热门电影数据失败: {e}")
        return jsonify({
            'code': -1,
            'message': f'爬取热门电影数据失败: {str(e)}',
            'data': {
                'saved_count': 0,
                'pages': 0
            }
        })


@movie_bp.route('/api/movies/crawl/new')
@api_token_required
def api_crawl_new_movies():
    """
    爬取新上映电影数据API
    """
    try:
        pages = request.args.get('pages', 1, type=int)
        
        # 验证输入
        validated_pages = validate_integer(pages, min_value=1, max_value=10)
        
        saved_count = 0
        for page in range(1, (validated_pages or 1) + 1):
            movies = movie_service.crawl_seedhub_new_movies(page)
            for movie in movies:
                movie_service.save_movie(movie)
                saved_count += 1
        
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'saved_count': saved_count,
                'pages': validated_pages or 1
            }
        })
    except Exception as e:
        logger.error(f"爬取新上映电影数据失败: {e}")
        return jsonify({
            'code': -1,
            'message': f'爬取新上映电影数据失败: {str(e)}',
            'data': {
                'saved_count': 0,
                'pages': 0
            }
        })
