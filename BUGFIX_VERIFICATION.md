# 夸克洗白全流程 Bug 修复与验证报告

**日期**: 2026-06-16
**测试分享链接**: `https://pan.quark.cn/s/c68eac63178b` (I.Wish.You.All.The.Best.2024)

---

## 修复清单

### Bug A: 裸 `requests.request()` 绕过代理设置
- **文件**: `src/clients/quark_client.py`
- **问题**: `detail()`, `save_task_id()`, `share_task_id()` 三处使用裸 `requests.request()` 而非 `self.session`，导致 `trust_env=False` 设置失效。当系统运行 Clash 等代理时，裸调用走代理导致连接失败。
- **修复**: 全部改为 `self.session.get()` / `self.session.post()`

### Bug B: `task()` 轮询无间隔
- **文件**: `src/clients/quark_client.py`
- **问题**: 转存/分享任务轮询 10 次重试之间没有 `sleep`，请求过快错过任务完成窗口（转存通常需 1-2 秒）。
- **修复**: 在 `except` 块后加入 `time.sleep(0.5)`

### Bug 1: 过期清理重试机制失效
- **文件**: `src/db/stored_files_dao.py` → `get_expired_files()`
- **问题**: SQL 只查 `delete_status='pending'` 的记录。一旦删除失败标记为 `failed`，永远不会被重试，形成僵尸记录。
- **修复**: SQL 条件改为 `delete_status IN ('pending', 'failed') AND delete_attempts < 3`
- **验证**: 插入 `failed` 状态 + `delete_attempts=1` 的记录，确认 `get_expired_files()` 能找到它。

### Bug 2: `clean_taobai_files_by_time()` 系列死代码
- **文件**: `src/scheduler/cleanup_scheduler.py`
- **问题**: `clean_taobai_files_by_time()`, `start_taobai_scheduler()`, `_taobai_scheduler_loop()`, `stop_taobai_scheduler()` 四个函数依赖文件名时间戳 `_YYYYMMDDHHMMSS.ext` 匹配清理，但 `store()` 早已不加时间戳。这些函数从未实际清理过文件。
- **修复**: 删除全部 4 个函数及相关全局变量，从 `start_scheduler()` 中移除 `start_taobai_scheduler()` 调用，从 `stop_scheduler()` 中移除 `stop_taobai_scheduler()` 调用。
- **代码变更**: -168 行

### Bug 3: `get_quota()` 返回 404
- **文件**: `src/clients/quark_client.py`, `routes/hot_resource_routes.py`
- **问题**: 夸克配额 API `https://drive-pc.quark.cn/1/clouddrive/capacity` 返回 404，导致 Cookie 验证和空间查询功能完全失效。
- **修复**:
  - Cookie 保存验证 (`save_cookie_config`): 改用 `get_all_file()` 验证 Cookie 有效性
  - 空间查询接口 (`/api/quota`): 夸克网盘改用 `get_all_file()` 返回文件数，百度网盘保持 `get_quota()` 不变

---

## E2E 验证结果 (12/12 通过)

| # | 测试项 | 结果 |
|---|--------|------|
| 1 | Cookie 从 DB 读取 | PASS |
| 2 | `get_all_file()` Cookie 有效性验证 | PASS (14 文件) |
| 3 | `get_stoken()` 获取分享 token | PASS |
| 4 | `detail()` 获取分享详情 | PASS |
| 5 | `store()` 转存到桃白白影视 | PASS |
| 6 | `insert_stored_file()` DB 写入 | PASS |
| 7 | `get_washed_link_by_original()` DB 查询 | PASS |
| 8 | `get_expired_files()` 识别 failed 记录 (Bug 1) | PASS |
| 9 | `del_file()` 网盘文件删除 | PASS |
| 10 | `delete_stored_file_by_original_link()` DB 清理 | PASS |
| 11 | 文件完全从 DB 清除 | PASS |
| 12 | 死代码已移除 (Bug 2) | PASS |

---

## DB 清理

- 清理了 18 条 `delete_status='failed'` 的僵尸 `stored_files` 记录
- 清理后 `stored_files` 表: 0 条记录

---

## 变更文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/clients/quark_client.py` | 修复 | 3 处裸 requests 改为 session 调用；task() 加 sleep |
| `src/db/stored_files_dao.py` | 修复 | `get_expired_files()` SQL 条件扩展 |
| `src/scheduler/cleanup_scheduler.py` | 修复 | 删除 4 个死代码函数 (-168 行) |
| `routes/hot_resource_routes.py` | 修复 | Cookie 验证和配额查询改用 get_all_file() |
| `src/db/qr_code_dao.py` | 修复 | 单记录保证 + 过期查询只返回最新一条 |
| `src/scheduler/email_scheduler.py` | 修复 | 二维码通知发完标记已通知，不重复发 |

---

## 二维码定时任务重复提醒修复 (Bug 4)

### 问题
每天 0 点定时任务会发送多封二维码到期提醒邮件。

### 根因
1. `get_expiring_qr_codes()` 查 `WHERE date(expires_at) <= date('now')` 返回**所有**过期记录（包括历史旧记录）
2. `check_qr_code_expiry()` **从不调用** `mark_as_notified()`，注释写"每天都提醒"
3. `upsert_qr_code()` 只更新最新记录，旧记录永远残留

### 修复
- `src/db/qr_code_dao.py`:
  - `get_expiring_qr_codes()`: 加 `ORDER BY upload_time DESC LIMIT 1`，只返回最新一条
  - `insert_qr_code()`: 插入前执行 `DELETE FROM qr_code` 清空旧记录
  - `upsert_qr_code()`: 更新后执行 `DELETE FROM qr_code WHERE id != %s` 清理旧记录
- `src/scheduler/email_scheduler.py`:
  - `check_qr_code_expiry()`: 增加 `notified` 检查，已通知的跳过
  - 发送成功后调用 `mark_as_notified()` 标记已通知

### 验证结果
| # | 测试项 | 结果 |
|---|--------|------|
| 1 | 首次插入，记录数 1 | PASS |
| 2 | 再次上传覆盖更新，记录数 1 | PASS |
| 3 | 连续上传 3 次，记录数始终 1 | PASS |
| 4 | 过期只返回 1 条，标记 notified 后不重复发 | PASS |
| 5 | 上传新二维码重置 notified=0 | PASS |

---

## 已知限制

- 夸克配额 API (`/clouddrive/capacity`) 当前返回 404，空间使用量无法显示，仅显示文件数
- `clean_old_files()` 内部依赖 `get_quota()` 判断空间使用率，因 API 失效将永远返回 "无需清理"
