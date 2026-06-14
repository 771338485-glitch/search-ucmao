#!/bin/bash

# 项目打包脚本
# 排除不需要的文件，创建干净的部署包

PROJECT_NAME="search-ucmao"
VERSION=$(date +%Y%m%d)
OUTPUT_FILE="${PROJECT_NAME}-${VERSION}.tar.gz"

echo "====================================="
echo "开始打包项目..."
echo "项目名称: ${PROJECT_NAME}"
echo "版本: ${VERSION}"
echo "====================================="

# 删除旧的打包文件
rm -f ${PROJECT_NAME}-*.tar.gz ${PROJECT_NAME}-*.zip

echo ""
echo "正在打包..."

# 使用 tar 打包，排除不需要的文件
tar -czf ${OUTPUT_FILE} \
  --exclude='.git' \
  --exclude='.gitignore' \
  --exclude='.DS_Store' \
  --exclude='.real' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.pyd' \
  --exclude='*.so' \
  --exclude='*.egg-info' \
  --exclude='app.db' \
  --exclude='data.db' \
  --exclude='database.db' \
  --exclude='search.db' \
  --exclude='app.log' \
  --exclude='logs/' \
  --exclude='seedhub_images/' \
  --exclude='movie_images/' \
  --exclude='static/images/douban_cache/' \
  --exclude='tests/' \
  --exclude='test_*.py' \
  --exclude='test_*.html' \
  --exclude='test_*.js' \
  --exclude='crawl_*.py' \
  --exclude='check_*.py' \
  --exclude='download_*.py' \
  --exclude='update_*.py' \
  --exclude='parse_*.py' \
  --exclude='compress_*.py' \
  --exclude='init_sqlite.py' \
  --exclude='douban_chart.html' \
  --exclude='full_response.html' \
  --exclude='simple_index.html' \
  --exclude='test.html' \
  --exclude='cookies.txt' \
  --exclude='nginx.conf' \
  --exclude='Makefile' \
  --exclude='build.sh' \
  --exclude='deploy.sh' \
  --exclude='DOCKER.md' \
  --exclude='*.tar.gz' \
  --exclude='*.zip' \
  .

if [ $? -eq 0 ]; then
  echo ""
  echo "====================================="
  echo "✅ 打包成功！"
  echo "输出文件: ${OUTPUT_FILE}"
  echo "文件大小: $(du -h ${OUTPUT_FILE} | cut -f1)"
  echo "====================================="
  echo ""
  echo "文件列表:"
  tar -tzf ${OUTPUT_FILE} | head -30
  echo "... (更多文件)"
else
  echo ""
  echo "❌ 打包失败！"
  exit 1
fi
