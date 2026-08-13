# 群晖 NAS 部署指南（AI Kitchen Assistant）

本方案按「**镜像只装基础环境，代码挂载进容器**」设计：

- 后端：`python:3.13-slim` 通用镜像，整个 `backend/` 目录挂载到容器内 `/app`
- 前端：`nginx:alpine` 通用镜像，`frontend/dist` 挂载为静态文件
- **改代码 = 上传/推送代码 + 重启后端**，不重建镜像
- **依赖有变动 = 容器内手动 `pip install`**，镜像始终保持最小

---

## 一、第一次部署

### 1. 把代码放到群晖上

建一个存放目录（例如 `/volume1/docker/ai-kitchen`），两种方式任选：

- **方式 A（推荐，更新最省事）**：群晖装 Git 套件，SSH 进 NAS：
  ```bash
  cd /volume1/docker
  git clone https://github.com/fenghuo1943/AI-Kitchen-Blueprint.git ai-kitchen
  ```
- **方式 B**：Windows 上把整个项目通过 SMB/群晖 Drive 传到该目录。

> 群晖默认的 `docker` 命令可能带权限限制，若报权限错误，后续命令统一加 `sudo`。

### 2. 配置后端环境变量

首次启动前，把 `backend/.env.example` 复制为 `backend/.env` 并修改：

```bash
cd /volume1/docker/ai-kitchen/backend
cp .env.example .env
```

关键项（**NAS 版必须改**）：

| 配置项 | NAS 上填什么 |
|---|---|
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MariaDB 所在机器的局域网 IP 和账号。若 MariaDB 跑在群晖本体上，填群晖的局域网 IP |
| `LLM_BASE_URL` | Ollama 机器的局域网地址，如 `http://192.168.x.x:11434`（不能再用 `127.0.0.1`） |
| `EMBEDDING_BASE_URL` | 同上，指向 Ollama 机器 |
| `ALLOWED_ORIGINS` | 加上访问前端用的地址，如 `http://192.168.x.x`、`http://nas-域名` |
| `APP_ENV` | `production` |
| `APP_DEBUG` | `false` |
| `BROWSER_FETCH_ENABLED` | NAS 容器里不装浏览器的话填 `false`（否则见下文"浏览器抓取"） |

> ⚠️ 容器内后端的工作目录是 `/app`（即挂载的 `backend/`），pydantic 会自动读取 `/app/.env`，**无需**把 .env 传进镜像。

### 3. 构建前端并上传 dist

前端在 **Windows 上构建**（群晖无需装 Node）：

```bash
cd frontend
npm install
npm run build      # 产出 frontend/dist
```

把 `frontend/dist` 文件夹传到 NAS 的 `ai-kitchen/frontend/dist`（覆盖旧文件即可，无需动镜像）。

### 4. 首次启动容器

```bash
cd /volume1/docker/ai-kitchen/deploy
docker compose up -d
```

### 5. 安装后端依赖（首次）

**自动完成**：容器入口脚本（`deploy/backend-entrypoint.sh`）对比 `requirements.txt` 的内容哈希，
首次启动（无安装记录）或 `requirements.txt` 有变化时自动执行 `pip install -r /app/requirements.txt`
（chromadb/playwright 较大，首次可能要等几分钟）。

`docker compose up -d` 之后稍等片刻，容器日志里能看到：
```bash
docker compose logs -f backend
# 出现 ">> requirements.txt 有更新，正在安装/更新依赖..." 即为自动安装中
# 装完自动启动 uvicorn，出现 "Uvicorn running on http://0.0.0.0:8001" 即就绪
```

> 依赖装在容器的可写层里（不在镜像里），镜像本体始终是干净的 `python:3.13-slim`；
> 安装记录（`backend/data/.requirements.sha256`）在挂载目录里，容器重建也不会触发重复安装。

### 6. 初始化数据库（首次）

数据库表在 `init_db()` 启动时自动创建；种子数据需手动跑一次：

```bash
docker compose exec backend python /app/scripts/init_seed_data.py
```

### 7. 验证

- 浏览器打开 `http://群晖局域网IP` 应看到前端首页
- `http://群晖局域网IP/api/v1/...` 能正常返回数据
- 后端健康检查：`http://群晖局域网IP:8001/health`

---

## 二、日常更新代码

### 改后端代码

1. 本地提交并 `git push`，然后 SSH 上群晖执行：
   ```bash
   cd /volume1/docker/ai-kitchen/deploy
   bash update.sh
   ```
2. 或者用 SMB 上传覆盖 `backend/` 下的改动文件，然后 `docker compose restart backend`。

### 改前端代码

1. Windows 上 `npm run build` 重新产出 `dist`。
2. 把 `dist` 覆盖上传到 NAS 的 `ai-kitchen/frontend/dist`。
3. **无需重启容器**——nginx 每次请求直接读磁盘，新文件立即生效。

### requirements.txt 有改动

**无需手动安装**：入口脚本每次启动都会比对哈希，`requirements.txt` 变了就自动重装。
所以更新依赖只需**重启后端**：

```bash
cd /volume1/docker/ai-kitchen/deploy
docker compose restart backend
```

> 想强制重装（如 pip 缓存损坏）可删掉安装记录再重启：
> `docker compose exec backend rm -f /app/data/.requirements.sha256 && docker compose restart backend`

---

## 三、可选：浏览器抓取（Playwright）

后端默认开启浏览器抓取用于小红书等登录墙页面。容器内要启用需额外装 chromium：

```bash
docker compose exec backend pip install -r /app/requirements.txt
docker compose exec backend playwright install chromium
docker compose exec backend playwright install-deps
docker compose restart backend
```

`python:3.13-slim` 上 `install-deps` 需要 apt 权限，容器内以 root 运行即可。
**不需要此功能的话，把 `backend/.env` 里 `BROWSER_FETCH_ENABLED=false`，最省事。**

---

## 四、常见问题

| 问题 | 解决 |
|---|---|
| 80 端口被群晖 Web Station / 其他服务占用 | 改 `docker-compose.yml` 里前端端口为 `8080:80`，浏览器访问 `:8080` |
| docker 命令权限不足 | 所有 `docker` 前加 `sudo`（update.sh 里改 `COMPOSE="sudo docker compose ..."`） |
| 后端连不上 MariaDB | 确认 `backend/.env` 的 `DB_HOST` 是 MariaDB 所在机的局域网 IP，且该机防火墙放行端口 |
| RAG/AI 摘要报连接错误 | 确认 Ollama 机器 `OLLAMA_HOST` 监听 `0.0.0.0`（默认 `127.0.0.1` 只允许本机），防火墙放行 11434 |
| 改完代码重启后端没生效 | 确认代码确实传到了挂载目录；uvicorn 是生产模式不自动 reload，重启才会加载 |
| 想用域名 + HTTPS 访问 | 群晖反代（Application Portal）把域名转发到 `localhost:80` 即可 |
