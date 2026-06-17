#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全流程 Mock 测试：转存-转发-删除 + 调度器清理
覆盖：夸克/百度两条链路、去重、定时清理、状态机、链接识别
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.stored_files_dao import (
    insert_stored_file,
    get_washed_link_by_original,
    get_expired_files,
    update_delete_status,
    delete_stored_file_by_original_link,
)
from src.db.resources_dao import delete_by_share_link
from src.db.db import db_cursor
from src.pan_operator import create_share, del_share
from utils.netdisk_utils import match_netdisk_link

# ============================================================
# 测试数据
# ============================================================
QUARK_ORIG = "https://pan.quark.cn/s/aaaa1111"
QUARK_NEW = "https://pan.quark.cn/s/quark_new_001"
QUARK_FID = "quark_fid_001"
QUARK_NAME = "[Mock] 夸克测试电影.mkv"

BAIDU_ORIG = "https://pan.baidu.com/s/1abcdef?pwd=1234"
BAIDU_NEW = "https://pan.baidu.com/s/1newlink?pwd=abcd"
BAIDU_FID = "/桃白白影视/baidu_test.mkv"
BAIDU_NAME = "[Mock] 百度测试电影.mkv"

MOCK_COOKIE = "fake_valid_cookie_" + "x" * 300


def _cleanup(url_list):
    for url in url_list:
        try:
            delete_stored_file_by_original_link(url)
        except Exception:
            pass
        try:
            delete_by_share_link(url)
        except Exception:
            pass


# ============================================================
# 1. 链接识别
# ============================================================
class TestLinkRecognition(unittest.TestCase):
    """验证 netdisk_utils 能正确识别夸克/百度链接"""

    def test_quark_link(self):
        self.assertEqual(match_netdisk_link(QUARK_ORIG), "夸克网盘")

    def test_baidu_link(self):
        self.assertEqual(match_netdisk_link(BAIDU_ORIG), "百度网盘")

    def test_unknown_link(self):
        result = match_netdisk_link("https://www.example.com/file")
        self.assertNotEqual(result, "夸克网盘")
        self.assertNotEqual(result, "百度网盘")


# ============================================================
# 2. 夸克网盘全流程
# ============================================================
class TestQuarkWashPipeline(unittest.TestCase):
    """夸克网盘：转存 -> DB记录 -> 去重 -> 删除"""

    def setUp(self):
        _cleanup([QUARK_ORIG, QUARK_NEW])

    def tearDown(self):
        _cleanup([QUARK_ORIG, QUARK_NEW])

    def test_full_quark_flow(self):
        """完整流程：转存 -> 入库 -> 去重 -> 删除 -> 清理"""
        # --- 转存 ---
        with patch("src.pan_operator.get_and_validate_cookie", return_value=MOCK_COOKIE), \
             patch("src.clients.quark_client.Quark.store") as mock_store:
            mock_store.return_value = (QUARK_FID, QUARK_NAME, QUARK_NEW)

            result = create_share({
                "share_url": QUARK_ORIG,
                "title": "夸克测试电影",
                "save_to_netdisk": {"quark": True, "baidu": False},
            })

        self.assertIsNotNone(result)
        self.assertEqual(result["share_url"], QUARK_NEW)
        self.assertEqual(result["file_id"], QUARK_FID)

        # --- DB 记录 ---
        cached = get_washed_link_by_original(QUARK_ORIG)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["share_link"], QUARK_NEW)
        self.assertEqual(cached["file_id"], QUARK_FID)

        # --- 去重：第二次不调用 store ---
        with patch("src.pan_operator.get_and_validate_cookie", return_value=MOCK_COOKIE), \
             patch("src.clients.quark_client.Quark.store") as mock_store:
            mock_store.return_value = (QUARK_FID, QUARK_NAME, QUARK_NEW)
            result2 = create_share({
                "share_url": QUARK_ORIG,
                "title": "夸克测试电影",
                "save_to_netdisk": {"quark": True, "baidu": False},
            })
            mock_store.assert_not_called()

        self.assertIsNotNone(result2)
        self.assertEqual(result2["share_url"], QUARK_NEW)

        # --- 删除 ---
        with patch("src.pan_operator.get_and_validate_cookie", return_value=MOCK_COOKIE), \
             patch("src.clients.quark_client.Quark.del_file", return_value=True):
            del_result = del_share({
                "share_url": QUARK_NEW,
                "file_id": QUARK_FID,
            })

        self.assertTrue(del_result)
        self.assertIsNone(get_washed_link_by_original(QUARK_ORIG))


