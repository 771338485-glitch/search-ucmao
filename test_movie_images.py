#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
影视图片获取测试脚本
此脚本演示如何从数据库和外部API获取影视图片
"""

import requests
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def test_movie_api():
    """测试电影API获取影视数据"""
    logging.info("开始测试电影API")
    
    # 测试不同分类
    categories = ["电影", "电视剧", "动漫"]
    
    for category in categories:
        logging.info(f"测试获取{category}数据")
        try:
            url = f"http://localhost:5000/api/movies/hot?page=1&limit=5&category={category}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Referer': 'http://localhost:5000/'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and data.get('data') and data.get('data').get('items'):
                    movies = data['data']['items']
                    logging.info(f"成功获取{len(movies)}个{category}数据")
                    
                    # 显示每个电影的信息和图片URL
                    for i, movie in enumerate(movies):
                        title = movie.get('title', '未知标题')
                        cover_url = movie.get('cover_url', '无图片')
                        rating = movie.get('rating', '无评分')
                        
                        logging.info(f"{i+1}. {title} - 评分: {rating}")
                        logging.info(f"   图片URL: {cover_url}")
                else:
                    logging.warning(f"{category}数据格式不正确: {data}")
            else:
                logging.error(f"{category}API请求失败，状态码: {response.status_code}")
                logging.error(f"响应内容: {response.text}")
                
        except Exception as e:
            logging.error(f"测试{category}API时出错: {e}")
        
        print()


def test_image_access():
    """测试图片访问"""
    logging.info("开始测试图片访问")
    
    # 测试几个已知的图片URL
    test_images = [
        "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p2811249023.jpg",  # 流浪地球3
        "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2871769053.jpg",  # 独行月球
        "https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2844411776.jpg"   # 满江红
    ]
    
    for i, image_url in enumerate(test_images):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Referer': 'https://movie.douban.com/'
            }
            response = requests.head(image_url, headers=headers, timeout=5)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '未知')
                logging.info(f"图片 {i+1} 可访问: {image_url}")
                logging.info(f"   内容类型: {content_type}")
            else:
                logging.warning(f"图片 {i+1} 访问失败，状态码: {response.status_code}")
        except Exception as e:
            logging.error(f"测试图片 {i+1} 时出错: {e}")
        
        print()


def main():
    """主函数"""
    print("=" * 60)
    print("影视图片获取测试")
    print("=" * 60)
    
    # 测试电影API
    test_movie_api()
    
    # 测试图片访问
    test_image_access()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()