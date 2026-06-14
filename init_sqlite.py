#!/usr/bin/env python3
"""
SQLite数据库初始化脚本
创建所有必要的表结构
"""

import sqlite3
import os
from datetime import datetime

# 数据库文件路径
DB_PATH = 'data/search_ucmao.db'


def init_database():
    """初始化SQLite数据库"""
    
    # 确保data目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("开始创建数据库表...")
    
    # 1. 创建 resources 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            name TEXT NOT NULL,
            share_link TEXT NOT NULL,
            cloud_name TEXT DEFAULT '',
            type TEXT DEFAULT '',
            remarks TEXT DEFAULT '',
            is_replaced INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. 创建 hot_movies 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hot_movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            movie_rank INTEGER,
            cover_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. 创建 api_config 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL,
            method TEXT DEFAULT 'GET',
            headers TEXT,
            params TEXT,
            body TEXT,
            is_enabled INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            last_used_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 4. 创建 cookie_config 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cookie_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cloud_name TEXT NOT NULL UNIQUE,
            cookie_value TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 5. 创建 search_history 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            search_count INTEGER DEFAULT 1,
            last_searched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 6. 创建 stored_files 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stored_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            cloud_name TEXT NOT NULL,
            size INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 7. 创建 email_config 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            smtp_server TEXT,
            smtp_port INTEGER,
            sender_email TEXT,
            sender_password TEXT,
            recipient_email TEXT,
            is_enabled INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("创建索引...")
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_name ON resources(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_cloud_name ON resources(cloud_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_created_at ON resources(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hot_movies_category ON hot_movies(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hot_movies_movie_rank ON hot_movies(movie_rank)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_config_is_enabled ON api_config(is_enabled)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_config_status ON api_config(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_history_keyword ON search_history(keyword)')
    
    conn.commit()
    conn.close()
    
    print(f"✅ SQLite数据库初始化完成！")
    print(f"📁 数据库文件: {DB_PATH}")


if __name__ == '__main__':
    init_database()
