#!/usr/bin/env python3
"""
夸克洗白全流程验证脚本
验证: Cookie有效性 → 转存 → 生成分享 → 数据库记录 → 删除网盘文件 → 删除数据库记录
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.clients.quark_client import Quark, get_id_from_url
from src.db.cookie_config_dao import get_cookie_by_cloud_name
from src.db.stored_files_dao import (
    insert_stored_file, get_washed_link_by_original,
    get_expired_files, delete_stored_file_by_original_link,
    delete_stored_files_by_ids, update_delete_status
)
from src.db.resources_dao import (
    insert_resource_simple, update_share_link,
    delete_resource_by_id, get_resource_by_id, delete_by_share_link
)
from utils.netdisk_utils import match_netdisk_link

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
SKIP = "\033[93m~ SKIP\033[0m"
SECTION = "\033[96m"

results = []

def report(name, ok, detail=""):
    tag = PASS if ok else FAIL
    results.append((name, ok, detail))
    print(f"  {tag}  {name}" + (f"  ({detail})" if detail else ""))

# ─── 1. Cookie 获取与验证 ───
print(f"\n{SECTION}═══ 1. Cookie 获取与验证 ═══\033[0m")

quark_cookie = get_cookie_by_cloud_name("夸克网盘")
report("夸克Cookie从DB获取", bool(quark_cookie), f"长度={len(quark_cookie) if quark_cookie else 0}")

if not quark_cookie or len(quark_cookie) < 300:
    print("\n  夸克Cookie无效或未配置，无法继续验证。")
    sys.exit(1)

client = Quark(quark_cookie)

# 验证Cookie有效性 (quota API返回404不影响核心功能，用文件列表API验证)
all_files_test = client.get_all_file()
cookie_valid = isinstance(all_files_test, list)
report("夸克Cookie有效性验证", cookie_valid,
       f"文件列表API返回{len(all_files_test)}个文件" if cookie_valid else "请求失败")

if not cookie_valid:
    print("\n  夸克Cookie已失效，无法继续验证实际API调用。")
    sys.exit(1)

# ─── 2. 网盘类型识别 ───
print(f"\n{SECTION}═══ 2. 网盘类型识别 ═══\033[0m")

test_urls = [
    ("https://pan.quark.cn/s/abc123", "夸克网盘"),
    ("https://pan.baidu.com/s/abc123", "百度网盘"),
    ("https://pan.xunlei.com/s/abc123", "迅雷网盘"),
    ("https://www.aliyundrive.com/s/abc123", "阿里云盘"),
]
for url, expected in test_urls:
    result = match_netdisk_link(url)
    report(f"识别 {url[:40]}...", result == expected, f"得到={result}")

# ─── 3. pwd_id 提取 ───
print(f"\n{SECTION}═══ 3. 分享链接ID提取 ═══\033[0m")

test_id = get_id_from_url("https://pan.quark.cn/s/6176e44c7c0a")
report("从URL提取pwd_id", test_id == "6176e44c7c0a", f"得到={test_id}")

test_id2 = get_id_from_url("https://pan.quark.cn/s/abc123def456?pwd=test")
report("带参数URL提取pwd_id", test_id2 == "abc123def456", f"得到={test_id2}")

# ─── 4. 查询个人网盘目录 ───
print(f"\n{SECTION}═══ 4. 查询/创建网盘目录 ═══\033[0m")

dir_id = client._get_or_create_dir("/桃白白影视/")
report("获取/创建桃白白影视目录", dir_id and dir_id != '0', f"目录ID={dir_id}")

# ─── 5. 获取网盘根目录文件列表 ───
print(f"\n{SECTION}═══ 5. 网盘文件列表 ═══\033[0m")

all_files = client.get_all_file()
report("获取根目录文件列表", isinstance(all_files, list), f"文件数={len(all_files)}")

if dir_id and dir_id != '0':
    dir_files = client.get_dir_file(dir_id)
    report("获取桃白白影视目录文件", isinstance(dir_files, list), f"文件数={len(dir_files)}")
    if dir_files:
        for f in dir_files[:5]:
            print(f"    📁 {f.get('file_name', '?')} (fid={f.get('fid', '?')}, type={f.get('file_type', '?')})")

# ─── 6. 洗白全流程: 用一个已知的夸克分享链接测试 ───
print(f"\n{SECTION}═══ 6. 夸克洗白全流程验证 ═══\033[0m")

# 先用一个已知的夸克分享链接来测试
# 用 ad_pwd_id 来测试(这是项目自带的广告链接)
test_share_url = f"https://pan.quark.cn/s/{Quark.ad_pwd_id}"

# 6a. 获取stoken
stoken = client.get_stoken(Quark.ad_pwd_id)
report("步骤1: 获取stoken", bool(stoken), f"stoken={stoken[:20]}..." if stoken else "空")

if stoken:
    # 6b. 获取分享详情
    detail = client.detail(Quark.ad_pwd_id, stoken)
    report("步骤2: 获取分享详情", bool(detail and detail.get('fid')),
           f"title={detail.get('title', '?')}, fid={detail.get('fid', '?')}" if detail else "空")

    if detail and detail.get('fid') and detail.get('share_fid_token'):
        first_id = detail['fid']
        share_fid_token = detail['share_fid_token']
        file_name = detail.get('title', 'test_file')

        # 6c. 转存到桃白白影视目录
        save_task_id = client.save_task_id(Quark.ad_pwd_id, stoken, first_id, share_fid_token, dir_id or '0')
        report("步骤3: 创建转存任务", bool(save_task_id), f"task_id={save_task_id}")

        if save_task_id:
            save_result = client.task(save_task_id)
            save_as = save_result.get('data', {}).get('save_as', {}) if save_result else {}
            saved_fids = save_as.get('save_as_top_fids', [])
            report("步骤4: 执行转存任务", bool(saved_fids),
                   f"file_id={saved_fids[0] if saved_fids else '无'}")

            if saved_fids:
                new_file_id = saved_fids[0]

                # 6d. 创建分享
                share_task_id = client.share_task_id(new_file_id, file_name)
                report("步骤5: 创建分享任务", bool(share_task_id), f"share_task_id={share_task_id}")

                if share_task_id:
                    share_result = client.task(share_task_id)
                    share_id = share_result.get('data', {}).get('share_id') if share_result else None
                    report("步骤6: 执行分享任务", bool(share_id), f"share_id={share_id}")

                    if share_id:
                        share_link = client.get_share_link(share_id)
                        report("步骤7: 获取分享链接", bool(share_link), f"link={share_link}")

                        if share_link:
                            # 6e. 验证新链接可识别为夸克网盘
                            new_type = match_netdisk_link(share_link)
                            report("步骤8: 新链接类型识别", new_type == "夸克网盘", f"type={new_type}")

                            # ─── 7. 数据库操作验证 ───
                            print(f"\n{SECTION}═══ 7. 数据库操作验证 ═══\033[0m")

                            # 7a. 写入stored_files
                            insert_ok = insert_stored_file({
                                'file_id': new_file_id,
                                'file_name': file_name,
                                'original_share_link': test_share_url,
                                'share_link': share_link,
                                'cloud_name': '夸克网盘'
                            })
                            report("写入stored_files表", insert_ok)

                            # 7b. 查询去重
                            existing = get_washed_link_by_original(test_share_url)
                            report("查询去重(已洗白链接)", bool(existing and existing.get('share_link')),
                                   f"share_link={existing.get('share_link', '无') if existing else '无'}")

                            # 7c. 写入resources表
                            success, msg, new_id = insert_resource_simple({
                                'name': f'[测试] {file_name}',
                                'share_link': share_link,
                                'cloud_name': '夸克网盘',
                                'type': '测试',
                                'remarks': '洗白验证脚本自动创建'
                            })
                            report("写入resources表", success, f"id={new_id}, msg={msg}")

                            # 7d. 查询刚写入的资源
                            if new_id:
                                ok, _, res = get_resource_by_id(new_id)
                                report("查询resources记录", ok and bool(res),
                                       f"name={res.get('name', '?') if res else '?'}")

                            # ─── 8. 删除全流程验证 ───
                            print(f"\n{SECTION}═══ 8. 删除全流程验证 ═══\033[0m")

                            # 8a. 删除网盘分享的文件 (转存生成的新文件)
                            del_file_ok = client.del_file(new_file_id)
                            report("删除网盘文件(转存的新文件)", del_file_ok, f"file_id={new_file_id}")

                            # 8b. 删除stored_files记录
                            del_stored = delete_stored_file_by_original_link(test_share_url)
                            report("删除stored_files记录", del_stored > 0, f"删除{del_stored}条")

                            # 8c. 验证去重查询返回空
                            after_del = get_washed_link_by_original(test_share_url)
                            report("删除后去重查询为空", after_del is None,
                                   f"结果={'仍有记录' if after_del else '已清空'}")

                            # 8d. 删除resources记录
                            if new_id:
                                ok2, msg2, _ = delete_resource_by_id(new_id)
                                report("删除resources记录", ok2, f"msg={msg2}")

                                # 8e. 验证resources已删除
                                ok3, msg3, res3 = get_resource_by_id(new_id)
                                report("确认resources已删除", msg3 == "资源不存在",
                                       f"msg={msg3}")

                            # ─── 9. 清理: 删除刚才转存过程中创建的目录中的多余文件 ───
                            print(f"\n{SECTION}═══ 9. 转存目录清理验证 ═══\033[0m")

                            # 列出桃白白影视目录当前文件
                            current_files = client.get_dir_file(dir_id) if dir_id and dir_id != '0' else []
                            remaining = [f for f in current_files if f.get('fid') == new_file_id]
                            report("转存文件已被删除", len(remaining) == 0,
                                   f"残留={len(remaining)}个")

# ─── 10. 过期文件清理机制验证 ───
print(f"\n{SECTION}═══ 10. 过期文件清理机制 ═══\033[0m")

expired = get_expired_files(5)
report("查询过期文件(pending, >5min)", isinstance(expired, list), f"数量={len(expired)}")

# ─── 汇总 ───
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
