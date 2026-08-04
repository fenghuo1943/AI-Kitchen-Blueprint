from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "AI Kitchen Assistant"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置 (MariaDB)
    DB_HOST: str = "192.168.31.146"
    DB_PORT: int = 3307
    DB_USER: str = "cook"
    DB_PASSWORD: str = "Wzcx131130_"
    DB_NAME: str = "cook"
    DATABASE_URL: str = ""
    # 是否打印 SQLAlchemy 执行的 SQL（调试 SQL 时开启）
    SQL_ECHO: bool = False

    # LLM 配置
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "qwen3.5:9b"
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "http://localhost:11434"

    # LLM 生成（AI 采集摘要用）
    # 上限需覆盖推理类模型开销：DeepSeek v4 等在 max_tokens 内先消费数千推理 token，
    # 4000 太小会导致 JSON 输出被截断（非法 JSON / 空内容），故默认 8000。
    LLM_MAX_TOKENS: int = 8000          # 结构化抽取单次输出上限（含推理 token）
    LLM_TEMPERATURE: float = 0.2        # 抽取类任务低温度，提高稳定性
    LLM_TIMEOUT: int = 120              # LLM 生成请求超时（秒）
    # 限制上下文长度，避免大模型默认 262K 上下文导致 Ollama 内存不足（抽取只需数 K token）
    LLM_CONTEXT_LENGTH: int = 8192
    # 注意：不用 ANTHROPIC_MODEL 这个名字，避免与外壳/工具链的 ANTHROPIC_MODEL 环境变量冲突
    ANTHROPIC_LLM_MODEL: str = "claude-opus-5"  # 可选商业供应商默认模型

    # OpenAI 兼容云端供应商（AI 采集摘要）：LLM_PROVIDER=deepseek/openrouter/openai_compat 时生效。
    # DeepSeek 官方 API（OpenAI 协议）
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    # OpenRouter 聚合（含小米 MiMo 等开源模型）
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "xiaomi/mimo-7b"     # MiMo 预设，可按实际改
    # 任意 OpenAI 兼容端点（base_url 留空时回落 LLM_BASE_URL）
    OPENAI_COMPAT_API_KEY: Optional[str] = None
    OPENAI_COMPAT_BASE_URL: str = ""
    OPENAI_COMPAT_MODEL: str = "gpt-4o-mini"     # 通用占位，按实际端点填写

    # 联网搜索（Tavily）
    TAVILY_API_KEY: Optional[str] = None
    TAVILY_BASE_URL: str = "https://api.tavily.com"
    TAVILY_TIMEOUT: int = 30

    # AI 采集限制
    AI_COLLECT_MAX_PAGES: int = 5       # 单任务最多采集页数
    AI_COLLECT_PAGE_CHARS: int = 8000   # 单页喂给 LLM 的字符上限（截断）
    AI_COLLECT_CONCURRENCY: int = 1     # 本地小模型串行，避免压垮 Ollama
    AI_COLLECT_MIN_SOURCES: int = 2     # 综合总结一份菜谱至少参考的来源数
    AI_COLLECT_MAX_SOURCES: int = 3     # 每批最多合并的来源数（单批一次 LLM 调用）

    # RAG 配置
    VECTOR_STORE_TYPE: str = "chroma"
    VECTOR_STORE_PATH: str = "./data/chroma"
    CHROMA_COLLECTION: str = "recipes"          # Chroma collection 名
    CHROMA_SPACE: str = "cosine"                # 距离度量（bge-m3 用余弦）
    EMBEDDING_MODEL: str = "bge-m3"             # Ollama 嵌入模型（dims=1024）
    # 用 127.0.0.1 而非 localhost：Windows 上 localhost 可能优先解析到 IPv6(::1)，
    # 而 Ollama 只监听 IPv4，会导致连接被重置/503
    EMBEDDING_BASE_URL: str = "http://127.0.0.1:11434"
    EMBEDDING_BATCH_SIZE: int = 16              # 一次 /api/embed 最多几条
    EMBEDDING_TIMEOUT: int = 60                 # 嵌入请求超时（秒）

    # 检索默认值
    RECALL_TOP_K: int = 20      # 向量召回上限（RAG 规范默认 Top20）
    RERANK_TOP_K: int = 10      # 重排输出上限（RAG 规范默认 Top5~10）

    # 后台索引
    INDEX_MAX_WORKERS: int = 2  # 后台线程池大小

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    # 安全配置
    SECRET_KEY: str = "dev-secret-key"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def allowed_origins_list(self) -> list[str]:
        return self.ALLOWED_ORIGINS.split(",") if self.ALLOWED_ORIGINS else []

    @property
    def database_url(self) -> str:
        """获取数据库连接 URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

# 确保数据目录存在
Path("./data").mkdir(exist_ok=True)
Path("./logs").mkdir(exist_ok=True)
