#!/usr/bin/env python3
"""
Mock-based E2E wash pipeline test.
Verifies: store -> share -> DB record -> cleanup -> delete
Mocks Quark API to bypass "41017 用户禁止转存自己的分享" restriction.
"""
import sys, os, time, unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.stored_files_dao import (
    insert_stored_file, get_expired_files,
    update_delete_status, get_washed_link_by_original, delete_stored_file_by_original_link
)
from src.db.resources_dao import delete_by_share_link
from src.db.db import db_cursor

MOCK_URL = "https://pan.quark.cn/s/mock_ext_share_001"
MOCK_NEW_FILE_ID = "mock_fid_abc001"
MOCK_NEW_SHARE_URL = "https://pan.quark.cn/s/mock_new_002"
MOCK_FILE_NAME = "[Mock] 测试电影.mkv"
MOCK_CLOUD = "夸克网盘"


def cleanup_test_data():
    try:
        delete_stored_file_by_original_link(MOCK_URL)
    except:
        pass
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM stored_files WHERE file_id=?", (MOCK_NEW_FILE_ID,))
    except:
        pass
    try:
        delete_by_share_link(MOCK_NEW_SHARE_URL)
    except:
        pass


class TestWashPipelineMock(unittest.TestCase):

    def setUp(self):
        cleanup_test_data()

    def tearDown(self):
        cleanup_test_data()

    def test_01_create_share_with_mock(self):
        """转存: create_share() with mocked Quark.store -> returns new share URL"""
        with patch('src.clients.quark_client.Quark.store') as mock_store, \
             patch('src.pan_operator.get_and_validate_cookie') as mock_cookie:
            mock_store.return_value = (MOCK_NEW_FILE_ID, MOCK_FILE_NAME, MOCK_NEW_SHARE_URL)
            mock_cookie.return_value = "fake_valid_cookie_123456789012345678901234567890"

            from src.pan_operator import create_share
            result = create_share({
                'share_url': MOCK_URL,
                'title': 'Mock测试电影',
                'save_to_netdisk': {'quark': True, 'baidu': False}
            })

            self.assertIsNotNone(result, "create_share should return a result")
            self.assertIsInstance(result, dict, "create_share should return a dict")
            self.assertEqual(result.get('share_url'), MOCK_NEW_SHARE_URL)
            self.assertEqual(result.get('file_id'), MOCK_NEW_FILE_ID)
            print(f"  ✓  转存成功: file_id={MOCK_NEW_FILE_ID}, share_url={MOCK_NEW_SHARE_URL}")

    def test_02_stored_file_db_record(self):
        """入库: 转存后 stored_files 表有记录"""
        with patch('src.clients.quark_client.Quark.store') as mock_store, \
             patch('src.pan_operator.get_and_validate_cookie') as mock_cookie:
            mock_store.return_value = (MOCK_NEW_FILE_ID, MOCK_FILE_NAME, MOCK_NEW_SHARE_URL)
            mock_cookie.return_value = "fake_valid_cookie_123456789012345678901234567890"

            from src.pan_operator import create_share
            create_share({
                'share_url': MOCK_URL,
                'title': 'Mock测试电影',
                'save_to_netdisk': {'quark': True, 'baidu': False}
            })

        cached = get_washed_link_by_original(MOCK_URL)
        self.assertIsNotNone(cached, "stored_files should have a record")
        self.assertEqual(cached.get('share_link'), MOCK_NEW_SHARE_URL)
        self.assertEqual(cached.get('file_id'), MOCK_NEW_FILE_ID)
        print(f"  ✓  DB去重记录存在: share_link={MOCK_NEW_SHARE_URL}")

    def test_03_dedup_cache(self):
        """去重: 重复调用 create_share 应走缓存, 不再调用 store"""
        with patch('src.clients.quark_client.Quark.store') as mock_store, \
             patch('src.pan_operator.get_and_validate_cookie') as mock_cookie:
            mock_store.return_value = (MOCK_NEW_FILE_ID, MOCK_FILE_NAME, MOCK_NEW_SHARE_URL)
            mock_cookie.return_value = "fake_valid_cookie_123456789012345678901234567890"

            from src.pan_operator import create_share
            # First call
            r1 = create_share({
                'share_url': MOCK_URL, 'title': 'Test',
                'save_to_netdisk': {'quark': True}
            })
            call_count_1 = mock_store.call_count

            # Second call - should use cache
            r2 = create_share({
                'share_url': MOCK_URL, 'title': 'Test',
                'save_to_netdisk': {'quark': True}
            })
            call_count_2 = mock_store.call_count

            self.assertEqual(call_count_1, call_count_2, "Second call should NOT invoke store again")
            self.assertEqual(r2.get('share_url'), MOCK_NEW_SHARE_URL)
            print(f"  ✓  去重生效: store调用次数={call_count_1} (第二次未调用)")

    def test_04_cleanup_scheduler_finds_expired(self):
        """定时清理: 过期文件被 cleanup scheduler 正确检测"""
        # Insert a record with old timestamp
        insert_stored_file({
            'file_id': MOCK_NEW_FILE_ID,
            'file_name': MOCK_FILE_NAME,
            'original_share_link': MOCK_URL,
            'share_link': MOCK_NEW_SHARE_URL,
            'cloud_name': MOCK_CLOUD
        })
        old_time = (datetime.now() - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
        with db_cursor() as cur:
            cur.execute("UPDATE stored_files SET created_at=? WHERE file_id=?",
                        (old_time, MOCK_NEW_FILE_ID))

        expired = get_expired_files(5)
        found = any(r.get('file_id') == MOCK_NEW_FILE_ID for r in (expired or []))
        self.assertTrue(found, "Expired file should be detected by cleanup scheduler")
        print(f"  ✓  过期检测: 过期文件数={len(expired or [])}, 测试记录已找到")

    def test_05_delete_status_state_machine(self):
        """状态机: pending -> failed -> success"""
        insert_stored_file({
            'file_id': MOCK_NEW_FILE_ID,
            'file_name': MOCK_FILE_NAME,
            'original_share_link': MOCK_URL,
            'share_link': MOCK_NEW_SHARE_URL,
            'cloud_name': MOCK_CLOUD
        })
        with db_cursor() as cur:
            cur.execute("SELECT id, delete_status, delete_attempts FROM stored_files WHERE file_id=?",
                        (MOCK_NEW_FILE_ID,))
            row = cur.fetchone()
        self.assertIsNotNone(row, "Record should exist")
        rid = row['id']

        # Initial state
        self.assertEqual(row['delete_status'], 'pending')
        self.assertEqual(row['delete_attempts'], 0)

        # Simulate failure
        update_delete_status(rid, 'failed', 1)
        with db_cursor() as cur:
            cur.execute("SELECT delete_status, delete_attempts FROM stored_files WHERE id=?", (rid,))
            r2 = cur.fetchone()
        self.assertEqual(r2['delete_status'], 'failed')
        self.assertEqual(r2['delete_attempts'], 1)

        # Simulate success
        update_delete_status(rid, 'success', 2)
        with db_cursor() as cur:
            cur.execute("SELECT delete_status FROM stored_files WHERE id=?", (rid,))
            r3 = cur.fetchone()
        self.assertEqual(r3['delete_status'], 'success')
        print(f"  ✓  状态机: pending -> failed -> success")

    def test_06_del_share(self):
        """删除: del_share() 删除网盘文件并清理DB"""
        # First create a share via mock
        with patch('src.clients.quark_client.Quark.store') as mock_store, \
             patch('src.pan_operator.get_and_validate_cookie') as mock_cookie:
            mock_store.return_value = (MOCK_NEW_FILE_ID, MOCK_FILE_NAME, MOCK_NEW_SHARE_URL)
            mock_cookie.return_value = "fake_valid_cookie_123456789012345678901234567890"

            from src.pan_operator import create_share, del_share
            create_share({
                'share_url': MOCK_URL, 'title': 'Mock',
                'save_to_netdisk': {'quark': True}
            })

        # Now test del_share with mocked del_file
        with patch('src.clients.quark_client.Quark.del_file') as mock_del, \
             patch('src.pan_operator.get_and_validate_cookie') as mock_cookie:
            mock_del.return_value = True
            mock_cookie.return_value = "fake_valid_cookie_123456789012345678901234567890"

            result = del_share({
                'share_url': MOCK_NEW_SHARE_URL,
                'file_id': MOCK_NEW_FILE_ID
            })
            self.assertTrue(result, "del_share should return True")

        # Verify cleanup
        cached = get_washed_link_by_original(MOCK_URL)
        self.assertIsNone(cached, "stored_files record should be deleted after del_share")
        print(f"  ✓  删除成功: 网盘文件已删除, DB记录已清理")

    def test_07_get_quota_fix(self):
        """配额: get_quota() 使用新接口返回有效数据"""
        with patch('src.pan_operator.get_and_validate_cookie') as mock_cookie:
            mock_cookie.return_value = "fake_valid_cookie_123456789012345678901234567890"
            from src.clients.quark_client import Quark
            # Mock the session.get to return valid capacity/detail response
            client = Quark("fake_cookie")
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 0, 'message': 'ok',
                'data': {
                    'capacity_summary': {
                        'sum_capacity': 28588585779200,
                        'detail': [{'capacity_type': 'SUPER_VIP', 'capacity': 6597069766656}]
                    }
                }
            }
            mock_response.raise_for_status = MagicMock()
            with patch.object(client.session, 'get', return_value=mock_response):
                quota = client.get_quota()
                self.assertIsNotNone(quota, "get_quota should return data")
                self.assertGreater(quota['total'], 0, "Total capacity should be > 0")
                self.assertEqual(quota['used_percent'], 0, "used should be 0 (API limitation)")
                print(f"  ✓  配额查询: total={quota['total']/(1024**3):.0f}GB, used={quota['used']}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