# ============================================================
# 3. 百度网盘全流程
# ============================================================
class TestBaiduWashPipeline(unittest.TestCase):
    """百度网盘：转存 -> DB记录 -> 去重 -> 删除"""

    def setUp(self):
        _cleanup([BAIDU_ORIG, BAIDU_NEW])

    def tearDown(self):
        _cleanup([BAIDU_ORIG, BAIDU_NEW])

    def test_full_baidu_flow(self):
        """完整流程：转存 -> 入库 -> 去重 -> 删除 -> 清理"""
        # --- 转存 ---
        with patch("src.pan_operator.get_and_validate_cookie", return_value=MOCK_COOKIE), \
             patch("src.clients.baidu_client.Baidu.store") as mock_store:
            mock_store.return_value = (BAIDU_FID, BAIDU_NAME, BAIDU_NEW)

            result = create_share({
                "share_url": BAIDU_ORIG,
                "title": "百度测试电影",
                "save_to_netdisk": {"quark": False, "baidu": True},
            })

        self.assertIsNotNone(result)
        self.assertEqual(result["share_url"], BAIDU_NEW)
        self.assertEqual(result["file_id"], BAIDU_FID)

        # --- DB 记录 ---
        cached = get_washed_link_by_original(BAIDU_ORIG)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["share_link"], BAIDU_NEW)
        self.assertEqual(cached["file_id"], BAIDU_FID)

        # --- 去重：第二次不调用 store ---
        with patch("src.pan_operator.get_and_validate_cookie", return_value=MOCK_COOKIE), \
             patch("src.clients.baidu_client.Baidu.store") as mock_store:
            mock_store.return_value = (BAIDU_FID, BAIDU_NAME, BAIDU_NEW)
            result2 = create_share({
                "share_url": BAIDU_ORIG,
                "title": "百度测试电影",
                "save_to_netdisk": {"quark": False, "baidu": True},
            })
            mock_store.assert_not_called()

        self.assertIsNotNone(result2)
        self.assertEqual(result2["share_url"], BAIDU_NEW)

        # --- 删除 ---
        with patch("src.pan_operator.get_and_validate_cookie", return_value=MOCK_COOKIE), \
             patch("src.clients.baidu_client.Baidu.del_file", return_value=True):
            del_result = del_share({
                "share_url": BAIDU_NEW,
                "file_id": BAIDU_FID,
            })

        self.assertTrue(del_result)
        self.assertIsNone(get_washed_link_by_original(BAIDU_ORIG))


