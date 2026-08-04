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
    LLM_MODEL: str = "qwen2.5"
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "http://localhost:11434"

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
