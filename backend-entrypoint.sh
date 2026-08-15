#!/bin/bash
# 后端容器入口脚本
#
# 设计：镜像只含基础 python，依赖通过 pip --user 装到 NAS 挂载目录
#       /opt/pyuser（宿主机 backend/data/python），不占容器层。
#   - 满足以下任一条件才重新安装：
#       * requirements.txt 内容哈希与上次安装记录不同（首次启动 / requirements 有更新）
#       * fastapi 导入失败（NAS 目录被删、换过基础镜像等自愈场景）
#   - 其余情况（依赖已在 NAS 目录里）跳过安装，快速启动
#   - 安装记录存在挂载目录 /app/data 下（gitignore 过的数据目录），容器重建也不会丢
#
# 注意：slim 基础镜像精简掉了 sha256sum/awk/cat 等工具，
#       所有文件操作统一用 Python（镜像必有），其余只用 bash 内建命令。
set -e

# 显式设全 PATH（不依赖 compose/Docker 的 PATH 展开，避免 command not found）：
# /opt/pyuser/bin 为用户依赖目录，其余为 slim 镜像默认路径。
export PATH="/opt/pyuser/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"

REQ=/app/requirements.txt
STAMP=/app/data/.requirements.sha256

# 当前 requirements.txt 的 SHA-256（Python 计算，避免依赖 coreutils）
CURRENT=$(python - "$REQ" <<'PYEOF'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())
PYEOF
)

# 上次安装成功时记录的哈希（首次启动时文件不存在，read 内建读取）
PREV=""
if [ -f "$STAMP" ]; then
    read -r PREV < "$STAMP"
    PREV="${PREV%$'\r'}"   # 去掉可能的 Windows 换行残留
fi

if [ "$CURRENT" != "$PREV" ] || ! python -c "import fastapi" 2>/dev/null; then
    echo ">> 安装/更新后端依赖（requirements 变更或依赖缺失）..."
    pip install --no-cache-dir --user -r "$REQ"
    # 记录本次哈希（Python 建目录 + 写文件，避免依赖 mkdir/cat）
    python - "$STAMP" "$CURRENT" <<'PYEOF'
import os, sys
path, content = sys.argv[1], sys.argv[2]
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content + '\n')
PYEOF
    echo ">> 依赖安装完成"
else
    echo ">> 依赖已就绪（NAS 目录命中），跳过安装"
fi

exec "$@"
