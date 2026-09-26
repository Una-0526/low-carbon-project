from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.schemas import LoginIn, TokenOut, UserOut
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenOut, summary="登录，返回 JWT 和角色")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user, token = auth_service.authenticate_user(db, data.username, data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return TokenOut(access_token=token, role=user.role, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut, summary="获取当前登录用户信息")
def me(user=Depends(get_current_user)):
    return UserOut.model_validate(user)
