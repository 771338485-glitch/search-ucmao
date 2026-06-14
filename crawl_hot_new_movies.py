#!/usr/bin/env python3
"""
爬取热门和新上映电影数据
"""
import logging
from src.services.movie_service import movie_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def crawl_hot_movies():
    """
    爬取热门电影
    """
    logger.info("开始爬取热门电影数据...")
    try:
        # 爬取热门电影（1页）
        movies = movie_service.crawl_seedhub_hot_movies(page=1)
        logger.info(f"爬取到 {len(movies)} 部热门电影")
        
        # 保存到数据库
        saved_count = 0
        for movie in movies:
            movie_id = movie_service.save_movie(movie)
            if movie_id:
                saved_count += 1
        
        logger.info(f"成功保存 {saved_count} 部热门电影")
        return saved_count
    except Exception as e:
        logger.error(f"爬取热门电影失败: {e}")
        return 0

def crawl_new_movies():
    """
    爬取新上映电影
    """
    logger.info("开始爬取新上映电影数据...")
    try:
        # 爬取新上映电影（1页）
        movies = movie_service.crawl_seedhub_new_movies(page=1)
        logger.info(f"爬取到 {len(movies)} 部新上映电影")
        
        # 保存到数据库
        saved_count = 0
        for movie in movies:
            movie_id = movie_service.save_movie(movie)
            if movie_id:
                saved_count += 1
        
        logger.info(f"成功保存 {saved_count} 部新上映电影")
        return saved_count
    except Exception as e:
        logger.error(f"爬取新上映电影失败: {e}")
        return 0

if __name__ == "__main__":
    logger.info("开始执行爬取任务...")
    
    # 爬取热门电影
    hot_count = crawl_hot_movies()
    
    # 爬取新上映电影
    new_count = crawl_new_movies()
    
    logger.info(f"爬取任务完成！热门电影: {hot_count} 部，新上映电影: {new_count} 部")
