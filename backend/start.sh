#!/bin/bash

# AI Kitchen Assistant 启动脚本

echo "==================================="
echo "  AI Kitchen Assistant 启动脚本"
echo "==================================="

# 检查 Python 虚拟环境
if [ ! -d "venv" ]; then
    echo "正在创建虚拟环境..."
    python -m venv venv
fi

# 激活虚拟环境
echo "正在激活虚拟环境..."
source venv/bin/activate 2>/dev/null || .\venv\Scripts\activate

# 安装依赖
echo "正在安装依赖..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 复制环境配置文件
if [ ! -f ".env" ]; then
    echo "正在创建环境配置文件..."
    cp .env.example .env
    echo "请根据需要修改 .env 文件中的配置"
fi

# 初始化数据库和种子数据
echo "正在初始化数据库..."
python -c "
import sys
sys.path.insert(0, '.')
from app.db.database import init_db
init_db()
print('数据库表创建完成')
"

# 运行种子数据初始化
echo "正在初始化种子数据..."
python scripts/init_seed_data.py

echo ""
echo "==================================="
echo "  启动开发服务器"
echo "==================================="
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
