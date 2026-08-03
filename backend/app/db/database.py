"""数据库配置"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator, Optional
import logging
import os

logger = logging.getLogger(__name__)

# 数据库引擎（延迟初始化）
_engine = None
_SessionLocal = None


def get_engine():
    """获取数据库引擎（延迟初始化）"""
    global _engine
    if _engine is None:
        from app.core.config import settings

        # 获取数据库 URL（添加连接超时参数）
        DATABASE_URL = settings.database_url
        if "?" in DATABASE_URL:
            DATABASE_URL += "&connect_timeout=10"
        else:
            DATABASE_URL += "?connect_timeout=10"
        logger.info(f"数据库连接: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

        # 创建数据库引擎
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"connect_timeout": 10},
            echo=settings.APP_DEBUG
        )
    return _engine


def get_session_local():
    """获取会话工厂（延迟初始化）"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


# 为了向后兼容，暴露 engine 和 SessionLocal
@property
def engine():
    return get_engine()


@property
def SessionLocal():
    return get_session_local()


class Base(DeclarativeBase):
    """数据库模型基类"""
    pass


def get_db() -> Generator:
    """获取数据库会话的依赖注入函数"""
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """获取数据库会话的上下文管理器"""
    db = get_session_local()()
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
    Base.metadata.create_all(bind=get_engine())
    logger.info("数据库表初始化完成")


def drop_all_tables():
    """删除所有表（仅用于测试）"""
    Base.metadata.drop_all(bind=get_engine())
    logger.warning("所有数据库表已删除")
