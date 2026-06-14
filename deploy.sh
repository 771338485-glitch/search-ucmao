#!/bin/bash

# ============================================
# 桃白白影视 - 一键部署脚本
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  桃白白影视 - 一键部署脚本${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker 和 Docker Compose 已安装${NC}"
echo ""

# 检查 .env 文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env 文件不存在，正在创建...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ 已从 .env.example 创建 .env 文件${NC}"
        echo ""
        echo -e "${YELLOW}请编辑 .env 文件，填入您的配置:${NC}"
        echo "  - SECRET_KEY: JWT签名密钥"
        echo "  - DB_PASSWORD: 数据库密码"
        echo "  - ADMIN_PASSWORD: 管理员密码"
        echo ""
        read -p "编辑完成后按 Enter 继续..."
    else
        echo -e "${RED}错误: .env.example 文件也不存在${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env 文件已存在${NC}"
fi

echo ""

# 检查是否需要重新构建
read -p "是否需要重新构建 Docker 镜像? (y/N): " rebuild
if [ "$rebuild" = "y" ] || [ "$rebuild" = "Y" ]; then
    echo -e "${BLUE}正在构建 Docker 镜像...${NC}"
    docker-compose build
fi

echo ""
echo -e "${BLUE}正在启动服务...${NC}"
docker-compose up -d

echo ""
echo -e "${BLUE}等待服务启动...${NC}"
sleep 10

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}服务状态:${NC}"
docker-compose ps
echo ""
echo -e "${BLUE}访问地址:${NC}"
echo "  - 应用首页: http://localhost:5004"
echo "  - 管理后台: http://localhost:5004/admin"
echo ""
echo -e "${BLUE}常用命令:${NC}"
echo "  make logs       - 查看日志"
echo "  make restart    - 重启服务"
echo "  make down       - 停止服务"
echo "  make backup     - 备份数据库"
echo ""
echo -e "${YELLOW}提示: 首次启动可能需要等待数据库初始化完成${NC}"
echo -e "${YELLOW}如需查看详细日志，请运行: make logs${NC}"
echo ""
