#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬取 seedhub.cc 网站的电影、电视剧、动漫图片，并更新数据库
"""

import logging
import requests
from bs4 import BeautifulSoup
import os
import sqlite3

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 图片保存目录
IMAGE_DIR = 'seedhub_images'

# 确保保存目录存在
os.makedirs(IMAGE_DIR, exist_ok=True)

def crawl_seedhub_and_update_db():
    """爬取 seedhub.cc 网站的电影、电视剧、动漫图片，并更新数据库"""
    logging.info("开始爬取 seedhub.cc 网站的影视图片")
    
    # 爬取热门榜和新上映数据
    categories = {
        "热门榜": ["https://www.seedhub.cc/?order=view&page=1"],
        "新上映": ["https://www.seedhub.cc/?order=date&page=1"]
    }
    
    all_movies = []
    
    for category, urls in categories.items():
        for url in urls:
            logging.info(f"爬取 {category} 分类，URL: {url}")
            movies = crawl_category(url, category)
            all_movies.extend(movies)
    
    # 更新数据库
    update_movie_db(all_movies)
    
    logging.info("爬取和更新完成")

def crawl_category(url, category):
    """爬取单个分类的影视图片"""
    movies = []
    
    try:
        import random
        import time
        
        # 随机延迟 2-5 秒，避免请求过快
        delay = random.uniform(2, 5)
        logging.info(f"准备爬取 {category} 分类，URL: {url}，延迟 {delay:.2f} 秒")
        time.sleep(delay)
        
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
        
        # 设置请求头
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
        
        logging.info(f"使用 User-Agent: {user_agent}")
        logging.info(f"使用 Referer: {referer}")
        
        # 使用session保持会话
        import requests
        session = requests.Session()
        
        # 先访问首页获取cookie
        logging.info("访问首页获取cookie")
        home_response = session.get("https://www.seedhub.cc", headers=headers, timeout=15)
        home_response.raise_for_status()
        logging.info(f"首页访问成功，状态码: {home_response.status_code}")
        
        # 再次随机延迟
        time.sleep(random.uniform(1, 3))
        
        # 发送请求
        logging.info(f"访问分类页面: {url}")
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        logging.info(f"分类页面访问成功，状态码: {response.status_code}")
        
        # 解析HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找电影链接
        links = soup.find_all('a', href=True)
        logging.info(f"找到 {len(links)} 个链接")
        
        for link in links:
            img = link.find('img')
            if img:
                # 尝试从链接文本或邻近元素获取标题
                title = link.get_text(strip=True)
                if not title:
                    # 尝试查找邻近的标题元素
                    next_element = link.find_next(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div'])
                    if next_element:
                        title = next_element.get_text(strip=True)
                
                if title and len(title) > 1:
                    # 清理标题
                    if title.startswith('#'):
                        title = title[1:].strip()
                    
                    # 获取图片URL
                    img_url = img.get('src')
                    if img_url:
                        # 处理相对路径
                        if not img_url.startswith('http'):
                            img_url = f"https://www.seedhub.cc{img_url}" if img_url.startswith('/') else f"https://www.seedhub.cc/{img_url}"
                        
                        # 下载图片
                        download_image(img_url, title)
                        
                        # 添加到电影列表
                        movies.append({
                            'title': title,
                            'cover_url': img_url,
                            'category': category
                        })
        
        logging.info(f"成功爬取 {len(movies)} 部 {category}")
        
    except Exception as e:
        logging.error(f"爬取 {category} 失败: {e}")
    
    return movies

def download_image(url, title):
    """下载单个图片"""
    try:
        import random
        import time
        import requests
        
        # 随机延迟 1-3 秒，避免请求过快
        delay = random.uniform(1, 3)
        logging.info(f"准备下载图片，URL: {url}，延迟 {delay:.2f} 秒")
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
        
        logging.info(f"使用 User-Agent: {user_agent}")
        logging.info(f"使用 Referer: {referer}")
        
        # 发送请求
        logging.info(f"下载图片: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        logging.info(f"图片下载成功，状态码: {response.status_code}")
        
        # 获取文件扩展名
        ext = url.split('.')[-1].split('?')[0].split('#')[0]
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            ext = 'jpg'  # 默认扩展名
        
        # 清理文件名
        safe_title = ''.join(c for c in title if c.isalnum() or c in [' ', '-', '_', '（', '）', '(', ')', ':', '：'])
        safe_title = safe_title.strip()
        
        # 保存图片
        filepath = os.path.join(IMAGE_DIR, f"{safe_title}.{ext}")
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        logging.info(f"✓ 成功下载图片: {filepath}")
        
    except Exception as e:
        logging.error(f"✗ 下载图片失败: {e}")

def update_movie_db(movies):
    """更新数据库中的电影数据"""
    logging.info("开始更新数据库")
    
    try:
        # 连接数据库
        conn = sqlite3.connect('data/search_ucmao.db')
        cursor = conn.cursor()
        
        # 遍历电影列表，更新数据库
        updated_count = 0
        for movie in movies:
            title = movie['title']
            cover_url = movie['cover_url']
            category = movie['category']
            
            # 更新数据库中的电影数据
            cursor.execute(
                "UPDATE movies SET cover_url = ? WHERE title = ? AND category = ?",
                (cover_url, title, category)
            )
            
            if cursor.rowcount > 0:
                updated_count += 1
                logging.info(f"更新电影 {title} 的封面图片")
        
        # 提交事务
        conn.commit()
        
        logging.info(f"成功更新 {updated_count} 部电影的封面图片")
        
        # 关闭连接
        conn.close()
        
    except Exception as e:
        logging.error(f"更新数据库失败: {e}")

def main():
    """主函数"""
    print("============================================================")
    print("爬取 seedhub.cc 网站的影视图片并更新数据库")
    print("============================================================")
    
    # 开始爬取
    crawl_seedhub_and_update_db()
    
    print("============================================================")
    print("爬取和更新完成")
    print("============================================================")

if __name__ == "__main__":
    main()