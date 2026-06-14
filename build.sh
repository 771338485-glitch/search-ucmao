#!/bin/bash

# 打包脚本，用于宝塔面板部署

echo "开始打包应用..."

# 确保脚本在项目根目录执行
cd "$(dirname "$0")"

# 导出依赖
echo "导出依赖到 requirements.txt..."
pip freeze > requirements.txt

# 创建打包目录
BUILD_DIR="build"
mkdir -p "$BUILD_DIR"

# 复制必要文件
echo "复制项目文件..."
cp -r app.py "$BUILD_DIR/"
cp -r routes/ "$BUILD_DIR/routes/"
cp -r src/ "$BUILD_DIR/src/"
cp -r static/ "$BUILD_DIR/static/"
cp -r templates/ "$BUILD_DIR/templates/"
cp -r configs/ "$BUILD_DIR/configs/"
cp -r utils/ "$BUILD_DIR/utils/"
cp -r clients/ "$BUILD_DIR/clients/"
cp -r data/ "$BUILD_DIR/data/"
cp -r seedhub_images/ "$BUILD_DIR/seedhub_images/"
cp requirements.txt "$BUILD_DIR/"
cp .env "$BUILD_DIR/"
cp compress_static.py "$BUILD_DIR/"

# 创建启动脚本
echo "创建启动脚本..."
cat > "$BUILD_DIR/start.sh" << 'EOF'
#!/bin/bash

# 启动脚本

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "创建虚拟环境失败，请检查Python是否正确安装"
        exit 1
    fi
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "激活虚拟环境失败"
    exit 1
fi

# 安装依赖
echo "安装依赖..."
# 使用完整路径的pip
VENV_PIP="$(pwd)/venv/bin/pip"
if [ ! -f "$VENV_PIP" ]; then
    echo "pip命令不存在，请检查虚拟环境是否正确创建"
    exit 1
fi

echo "升级pip..."
"$VENV_PIP" install --upgrade pip
if [ $? -ne 0 ]; then
    echo "升级pip失败"
    exit 1
fi

echo "安装requirements.txt中的依赖..."
"$VENV_PIP" install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "安装依赖失败"
    exit 1
fi

# 确保安装Flask-Compress
echo "确保安装Flask-Compress..."
"$VENV_PIP" install Flask-Compress
if [ $? -ne 0 ]; then
    echo "安装Flask-Compress失败"
    exit 1
fi

# 压缩静态文件
echo "压缩静态文件..."
# 检查python3是否可用
if command -v python3 &> /dev/null; then
    echo "使用 python3 压缩静态文件"
    python3 compress_static.py
elif command -v python &> /dev/null; then
    echo "使用 python 压缩静态文件"
    python compress_static.py
else
    echo "错误: 未找到 python 或 python3 命令"
    exit 1
fi

# 启动应用
echo "启动应用..."
# 默认端口为5004，可通过命令行参数修改
PORT=${1:-5004}
echo "使用端口: $PORT"

# 检查python3是否可用
if command -v python3 &> /dev/null; then
    echo "使用 python3 启动应用"
    python3 app.py --port $PORT
elif command -v python &> /dev/null; then
    echo "使用 python 启动应用"
    python app.py --port $PORT
else
    echo "错误: 未找到 python 或 python3 命令"
    exit 1
fi
EOF

chmod +x "$BUILD_DIR/start.sh"

# 打包成zip文件
echo "打包成zip文件..."
ZIP_FILE="search-ucmao-$(date +%Y%m%d).zip"
cd "$BUILD_DIR"
zip -r "../$ZIP_FILE" .
cd ..

# 清理临时目录
echo "清理临时目录..."
rm -rf "$BUILD_DIR"

echo "打包完成！"
echo "打包文件：$ZIP_FILE"
echo "使用方法："
echo "1. 在宝塔面板中创建网站"
echo "2. 上传 $ZIP_FILE 并解压"
echo "3. 执行 start.sh 脚本启动应用"
echo "4. 配置反向代理指向 127.0.0.1:5004"
