#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试影视图片获取
"""

import logging
import requests
from bs4 import BeautifulSoup
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 测试不同的图片来源
def test_image_sources():
    """测试不同的图片来源"""
    logging.info("开始测试影视图片获取")
    
    # 测试占位图片
    placeholder_url = "https://via.placeholder.com/300x450?text=测试"
    test_image_url(placeholder_url, "占位图片")
    
    # 测试从API获取的图片
    api_url = "http://localhost:5005/api/movies/hot?page=1&limit=5&category=%E7%94%B5%E5%BD%B1"
    test_api_images(api_url)

def test_image_url(url, source_name):
    """测试单个图片URL"""
    try:
        logging.info(f"测试 {source_name} 图片: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # 检查响应头
        content_type = response.headers.get('Content-Type', '')
        if 'image' in content_type:
            logging.info(f"✓ {source_name} 图片获取成功，类型: {content_type}")
        else:
            logging.warning(f"⚠ {source_name} 图片获取成功，但不是图片类型: {content_type}")
            
    except Exception as e:
        logging.error(f"✗ {source_name} 图片获取失败: {e}")

def test_api_images(api_url):
    """测试从API获取的图片"""
    try:
        logging.info(f"测试从API获取图片: {api_url}")
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') == 0 and data.get('data', {}).get('items'):
            movies = data['data']['items']
            logging.info(f"成功获取 {len(movies)} 部影视数据")
            
            for i, movie in enumerate(movies):
                title = movie.get('title', '未知标题')
                cover_url = movie.get('cover_url', '')
                logging.info(f"测试 {i+1}. {title} 的图片: {cover_url}")
                test_image_url(cover_url, title)
        else:
            logging.error("API返回数据格式不正确")
            
    except Exception as e:
        logging.error(f"测试API图片失败: {e}")

def main():
    """主函数"""
    print("============================================================")
    print("测试影视图片获取")
    print("============================================================")
    
    test_image_sources()
    
    print("============================================================")
    print("测试完成")
    print("============================================================")

if __name__ == "__main__":
    main()