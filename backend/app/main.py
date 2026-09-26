from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine
from app.routers import auth, carbon, carbon_accounting
from app.services import auth_service
from app.services import carbon as carbon_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（SQLite），并创建演示账号 / 默认排放因子（仅对应表为空时）
    Base.metadata.create_all(bind=engine)
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


@app.get("/api/health", tags=["健康检查"])
def health():
    return {"status": "ok"}
