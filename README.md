# AI 家庭厨房助手

本项目基于 AI + 结构化菜谱知识库，目标是支持：
- 菜谱入库与发布
- 库存管理
- 基于现有食材/季节/目标的推荐
- 基于已发布菜谱的问答

## 目录结构

- backend/：FastAPI 后端骨架
- frontend/：Vue 3 前端骨架
- docs/：开发文档
- sql/：数据库设计与迁移脚本
- tests/：测试目录
- data/：本地样本数据与导出文件

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```
