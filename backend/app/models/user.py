from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """用户表：学生 / 教师双角色。

    学生需要填写班级和宿舍；教师这两个字段为空。
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(10))  # student / teacher
    class_name: Mapped[str | None] = mapped_column("class_name", String(50), default=None)  # 班级
    dormitory: Mapped[str | None] = mapped_column(String(50), default=None)  # 宿舍
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
