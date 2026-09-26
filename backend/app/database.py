from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./lowcarbon.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_sqlite_columns() -> None:
    """轻量迁移：create_all 只建新表不改旧表，这里给旧库补齐新增列。

    新增模型字段后，在此登记 (列名, DDL) 即可，缺列才会执行。
    """
    migrations: dict[str, list[tuple[str, str]]] = {
        "users": [
            ("dorm_latitude", "ALTER TABLE users ADD COLUMN dorm_latitude FLOAT"),
            ("dorm_longitude", "ALTER TABLE users ADD COLUMN dorm_longitude FLOAT"),
        ],
        "checkins": [
            ("note", "ALTER TABLE checkins ADD COLUMN note VARCHAR(200)"),
        ],
    }
    with engine.connect() as conn:
        for table, columns in migrations.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if not existing:  # 表还不存在，create_all 会建
                continue
            for col, ddl in columns:
                if col not in existing:
                    conn.execute(text(ddl))
        conn.commit()


def get_db():
    """FastAPI 依赖：获取数据库会话，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
