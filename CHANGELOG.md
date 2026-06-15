# Changelog

## [1.2.0] - 2026-06-15

### Bug Fix: 删除分享后stored_files缓存记录未清理

**问题描述**: 删除转存后的分享链接时，del_share只删除了百度网盘文件和resources表记录，stored_files表缓存未清理，再次转存同一链接返回旧链接。

**修复**:
1. stored_files_dao.py - 新增 delete_stored_file_by_original_link()
2. pan_operator.py - del_share() 中调用缓存清理

### 过期清理时间从15分钟改为5分钟

**改动**:
1. cleanup_scheduler.py - 过期时间和检查间隔改为5分钟
2. app.py - 更新 start_scheduler 参数

### Bug Fix: SQLite时区比较Bug导致定时清理失效

**问题描述**: created_at存本地时间，SQL用UTC时间比较，时区差8小时导致清理条件永远为False。

**修复**: stored_files_dao.py - SQL改用 datetime('now', 'localtime', ?)
## [1.1.0] - 2026-06-15

### Bug Fix: 百度网盘转存成功但未返回分享链接

**问题描述**: 百度网盘转存操作执行成功（文件出现在网盘中），但系统没有返回转存后的分享链接。

**根因分析**: `.env` 中 `DEFAULT_SAVE_DIR=桃白白影视` 缺少前导 `/`，导致链路中路径格式不一致：
- `_get_or_create_dir` 内部拼接时加了 `/` -> 目录创建在 `/桃白白影视`（正确）
- `_transfer_file` 发送给百度 API 的 `path` 是 `桃白白影视`（相对路径，错误）
- 百度 API 要求绝对路径 -> 返回 `errno: 2, '转存路径不存在'`

**修复内容**:
1. `src/clients/baidu_client.py` - `store()` 方法：确保 `full_path` 以 `/` 开头
2. `src/clients/baidu_client.py` - `_transfer_file()` 方法：确保 `to_path` 以 `/` 开头
3. `src/pan_operator.py` - `sync_create_share()` 函数：确保从 `.env` 读取的 `DEFAULT_SAVE_DIR` 以 `/` 开头

**验证结果**: API 调用 `/api/wash` 返回 `"success": true`，新分享链接成功生成。
- 原始链接: `https://pan.baidu.com/s/1yXPuFIltZS2YR5V88LASTw?pwd=c819`
- 新链接: `https://pan.baidu.com/s/1YR_C28mg6lGID66OJyxPNg?pwd=nmad`
- 文件路径: `/桃白白影视/一人之下 第1季`

### 其他改动
- 增强百度网盘目录创建和 bdstoken 获取的日志输出
- 新增 `_check_dir_exists` 方法，避免重复创建目录
