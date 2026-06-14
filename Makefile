# ============================================
# 桃白白影视 - Makefile
# ============================================
# 使用方法: make [target]

.PHONY: help build up down restart logs shell db-shell backup restore clean prune

# 默认显示帮助
help:
	@echo "============================================"
	@echo "桃白白影视 - Docker 管理工具"
	@echo "============================================"
	@echo ""
	@echo "常用命令:"
	@echo "  make up         - 启动所有服务"
	@echo "  make down       - 停止所有服务"
	@echo "  make restart    - 重启所有服务"
	@echo "  make logs       - 查看所有服务日志"
	@echo "  make shell      - 进入 Web 应用容器"
	@echo "  make db-shell   - 进入 MySQL 容器"
	@echo "  make build      - 重新构建镜像"
	@echo "  make backup     - 备份数据库"
	@echo "  make restore    - 恢复数据库"
	@echo "  make clean      - 清理未使用的资源"
	@echo ""
	@echo "开发环境:"
	@echo "  make dev-up     - 启动开发环境"
	@echo "  make dev-down   - 停止开发环境"
	@echo ""
	@echo "生产环境:"
	@echo "  make prod-up    - 启动生产环境"
	@echo "  make prod-down  - 停止生产环境"
	@echo ""

# 构建镜像
build:
	@echo "构建 Docker 镜像..."
	docker-compose build

# 启动服务
up:
	@echo "启动所有服务..."
	docker-compose up -d

# 停止服务
down:
	@echo "停止所有服务..."
	docker-compose down

# 重启服务
restart:
	@echo "重启所有服务..."
	docker-compose restart

# 查看日志
logs:
	@echo "查看服务日志 (Ctrl+C 退出)..."
	docker-compose logs -f

# 查看特定服务日志
logs-web:
	@echo "查看 Web 应用日志 (Ctrl+C 退出)..."
	docker-compose logs -f web

logs-db:
	@echo "查看数据库日志 (Ctrl+C 退出)..."
	docker-compose logs -f db

# 进入 Web 应用容器
shell:
	@echo "进入 Web 应用容器..."
	docker-compose exec web bash

# 进入 MySQL 容器
db-shell:
	@echo "进入 MySQL 容器..."
	docker-compose exec db bash

# 连接 MySQL
mysql:
	@echo "连接 MySQL 数据库..."
	docker-compose exec db mysql -u $$(grep DB_USER .env | cut -d '=' -f2) -p$$(grep DB_PASSWORD .env | cut -d '=' -f2) $$(grep DB_DATABASE .env | cut -d '=' -f2)

# 备份数据库
backup:
	@echo "备份数据库..."
	@mkdir -p backups
	@DATE=$$(date +%Y%m%d_%H%M%S); \
	docker-compose exec db mysqldump -u $$(grep DB_USER .env | cut -d '=' -f2) -p$$(grep DB_PASSWORD .env | cut -d '=' -f2) $$(grep DB_DATABASE .env | cut -d '=' -f2) > backups/backup_$$DATE.sql
	@echo "数据库已备份到: backups/backup_$$DATE.sql"

# 恢复数据库（需要提供备份文件名）
restore:
	@if [ -z "$(file)" ]; then \
		echo "请指定备份文件: make restore file=backups/backup_20240101_120000.sql"; \
	else \
		echo "恢复数据库从: $(file)"; \
		docker-compose exec -T db mysql -u $$(grep DB_USER .env | cut -d '=' -f2) -p$$(grep DB_PASSWORD .env | cut -d '=' -f2) $$(grep DB_DATABASE .env | cut -d '=' -f2) < $(file); \
		echo "数据库恢复完成"; \
	fi

# 清理未使用的 Docker 资源
clean:
	@echo "清理未使用的 Docker 资源..."
	docker system prune -f

# 完全清理（谨慎使用！）
prune:
	@echo "警告: 这将删除所有未使用的镜像、容器、卷和网络！"
	@read -p "确认继续? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker system prune -a -f --volumes; \
		echo "清理完成"; \
	else \
		echo "已取消"; \
	fi

# 开发环境
dev-up:
	@echo "启动开发环境..."
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

dev-down:
	@echo "停止开发环境..."
	docker-compose -f docker-compose.yml -f docker-compose.override.yml down

dev-logs:
	@echo "查看开发环境日志..."
	docker-compose -f docker-compose.yml -f docker-compose.override.yml logs -f

# 生产环境
prod-up:
	@echo "启动生产环境..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	@echo "停止生产环境..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-logs:
	@echo "查看生产环境日志..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# 查看服务状态
status:
	@echo "查看服务状态..."
	docker-compose ps

# 健康检查
health:
	@echo "检查服务健康状态..."
	docker-compose ps --format json | jq '.[] | select(.State=="running") | .Name'
