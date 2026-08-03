"""测试配置和 fixtures"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.core.config import settings


# 使用测试数据库（优先使用环境变量，否则使用 MariaDB 测试数据库）
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/cook_test?charset=utf8mb4"
)

engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    # 创建测试数据库（如果不存在）
    from sqlalchemy import text
    try:
        engine.connect().execute(text("SELECT 1"))
    except Exception:
        # 数据库不存在，尝试创建
        test_db_url = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}"
        temp_engine = create_engine(test_db_url)
        with temp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS cook_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        temp_engine.dispose()

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """每个测试函数使用独立的数据库会话"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
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
