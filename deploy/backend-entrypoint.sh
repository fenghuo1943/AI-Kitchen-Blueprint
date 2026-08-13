#!/bin/bash
# 后端容器入口脚本
#
# 设计：镜像只含基础 python，依赖在容器运行时安装。
#   - 每次启动对比 requirements.txt 的内容哈希与上次安装记录：
#       * 哈希不同（含首次启动、requirements 有更新）→ 自动 pip install，并更新记录
#       * 哈希相同 → 跳过安装，快速启动
#   - 安装记录存在挂载目录 /app/data 下（gitignore 过的数据目录），容器重建也不会丢
set -e

REQ=/app/requirements.txt
STAMP=/app/data/.requirements.sha256

# 当前 requirements.txt 的哈希
CURRENT=$(sha256sum "$REQ" | awk '{print $1}')
# 上次安装成功时记录的哈希（首次启动时不存在）
PREV=$(cat "$STAMP" 2>/dev/null || true)

if [ "$CURRENT" != "$PREV" ]; then
    echo ">> requirements.txt 有更新，正在安装/更新依赖（首次或变更后执行）..."
    pip install --no-cache-dir -r "$REQ"
    mkdir -p "$(dirname "$STAMP")"
    echo "$CURRENT" > "$STAMP"
    echo ">> 依赖安装完成"
else
    echo ">> 依赖已是最新，跳过安装"
fi

exec "$@"