# ============================================================
# 4. 定时清理调度器
# ============================================================
class TestCleanupScheduler(unittest.TestCase):
    """定时清理：过期文件检测 + 状态机 + 重试上限"""

    def setUp(self):
        _cleanup(["https://test.scheduler/clean1", "https://test.scheduler/clean2"])

    def tearDown(self):
        _cleanup(["https://test.scheduler/clean1", "https://test.scheduler/clean2"])

    def _insert_with_age(self, file_id, url, minutes_ago, status="pending", attempts=0):
        insert_stored_file({
            "file_id": file_id,
            "file_name": f"[Scheduler] {file_id}",
            "original_share_link": url,
            "share_link": url.replace("clean", "washed"),
            "cloud_name": "夸克网盘",
        })
        old = (datetime.now() - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")
        with db_cursor() as cur:
            if cur:
                cur.execute(
                    "UPDATE stored_files SET created_at=?, delete_status=?, delete_attempts=? WHERE file_id=?",
                    (old, status, attempts, file_id),
                )

    def test_expired_pending_detected(self):
        """pending 且过期的文件应被检测到"""
        self._insert_with_age("sched_001", "https://test.scheduler/clean1", 10)
        expired = get_expired_files(5)
        found = any(r["file_id"] == "sched_001" for r in expired)
        self.assertTrue(found)

    def test_failed_low_attempts_detected(self):
        """failed 且 attempts<3 的文件应被检测到（可重试）"""
        self._insert_with_age("sched_002", "https://test.scheduler/clean2", 10, "failed", 1)
        expired = get_expired_files(5)
        found = any(r["file_id"] == "sched_002" for r in expired)
        self.assertTrue(found)

    def test_failed_high_attempts_not_detected(self):
        """failed 且 attempts>=3 的文件不再返回（放弃重试）"""
        self._insert_with_age("sched_003", "https://test.scheduler/clean1", 10, "failed", 3)
        expired = get_expired_files(5)
        found = any(r["file_id"] == "sched_003" for r in expired)
        self.assertFalse(found)

    def test_success_not_detected(self):
        """success 状态的文件不被检测"""
        self._insert_with_age("sched_004", "https://test.scheduler/clean2", 10, "success", 0)
        expired = get_expired_files(5)
        found = any(r["file_id"] == "sched_004" for r in expired)
        self.assertFalse(found)

    def test_not_expired_not_detected(self):
        """未过期的文件不被检测"""
        self._insert_with_age("sched_005", "https://test.scheduler/clean1", 2)
        expired = get_expired_files(5)
        found = any(r["file_id"] == "sched_005" for r in expired)
        self.assertFalse(found)


# ============================================================
# 5. 删除状态机
# ============================================================
class TestDeleteStatusStateMachine(unittest.TestCase):
    """delete_status 状态机: pending -> failed -> success"""

    def setUp(self):
        _cleanup(["https://test.status/sm"])

    def tearDown(self):
        _cleanup(["https://test.status/sm"])

    def test_status_transitions(self):
        insert_stored_file({
            "file_id": "status_fid",
            "file_name": "[Status] 测试",
            "original_share_link": "https://test.status/sm",
            "share_link": "https://test.status/sm_washed",
            "cloud_name": "夸克网盘",
        })

        with db_cursor(dictionary=True) as cur:
            cur.execute("SELECT id, delete_status, delete_attempts FROM stored_files WHERE file_id='status_fid'")
            row = cur.fetchone()

        self.assertEqual(row["delete_status"], "pending")
        self.assertEqual(row["delete_attempts"], 0)

        # pending -> failed
        update_delete_status(row["id"], "failed", 1)
        with db_cursor(dictionary=True) as cur:
            cur.execute("SELECT delete_status, delete_attempts FROM stored_files WHERE id=?", (row["id"],))
            r2 = cur.fetchone()
        self.assertEqual(r2["delete_status"], "failed")
        self.assertEqual(r2["delete_attempts"], 1)

        # failed -> success
        update_delete_status(row["id"], "success", 2)
        with db_cursor(dictionary=True) as cur:
            cur.execute("SELECT delete_status FROM stored_files WHERE id=?", (row["id"],))
            r3 = cur.fetchone()
        self.assertEqual(r3["delete_status"], "success")


# ============================================================
# 6. 错误处理
# ============================================================
class TestErrorHandling(unittest.TestCase):
    """异常场景：Cookie 无效、转存失败、删除失败"""

    def test_empty_cookie_skips_wash(self):
        """Cookie 为空时，create_share 跳过洗白返回原始链接"""
        with patch("src.pan_operator.get_and_validate_cookie", return_value=""):
            result = create_share({
                "share_url": QUARK_ORIG,
                "title": "无Cookie测试",
                "save_to_netdisk": {"quark": True, "baidu": False},
            })
        # 无 ID 的场景返回原始 share_data
        self.assertIsNotNone(result)
        self.assertEqual(result.get("share_url"), QUARK_ORIG)

    def test_store_returns_none(self):
        """转存返回 None 时，create_share 返回 None"""
        with patch("src.pan_operator.get_and_validate_cookie", return_value=MOCK_COOKIE), \
             patch("src.clients.quark_client.Quark.store", return_value=(None, None, None)):
            result = create_share({
                "share_url": QUARK_ORIG,
                "title": "转存失败测试",
                "save_to_netdisk": {"quark": True, "baidu": False},
            })
        # 无 ID 且转存失败时，create_share 返回原始 share_data 以避免丢数据
        self.assertIsNotNone(result)
        self.assertEqual(result.get("share_url"), QUARK_ORIG)

    def test_unsupported_cloud_type(self):
        """不支持的网盘类型，返回原始链接"""
        result = create_share({
            "share_url": "https://www.example.com/file",
            "title": "不支持的网盘",
            "save_to_netdisk": {"quark": True, "baidu": True},
        })
        self.assertIsNotNone(result)
        self.assertEqual(result.get("share_url"), "https://www.example.com/file")

    def test_del_share_missing_url(self):
        """del_share 缺少 share_url 时返回 False"""
        result = del_share({"file_id": "some_id"})
        self.assertFalse(result)

    def test_del_share_cookie_expired(self):
        """Cookie 过期时 del_share 返回 False"""
        with patch("src.pan_operator.get_and_validate_cookie", return_value=""):
            result = del_share({
                "share_url": QUARK_ORIG,
                "file_id": "some_id",
            })
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
