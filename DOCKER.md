# 🐳 桃白白影视 - Docker 部署指南

本指南将帮助您使用 Docker 和 Docker Compose 快速部署桃白白影视系统。

## 📋 前置要求

- Docker (版本 20.10 或更高)
- Docker Compose (版本 2.0 或更高)
- 至少 2GB 可用内存
- 至少 10GB 可用磁盘空间

## 🚀 快速开始

### 1. 准备环境配置文件

```bash
# 复制环境配置示例文件
cp .env.example .env

# 编辑 .env 文件，填入您的实际配置
# 特别是 SECRET_KEY 和数据库密码
nano .env
```

### 2. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 或者，如果您修改了 Dockerfile，需要重新构建
docker-compose up -d --build
```

### 3. 查看服务状态

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看特定服务的日志
docker-compose logs -f web
docker-compose logs -f db
```

### 4. 访问应用

启动成功后，您可以通过以下地址访问：

- **应用首页**: http://localhost:5004
- **管理后台**: http://localhost:5004/admin

默认管理员账号（请在 .env 中修改）：
- 用户名: `admin`
- 密码: `admin123`

## 📁 服务说明

### 1. 数据库服务 (db)

- **镜像**: MySQL 8.0
- **端口**: 3306 (可从宿主机访问)
- **数据卷**: `search-ucmao-mysql-data` (持久化存储)
- **自动初始化**: 首次启动时会自动执行 `schema.sql` 创建表结构

### 2. Web 应用服务 (web)

- **镜像**: 基于 Python 3.9 构建
- **端口**: 5004
- **WSGI 服务器**: Gunicorn (4 个 worker)
- **健康检查**: 每 30 秒检查一次
- **数据卷**: 
  - `search-ucmao-app-logs`: 日志存储
  - `./static/images`: 图片存储 (可读写)

### 3. Nginx 反向代理 (可选)

在 `docker-compose.yml` 中已注释掉 Nginx 服务配置。如需使用：

1. 取消 `docker-compose.yml` 中 nginx 服务的注释
2. 配置 SSL 证书（如需要 HTTPS）
3. 重新启动服务

## 🔧 常用命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose stop

# 重启所有服务
docker-compose restart

# 停止并删除所有容器（保留数据卷）
docker-compose down

# 停止并删除所有容器和数据卷（谨慎使用！）
docker-compose down -v
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f web
docker-compose logs -f db

# 查看最近 100 行日志
docker-compose logs --tail=100 web
```

### 进入容器

```bash
# 进入 Web 应用容器
docker-compose exec web bash

# 进入 MySQL 容器
docker-compose exec db bash

# 直接连接 MySQL
docker-compose exec db mysql -u root -p
```

### 数据备份

```bash
# 备份数据库
docker-compose exec db mysqldump -u root -p ucmao_search > backup.sql

# 恢复数据库
docker-compose exec -T db mysql -u root -p ucmao_search < backup.sql

# 备份数据卷
docker run --rm -v search-ucmao-mysql-data:/data -v $(pwd):/backup alpine tar czf /backup/mysql-backup.tar.gz /data
```

## 🔐 安全建议

1. **修改默认密码**
   - 修改 .env 中的 `SECRET_KEY` 为随机字符串
   - 修改数据库密码
   - 修改管理员密码

2. **使用 HTTPS**
   - 配置 SSL 证书
   - 启用 Nginx 的 HTTPS 配置

3. **限制端口访问**
   - 不要将 MySQL 端口暴露到公网
   - 使用防火墙规则限制访问

4. **定期备份**
   - 定期备份数据库
   - 备份重要数据卷

## 🐛 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker-compose logs

# 检查服务状态
docker-compose ps

# 重新构建并启动
docker-compose up -d --build
```

### 数据库连接失败

```bash
# 检查数据库容器状态
docker-compose ps db

# 查看数据库日志
docker-compose logs db

# 等待数据库完全启动
sleep 30
```

### 应用访问被拒绝

```bash
# 检查端口是否被占用
netstat -tulpn | grep 5004

# 检查防火墙规则
sudo ufw status

# 查看应用日志
docker-compose logs web
```

## 📚 进阶配置

### 使用自定义域名

1. 在 `nginx.conf` 中修改 `server_name`
2. 配置 DNS 解析
3. 申请 SSL 证书（推荐使用 Let's Encrypt）

### 性能优化

1. 调整 Gunicorn worker 数量：
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:5004", "--workers", "8", ...]
   ```

2. 配置 Redis 缓存（需要额外添加 Redis 服务）

3. 使用 CDN 加速静态资源

### 监控和告警

1. 添加 Prometheus + Grafana 监控
2. 配置日志收集（ELK Stack）
3. 设置健康检查告警

## 📞 技术支持

如遇到问题，请：

1. 查看 [项目 README](README.md)
2. 检查 [GitHub Issues](https://github.com/ucmao/search-ucmao/issues)
3. 联系作者获取帮助

---

**祝您使用愉快！** 🎉
