"""用户与登录业务逻辑。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.models import User

DEMO_PASSWORD = "123456"


def authenticate_user(db: Session, username: str, password: str) -> tuple[User | None, str | None]:
    """校验账号密码，成功返回 (user, token)，失败返回 (None, None)。"""
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return None, None
    return user, create_access_token(user.username, user.role)


def ensure_demo_users(db: Session) -> None:
    """用户表为空时创建演示账号，方便本地联调。"""
    if db.scalar(select(User.id).limit(1)) is not None:
        return
    db.add_all(
        [
            User(
                username="张三",
                password_hash=hash_password(DEMO_PASSWORD),
                role="student",
                class_name="计算机2401班",
                dormitory="桃园3栋302",
            ),
            User(
                username="李老师",
                password_hash=hash_password(DEMO_PASSWORD),
                role="teacher",
            ),
        ]
    )
    db.commit()
