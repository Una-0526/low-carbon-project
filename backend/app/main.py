from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, SessionLocal, engine, ensure_sqlite_columns
from app.routers import auth, carbon, carbon_accounting, checkin
from app.routers.checkin import UPLOAD_DIR
from app.services import auth_service
from app.services import carbon as carbon_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（SQLite），并创建演示账号 / 默认排放因子（仅对应表为空时）
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_columns()  # 旧库补齐新增列
    with SessionLocal() as db:
        auth_service.ensure_demo_users(db)
        carbon_service.ensure_default_factors(db)
    yield


app = FastAPI(title="低碳校园 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(carbon.router)
app.include_router(carbon_accounting.router)
app.include_router(checkin.router)
app.include_router(checkin.points_router)

# 打卡照片等静态文件
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/api/health", tags=["健康检查"])
def health():
    return {"status": "ok"}
