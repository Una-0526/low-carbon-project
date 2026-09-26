# 低碳校园（Low-Carbon Campus）

学生与教师记录、统计低碳行为（绿色出行、节能行动等）的全栈示例项目。

- **前端**：Vue 3 + Vite + Element Plus
- **后端**：Python FastAPI + SQLAlchemy
- **数据库**：SQLite（无需单独安装，首次启动自动建库建表）

## 目录结构

```
low-carbon project/
├── frontend/                     # 前端（Vue 3 + Vite + Element Plus）
│   └── src/
│       ├── api/                  # axios 接口封装
│       ├── router/               # 路由
│       └── views/
│           ├── student/          # 学生端页面
│           └── teacher/          # 教师端页面
├── backend/                      # 后端（FastAPI）
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # 应用入口
│       ├── database.py           # SQLite + SQLAlchemy 连接
│       ├── schemas.py            # Pydantic 请求/响应模型
│       ├── models/               # SQLAlchemy ORM 模型
│       ├── routers/              # 路由（API 接口）
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

| 方法   | 路径                     | 说明                       |
| ------ | ------------------------ | -------------------------- |
| GET    | `/api/health`            | 健康检查                   |
| POST   | `/api/activities`        | 提交一条低碳行为记录       |
| GET    | `/api/activities`        | 查询记录（可按角色/姓名筛选） |
| GET    | `/api/activities/stats`  | 减碳量统计（按角色/行为）  |
| DELETE | `/api/activities/{id}`   | 删除一条记录               |

完整参数说明见 `/docs` 下的 Swagger 文档。
