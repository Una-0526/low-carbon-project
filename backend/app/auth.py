"""认证工具：密码哈希（标准库 pbkdf2）、JWT 签发与校验、登录态依赖。"""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")
TOKEN_EXPIRE_HOURS = 12

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return "pbkdf2$%s$%s" % (base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def verify_password(password: str, hashed: str) -> bool:
    try:
        _, salt_b64, dk_b64 = hashed.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), 100_000)
        return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except ValueError:
        return False


def create_access_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """登录态依赖：校验 Authorization: Bearer <token>。"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = db.scalar(select(User).where(User.username == payload.get("sub")))
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_teacher(user: User = Depends(get_current_user)) -> User:
    """教师权限依赖。"""
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="需要教师权限")
    return user
