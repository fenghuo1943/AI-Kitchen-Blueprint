"""数据库配置"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator, Optional
import logging
import threading
import time

logger = logging.getLogger(__name__)

# 数据库引擎（延迟初始化）
_engine = None
_SessionLocal = None


def get_engine():
    """获取数据库引擎（延迟初始化）"""
    global _engine
    if _engine is None:
        from app.core.config import settings

        # 获取数据库 URL（添加连接超时参数，仅 MySQL/MariaDB）
        DATABASE_URL = settings.database_url
        is_sqlite = DATABASE_URL.startswith("sqlite")
        engine_kwargs = dict(
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.SQL_ECHO,
        )
        if not is_sqlite:
            if "?" in DATABASE_URL:
                DATABASE_URL += "&connect_timeout=10"
            else:
                DATABASE_URL += "?connect_timeout=10"
            engine_kwargs["connect_args"] = {"connect_timeout": 10}
        logger.info(f"数据库连接: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

        # 创建数据库引擎
        _engine = create_engine(DATABASE_URL, **engine_kwargs)
    return _engine


def get_session_local():
    """获取会话工厂（延迟初始化）"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


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


def init_db(retries: Optional[int] = None, interval: Optional[float] = None) -> bool:
    """初始化数据库表结构（带重试，数据库未就绪时不会立刻崩溃）。

    启动阶段数据库可能尚未就绪（如 NAS 刚开机、DB 机器未起），
    按间隔重试多次；重试耗尽返回 False（不再抛异常），配合降级模式避免容器崩溃循环。

    返回 True 表示初始化成功，False 表示数据库仍不可用。
    """
    from app.core.config import settings

    retries = retries if retries is not None else settings.DB_RETRY_ATTEMPTS
    interval = interval if interval is not None else settings.DB_RETRY_INTERVAL

    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=get_engine())
            logger.info("数据库表初始化完成")
            return True
        except Exception as exc:
            logger.warning(f"数据库连接失败（第 {attempt}/{retries} 次）：{exc}")
            if attempt < retries:
                time.sleep(interval)

    logger.error(
        f"数据库初始化失败：请检查 DB_HOST/DB_PORT/DB_USER/DB_PASSWORD 及数据库是否可达"
    )
    return False


_db_retry_thread: Optional[threading.Thread] = None


def start_db_retry_loop(interval: Optional[float] = None) -> None:
    """后台线程持续重试数据库连接，直到可用（降级模式自愈，进程退出自动结束）。"""
    global _db_retry_thread
    if _db_retry_thread is not None and _db_retry_thread.is_alive():
        return

    from app.core.config import settings

    interval = interval if interval is not None else settings.DB_BG_RETRY_INTERVAL

    def _loop() -> None:
        while True:
            if init_db(retries=1):
                logger.info("数据库已恢复，应用进入正常模式")
                return
            time.sleep(interval)

    _db_retry_thread = threading.Thread(target=_loop, daemon=True, name="db-retry")
    _db_retry_thread.start()


def drop_all_tables():
    """删除所有表（仅用于测试）"""
    Base.metadata.drop_all(bind=get_engine())
    logger.warning("所有数据库表已删除")
