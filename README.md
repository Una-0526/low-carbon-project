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
│       ├── models/               # SQLAlchemy ORM 模型（User、CarbonActivity、Checkin 等）
│       ├── routers/              # 路由（认证、碳核算、打卡、积分）
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

# （可选）生成最近 12 个月的模拟能耗数据，方便验证碳核算接口
python seed_mock_data.py            # energy_records 为空时生成
python seed_mock_data.py --force    # 清空已有能耗记录后重新生成
```

模拟数据覆盖：教学楼A/B、宿舍楼、图书馆、食堂（含天然气）、公务车（汽油）。
用电量按日模拟再按月汇总：周末低于工作日，冬夏为制冷/采暖高峰，寒暑假教学楼/图书馆明显下降。

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

| 方法   | 路径                          | 说明                                          |
| ------ | ----------------------------- | --------------------------------------------- |
| GET    | `/api/health`                 | 健康检查                                      |
| POST   | `/api/auth/login`             | 登录，返回 JWT 和 role                        |
| GET    | `/api/auth/me`                | 获取当前登录用户信息（含班级 / 宿舍）         |
| POST   | `/api/activities`             | 提交记录（身份取自登录态）                    |
| GET    | `/api/activities`             | 查询记录（学生仅本人；教师可按角色/姓名筛选） |
| GET    | `/api/activities/stats`       | 减碳量统计（仅教师）                          |
| DELETE | `/api/activities/{id}`        | 删除记录（仅教师）                            |
| GET    | `/api/carbon/factors`         | 查询排放因子表（登录即可）                    |
| PUT    | `/api/carbon/factors/{key}`   | 修改因子数值（仅教师，改后立即生效）          |
| POST   | `/api/carbon/records`         | 录入建筑能耗记录（仅教师）                    |
| GET    | `/api/carbon/records`         | 查询能耗记录与逐条核算结果（仅教师）          |
| DELETE | `/api/carbon/records/{id}`    | 删除能耗记录（仅教师）                        |
| GET    | `/api/carbon/stats`           | 碳排放统计（仅教师）：`group_by=building\|month\|semester`，可加 `year`/`building`/`semester` 筛选 |
| GET    | `/api/checkins/tasks`         | 打卡任务类型与基础积分                        |
| POST   | `/api/checkins`               | 提交打卡（multipart，可带定位经纬度与照片，自动 AI 防作弊检查） |
| GET    | `/api/checkins/me`            | 我的打卡记录                                  |
| GET    | `/api/checkins/me/summary`    | 我的累计积分与连续打卡天数                    |
| GET    | `/api/checkins`               | 全部打卡（仅教师，可按 status/ai_flagged/user_id 筛选） |
| POST   | `/api/checkins/{id}/approve`  | 审核通过：积分入账 + 连续奖励（仅教师）       |
| POST   | `/api/checkins/{id}/reject`   | 审核驳回（仅教师）                            |
| GET    | `/api/points/me`              | 我的积分流水与累计积分                        |
| GET    | `/api/points/transactions`    | 指定学生积分流水（仅教师，`user_id=`）        |

除健康检查和登录外，其余接口均需请求头 `Authorization: Bearer <token>`。

### 碳核算口径（kgCO2e）

- Scope2 排放 = 用电量(kWh) × 电网排放因子（默认 0.5703）
- Scope1 排放 = 天然气(m³) × 2.162 + 汽油(L) × 2.30
- 减碳量 = 光伏 / 储能削峰 / 节能电量 × 对应减碳因子（默认 0.5703，即替代电网电量）
- 净排放 = Scope1 + Scope2 − 减碳量

因子存于 `carbon_factors` 表，可通过 API 修改；核算逻辑见 `backend/app/services/carbon.py`。

### 绿色打卡规则

- 任务类型与基础积分：骑行 10 / 光盘 5 / 自带水杯 3 / 爬楼 3 / 随手关灯 2
- 打卡提交后为 `pending` 状态，教师审核通过后积分入账 `point_transactions` 流水表
- 连续打卡里程碑奖励：连打 3 天 +5 分、7 天 +10 分、14 天 +20 分、30 天 +50 分
- AI 防作弊（自动标记 `ai_flagged`，不影响提交，由教师审核裁决）：
  - 同类型打卡间隔不足 5 分钟
  - 打卡定位距学生宿舍坐标超过 2km（疑似位置漂移）
- 打卡照片保存于 `backend/uploads/`（不入库 git），通过 `/uploads/文件名` 访问

完整参数说明见 `/docs` 下的 Swagger 文档。

## 测试

```bash
cd backend
.venv\Scripts\activate
python test_checkin_api.py   # 打卡全流程 15 项断言（防作弊/上传/审核/积分/权限）
```
