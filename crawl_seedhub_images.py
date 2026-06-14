#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬取 seedhub.cc 页面的图片
"""

import logging
import requests
from bs4 import BeautifulSoup
import os
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 图片保存目录
IMAGE_DIR = 'seedhub_images'

# 确保保存目录存在
os.makedirs(IMAGE_DIR, exist_ok=True)

def crawl_seedhub_images():
    """爬取 seedhub.cc 页面的图片"""
    logging.info("开始爬取 seedhub.cc 页面的图片")
    
    # 目标URL
    url = "https://www.seedhub.cc/?page=2"
    
    try:
        # 设置请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://www.seedhub.cc/"
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找图片元素
        # 首先尝试查找常见的图片标签
        images = soup.find_all('img')
        logging.info(f"找到 {len(images)} 个 img 标签")
        
        # 也查找可能包含背景图片的元素
        style_elements = soup.find_all(style=re.compile(r'background.*url'))
        logging.info(f"找到 {len(style_elements)} 个包含背景图片的元素")
        
        # 提取并下载图片
        image_urls = []
        
        # 处理 img 标签
        for img in images:
            img_url = img.get('src')
            if img_url:
                # 处理相对路径
                if not img_url.startswith('http'):
                    img_url = f"https://www.seedhub.cc{img_url}" if img_url.startswith('/') else f"https://www.seedhub.cc/{img_url}"
                image_urls.append(img_url)
        
        # 处理背景图片
        for element in style_elements:
            style = element.get('style')
            if style:
                # 提取背景图片URL
                match = re.search(r'background.*url\(([^)]+)\)', style)
                if match:
                    img_url = match.group(1).strip('"\'')
                    if not img_url.startswith('http'):
                        img_url = f"https://www.seedhub.cc{img_url}" if img_url.startswith('/') else f"https://www.seedhub.cc/{img_url}"
                    image_urls.append(img_url)
        
        # 去重
        image_urls = list(set(image_urls))
        logging.info(f"去重后找到 {len(image_urls)} 个图片URL")
        
        # 下载图片
        for i, img_url in enumerate(image_urls):
            logging.info(f"下载 {i+1}. {img_url}")
            download_image(img_url, f"seedhub_{i+1}")
        
        logging.info("爬取完成")
        
    except Exception as e:
        logging.error(f"爬取失败: {e}")

def download_image(url, filename):
    """下载单个图片"""
    try:
        # 发送请求
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # 获取文件扩展名
        ext = url.split('.')[-1].split('?')[0].split('#')[0]
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            ext = 'jpg'  # 默认扩展名
        
        # 保存图片
        filepath = os.path.join(IMAGE_DIR, f"{filename}.{ext}")
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        logging.info(f"✓ 成功下载图片: {filepath}")
        
    except Exception as e:
        logging.error(f"✗ 下载图片失败: {e}")

def main():
    """主函数"""
    print("============================================================")
    print("爬取 seedhub.cc 页面的图片")
    print("============================================================")
    
    crawl_seedhub_images()
    
    print("============================================================")
    print("爬取完成")
    print("============================================================")

if __name__ == "__main__":
    main()