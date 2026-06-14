import sqlite3
import os
from configs.app_config import sqlite_db_path

print(f"数据库路径: {sqlite_db_path}")
print(f"文件存在: {os.path.exists(sqlite_db_path)}")

conn = sqlite3.connect(sqlite_db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, cloud_name, cookie, created_at, updated_at FROM cookie_config")
rows = cursor.fetchall()

print("\n" + "="*60)
print("数据库中的实际数据:")
print("="*60)
for row in rows:
    print(f"ID: {row[0]}")
    print(f"云盘: {row[1]}")
    print(f"Cookie长度: {len(row[2]) if row[2] else 0}")
    print(f"创建时间: {row[3]}")
    print(f"更新时间: {row[4]}")
    print("-"*60)

conn.close()
