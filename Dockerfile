# 基于 Python 3.9 Slim 基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖（cryptography 需要 libssl-dev）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app

# 创建必需的目录
RUN mkdir -p data logs static/images

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.prod.txt

# 设置环境变量
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 5004

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5004/ || exit 1

# 启动应用（用 Flask 开发服务器，简单稳定）
CMD ["python", "app.py", "--port", "5004"]