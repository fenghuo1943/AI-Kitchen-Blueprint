# AI 家庭厨房助手

本项目基于 AI + 结构化菜谱知识库，目标是支持：
- 菜谱入库与发布
- 库存管理
- 基于现有食材/季节/目标的推荐
- 基于已发布菜谱的问答

## 目录结构

- `backend/`：FastAPI 后端应用
- `frontend/`：Vue 3 前端应用
- `docs/`：开发文档
- `sql/`：数据库设计与迁移脚本
- `tests/`：测试目录
- `data/`：本地样本数据与导出文件

## 快速启动

### 后端

```bash
cd backend

# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### 访问服务

- API 文档：http://localhost:8001/docs
- 健康检查：http://localhost:8001/health

## 功能模块

### Phase 0：工程基线 ✅
- 项目配置管理
- 数据库模型与迁移
- 日志系统
- 测试脚手架

### Phase 1：知识库与入库 ✅
- 食材管理（CRUD + 别名）
- 菜谱管理（CRUD + 发布）

### Phase 2：库存与推荐 ✅
- 库存管理（CRUD + 保质期）
- 推荐引擎（基于规则的推荐）

## 测试

```bash
cd backend
pytest tests/ -v
```

## 文档

详细文档请查看 [docs/](docs/) 目录。

## 开发进度

详见 [DEVELOPMENT_SUMMARY.md](DEVELOPMENT_SUMMARY.md)
