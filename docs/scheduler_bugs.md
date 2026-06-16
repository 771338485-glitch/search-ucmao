# 定时任务 Bug 记录

## Bug 1 (HIGH) - 22:00访客统计 minute==0 检查过于严格

- **文件**: `src/scheduler/email_scheduler.py` 约第245行
- **问题**: `if now.hour == 22 and now.minute == 0` 条件过于严格。调度器每小时唤醒一次，但线程漂移可能导致唤醒时 `minute>0`，此时访客统计邮件当天漏发。
- **修复**: 去掉 `now.minute == 0`，改为 `if now.hour == 22:`
- **验证**: `TestBug1VisitorStatsMinuteCheck` - 22:01、22:05 唤醒均能正常发送

## Bug 2 (MEDIUM) - 每月20号Cookie提醒后跳过22:00访客统计

- **文件**: `src/scheduler/email_scheduler.py` 约第238-253行
- **问题**: 每月20号9点发送Cookie提醒邮件后，代码执行 `wait→continue` 跳到明天，导致当天22:00的访客统计邮件被跳过。
- **修复**: 月度提醒只发送邮件，不再 `wait→continue`，让循环自然继续到22:00发送访客统计。
- **验证**: `TestBug2MonthlyReminderSkipsNextTasks` - 20号22:00访客统计不再被跳过

## Bug 3 (MEDIUM) - 失败的文件删除记录永不重试、永不清理

- **文件**: `src/db/stored_files_dao.py` 约第118-130行
- **问题**: `get_expired_files` 的 SQL 只查询 `delete_status='pending'`，删除失败变成 `'failed'` 后永远不会被重试，也不会被清理，导致 failed 记录无限累积。
- **修复**: SQL 改为 `WHERE delete_status IN ('pending', 'failed') AND delete_attempts < 3`，failed 记录在重试次数 <3 时会被重新查询和重试。
- **验证**: `TestBug3FailedFilesNeverRetry` - failed 且 attempts<3 的记录可被查询，attempts>=3 的不再返回

## Bug 4 (LOW) - Cookie长度<300硬编码判断误报

- **文件**: `src/scheduler/email_scheduler.py` 约第73-80行
- **问题**: `check_cookies_expired` 使用 `len(cookie) < 300` 判断是否过期，这个硬编码启发式可能将有效的短 Cookie 误判为过期。
- **修复**: 去掉 `len(cookie) < 300` 检查，改为只判断 `if not cookie:`（是否为空）。
- **验证**: `TestBug4CookieLengthHeuristic` - 120字符的有效 Cookie 不再被误判

## Bug 5 (MEDIUM) - 二维码定时任务重复提醒

- **文件**: `src/db/qr_code_dao.py`, `src/scheduler/email_scheduler.py`
- **问题**: 每天 0 点定时任务发送多封二维码到期提醒邮件。`qr_code` 表残留多条历史记录，`get_expiring_qr_codes()` 返回所有过期记录，且 `check_qr_code_expiry()` 从不调用 `mark_as_notified()`。
- **修复**:
  - `qr_code_dao.py` - `get_expiring_qr_codes()` 加 `ORDER BY upload_time DESC LIMIT 1` 只返回最新一条
  - `qr_code_dao.py` - `insert_qr_code()` 插入前清空旧记录
  - `qr_code_dao.py` - `upsert_qr_code()` 更新后删除旧记录
  - `email_scheduler.py` - `check_qr_code_expiry()` 发送后调用 `mark_as_notified()`，已通知跳过
- **验证**: 首次插入/再次上传/连续上传均只有 1 条记录；过期只返回 1 条；通知后标记已通知不重复发

---

## 测试文件

`tests/test_scheduler_bugs.py` - 23个测试用例，覆盖所有5个 Bug 的修复验证。

运行测试：
```bash
cd /Users/zhao/项目/网盘/search-ucmao && python3 -m unittest tests.test_scheduler_bugs -v
```

## 修复状态

| Bug | 严重程度 | 状态 | 修复文件 |
|-----|---------|------|---------|
| Bug 1 - minute==0 检查 | HIGH | ✅ 已修复 | email_scheduler.py |
| Bug 2 - 月度提醒跳过后续任务 | MEDIUM | ✅ 已修复 | email_scheduler.py |
| Bug 3 - failed 记录永不重试 | MEDIUM | ✅ 已修复 | stored_files_dao.py |
| Bug 4 - Cookie长度误判 | LOW | ✅ 已修复 | email_scheduler.py |
| Bug 5 - 二维码重复提醒 | MEDIUM | ✅ 已修复 | qr_code_dao.py, email_scheduler.py |
