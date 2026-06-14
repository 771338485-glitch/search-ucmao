#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 get_hot_movies 方法
"""

import logging
from src.services.movie_service import movie_service

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_get_hot_movies():
    """测试 get_hot_movies 方法"""
    logging.info("开始测试 get_hot_movies 方法")
    
    try:
        # 调用方法获取热门电影
        result = movie_service.get_hot_movies(page=1, limit=5, category="电影")
        
        logging.info(f"成功获取热门电影，共 {len(result.get('items', []))} 部，总计 {result.get('total', 0)} 部")
        
        # 显示电影信息
        for i, movie in enumerate(result.get('items', [])):
            logging.info(f"{i+1}. {movie.get('title')} (ID: {movie.get('id')})")
            logging.info(f"   分类: {movie.get('category')}")
            logging.info(f"   评分: {movie.get('rating')}")
            logging.info(f"   上映日期: {movie.get('release_date')}")
            logging.info(f"   图片URL: {movie.get('cover_url')}")
            logging.info(f"   查询次数: {movie.get('query_count')}")
            logging.info(f"   类型: {movie.get('genres', [])}")
            print()
        
        return result
        
    except Exception as e:
        logging.error(f"测试 get_hot_movies 方法失败: {e}")
        return {}

def main():
    """主函数"""
    print("============================================================")
    print("测试 get_hot_movies 方法")
    print("============================================================")
    
    result = test_get_hot_movies()
    
    if result.get('items'):
        logging.info("测试完成，成功获取热门电影数据")
    else:
        logging.error("测试失败，无法获取热门电影数据")
    
    print("============================================================")
    print("测试完成")
    print("============================================================")

if __name__ == "__main__":
    main()