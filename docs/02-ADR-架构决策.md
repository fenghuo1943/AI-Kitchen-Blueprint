# ADR：架构决策记录

ADR 格式：`状态 / 背景 / 决策 / 后果`。新决策追加编号，已接受决策只能被新 ADR 替代。

## ADR-001：后端采用 FastAPI（已接受）

使用 Python + FastAPI 提供 REST API、OpenAPI 文档和异步任务入口。领域服务不得依赖 FastAPI 对象，以便单测和后续任务队列复用。

## ADR-002：前端采用 Vue 3（已接受）

使用 Vue 3、TypeScript、Vite、Vue Router 与 Pinia。前端通过 API 客户端访问后端，不直连数据库、Chroma 或模型服务。

## ADR-003：关系数据 SQLite 起步、PostgreSQL 可迁移（已接受）

单机 MVP 使用 SQLite；通过 SQLAlchemy/Alembic 与数据库无关的迁移维护模式。需要并发写入、共享部署或全文/向量增强时迁移 PostgreSQL；不得将 SQLite 方言散落在业务层。

## ADR-004：向量库采用 Chroma（已接受）

Chroma 保存可重建的文档块向量，不作为菜谱事实唯一来源。关系库是权威数据源，向量条目必须保存 `recipe_id`、`revision`、`chunk_type` 和 `content_hash`。

## ADR-005：Ollama 默认，商业 API 可选（已接受）

默认使用本地 Ollama，供应商经统一 `LLMProvider` 抽象接入。云 API 只用于配置允许的增强任务，并有超时、预算和本地降级。

## ADR-006：规则和 RAG 优先于 LLM 生成（已接受）

规则引擎完成硬约束过滤，RAG 完成候选召回，LLM 仅生成解释、澄清问题或受约束的菜单组织。最终推荐不可脱离候选集。

## ADR-007：异步入库任务（已接受）

采集、解析、嵌入和重建索引是可重试的后台任务。MVP 可由进程内队列执行，但任务状态必须持久化；生产环境可替换为 Redis/Celery 等实现，调用方不感知差异。

