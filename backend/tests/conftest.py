"""测试配置和 fixtures"""
import os
import sys
from pathlib import Path

# 设置测试环境变量
os.environ["APP_ENV"] = "testing"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 使用 SQLite 内存数据库进行测试（避免依赖外部数据库）
TEST_DATABASE_URL = "sqlite:///:memory:"

# 创建测试引擎
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 导入应用（在设置好测试数据库之后）
from app.main import app
from app.db.database import Base, get_db
import app.db.database as db_module


# 覆盖数据库引擎和会话工厂
db_module._engine = test_engine
db_module._SessionLocal = TestingSessionLocal


def override_get_db():
    """覆盖数据库依赖"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """测试前创建数据库表"""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def db_session():
    """每个测试函数使用独立的数据库会话，并在测试后回滚"""
    # 清理所有表的数据（保留表结构）
    with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()

    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """测试客户端"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_ingredient(db_session):
    """示例食材"""
    from app.db.models import Ingredient
    import uuid

    ingredient = Ingredient(
        id=str(uuid.uuid4()),
        canonical_name="测试食材",
        category="蔬菜",
        confidence_status="verified"
    )
    db_session.add(ingredient)
    db_session.commit()
    return ingredient


@pytest.fixture
def sample_recipe(db_session, sample_ingredient):
    """示例菜谱"""
    from app.db.models import Recipe, RecipeIngredient
    import uuid

    recipe_id = str(uuid.uuid4())
    recipe = Recipe(
        id=recipe_id,
        title="测试菜谱",
        summary="这是一个测试菜谱",
        servings=2,
        prep_minutes=10,
        cook_minutes=20,
        difficulty="简单",
        status="draft"
    )
    db_session.add(recipe)

    recipe_ingredient = RecipeIngredient(
        id=str(uuid.uuid4()),
        recipe_id=recipe_id,
        ingredient_id=sample_ingredient.id,
        quantity="100",
        unit="克",
        sort_order=0
    )
    db_session.add(recipe_ingredient)
    db_session.commit()

    return recipe


# ============================================================
# RAG 测试 fixtures
# ============================================================

@pytest.fixture(autouse=True)
def no_background_indexing(monkeypatch):
    """默认屏蔽 recipe_service 的后台索引钩子，避免现有测试触发真实 Chroma/Ollama。"""
    import app.services.recipe_service as rs

    def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(rs, "enqueue_index", _noop)
    monkeypatch.setattr(rs, "enqueue_delete", _noop)


@pytest.fixture
def sync_tasks(monkeypatch):
    """后台任务同步执行，便于断言（rag 测试用）。"""
    import app.tasks.executor as ex
    monkeypatch.setattr(ex, "SYNC", True)
    yield ex


@pytest.fixture
def rag_store(tmp_path):
    """临时目录隔离的 Chroma store（不触碰真实 data/chroma）。"""
    from app.rag.vector_store import ChromaStore
    store = ChromaStore(path=str(tmp_path / "chroma"))
    store._ensure()
    store.clear()
    yield store


@pytest.fixture
def rag_engine(monkeypatch, rag_store):
    """将 indexer/retriever 默认使用的 store/embedding 替换为临时实现。"""
    import app.rag.indexer as idx
    import app.rag.retriever as ret
    from tests.rag_helpers import FakeEmbedder
    fake = FakeEmbedder()
    monkeypatch.setattr(idx, "ChromaStore", lambda: rag_store)
    monkeypatch.setattr(idx, "OllamaEmbeddingClient", lambda: fake)
    monkeypatch.setattr(ret, "ChromaStore", lambda: rag_store)
    monkeypatch.setattr(ret, "OllamaEmbeddingClient", lambda: fake)
    return rag_store
