#!/bin/bash
# AI Kitchen Assistant —— 群晖 NAS 一键更新脚本
#
# 更新流程（贴合"镜像最小、代码挂载"的设计）：
#   1. 拉取/同步最新代码到仓库根目录
#   2. docker compose up -d 确保容器在运行
#   3. 重启后端容器，让挂载的新代码生效（前端静态文件 nginx 自动读取，无需重启）
#
# 用法：在仓库根目录下执行  bash deploy/update.sh
#       若群晖 docker 需要 sudo：把下面 COMPOSE 变量改成 sudo docker compose ...
set -e
cd "$(dirname "$0")/.."     # 切到仓库根目录（docker-compose.yml 所在处）
COMPOSE="docker compose"

echo "==================== AI Kitchen 更新 ===================="

# 1. 拉取最新代码（NAS 上 git clone 过仓库时有效）
#    如果你用 SMB/文件传输上传代码，这步会自动跳过
if [ -d .git ]; then
    echo ">> 拉取最新代码..."
    git pull --ff-only || echo "   (git pull 失败，跳过 —— 可能用的是文件上传方式)"
else
    echo ">> 未检测到 git 仓库，跳过拉取（请确认代码已上传到当前目录）"
fi

# 2. 确保容器按最新 compose 配置在运行
echo ">> 启动/更新容器..."
$COMPOSE up -d

# 3. 重启后端，让挂载的新代码生效
echo ">> 重启后端容器..."
$COMPOSE restart backend

echo ""
echo "========================================================="
echo "  ✅ 更新完成"
echo ""
echo "  前端：静态文件由 nginx 直接读取，新上传的 dist 自动生效"
echo "  后端：已重启，挂载的新代码已加载"
echo ""
echo "  💡 requirements.txt 有改动时无需手动处理："
echo "     本次重启后端时入口脚本会比对哈希并自动重新安装依赖"
echo "========================================================="
