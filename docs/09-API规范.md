# API 规范

## 通用约定

基路径 `/api/v1`，RESTful JSON，字段使用 `snake_case`，时间为 ISO 8601 UTC。成功响应为 `{ "data": ..., "meta": {...} }`；失败为 `{ "error": {"code": "...", "message": "...", "details": [...]}, "request_id": "..." }`。输入经 Pydantic 校验；分页使用 `page`、`page_size`（默认 20，最大 100）。

HTTP 语义：200 查询/更新成功，201 创建，202 异步任务已接收，204 删除成功，400 请求无效，404 不存在，409 状态/唯一性冲突，422 字段校验失败，429 限流，500 未预期错误。不要用 200 包装错误。

## MVP 资源

| 方法 | 路径 | 目的 |
| --- | --- | --- |
| GET/POST | `/recipes` | 查询已发布菜谱 / 创建草稿 |
| GET/PATCH | `/recipes/{id}` | 查看 / 编辑菜谱 |
| POST | `/recipes/{id}/publish` | 校验后发布并触发索引 |
| GET/POST/PATCH/DELETE | `/inventory/items[/{id}]` | 库存管理 |
| GET | `/ingredients` | 食材搜索、别名建议 |
| POST | `/recommendations` | 按约束返回排序候选和解释依据 |
| POST | `/chat` | 基于知识库的问答 |
| POST | `/ingestions` | 提交文件或来源 URL 的异步入库 |
| GET | `/ingestions/{id}` | 查看任务阶段、错误与结果 |
| GET | `/health` | 服务和依赖健康状态 |

发布、入库和索引类请求支持 `Idempotency-Key`。写操作记录审计事件。认证层预留 JWT Bearer；单机 MVP 可以配置为本地管理员模式，但接口权限判断不得散落在路由中。任何破坏性变更新开 `/v2`，旧版本维持兼容期。

## 关键接口细化

### 1. `POST /api/v1/recipes`

创建菜谱草稿。请求体建议包含：
- `title`：菜谱名称
- `summary`：简述
- `servings`：份量
- `prep_minutes`：准备时间
- `cook_minutes`：烹饪时间
- `difficulty`：难度
- `ingredients`：食材列表
- `steps`：步骤列表
- `tags`：标签列表
- `source_id`：来源 ID（可选）

响应返回新建菜谱的 `id`、`status`、`revision` 与 `created_at`。

### 2. `POST /api/v1/recommendations`

按约束返回推荐结果。请求体建议包含：
- `ingredients`：现有食材列表
- `season_month`：月份
- `max_minutes`：最大时长
- `people_count`：人数
- `equipment`：设备标签
- `diet_restrictions`：忌口或限制
- `goals`：目标标签
- `allow_missing`：是否允许缺料

响应应包含：
- `results`：推荐菜谱列表
- `reasoning`：每条结果的解释依据
- `fallback_reason`：无结果时的降级说明

### 3. `POST /api/v1/ingestions`

提交入库任务。请求体建议包含：
- `source_type`：文件/URL/人工录入
- `source_ref`：文件路径或 URL
- `metadata`：来源信息
- `import_mode`：`draft` 或 `review`

响应返回 `job_id`、`status` 与 `accepted_at`。

## 错误码建议

- `recipe_not_found`
- `ingredient_conflict`
- `invalid_status_transition`
- `ingestion_failed`
- `index_build_failed`
- `llm_unavailable`

