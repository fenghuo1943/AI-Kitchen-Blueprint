"""轻量后台任务执行器（线程池），不引入 Celery。

内存 registry 仅作观测；document_chunks 表才是"是否已索引"的持久真相源，
服务重启后索引状态从关系库统计，不依赖内存。
"""
import logging
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable, Deque, Dict, List, Optional, Set

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[ThreadPoolExecutor] = None
# RLock：SYNC 模式下 submit 持锁调用 _run，_run 内再取同一把锁（同线程重入）需要可重入锁
_lock = threading.RLock()

# 测试模式：True 时 submit 直接同步执行，便于断言
SYNC = False

_registry: Dict = {
    "running": set(),        # set[str] 任务名
    "queued": deque(),       # deque[str] 任务名
    "failed": [],            # list[dict]，最多保留 100 条
    "last_error": {},        # dict[recipe_id, str] 最近一次错误
    "last_rebuild_at": None,  # Optional[datetime]
}


def _get_pool() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(
            max_workers=settings.INDEX_MAX_WORKERS,
            thread_name_prefix="rag-index",
        )
    return _pool


def submit(name: str, fn: Callable, *args, **kwargs) -> None:
    """入队任务；同 name 去重（running/queued 中存在则忽略）。"""
    with _lock:
        if name in _registry["running"] or name in _registry["queued"]:
            logger.debug("任务 %s 已在运行/排队，跳过", name)
            return
        if SYNC:
            _run(name, fn, *args, **kwargs)
            return
        _registry["queued"].append(name)
    _get_pool().submit(_run, name, fn, *args, **kwargs)


def _run(name: str, fn: Callable, *args, **kwargs) -> None:
    """线程内执行；异常记录后吞掉，绝不向外传播。"""
    with _lock:
        if name in _registry["queued"]:
            _registry["queued"].remove(name)
        _registry["running"].add(name)
    try:
        result = fn(*args, **kwargs)
        if name == "rebuild":
            _registry["last_rebuild_at"] = datetime.utcnow()
        # 索引类任务返回 IndexResult，把 error 记入 last_error 供状态接口观测
        if hasattr(result, "error") and getattr(result, "error"):
            _record_error(name, str(getattr(result, "error")))
    except Exception as e:  # noqa: BLE001 - 后台线程内吞掉
        logger.exception("后台任务 %s 执行异常", name)
        _record_error(name, str(e))
    finally:
        with _lock:
            _registry["running"].discard(name)


def _record_error(name: str, error: str) -> None:
    recipe_id = name.split(":", 1)[1] if ":" in name else name
    with _lock:
        _registry["last_error"][recipe_id] = error
        _registry["failed"].append({
            "name": name,
            "recipe_id": recipe_id,
            "error": error,
            "at": datetime.utcnow().isoformat(),
        })
        if len(_registry["failed"]) > 100:
            _registry["failed"] = _registry["failed"][-100:]


def enqueue_index(recipe_id: str) -> None:
    """发布 / PATCH->published / 恢复后索引单道菜。"""
    from app.rag.indexer import RecipeIndexer
    submit(f"index:{recipe_id}", RecipeIndexer().index_recipe, recipe_id)


def enqueue_delete(recipe_id: str) -> None:
    """软删 / 硬删 / 归档后删除向量。"""
    from app.rag.indexer import RecipeIndexer
    submit(f"delete:{recipe_id}", RecipeIndexer().delete_index, recipe_id)


def enqueue_rebuild() -> None:
    """全量重建（单飞：已有重建任务则忽略）。"""
    from app.rag.indexer import RecipeIndexer
    submit("rebuild", RecipeIndexer().rebuild_all)


def shutdown() -> None:
    """应用关闭时释放线程池。"""
    global _pool
    with _lock:
        if _pool is not None:
            _pool.shutdown(wait=False, cancel_futures=False)
            _pool = None


def snapshot() -> Dict:
    """供 GET /rag/index/status 使用。"""
    with _lock:
        return {
            "running": sorted(_registry["running"]),
            "queued": list(_registry["queued"]),
            "failed": len(_registry["failed"]),
            "last_error": dict(_registry["last_error"]),
            "last_rebuild_at": _registry["last_rebuild_at"],
        }
