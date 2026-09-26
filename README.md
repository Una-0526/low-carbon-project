# 低碳校园（Low-Carbon Campus）

学生与教师双角色登录、记录并统计低碳行为（绿色出行、节能行动等）的全栈项目。

- **前端**：Vue 3 + Vite + Element Plus
- **后端**：Python FastAPI + SQLAlchemy + JWT 认证
- **数据库**：SQLite（无需单独安装，首次启动自动建库建表，并自动创建演示账号）

## 演示账号

| 角色 | 用户名 | 密码   | 班级         | 宿舍        |
| ---- | ------ | ------ | ------------ | ----------- |
| 学生 | 张三   | 123456 | 计算机2401班 | 桃园3栋302  |
| 教师 | 李老师 | 123456 | -            | -           |

> 用户表为空时后端启动会自动创建以上演示账号。

## 登录与权限

- `POST /api/auth/login` 返回 JWT 与用户角色，前端按角色跳转 `/student/home` 或 `/teacher/dashboard`
- 前端路由守卫：未登录跳转 `/login`；学生访问教师页面（或反向）会被拦截并送回各自首页
- 后端权限：学生只能查看 / 提交自己的记录；统计与删除仅教师可用（403）

## 目录结构

```
low-carbon project/
├── frontend/                     # 前端（Vue 3 + Vite + Element Plus）
│   └── src/
│       ├── api/                  # axios 封装（自动携带 JWT、401 跳登录）
│       ├── stores/auth.js        # 登录态（token + 用户信息，localStorage 持久化）
│       ├── router/               # 路由 + 角色守卫
│       └── views/
│           ├── LoginView.vue     # 登录页
│           ├── student/          # 学生端页面（/student/home）
│           └── teacher/          # 教师端页面（/teacher/dashboard）
├── backend/                      # 后端（FastAPI）
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # 应用入口
│       ├── auth.py               # 密码哈希 / JWT / 登录态与权限依赖
│       ├── database.py           # SQLite + SQLAlchemy 连接
│       ├── schemas.py            # Pydantic 请求/响应模型
│       ├── models/               # SQLAlchemy ORM 模型（User、CarbonActivity）
│       ├── routers/              # 路由（认证、API 接口）
│       └── services/             # 业务逻辑层
└── README.md
```

## 后端启动

要求：Python 3.10+

```bash
# 1. 进入后端目录
cd backend

# 2. 创建并激活虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
uvicorn app.main:app --reload --port 8000
```

启动后：

- API 地址：<http://127.0.0.1:8000>
- 交互式文档（Swagger）：<http://127.0.0.1:8000/docs>

## 前端启动

要求：Node.js 20.19+（建议 22+）

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

启动后访问：<http://localhost:5173>

> 开发模式下 Vite 已配置代理：`/api` 请求自动转发到 `http://127.0.0.1:8000`，
> 无需处理跨域，请先启动后端再启动前端。

## API 一览

| 方法   | 路径                     | 说明                                      |
| ------ | ------------------------ | ----------------------------------------- |
| GET    | `/api/health`            | 健康检查                                  |
| POST   | `/api/auth/login`        | 登录，返回 JWT 和 role                    |
| GET    | `/api/auth/me`           | 获取当前登录用户信息（含班级 / 宿舍）     |
| POST   | `/api/activities`        | 提交记录（身份取自登录态）                |
| GET    | `/api/activities`        | 查询记录（学生仅本人；教师可按角色/姓名筛选） |
| GET    | `/api/activities/stats`  | 减碳量统计（仅教师）                      |
| DELETE | `/api/activities/{id}`   | 删除记录（仅教师）                        |

除健康检查和登录外，其余接口均需请求头 `Authorization: Bearer <token>`。

完整参数说明见 `/docs` 下的 Swagger 文档。
