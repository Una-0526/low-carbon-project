from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import carbon


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（SQLite）
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="低碳校园 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(carbon.router)


@app.get("/api/health", tags=["健康检查"])
def health():
    return {"status": "ok"}
