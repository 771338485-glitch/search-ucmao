#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试电影API返回的数据格式
"""

import logging
import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_movie_api():
    """测试电影API返回的数据格式"""
    logging.info("开始测试电影API")
    
    # API URL
    api_url = "http://localhost:5005/api/movies/hot?page=1&limit=12&category=%E7%94%B5%E5%BD%B1"
    
    try:
        # 发送请求
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        
        # 解析响应
        data = response.json()
        
        logging.info(f"API返回状态码: {data.get('code')}")
        logging.info(f"API返回消息: {data.get('message')}")
        
        if data.get('code') == 0 and data.get('data'):
            movies = data['data'].get('items', [])
            logging.info(f"成功获取 {len(movies)} 部电影")
            
            # 显示电影信息
            for i, movie in enumerate(movies):
                logging.info(f"{i+1}. {movie.get('title')}")
                logging.info(f"   分类: {movie.get('category')}")
                logging.info(f"   封面URL: {movie.get('cover_url')}")
                logging.info(f"   类型: {movie.get('genres')}")
                logging.info(f"   查询次数: {movie.get('query_count')}")
                print()
        else:
            logging.error("API返回数据格式不正确")
            
    except Exception as e:
        logging.error(f"测试电影API失败: {e}")

def main():
    """主函数"""
    print("============================================================")
    print("测试电影API返回的数据格式")
    print("============================================================")
    
    test_movie_api()
    
    print("============================================================")
    print("测试完成")
    print("============================================================")

if __name__ == "__main__":
    main()