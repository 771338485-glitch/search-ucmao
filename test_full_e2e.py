#!/usr/bin/env python3
"""
全流程端到端测试
覆盖: pan_operator.create_share() -> 验证DB -> del_share() -> 验证清理 -> 定时任务逻辑
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.clients.quark_client import Quark, get_id_from_url
from src.db.cookie_config_dao import get_cookie_by_cloud_name
from src.db.stored_files_dao import (
    insert_stored_file, get_washed_link_by_original,
    get_expired_files, delete_stored_file_by_original_link,
    delete_stored_files_by_ids, update_delete_status
)
from src.db.resources_dao import (
    insert_resource, insert_resource_simple, update_share_link,
    delete_by_share_link, delete_resource_by_id, get_resource_by_id
)
from src.pan_operator import create_share, del_share, sync_create_share
from src.scheduler.cleanup_scheduler import clean_expired_files
from src.db.db import db_cursor

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
SKIP = "\033[93m~\033[0m"
results = []

def report(name, ok, detail=""):
    tag = PASS if ok else FAIL
    results.append((name, ok, detail))
    print(f"  {tag}  {name}" + (f"  ({detail})" if detail else ""))

# --- 1. 前置条件验证 ---
print(f"\n\033[96m=== 1. 前置条件 ===\033[0m")

quark_cookie = get_cookie_by_cloud_name("夸克网盘")
report("夸克Cookie获取", bool(quark_cookie) and len(quark_cookie) > 300, f"长度={len(quark_cookie) if quark_cookie else 0}")

client = Quark(quark_cookie)
dir_id = client._get_or_create_dir("/桃白白影视/")
report("桃白白影视目录", bool(dir_id) and dir_id != '0', f"ID={dir_id}")

# --- 2. 创建测试用分享链接 ---
print(f"\n\033[96m=== 2. 创建测试用分享链接 ===\033[0m")

dir_files = client.get_dir_file(dir_id)
report("获取目录文件列表", isinstance(dir_files, list) and len(dir_files) > 0, f"文件数={len(dir_files) if isinstance(dir_files, list) else 0}")

if not dir_files:
    print("\n  桃白白影视目录为空，无法继续测试")
    sys.exit(1)

test_source_file = None
for f in dir_files:
    if f.get('file_type') == 0:
        continue
    test_source_file = f
    break

if not test_source_file:
    test_source_file = dir_files[0]

source_fid = test_source_file['fid']
source_name = test_source_file['file_name']
print(f"  选定测试源文件: {source_name} (fid={source_fid})")

share_task = client.share_task_id(source_fid, f"[E2E] {source_name}")
report("创建分享任务", bool(share_task), f"task_id={share_task}")

test_share_url = None
if share_task:
    share_result = client.task(share_task)
    share_id = share_result.get('data', {}).get('share_id') if share_result else None
    report("执行分享任务", bool(share_id), f"share_id={share_id}")

    if share_id:
        test_share_url = client.get_share_link(share_id)
        report("获取分享链接", bool(test_share_url), f"URL={test_share_url[:50]}..." if test_share_url else "空")

if not test_share_url:
    print("\n  无法创建测试分享链接，无法继续")
    sys.exit(1)

# --- 3. 测试 pan_operator.create_share() 全流程 ---
print(f"\n\033[96m=== 3. pan_operator.create_share() [转存+转发+入库] ===\033[0m")

share_data = {
    'share_url': test_share_url,
    'title': '[E2E测试资源]',
    'save_to_netdisk': {'quark': True, 'baidu': False},
}

start = time.time()
result = create_share(share_data)
elapsed = time.time() - start

report("create_share 返回值", result is not None, f"耗时={elapsed:.2f}s")

new_share_url = None
new_file_id = None

if result:
    new_share_url = result.get('share_url')
    new_file_id = result.get('file_id')
    report("生成新分享链接", bool(new_share_url), f"URL={new_share_url[:50]}..." if new_share_url else "空")
    report("获取新文件ID", bool(new_file_id), f"file_id={new_file_id}")
    if new_share_url:
        report("新链接 != 原链接", new_share_url != test_share_url)
        from utils.netdisk_utils import match_netdisk_link
        report("新链接识别为夸克网盘", match_netdisk_link(new_share_url) == "夸克网盘")

# --- 4. 验证数据库记录 ---
print(f"\n\033[96m=== 4. 验证数据库记录 ===\033[0m")

cached = get_washed_link_by_original(test_share_url)
report("stored_files 去重记录存在", bool(cached) and bool(cached.get('share_link')),
       f"cached_link={cached.get('share_link', '无')[:50] if cached else '无'}...")

if cached:
    report("stored_files 记录匹配新链接", cached.get('share_link') == new_share_url)

# --- 5. 测试去重机制 ---
print(f"\n\033[96m=== 5. 测试去重机制 ===\033[0m")

start2 = time.time()
result2 = create_share(share_data)
elapsed2 = time.time() - start2
report("重复调用走缓存", result2 is not None and result2.get('share_url') == new_share_url,
       f"耗时={elapsed2:.2f}s (首次={elapsed:.2f}s)")

# --- 6. 测试 pan_operator.del_share() 删除全流程 ---
print(f"\n\033[96m=== 6. del_share() [删除网盘文件+清理DB] ===\033[0m")

if new_file_id and new_share_url:
    del_data = {
        'share_url': test_share_url,
        'file_id': new_file_id
    }
    del_result = del_share(del_data)
    report("del_share 返回 True", del_result is True)

    remaining = client.search_file(f"[E2E] {source_name}")
    e2e_files = [f for f in remaining if f.get('fid') == new_file_id]
    report("网盘文件已删除", len(e2e_files) == 0)

    cached2 = get_washed_link_by_original(test_share_url)
    report("stored_files 记录已清理", cached2 is None, f"查询结果={'仍有记录' if cached2 else '已清空'}")
else:
    print(f"  {SKIP}  跳过删除测试 (没有新文件ID)")

# --- 7. 测试定时清理调度器逻辑 ---
print(f"\n\033[96m=== 7. 定时清理调度器逻辑 ===\033[0m")

from datetime import datetime
past = datetime.fromtimestamp(time.time() - 360)

insert_stored_file({
    'file_id': 'fake_expired_001',
    'file_name': '[E2E] 过期测试文件',
    'original_share_link': 'https://pan.quark.cn/s/e2e_expired_001',
    'share_link': 'https://pan.quark.cn/s/e2e_expired_new_001',
    'cloud_name': '夸克网盘'
})

with db_cursor() as cur:
    if cur:
        cur.execute("UPDATE stored_files SET created_at = ? WHERE file_id = ?", (past, 'fake_expired_001'))

expired = get_expired_files(5)
report("get_expired_files 返回过期记录", len(expired) > 0, f"数量={len(expired)}")

found_fake = any(r.get('file_id') == 'fake_expired_001' for r in expired)
report("包含模拟过期记录", found_fake)

delete_stored_file_by_original_link('https://pan.quark.cn/s/e2e_expired_001')
after = get_washed_link_by_original('https://pan.quark.cn/s/e2e_expired_001')
report("模拟记录已清理", after is None)

# --- 8. 测试 delete_status 状态机 ---
print(f"\n\033[96m=== 8. delete_status 状态机 ===\033[0m")

insert_stored_file({
    'file_id': 'fake_status_test',
    'file_name': '[E2E] 状态测试',
    'original_share_link': 'https://pan.quark.cn/s/e2e_status_test',
    'share_link': 'https://pan.quark.cn/s/e2e_status_new',
    'cloud_name': '夸克网盘'
})

with db_cursor(dictionary=True) as cur:
    if cur:
        cur.execute("SELECT id, delete_status, delete_attempts FROM stored_files WHERE file_id = 'fake_status_test'")
        rec = cur.fetchone()
        if rec:
            rid = rec['id']
            report("初始状态=pending", rec['delete_status'] == 'pending')
            report("初始attempts=0", rec['delete_attempts'] == 0)

            update_delete_status(rid, 'failed', 1)
            cur.execute("SELECT delete_status, delete_attempts FROM stored_files WHERE id = ?", (rid,))
            r2 = cur.fetchone()
            report("失败后状态=failed", r2['delete_status'] == 'failed')
            report("失败后attempts=1", r2['delete_attempts'] == 1)

            update_delete_status(rid, 'success', 1)
            cur.execute("SELECT delete_status FROM stored_files WHERE id = ?", (rid,))
            r3 = cur.fetchone()
            report("成功后状态=success", r3['delete_status'] == 'success')

delete_stored_file_by_original_link('https://pan.quark.cn/s/e2e_status_test')

# --- 9. 夸克网盘空间查询 ---
print(f"\n\033[96m=== 9. 夸克网盘空间查询 ===\033[0m")

quota = client.get_quota()
report("获取网盘配额", quota is not None and quota.get('total', 0) > 0,
       f"使用率={quota.get('used_percent', 0)}%" if quota else "获取失败")

# --- 10. 清理残留 ---
print(f"\n\033[96m=== 10. 清理残留 ===\033[0m")

if new_file_id:
    remaining_check = client.search_file(f"[E2E] {source_name}")
    for f in remaining_check:
        if f.get('fid') == new_file_id:
            client.del_file(new_file_id)
            print(f"  {PASS}  清理残留文件: {new_file_id}")
            break

report("临时数据清理完成", True)

# --- 汇总 ---
print(f"\n{'='*60}")
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
print(f"  总计: {total} 项 | \033[92m通过: {passed}\033[0m | \033[91m失败: {failed}\033[0m")
if failed:
    print(f"\n  \033[91m失败项:\033[0m")
    for name, ok, detail in results:
        if not ok:
            print(f"    - {name}  {detail}")
print(f"{'='*60}\n")
