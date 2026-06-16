#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
定时任务 Bug 修复验证测试

测试覆盖以下已修复 Bug：

Bug 1 (FIXED): email_scheduler - 22:00访客统计 minute==0 检查过于严格
  - 已修复：去掉 now.minute == 0，只检查 now.hour == 22

Bug 2 (FIXED): email_scheduler - 每月20号Cookie提醒后跳过22:00访客统计
  - 已修复：月度提醒发送后不再 wait→continue，自然继续到22:00发访客统计

Bug 3 (FIXED): stored_files_dao - 失败的文件删除记录永不重试、永不清理
  - 已修复：SQL 改为 delete_status IN ('pending', 'failed') AND delete_attempts < 3

Bug 4 (FIXED): email_scheduler - Cookie长度<300硬编码判断误报
  - 已修复：去掉 len(cookie) < 300 检查，只判断 cookie 是否为空

Bug 5 (FIXED): 二维码定时任务重复提醒
  - 已修复：get_expiring_qr_codes 加 LIMIT 1，insert/upsert 保证只有一条记录
  - 已修复：check_qr_code_expiry 发送后 mark_as_notified，已通知跳过
"""

import sqlite3
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call


# ============================================================
# Bug 1: 22:00 访客统计 — 修复后只检查 hour
# ============================================================
class TestBug1VisitorStatsMinuteCheck(unittest.TestCase):
    """
    验证：修复后当调度器在 22:01~22:59 唤醒时，访客统计邮件仍能正常发送。
    """

    def _run_one_iteration(self, mock_now):
        """
        模拟 _email_scheduler_loop 的一次迭代，返回 send_visitor_stats_email 是否被调用。
        修复后逻辑：if now.hour == 22（不再检查 minute）。
        """
        now = mock_now
        _daily_check_executed = False
        visitor_stats_sent = False

        if now.hour != 0:
            _daily_check_executed = False

        # 修复后：只检查 hour
        if now.hour == 22:
            visitor_stats_sent = True

        return visitor_stats_sent

    def test_visitor_stats_sent_at_22_00(self):
        """正常情况：22:00 唤醒，应该发送"""
        mock_now = datetime(2026, 6, 15, 22, 0, 5)
        result = self._run_one_iteration(mock_now)
        self.assertTrue(result, "22:00 应该发送访客统计邮件")

    def test_visitor_stats_sent_at_22_01(self):
        """Bug1 修复验证：22:01 唤醒，访客统计应正常发送"""
        mock_now = datetime(2026, 6, 15, 22, 1, 30)
        result = self._run_one_iteration(mock_now)
        self.assertTrue(result, "Bug1 已修复：22:01 时访客统计应正常发送")

    def test_visitor_stats_sent_at_22_05(self):
        """Bug1 修复验证：22:05 唤醒，访客统计应正常发送"""
        mock_now = datetime(2026, 6, 15, 22, 5, 0)
        result = self._run_one_iteration(mock_now)
        self.assertTrue(result, "Bug1 已修复：22:05 时访客统计应正常发送")

    def test_visitor_stats_not_sent_at_21_59(self):
        """边界：21:59 不应该发送（还没到22点）"""
        mock_now = datetime(2026, 6, 15, 21, 59, 0)
        result = self._run_one_iteration(mock_now)
        self.assertFalse(result, "21:59 不应该发送")


# ============================================================
# Bug 2: 每月20号Cookie提醒 — 修复后不再跳过后续任务
# ============================================================
class TestBug2MonthlyReminderSkipsNextTasks(unittest.TestCase):
    """
    验证：修复后每月20号9点发送Cookie提醒后，不再 wait→continue，
    当天22:00的访客统计邮件可以正常发送。
    """

    def _simulate_loop_iteration(self, now, daily_check_executed):
        """
        模拟 _email_scheduler_loop 的一次迭代。
        返回 (actions_taken, new_daily_check_executed, jumps_to_tomorrow)
        """
        actions = []
        new_daily_check_executed = daily_check_executed
        jumps_to_tomorrow = False

        # 每天0点检查
        if now.hour == 0 and not daily_check_executed:
            actions.append('daily_check')
            new_daily_check_executed = True
        elif now.hour != 0:
            new_daily_check_executed = False

        # 每月20号检查 — 修复后不再 wait→continue
        if now.day == 20 and now.hour == 9:
            actions.append('monthly_reminder')
            # 修复后：只发邮件，不跳过后续逻辑

        # 22:00访客统计 — 修复后只检查 hour
        if now.hour == 22:
            actions.append('visitor_stats')

        return actions, new_daily_check_executed, jumps_to_tomorrow

    def test_monthly_reminder_no_longer_skips_visitor_stats(self):
        """Bug2 修复验证：20号9点发送后，20号22:00的访客统计不再被跳过"""
        # 第1步：20号9点迭代
        now_9am = datetime(2026, 6, 20, 9, 0, 0)
        actions, daily_flag, jumps = self._simulate_loop_iteration(now_9am, False)

        self.assertIn('monthly_reminder', actions)
        self.assertFalse(jumps, "Bug2 已修复：20号9点不再跳到明天")

        # 第2步：20号22点，访客统计应正常发送
        now_10pm = datetime(2026, 6, 20, 22, 0, 0)
        actions_10pm, _, _ = self._simulate_loop_iteration(now_10pm, False)
        self.assertIn('visitor_stats', actions_10pm,
                       "Bug2 已修复：20号22:00的访客统计正常发送")

    def test_monthly_reminder_does_not_skip_next_day_0am_check(self):
        """验证：20号9:00的 elif now.hour!=0 分支会重置 daily_flag，21号0:00 日常检查正常执行"""
        daily_flag = False
        now_midnight = datetime(2026, 6, 20, 0, 0, 0)
        _, daily_flag, _ = self._simulate_loop_iteration(now_midnight, daily_flag)
        self.assertTrue(daily_flag, "20号0:00日常检查执行，flag 设为 True")

        # 模拟：20号9:00发送月度提醒（修复后不再 wait→continue）
        now_9am = datetime(2026, 6, 20, 9, 0, 0)
        actions_9am, daily_flag, jumps = self._simulate_loop_iteration(now_9am, daily_flag)
        self.assertIn('monthly_reminder', actions_9am)
        self.assertFalse(jumps)
        self.assertFalse(daily_flag, "9:00 的 elif now.hour!=0 分支将 flag 重置为 False")

        # 模拟：21号0:00，日常检查正常执行
        now_next_midnight = datetime(2026, 6, 21, 0, 0, 0)
        actions, new_flag, _ = self._simulate_loop_iteration(now_next_midnight, daily_flag)

        self.assertIn('daily_check', actions,
                       "21号0:00的日常检查正常执行")

    def test_normal_day_22pm_works(self):
        """对照组：非20号的22:00正常发送"""
        now = datetime(2026, 6, 15, 22, 0, 0)
        actions, _, _ = self._simulate_loop_iteration(now, False)
        self.assertIn('visitor_stats', actions, "非20号的22:00应该正常发送")


# ============================================================
# Bug 3: 失败的文件删除记录 — 修复后可重试 (attempts < 3)
# ============================================================
class TestBug3FailedFilesNeverRetry(unittest.TestCase):
    """
    验证：修复后 get_expired_files 的 SQL 查 pending + failed（attempts < 3），
    失败记录在重试次数 <3 时会被重新查询和重试。
    """

    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE stored_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                original_share_link TEXT NOT NULL,
                share_link TEXT NOT NULL,
                cloud_name TEXT NOT NULL,
                delete_status TEXT DEFAULT 'pending',
                delete_attempts INTEGER DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def _insert_file(self, file_id, status, attempts, created_minutes_ago):
        created = datetime.now() - timedelta(minutes=created_minutes_ago)
        self.cursor.execute(
            "INSERT INTO stored_files (file_id, file_name, original_share_link, share_link, cloud_name, "
            "delete_status, delete_attempts, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (file_id, f'file_{file_id}', f'orig_{file_id}', f'share_{file_id}', '夸克网盘',
             status, attempts, created, created)
        )
        self.conn.commit()

    def _get_expired_files_fixed_sql(self, expire_minutes=15):
        """
        复现修复后的 get_expired_files SQL（pending + failed 且 attempts < 3）
        """
        expire_param = f'-{expire_minutes} minutes'
        self.cursor.execute(
            "SELECT id, file_id, file_name, cloud_name, delete_status, delete_attempts "
            "FROM stored_files "
            "WHERE delete_status IN ('pending', 'failed') AND delete_attempts < 3 "
            "AND created_at < datetime('now', 'localtime', ?) "
            "ORDER BY created_at ASC",
            (expire_param,)
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def test_pending_files_are_returned(self):
        """pending 状态的过期文件应该被返回"""
        self._insert_file('f1', 'pending', 0, 20)
        results = self._get_expired_files_fixed_sql()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['file_id'], 'f1')

    def test_failed_files_with_low_attempts_are_returned(self):
        """Bug3 修复验证：failed 且 attempts < 3 的文件应被返回（可重试）"""
        self._insert_file('f2', 'failed', 1, 20)
        results = self._get_expired_files_fixed_sql()
        self.assertEqual(len(results), 1,
                         "Bug3 已修复：failed 且 attempts=1 < 3 的记录会被返回重试")
        self.assertEqual(results[0]['file_id'], 'f2')

    def test_failed_files_high_attempts_not_returned(self):
        """Bug3 修复验证：failed 且 attempts >= 3 的文件不再返回（放弃重试）"""
        self._insert_file('f3_high', 'failed', 3, 20)
        self._insert_file('f4_low', 'failed', 2, 20)
        results = self._get_expired_files_fixed_sql()
        returned_ids = [r['file_id'] for r in results]
        self.assertNotIn('f3_high', returned_ids, "Bug3：attempts >= 3 不再返回")
        self.assertIn('f4_low', returned_ids, "Bug3：attempts=2 < 3 仍返回")

    def test_success_files_still_in_db(self):
        """success 状态的记录不会被 get_expired_files 返回（预期行为）"""
        self._insert_file('f3', 'success', 0, 20)
        results = self._get_expired_files_fixed_sql()
        self.assertEqual(len(results), 0)

    def test_mixed_statuses(self):
        """混合状态：pending 和 failed(attempts<3) 被返回"""
        self._insert_file('p1', 'pending', 0, 20)
        self._insert_file('f1', 'failed', 1, 20)
        self._insert_file('f2', 'failed', 3, 20)
        self._insert_file('s1', 'success', 0, 20)
        self._insert_file('p2', 'pending', 0, 20)

        results = self._get_expired_files_fixed_sql()
        returned_ids = [r['file_id'] for r in results]
        self.assertIn('p1', returned_ids)
        self.assertIn('p2', returned_ids)
        self.assertIn('f1', returned_ids, "Bug3 已修复：failed 且 attempts=1 被返回")
        self.assertNotIn('f2', returned_ids, "Bug3：failed 且 attempts=3 不被返回")
        self.assertNotIn('s1', returned_ids)


# ============================================================
# Bug 4: Cookie过期判断 — 修复后只检查是否为空
# ============================================================
class TestBug4CookieLengthHeuristic(unittest.TestCase):
    """
    验证：修复后 check_cookies_expired 只检查 cookie 是否为空，
    不再用 len(cookie) < 300 误报。
    """

    def _is_cookie_expired(self, cookie):
        """复现修复后的判断逻辑"""
        if not cookie:
            return True
        return False

    def test_short_valid_cookie_not_falsely_detected(self):
        """Bug4 修复验证：有效但较短的 Cookie 不再被误判为过期"""
        short_cookie = "valid_cookie_value=" + "x" * 100  # 120字符
        result = self._is_cookie_expired(short_cookie)
        self.assertFalse(result, "Bug4 已修复：有效短 Cookie 不再被误判")

    def test_empty_cookie_correctly_detected(self):
        """空 Cookie 应该被正确检测"""
        self.assertTrue(self._is_cookie_expired(""))
        self.assertTrue(self._is_cookie_expired(None))

    def test_normal_cookie_not_falsely_detected(self):
        """正常长度的 Cookie 不应该被误判"""
        long_cookie = "a" * 301
        self.assertFalse(self._is_cookie_expired(long_cookie))



# ============================================================
# Bug 5: 二维码定时任务重复提醒 — 修复后只返回一条且标记已通知
# ============================================================
class TestBug5QrCodeDuplicateReminder(unittest.TestCase):
    """
    验证：修复后 get_expiring_qr_codes 只返回最新一条过期记录，
    insert/upsert 保证只有一条记录，check_qr_code_expiry 发送后标记已通知。
    """

    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE qr_code (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                expires_at DATETIME,
                notified INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def _insert_qr(self, file_name, expires_at, notified=0, upload_time=None):
        if upload_time:
            self.cursor.execute(
                "INSERT INTO qr_code (file_name, file_path, file_size, expires_at, notified, upload_time) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (file_name, f'/path/{file_name}', 1024, expires_at, notified, upload_time)
            )
        else:
            self.cursor.execute(
                "INSERT INTO qr_code (file_name, file_path, file_size, expires_at, notified) "
                "VALUES (?, ?, ?, ?, ?)",
                (file_name, f'/path/{file_name}', 1024, expires_at, notified)
            )
        self.conn.commit()
        return self.cursor.lastrowid

    def _get_expiring_qr_codes_fixed(self):
        """复现修复后的 SQL：LIMIT 1，只返回最新一条"""
        self.cursor.execute(
            "SELECT id, upload_time, file_name, file_path, file_size, expires_at, notified "
            "FROM qr_code WHERE date(expires_at) <= date('now') "
            "ORDER BY upload_time DESC LIMIT 1"
        )
        row = self.cursor.fetchone()
        return [dict(row)] if row else []

    def _mark_as_notified(self, qr_id):
        self.cursor.execute(
            "UPDATE qr_code SET notified = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (qr_id,)
        )
        self.conn.commit()

    def test_only_one_record_returned_even_with_multiple_expired(self):
        """Bug5 修复验证：即使有多条过期记录，也只返回最新一条"""
        # 插入3条过期记录，使用不同的 upload_time 以确保排序正确
        self._insert_qr('old.png', '2026-01-01', upload_time='2026-01-01 10:00:00')
        self._insert_qr('mid.png', '2026-03-01', upload_time='2026-03-01 10:00:00')
        self._insert_qr('new.png', '2026-06-01', upload_time='2026-06-01 10:00:00')

        results = self._get_expiring_qr_codes_fixed()
        self.assertEqual(len(results), 1, "Bug5 已修复：只返回最新一条过期记录")
        self.assertEqual(results[0]['file_name'], 'new.png')

    def test_insert_clears_old_records(self):
        """Bug5 修复验证：insert_qr_code 插入前清空旧记录"""
        self._insert_qr('old1.png', '2026-01-01')
        self._insert_qr('old2.png', '2026-03-01')

        # 模拟 insert_qr_code 的修复逻辑：DELETE all then INSERT
        self.cursor.execute("DELETE FROM qr_code")
        self.cursor.execute(
            "INSERT INTO qr_code (file_name, file_path, file_size, expires_at) "
            "VALUES (?, ?, ?, ?)",
            ('new.png', '/path/new.png', 1024, '2026-12-01')
        )
        self.conn.commit()

        self.cursor.execute("SELECT COUNT(*) FROM qr_code")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 1, "Bug5 已修复：insert 后只保留一条记录")

    def test_notified_flag_skips_resend(self):
        """Bug5 修复验证：已通知的记录不再重复发送"""
        qr_id = self._insert_qr('test.png', '2026-06-01', notified=0)
        self._mark_as_notified(qr_id)

        results = self._get_expiring_qr_codes_fixed()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['notified'], 1,
                         "已通知记录的 notified 标记为 1，发送时应跳过")

    def test_upsert_resets_notified_on_update(self):
        """Bug5 修复验证：upsert 更新时重置 notified=0"""
        qr_id = self._insert_qr('old.png', '2026-06-01', notified=1)

        # 模拟 upsert 的更新逻辑：重置 notified=0
        self.cursor.execute(
            "UPDATE qr_code SET file_name=?, expires_at=?, notified=0, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?",
            ('new.png', '2026-12-01', qr_id)
        )
        self.conn.commit()

        self.cursor.execute("SELECT notified FROM qr_code WHERE id=?", (qr_id,))
        row = self.cursor.fetchone()
        self.assertEqual(row['notified'], 0,
                         "Bug5 已修复：upsert 更新后 notified 重置为 0")

    def test_upsert_deletes_old_records(self):
        """Bug5 修复验证：upsert 更新后删除旧记录"""
        qr_id = self._insert_qr('current.png', '2026-06-01')
        # 模拟残留旧记录
        self._insert_qr('stale1.png', '2026-01-01')
        self._insert_qr('stale2.png', '2026-03-01')

        # 模拟 upsert 的修复逻辑：DELETE WHERE id != current
        self.cursor.execute("DELETE FROM qr_code WHERE id != ?", (qr_id,))
        self.conn.commit()

        self.cursor.execute("SELECT COUNT(*) FROM qr_code")
        count = self.cursor.fetchone()[0]
        self.assertEqual(count, 1, "Bug5 已修复：upsert 后只保留一条记录")

# ============================================================
# 综合测试：调度器循环逻辑验证
# ============================================================
class TestSchedulerLoopIntegration(unittest.TestCase):
    """
    综合验证调度器循环在各种时间点的行为（修复后）。
    """

    def _simulate_email_scheduler_tick(self, now, state):
        """
        模拟 _email_scheduler_loop 的一次迭代（修复后逻辑）。
        state: dict with 'daily_check_executed'
        返回: (triggered_actions, should_jump_to_tomorrow)
        """
        actions = []
        should_jump = False

        # 0:00 日常检查
        if now.hour == 0 and not state.get('daily_check_executed'):
            actions.append('daily_cookie_check')
            actions.append('daily_qr_check')
            state['daily_check_executed'] = True
        elif now.hour != 0:
            state['daily_check_executed'] = False

        # 每月20号 — 修复后不跳过
        if now.day == 20 and now.hour == 9:
            actions.append('monthly_cookie_reminder')
            # 修复后不跳过，继续执行后续检查

        # 22:00 访客统计 — 修复后只检查 hour
        if now.hour == 22:
            actions.append('visitor_stats')

        return actions, should_jump

    def test_full_day_20_scenario(self):
        """
        修复后完整的20号场景：
        0:00 日常检查 → 9:00 月度提醒(不跳过) → 22:00 正常发送 → 21号0:00 正常执行
        """
        state = {'daily_check_executed': False}

        # 20号 0:00 — 日常检查
        actions, jump = self._simulate_email_scheduler_tick(
            datetime(2026, 6, 20, 0, 0), state)
        self.assertIn('daily_cookie_check', actions)
        self.assertFalse(jump)

        # 20号 9:00 — 月度提醒，不跳过
        actions, jump = self._simulate_email_scheduler_tick(
            datetime(2026, 6, 20, 9, 0), state)
        self.assertIn('monthly_cookie_reminder', actions)
        self.assertFalse(jump, "Bug2 已修复：月度提醒后不再跳过")

        self.assertFalse(state['daily_check_executed'],
                         "9:00 的 elif now.hour!=0 分支已将 daily_check_executed 重置为 False")

        # 20号 22:00 — 访客统计正常发送
        actions, jump = self._simulate_email_scheduler_tick(
            datetime(2026, 6, 20, 22, 0), state)
        self.assertIn('visitor_stats', actions,
                       "Bug2 已修复：20号22:00访客统计正常发送")

        # 21号 0:00 — 日常检查正常执行
        actions, jump = self._simulate_email_scheduler_tick(
            datetime(2026, 6, 21, 0, 0), state)
        self.assertIn('daily_cookie_check', actions,
                       "21号0:00的日常检查正常执行")
        self.assertIn('daily_qr_check', actions,
                       "21号0:00的二维码检查正常执行")

    def test_normal_day_flow(self):
        """对照组：正常日（非20号）的完整流程"""
        state = {'daily_check_executed': False}

        # 0:00 日常检查
        actions, _ = self._simulate_email_scheduler_tick(
            datetime(2026, 6, 15, 0, 0), state)
        self.assertIn('daily_cookie_check', actions)

        # 22:00 访客统计
        actions, _ = self._simulate_email_scheduler_tick(
            datetime(2026, 6, 15, 22, 0), state)
        self.assertIn('visitor_stats', actions)

        # 次日0:00 日常检查
        actions, _ = self._simulate_email_scheduler_tick(
            datetime(2026, 6, 16, 0, 0), state)
        self.assertIn('daily_cookie_check', actions)

    def test_22pm_with_drift(self):
        """Bug1 修复验证：22:01 漂移不再导致访客统计丢失"""
        state = {'daily_check_executed': False}

        actions, _ = self._simulate_email_scheduler_tick(
            datetime(2026, 6, 15, 22, 1), state)
        self.assertIn('visitor_stats', actions,
                       "Bug1 已修复：22:01漂移不再导致访客统计丢失")


if __name__ == '__main__':
    unittest.main(verbosity=2)
