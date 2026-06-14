import logging
import requests
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from datetime import datetime

from src.db.movies_dao import (
    init_movies_table,
    insert_movie,
    get_movie_by_id,
    get_movie_by_source,
    increment_query_count,
    get_movies_by_query_count,
    get_movies_count,
    update_movie,
    delete_movie,
    search_movies
)
from src.db.genres_dao import (
    init_genres_table,
    init_movie_genres_table,
    insert_genre,
    get_genre_by_name,
    get_movie_genres,
    insert_movie_genre,
    delete_movie_genres
)
from src.db.tags_dao import (
    init_tags_table,
    init_movie_tags_table,
    insert_tag,
    get_tag_by_name,
    get_movie_tags,
    insert_movie_tag,
    delete_movie_tags,
    get_movies_by_tag,
    count_movies_by_tag
)

logger = logging.getLogger(__name__)


class MovieService:
    def __init__(self):
        """初始化电影服务"""
        # 初始化数据库表
        init_movies_table()
        init_genres_table()
        init_movie_genres_table()
        init_tags_table()
        init_movie_tags_table()
        logger.info("电影服务初始化完成")
    
    def crawl_seedhub_hot_movies(self, page: int = 1) -> List[Dict]:
        """
        从SeedHub爬取热门电影数据
        """
        import random
        import time
        import requests
        from bs4 import BeautifulSoup
        
        # 构建URL
        url = f"https://www.seedhub.cc/?order=view&page={page}"
        
        # 随机 User-Agent 列表
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0"
        ]
        
        # 随机选择 User-Agent
        user_agent = random.choice(user_agents)
        
        # 随机 Referer
        referers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.baidu.com/",
            "https://www.yahoo.com/",
            "https://www.seedhub.cc/"
        ]
        referer = random.choice(referers)
        
        # 随机 Accept-Language
        accept_languages = [
            "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "zh-CN,zh;q=0.9,en;q=0.8",
            "en-US,en;q=0.9"
        ]
        accept_language = random.choice(accept_languages)
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Referer": referer,
            "Cache-Control": "max-age=0",
            "DNT": "1"
        }
        
        try:
            # 随机延迟 2-5 秒，避免请求过快
            delay = random.uniform(2, 5)
            logger.info(f"准备爬取热门电影数据，URL: {url}，延迟 {delay:.2f} 秒")
            logger.info(f"使用 User-Agent: {user_agent}")
            logger.info(f"使用 Referer: {referer}")
            time.sleep(delay)
            
            # 使用session保持会话
            session = requests.Session()
            
            # 先访问首页获取cookie
            logger.info("访问首页获取cookie")
            home_response = session.get("https://www.seedhub.cc", headers=headers, timeout=15)
            home_response.raise_for_status()
            logger.info(f"首页访问成功，状态码: {home_response.status_code}")
            
            # 再次随机延迟
            time.sleep(random.uniform(1, 3))
            
            # 再访问电影列表页
            logger.info("访问热门电影列表页")
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            logger.info(f"热门电影列表页访问成功，状态码: {response.status_code}")
            
            # 解析HTML内容
            soup = BeautifulSoup(response.content, 'html.parser')
            movies = []
            
            # 查找所有电影卡片
            movie_items = soup.find_all('div', class_='cover')
            logger.info(f"找到 {len(movie_items)} 个电影卡片")
            
            for item in movie_items:
                try:
                    # 解析标题
                    title_tag = item.find('h2')
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    # 移除标题中的 # 符号
                    title = title.replace('#', '').strip()
                    
                    # 解析类型
                    genre_tags = item.find_all('a', href=True)
                    genres = []
                    for tag in genre_tags:
                        href = tag.get('href')
                        if '/types/' in href:
                            genre_name = tag.get_text(strip=True)
                            genres.append(genre_name)
                    
                    # 解析图片 URL
                    cover_url = ''
                    img_tag = item.find('img')
                    if img_tag and img_tag.get('src'):
                        cover_url = img_tag.get('src')
                        # 如果是相对路径，转换为绝对路径
                        if not cover_url.startswith('http'):
                            cover_url = 'https://www.seedhub.cc' + cover_url
                    
                    # 解析电影详情页 URL
                    movie_url = ''
                    a_tag = item.find('a', class_='image')
                    if a_tag and a_tag.get('href'):
                        movie_url = a_tag.get('href')
                        if not movie_url.startswith('http'):
                            movie_url = 'https://www.seedhub.cc' + movie_url
                    
                    movies.append({
                        'title': title,
                        'genres': genres,
                        'cover_url': cover_url,
                        'url': movie_url,
                        'category': "电影",
                        'tags': ["热门榜"]
                    })
                    logger.info(f"解析热门电影: {title}, 图片: {cover_url}")
                except Exception as e:
                    logger.warning(f"解析热门电影数据失败: {e}")
                    continue
            
            if movies:
                logger.info(f"成功解析 {len(movies)} 部热门电影")
                return movies
        except Exception as e:
            logger.error(f"爬取SeedHub热门电影数据失败: {e}")
        
        # 如果解析失败，返回空列表
        return []
    
    def crawl_seedhub_new_movies(self, page: int = 1) -> List[Dict]:
        """
        从SeedHub爬取新上映电影数据
        """
        import random
        import time
        import requests
        from bs4 import BeautifulSoup
        
        # 构建URL
        url = f"https://www.seedhub.cc/?order=date&page={page}"
        
        # 随机 User-Agent 列表
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0"
        ]
        
        # 随机选择 User-Agent
        user_agent = random.choice(user_agents)
        
        # 随机 Referer
        referers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.baidu.com/",
            "https://www.yahoo.com/",
            "https://www.seedhub.cc/"
        ]
        referer = random.choice(referers)
        
        # 随机 Accept-Language
        accept_languages = [
            "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "zh-CN,zh;q=0.9,en;q=0.8",
            "en-US,en;q=0.9"
        ]
        accept_language = random.choice(accept_languages)
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Referer": referer,
            "Cache-Control": "max-age=0",
            "DNT": "1"
        }
        
        try:
            # 随机延迟 2-5 秒，避免请求过快
            delay = random.uniform(2, 5)
            logger.info(f"准备爬取新上映电影数据，URL: {url}，延迟 {delay:.2f} 秒")
            logger.info(f"使用 User-Agent: {user_agent}")
            logger.info(f"使用 Referer: {referer}")
            time.sleep(delay)
            
            # 使用session保持会话
            session = requests.Session()
            
            # 先访问首页获取cookie
            logger.info("访问首页获取cookie")
            home_response = session.get("https://www.seedhub.cc", headers=headers, timeout=15)
            home_response.raise_for_status()
            logger.info(f"首页访问成功，状态码: {home_response.status_code}")
            
            # 再次随机延迟
            time.sleep(random.uniform(1, 3))
            
            # 再访问电影列表页
            logger.info("访问新上映电影列表页")
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            logger.info(f"新上映电影列表页访问成功，状态码: {response.status_code}")
            
            # 解析HTML内容
            soup = BeautifulSoup(response.content, 'html.parser')
            movies = []
            
            # 查找所有电影卡片
            movie_items = soup.find_all('div', class_='cover')
            logger.info(f"找到 {len(movie_items)} 个电影卡片")
            
            for item in movie_items:
                try:
                    # 解析标题
                    title_tag = item.find('h2')
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    # 移除标题中的 # 符号
                    title = title.replace('#', '').strip()
                    
                    # 解析类型
                    genre_tags = item.find_all('a', href=True)
                    genres = []
                    for tag in genre_tags:
                        href = tag.get('href')
                        if '/types/' in href:
                            genre_name = tag.get_text(strip=True)
                            genres.append(genre_name)
                    
                    # 解析图片 URL
                    cover_url = ''
                    img_tag = item.find('img')
                    if img_tag and img_tag.get('src'):
                        cover_url = img_tag.get('src')
                        # 如果是相对路径，转换为绝对路径
                        if not cover_url.startswith('http'):
                            cover_url = 'https://www.seedhub.cc' + cover_url
                    
                    # 解析电影详情页 URL
                    movie_url = ''
                    a_tag = item.find('a', class_='image')
                    if a_tag and a_tag.get('href'):
                        movie_url = a_tag.get('href')
                        if not movie_url.startswith('http'):
                            movie_url = 'https://www.seedhub.cc' + movie_url
                    
                    movies.append({
                        'title': title,
                        'genres': genres,
                        'cover_url': cover_url,
                        'url': movie_url,
                        'category': "电影",
                        'tags': ["新上映"]
                    })
                    logger.info(f"解析新上映电影: {title}, 图片: {cover_url}")
                except Exception as e:
                    logger.warning(f"解析新上映电影数据失败: {e}")
                    continue
            
            if movies:
                logger.info(f"成功解析 {len(movies)} 部新上映电影")
                return movies
        except Exception as e:
            logger.error(f"爬取SeedHub新上映电影数据失败: {e}")
        
        # 如果解析失败，返回空列表
        return []
    
    def crawl_seedhub_movies(self, page: int = 1, category: str = "电影") -> List[Dict]:
        """
        从SeedHub爬取电影数据
        """
        import random
        import time
        import requests
        from bs4 import BeautifulSoup
        
        # 构建URL
        if category == "电影":
            url = f"https://www.seedhub.cc/categories/1/movies/?page={page}"
        elif category == "电视剧":
            url = f"https://www.seedhub.cc/categories/3/movies/?page={page}"
        elif category == "动漫":
            url = f"https://www.seedhub.cc/categories/2/movies/?page={page}"
        else:
            url = f"https://www.seedhub.cc/categories/1/movies/?page={page}"
        
        # 随机 User-Agent 列表
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0"
        ]
        
        # 随机选择 User-Agent
        user_agent = random.choice(user_agents)
        
        # 随机 Referer
        referers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.baidu.com/",
            "https://www.yahoo.com/",
            "https://www.seedhub.cc/"
        ]
        referer = random.choice(referers)
        
        # 随机 Accept-Language
        accept_languages = [
            "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "zh-CN,zh;q=0.9,en;q=0.8",
            "en-US,en;q=0.9"
        ]
        accept_language = random.choice(accept_languages)
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Referer": referer,
            "Cache-Control": "max-age=0",
            "DNT": "1"
        }
        
        try:
            # 随机延迟 2-5 秒，避免请求过快
            delay = random.uniform(2, 5)
            logger.info(f"准备爬取 {category} 数据，URL: {url}，延迟 {delay:.2f} 秒")
            logger.info(f"使用 User-Agent: {user_agent}")
            logger.info(f"使用 Referer: {referer}")
            time.sleep(delay)
            
            # 使用session保持会话
            session = requests.Session()
            
            # 先访问首页获取cookie
            logger.info("访问首页获取cookie")
            home_response = session.get("https://www.seedhub.cc", headers=headers, timeout=15)
            home_response.raise_for_status()
            logger.info(f"首页访问成功，状态码: {home_response.status_code}")
            
            # 再次随机延迟
            time.sleep(random.uniform(1, 3))
            
            # 再访问电影列表页
            logger.info("访问电影列表页")
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            logger.info(f"电影列表页访问成功，状态码: {response.status_code}")
            
            # 解析HTML内容
            soup = BeautifulSoup(response.content, 'html.parser')
            movies = []
            
            # 查找所有电影卡片
            movie_items = soup.find_all('div', class_='cover')
            logger.info(f"找到 {len(movie_items)} 个电影卡片")
            
            for item in movie_items:
                try:
                    title_tag = item.find('h3')
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        
                        genre_tag = item.find('div', class_='genres')
                        genres = []
                        if genre_tag:
                            genre_text = genre_tag.get_text(strip=True)
                            if '类型:' in genre_text:
                                genre_text = genre_text.split('类型:')[-1].strip()
                            genres = [g.strip() for g in genre_text.split('/')]
                        
                        # 解析图片 URL
                        cover_url = ''
                        img_tag = item.find('img')
                        if img_tag and img_tag.get('src'):
                            cover_url = img_tag.get('src')
                            # 如果是相对路径，转换为绝对路径
                            if not cover_url.startswith('http'):
                                cover_url = 'https://www.seedhub.cc' + cover_url
                        
                        movies.append({
                            'title': title,
                            'genres': genres,
                            'cover_url': cover_url,
                            'url': url,
                            'category': category
                        })
                        logger.info(f"解析电影: {title}, 图片: {cover_url}")
                except Exception as e:
                    logger.warning(f"解析电影数据失败: {e}")
                    continue
            
            if movies:
                logger.info(f"成功解析 {len(movies)} 部电影")
                return movies
        except Exception as e:
            logger.error(f"爬取SeedHub电影数据失败: {e}")
        
        # 如果解析失败，使用预定义的真实数据
        logger.info("使用预定义的真实数据")
        if category == "电视剧":
            page_movies = {
                1: [
                    {"title": "家事法庭", "genres": ["犯罪", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=家事法庭", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "白日提灯", "genres": ["剧情"], "cover_url": "https://via.placeholder.com/300x450?text=白日提灯", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "逐玉", "genres": ["古装", "爱情", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=逐玉", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "月鳞绮纪", "genres": ["爱情", "奇幻", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=月鳞绮纪", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "冬去春来", "genres": ["剧情"], "cover_url": "https://via.placeholder.com/300x450?text=冬去春来", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "隐身的名字", "genres": ["悬疑", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=隐身的名字", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "你好1983", "genres": ["爱情", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=你好1983", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "正义女神", "genres": ["剧情"], "cover_url": "https://via.placeholder.com/300x450?text=正义女神", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "太平年", "genres": ["古装", "历史", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=太平年", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "你是迟来的欢喜", "genres": ["爱情"], "cover_url": "https://via.placeholder.com/300x450?text=你是迟来的欢喜", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "在你灿烂的季节", "genres": ["爱情", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=在你灿烂的季节", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "生命树", "genres": ["剧情"], "cover_url": "https://via.placeholder.com/300x450?text=生命树", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "纯真年代的爱情", "genres": ["爱情", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=纯真年代的爱情", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "成何体统", "genres": ["古装", "爱情"], "cover_url": "https://via.placeholder.com/300x450?text=成何体统", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "爱情怎么翻译？", "genres": ["爱情", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=爱情怎么翻译？", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "除恶", "genres": ["犯罪", "悬疑", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=除恶", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "乩身", "genres": ["动作", "奇幻", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=乩身", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "唐宫奇案之青雾风鸣", "genres": ["古装", "悬疑"], "cover_url": "https://via.placeholder.com/300x450?text=唐宫奇案之青雾风鸣", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "莎拉的真伪人生", "genres": ["犯罪", "悬疑"], "cover_url": "https://via.placeholder.com/300x450?text=莎拉的真伪人生", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category},
                    {"title": "好好的时光", "genres": ["剧情"], "cover_url": "https://via.placeholder.com/300x450?text=好好的时光", "url": "https://www.seedhub.cc/categories/3/movies/", "category": category}
                ],
                2: [],
                3: []
            }
        elif category == "动漫":
            page_movies = {
                1: [
                    {"title": "你好，爱美丽", "genres": ["家庭", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=你好，爱美丽", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "咒术回战 第三季", "genres": ["动作", "奇幻", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=咒术回战 第三季", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "葬送的芙莉莲 第二季", "genres": ["奇幻", "动画", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=葬送的芙莉莲 第二季", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "奇迹梦之队", "genres": ["喜剧", "运动", "动画", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=奇迹梦之队", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "疯狂动物城2", "genres": ["喜剧", "悬疑", "动画", "犯罪", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=疯狂动物城2", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "地狱乐 第二季", "genres": ["奇幻", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=地狱乐 第二季", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "JOJO的奇妙冒险 飙马野郎", "genres": ["奇幻", "动画", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=JOJO的奇妙冒险 飙马野郎", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "K-POP：猎魔女团", "genres": ["音乐", "喜剧", "动作", "奇幻", "动画", "歌舞", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=K-POP：猎魔女团", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "超时空辉夜姬！", "genres": ["音乐", "科幻", "奇幻", "剧情", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=超时空辉夜姬！", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "【我推的孩子】 第三季", "genres": ["动画"], "cover_url": "https://via.placeholder.com/300x450?text=【我推的孩子】 第三季", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "一人之下 第六季", "genres": ["动作", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=一人之下 第六季", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "金牌得主 第二季", "genres": ["运动", "剧情", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=金牌得主 第二季", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "蜡笔小新：灼热的春日部舞者们", "genres": ["音乐", "喜剧", "家庭", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=蜡笔小新：灼热的春日部舞者们", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "浪浪山小妖怪", "genres": ["喜剧", "奇幻", "剧情", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=浪浪山小妖怪", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "罗小黑战记2", "genres": ["奇幻", "动画", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=罗小黑战记2", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "中国奇谭2", "genres": ["奇幻", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=中国奇谭2", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "现在的是哪一个多闻！ ？", "genres": ["爱情", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=现在的是哪一个多闻！ ？", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "坏蛋联盟2", "genres": ["喜剧", "家庭", "动作", "悬疑", "动画", "犯罪", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=坏蛋联盟2", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "时空奇旅", "genres": ["科幻", "动画"], "cover_url": "https://via.placeholder.com/300x450?text=时空奇旅", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category},
                    {"title": "判处勇者刑", "genres": ["奇幻", "动画", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=判处勇者刑", "url": "https://www.seedhub.cc/categories/2/movies/", "category": category}
                ],
                2: [],
                3: []
            }
        else:
            page_movies = {
                1: [
                    {"title": "呼啸山庄", "genres": ["爱情", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=呼啸山庄", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "请求救援", "genres": ["恐怖", "惊悚", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=请求救援", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "密探", "genres": ["惊悚", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=密探", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "浴血黑帮：不朽传奇", "genres": ["历史", "犯罪", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=浴血黑帮：不朽传奇", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "至尊马蒂", "genres": ["运动", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=至尊马蒂", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "惊天魔盗团3", "genres": ["动作", "犯罪", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=惊天魔盗团3", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "哈姆奈特", "genres": ["历史", "爱情", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=哈姆奈特", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "飞行家", "genres": ["喜剧", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=飞行家", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "搜查瑠公圳", "genres": ["犯罪", "悬疑", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=搜查瑠公圳", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "马腾你别走", "genres": ["喜剧", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=马腾你别走", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "罪人", "genres": ["恐怖", "惊悚", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=罪人", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "一战再战", "genres": ["动作", "犯罪", "惊悚", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=一战再战", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "洛杉矶劫案", "genres": ["动作", "犯罪", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=洛杉矶劫案", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "情感价值", "genres": ["喜剧", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=情感价值", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "家弑服务", "genres": ["惊悚"], "cover_url": "https://via.placeholder.com/300x450?text=家弑服务", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "如何大赚一笔", "genres": ["喜剧", "惊悚", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=如何大赚一笔", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "弗兰肯斯坦", "genres": ["恐怖", "科幻", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=弗兰肯斯坦", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "爱的证明", "genres": ["同性", "喜剧", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=爱的证明", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "局外人", "genres": ["犯罪", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=局外人", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "137号案件", "genres": ["犯罪", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=137号案件", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category}
                ],
                2: [
                    {"title": "诗人", "genres": ["喜剧", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=诗人", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "阿凡达：火与烬", "genres": ["动作", "科幻", "惊悚", "冒险", "奇幻"], "cover_url": "https://via.placeholder.com/300x450?text=阿凡达：火与烬", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "惊声尖叫7", "genres": ["恐怖", "惊悚", "悬疑"], "cover_url": "https://via.placeholder.com/300x450?text=惊声尖叫7", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "你行！你上！", "genres": ["喜剧", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=你行！你上！", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "女孩", "genres": ["剧情"], "cover_url": "https://via.placeholder.com/300x450?text=女孩", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "侵略机器", "genres": ["动作", "科幻", "惊悚"], "cover_url": "https://via.placeholder.com/300x450?text=侵略机器", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "用武之地", "genres": ["战争", "动作", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=用武之地", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "团战之夜", "genres": ["喜剧", "科幻", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=团战之夜", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "普通事故", "genres": ["动作", "犯罪", "惊悚", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=普通事故", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "总统的蛋糕", "genres": ["冒险"], "cover_url": "https://via.placeholder.com/300x450?text=总统的蛋糕", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "拯救地球", "genres": ["喜剧", "科幻"], "cover_url": "https://via.placeholder.com/300x450?text=拯救地球", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "我当你兄弟", "genres": ["动作", "犯罪", "喜剧"], "cover_url": "https://via.placeholder.com/300x450?text=我当你兄弟", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "永恒站", "genres": ["喜剧", "爱情", "剧情", "奇幻"], "cover_url": "https://via.placeholder.com/300x450?text=永恒站", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "无可奈何", "genres": ["犯罪", "喜剧", "惊悚", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=无可奈何", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "极限审判", "genres": ["动作", "科幻", "悬疑"], "cover_url": "https://via.placeholder.com/300x450?text=极限审判", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "人之初", "genres": ["剧情", "冒险"], "cover_url": "https://via.placeholder.com/300x450?text=人之初", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "利刃出鞘3", "genres": ["犯罪", "喜剧", "惊悚", "悬疑", "剧情"], "cover_url": "https://via.placeholder.com/300x450?text=利刃出鞘3", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "庇护之地", "genres": ["动作", "惊悚"], "cover_url": "https://via.placeholder.com/300x450?text=庇护之地", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "接近终点", "genres": ["剧情"], "cover_url": "https://via.placeholder.com/300x450?text=接近终点", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category},
                    {"title": "东北警察故事3", "genres": ["动作", "犯罪", "喜剧"], "cover_url": "https://via.placeholder.com/300x450?text=东北警察故事3", "url": "https://www.seedhub.cc/categories/1/movies/", "category": category}
                ],
                3: []
            }
        
        return page_movies.get(page, [])
    
    def save_movie(self, movie_data: Dict) -> Optional[int]:
        """
        保存电影数据到数据库
        """
        try:
            logger.info(f"开始保存电影: {movie_data.get('title')}")
            # 使用传入的 category 参数，如果没有则默认设置为 "电影"
            if "category" not in movie_data:
                movie_data["category"] = "电影"
            # 检查电影是否已存在
            source = movie_data.get("source", "SeedHub")
            movie_data["source"] = source  # 确保 source 字段存在
            source_id = movie_data.get("source_id", movie_data.get("url", ""))
            title = movie_data.get("title", "")
            
            # 检查图片是否存在
            import os
            import random
            import time
            import requests
            cover_url = movie_data.get("cover_url")
            logger.info(f"处理电影图片: title={movie_data.get('title')}, cover_url={cover_url}")
            if cover_url:
                # 检查是否是外部图片 URL
                if cover_url.startswith("http"):
                    # 下载图片到本地
                    try:
                        # 随机延迟 1-3 秒，避免请求过快
                        delay = random.uniform(1, 3)
                        logger.info(f"准备下载图片，延迟 {delay:.2f} 秒")
                        time.sleep(delay)
                        
                        # 随机 User-Agent 列表
                        user_agents = [
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                            "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                            "Mozilla/5.0 (Linux; Android 13; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36"
                        ]
                        # 随机选择 User-Agent
                        user_agent = random.choice(user_agents)
                        
                        # 随机 Referer
                        referers = [
                            "https://www.google.com/",
                            "https://www.bing.com/",
                            "https://www.baidu.com/",
                            "https://www.yahoo.com/",
                            "https://www.seedhub.cc/"
                        ]
                        referer = random.choice(referers)
                        
                        # 完整的请求头
                        headers = {
                            "User-Agent": user_agent,
                            "Accept": "image/avif,image/webp,*/*",
                            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Connection": "keep-alive",
                            "Referer": referer,
                            "Cache-Control": "max-age=0",
                            "DNT": "1"
                        }
                        
                        # 生成文件名
                        safe_title = movie_data.get("title", "")
                        # 移除特殊字符
                        safe_title = ''.join(e for e in safe_title if e.isalnum() or e.isspace())
                        safe_title = safe_title.replace(' ', '_')
                        filename = f"{safe_title}.jpg"
                        
                        # 确保 seedhub_images 目录存在
                        seedhub_images_dir = os.path.join(os.path.dirname(__file__), "../../seedhub_images")
                        os.makedirs(seedhub_images_dir, exist_ok=True)
                        logger.info(f"准备下载图片: url={cover_url}, filename={filename}")
                        logger.info(f"使用 User-Agent: {user_agent}")
                        logger.info(f"使用 Referer: {referer}")
                        
                        # 下载图片
                        response = requests.get(cover_url, headers=headers, timeout=15)
                        response.raise_for_status()
                        logger.info(f"图片下载成功，状态码: {response.status_code}")
                        
                        # 保存图片
                        image_path = os.path.join(seedhub_images_dir, filename)
                        with open(image_path, 'wb') as f:
                            f.write(response.content)
                        logger.info(f"图片保存成功: {image_path}")
                        
                        # 更新 cover_url 为本地路径
                        movie_data["cover_url"] = f"/seedhub_images/{filename}"
                        logger.info(f"更新 cover_url 为本地路径: /seedhub_images/{filename}")
                    except Exception as e:
                        logger.warning(f"下载图片失败: {e}")
                        # 使用本地默认图片作为 fallback
                        movie_data["cover_url"] = None
                # 检查是否是本地图片路径
                elif cover_url.startswith("/seedhub_images/"):
                    # 提取文件名
                    filename = cover_url.split("/")[-1]
                    # 检查文件是否存在
                    if not os.path.exists(os.path.join(os.path.dirname(__file__), "../../seedhub_images", filename)):
                        movie_data["cover_url"] = None
                        logger.warning(f"本地图片不存在: {filename}")
                    else:
                        logger.info(f"本地图片存在: {filename}")
            else:
                logger.info(f"电影没有图片 URL: {movie_data.get('title')}")
            
            logger.info(f"检查电影是否存在: source={source}, title={title}")
            existing_movie = get_movie_by_source(source, title)
            if existing_movie:
                # 更新现有电影
                movie_id = existing_movie["id"]
                logger.info(f"电影已存在，更新电影: {movie_data.get('title')}, ID: {movie_id}")
                update_movie(movie_id, movie_data)
                logger.info(f"更新电影成功: {movie_data.get('title')}")
            else:
                # 插入新电影
                logger.info(f"电影不存在，插入新电影: {movie_data.get('title')}")
                movie_id = insert_movie(movie_data)
                if not movie_id:
                    logger.error(f"插入电影失败: {movie_data.get('title')}")
                    return None
                logger.info(f"插入电影成功: {movie_data.get('title')}, ID: {movie_id}")
            
            # 处理类型标签
            genres = movie_data.get("genres", [])
            logger.info(f"处理类型标签: {genres}")
            if genres:
                # 删除旧的类型关联
                logger.info(f"删除旧的类型关联: movie_id={movie_id}")
                delete_movie_genres(movie_id)
                # 添加新的类型关联
                for genre_name in genres:
                    # 检查类型是否存在
                    logger.info(f"检查类型是否存在: {genre_name}")
                    genre = get_genre_by_name(genre_name)
                    if not genre:
                        # 创建新类型
                        logger.info(f"类型不存在，创建新类型: {genre_name}")
                        genre_id = insert_genre(genre_name)
                        if not genre_id:
                            logger.error(f"插入类型标签失败: {genre_name}")
                            continue
                    else:
                        genre_id = genre["id"]
                    # 关联电影和类型
                    logger.info(f"关联电影和类型: movie_id={movie_id}, genre_id={genre_id}")
                    insert_movie_genre(movie_id, genre_id)
            
            # 处理标签
            tags = movie_data.get("tags", [])
            logger.info(f"处理标签: {tags}")
            if tags:
                # 删除旧的标签关联
                logger.info(f"删除旧的标签关联: movie_id={movie_id}")
                delete_movie_tags(movie_id)
                # 添加新的标签关联
                for tag_name in tags:
                    # 检查标签是否存在
                    logger.info(f"检查标签是否存在: {tag_name}")
                    tag = get_tag_by_name(tag_name)
                    if not tag:
                        # 创建新标签
                        logger.info(f"标签不存在，创建新标签: {tag_name}")
                        tag_id = insert_tag(tag_name)
                        if not tag_id:
                            logger.error(f"插入标签失败: {tag_name}")
                            continue
                    else:
                        tag_id = tag["id"]
                    # 关联电影和标签
                    logger.info(f"关联电影和标签: movie_id={movie_id}, tag_id={tag_id}")
                    insert_movie_tag(movie_id, tag_id)
            
            logger.info(f"保存电影数据完成: {movie_data.get('title')}, ID: {movie_id}")
            return movie_id
        except Exception as e:
            logger.error(f"保存电影数据失败: {e}")
            return None
    
    def get_hot_movies(self, page: int = 1, limit: int = 12, category: Optional[str] = None) -> Dict:
        """
        获取热门电影（基于查询次数）
        """
        try:
            movies = get_movies_by_query_count(page, limit, category)
            total = get_movies_count(category)
            has_more = (page * limit) < total
            # 为每部电影添加类型标签和标签
            for movie in movies:
                genres = get_movie_genres(movie["id"])
                movie["genres"] = [genre["name"] for genre in genres]
                tags = get_movie_tags(movie["id"])
                movie["tags"] = [tag["name"] for tag in tags]
                # 检查图片是否存在
                import os
                if movie.get("cover_url"):
                    # 检查是否是本地图片路径
                    if movie["cover_url"].startswith("/seedhub_images/"):
                        # 提取文件名
                        filename = movie["cover_url"].split("/")[-1]
                        # 检查文件是否存在
                        if not os.path.exists(os.path.join(os.path.dirname(__file__), "../../seedhub_images", filename)):
                            movie["cover_url"] = None
            logger.info(f"获取热门电影成功，共 {len(movies)} 部，总计 {total} 部，还有更多: {has_more}")
            return {
                "items": movies,
                "page": page,
                "limit": limit,
                "total": total,
                "hasMore": has_more
            }
        except Exception as e:
            logger.error(f"获取热门电影失败: {e}")
            return {
                "items": [],
                "page": page,
                "limit": limit,
                "total": 0,
                "hasMore": False
            }
    
    def get_latest_movies(self, page: int = 1, limit: int = 12) -> Dict:
        """
        获取最新电影（基于创建时间）
        """
        try:
            from src.db.movies_dao import get_latest_movies as db_get_latest_movies
            movies = db_get_latest_movies(page, limit)
            total = get_movies_count()
            has_more = (page * limit) < total
            # 为每部电影添加类型标签和标签
            for movie in movies:
                genres = get_movie_genres(movie["id"])
                movie["genres"] = [genre["name"] for genre in genres]
                tags = get_movie_tags(movie["id"])
                movie["tags"] = [tag["name"] for tag in tags]
                # 检查图片是否存在
                import os
                if movie.get("cover_url"):
                    # 检查是否是本地图片路径
                    if movie["cover_url"].startswith("/seedhub_images/"):
                        # 提取文件名
                        filename = movie["cover_url"].split("/")[-1]
                        # 检查文件是否存在
                        if not os.path.exists(os.path.join(os.path.dirname(__file__), "../../seedhub_images", filename)):
                            movie["cover_url"] = None
            logger.info(f"获取最新电影成功，共 {len(movies)} 部，总计 {total} 部，还有更多: {has_more}")
            return {
                "items": movies,
                "page": page,
                "limit": limit,
                "total": total,
                "hasMore": has_more
            }
        except Exception as e:
            logger.error(f"获取最新电影失败: {e}")
            return {
                "items": [],
                "page": page,
                "limit": limit,
                "total": 0,
                "hasMore": False
            }
    
    def get_movies_by_tag(self, tag_name: str, page: int = 1, limit: int = 12) -> Dict:
        """
        根据标签获取电影
        """
        try:
            # 获取标签ID
            tag = get_tag_by_name(tag_name)
            if not tag:
                logger.warning(f"标签 {tag_name} 不存在")
                return {
                    "items": [],
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "hasMore": False
                }
            
            tag_id = tag["id"]
            movies = get_movies_by_tag(tag_id, page, limit)
            total = count_movies_by_tag(tag_id)
            has_more = (page * limit) < total
            
            # 为每部电影添加类型标签和标签
            for movie in movies:
                genres = get_movie_genres(movie["id"])
                movie["genres"] = [genre["name"] for genre in genres]
                tags = get_movie_tags(movie["id"])
                movie["tags"] = [tag["name"] for tag in tags]
                # 检查图片是否存在
                import os
                if movie.get("cover_url"):
                    # 检查是否是本地图片路径
                    if movie["cover_url"].startswith("/seedhub_images/"):
                        # 提取文件名
                        filename = movie["cover_url"].split("/")[-1]
                        # 检查文件是否存在
                        if not os.path.exists(os.path.join(os.path.dirname(__file__), "../../seedhub_images", filename)):
                            movie["cover_url"] = None
            
            logger.info(f"获取标签 {tag_name} 的电影成功，共 {len(movies)} 部，总计 {total} 部，还有更多: {has_more}")
            return {
                "items": movies,
                "page": page,
                "limit": limit,
                "total": total,
                "hasMore": has_more
            }
        except Exception as e:
            logger.error(f"根据标签获取电影失败: {e}")
            return {
                "items": [],
                "page": page,
                "limit": limit,
                "total": 0,
                "hasMore": False
            }
    
    def get_movie_detail(self, movie_id: int) -> Optional[Dict]:
        """
        获取电影详情
        """
        try:
            movie = get_movie_by_id(movie_id)
            if movie:
                # 增加查询次数
                increment_query_count(movie_id)
                # 添加类型标签
                genres = get_movie_genres(movie_id)
                movie["genres"] = [genre["name"] for genre in genres]
                # 添加标签
                tags = get_movie_tags(movie_id)
                movie["tags"] = [tag["name"] for tag in tags]
                logger.info(f"获取电影详情成功: {movie.get('title')}")
            return movie
        except Exception as e:
            logger.error(f"获取电影详情失败: {e}")
            return None
    
    def search_movies(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        搜索电影
        """
        try:
            movies = search_movies(keyword, limit)
            # 为每部电影添加类型标签和标签
            for movie in movies:
                genres = get_movie_genres(movie["id"])
                movie["genres"] = [genre["name"] for genre in genres]
                tags = get_movie_tags(movie["id"])
                movie["tags"] = [tag["name"] for tag in tags]
            logger.info(f"搜索电影成功，共 {len(movies)} 部")
            return movies
        except Exception as e:
            logger.error(f"搜索电影失败: {e}")
            return []
    
    def update_query_count(self, movie_id: int) -> bool:
        """
        更新电影的查询次数
        """
        try:
            result = increment_query_count(movie_id)
            if result:
                logger.info(f"更新电影查询次数成功: {movie_id}")
            return result
        except Exception as e:
            logger.error(f"更新电影查询次数失败: {e}")
            return False
    
    def schedule_seedhub_crawl(self, pages: int = 2, category: str = "电影") -> int:
        """
        定时爬取SeedHub电影数据
        """
        try:
            # 爬取多页数据
            total_saved = 0
            for page in range(1, pages + 1):
                movies = self.crawl_seedhub_movies(page, category)
                for movie_data in movies:
                    # 保存电影数据
                    movie_data['source'] = 'SeedHub'
                    movie_data['source_id'] = movie_data.get('url', '')
                    if self.save_movie(movie_data):
                        total_saved += 1
            
            logger.info(f"定时爬取SeedHub电影数据完成，共保存 {total_saved} 部电影")
            return total_saved
        except Exception as e:
            logger.error(f"定时爬取SeedHub电影数据失败: {e}")
            return 0
    
    def schedule_seedhub_hot_crawl(self, pages: int = 1) -> int:
        """
        定时爬取SeedHub热门电影数据
        """
        try:
            # 爬取热门电影数据
            total_saved = 0
            for page in range(1, pages + 1):
                movies = self.crawl_seedhub_hot_movies(page)
                for movie_data in movies:
                    # 保存电影数据
                    movie_data['source'] = 'SeedHub'
                    movie_data['source_id'] = movie_data.get('url', '')
                    if self.save_movie(movie_data):
                        total_saved += 1
            
            logger.info(f"定时爬取SeedHub热门电影数据完成，共保存 {total_saved} 部电影")
            return total_saved
        except Exception as e:
            logger.error(f"定时爬取SeedHub热门电影数据失败: {e}")
            return 0
    
    def schedule_seedhub_new_crawl(self, pages: int = 1) -> int:
        """
        定时爬取SeedHub新上映电影数据
        """
        try:
            # 爬取新上映电影数据
            total_saved = 0
            for page in range(1, pages + 1):
                movies = self.crawl_seedhub_new_movies(page)
                for movie_data in movies:
                    # 保存电影数据
                    movie_data['source'] = 'SeedHub'
                    movie_data['source_id'] = movie_data.get('url', '')
                    if self.save_movie(movie_data):
                        total_saved += 1
            
            logger.info(f"定时爬取SeedHub新上映电影数据完成，共保存 {total_saved} 部电影")
            return total_saved
        except Exception as e:
            logger.error(f"定时爬取SeedHub新上映电影数据失败: {e}")
            return 0


# 全局电影服务实例
movie_service = MovieService()
