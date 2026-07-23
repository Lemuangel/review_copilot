"""
数据库连接和会话管理 — MySQL
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# MySQL 连接引擎（pool_pre_ping + pool_recycle 防止断连）
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,          # 1小时回收连接
    pool_size=5,                # 连接池大小
    max_overflow=10,            # 最大溢出连接
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """SQLAlchemy 基类"""
    pass


def get_db():
    """
    数据库会话依赖注入

    用法:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
