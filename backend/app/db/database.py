"""数据库配置"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 获取数据库 URL
DATABASE_URL = settings.database_url
logger.info(f"数据库连接: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.APP_DEBUG
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """数据库模型基类"""
    pass


def get_db() -> Generator:
    """获取数据库会话的依赖注入函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """获取数据库会话的上下文管理器"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """初始化数据库表结构"""
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")


def drop_all_tables():
    """删除所有表（仅用于测试）"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("所有数据库表已删除")
