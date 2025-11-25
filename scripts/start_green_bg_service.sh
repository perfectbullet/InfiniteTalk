#!/bin/bash
# 启动绿色背景去除服务的脚本

cd "$(dirname "$0")/.." || exit 1

# 检查 Python 虚拟环境
if [ ! -d ".venv" ]; then
    echo "错误: 找不到虚拟环境 .venv"
    echo "请先运行: uv venv .venv"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖是否安装
if ! python -c "import fastapi" 2>/dev/null; then
    echo "正在安装依赖..."
    uv pip install -r green_bg_removal_service/requirements.txt
fi

# 启动服务
echo "正在启动绿色背景去除服务..."
uvicorn green_bg_removal_service.app:app --host 0.0.0.0 --port 8000 --reload
