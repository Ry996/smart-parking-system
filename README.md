# 智慧停车场管理系统 V2

本项目是在课程实训作品《智慧停车场管理系统 V1》基础上全面升级的 **V2 版本**，作为新的项目作业交付。V2 在保留 V1 全部能力（车牌识别、车辆入场、离场计费、记录查询、统计可视化、收费规则、用户权限、车位管理）的同时，新增**月租车辆管理、车位预约、黑名单拦截、操作日志审计、数据导出、在线支付模拟、首页数据大屏**等运营级功能，形成"临停 + 月租 + 预约 + 风控 + 支付 + 审计"的完整智慧停车运营闭环。

## 技术栈

| 层级 | 技术 | 作用 |
|---|---|---|
| 前端框架 | Vue 3 + Vite | 构建单页应用 |
| UI 组件 | Element Plus | 表单、表格、弹窗、菜单 |
| 状态管理 | Pinia | 登录状态、用户角色 |
| 路由 | Vue Router | 页面路由、登录拦截、角色拦截 |
| HTTP | Axios | 调用后端 API，统一 Token 处理 |
| 图表 | ECharts / vue-echarts | 数据可视化 |
| 后端框架 | Flask | REST API 服务 |
| ORM | Flask-SQLAlchemy | 数据模型与查询 |
| 认证 | JWT + bcrypt | Token 认证与密码哈希 |
| 数据库 | SQLite（默认）/ MySQL 8.0 | 存储业务数据 |
| AI 识别 | HyperLPR3 + OpenCV + Pillow | 车牌识别（真实 + 模拟双模式） |
| AI 建议 | DeepSeek API（可选）+ 本地规则兜底 | 运营建议 |
| 测试 | unittest（Python 标准库） | 计费单测 + 接口冒烟测试 |

运行环境：Python 3.9+（已在 **Python 3.14** 实测通过）、Node.js 18+、npm 9+。依赖版本已放宽为兼容新版 Python 的版本。

## 项目亮点（V2 新增）

- **月租车辆管理**：套餐维护、到期自动判定（生效中/7天内到期/已过期）、一键续费、到期提醒看板；月租车入场自动标记、离场套餐内免费放行。
- **车位预约**：提前预约入场时段，预约时段内车辆入场自动校验并优先放行，预约状态全程可跟踪（待入场/已到达/已取消/已过期）。
- **黑名单风控**：欠费、逃费等车辆加入黑名单后，入场时被系统自动拦截并记录审计日志。
- **操作日志审计**：登录、入场、离场、拦截、增删改、导出等关键操作全部留痕，支持按操作人/类型/日期筛选，可追溯、可答辩。
- **数据导出**：停车记录、月租台账一键导出 CSV（UTF-8 BOM，Excel 直接打开）。
- **车位实时分布可视化**：首页车位网格图（可用/预约预留/占用三色示意），直观展示车位占用状态。
- **全站深色科技风 UI 焕新**：Element Plus 深色模式 + 全局设计变量（深蓝渐变背景、玻璃拟态卡片、品牌青蓝点缀），登录页、导航、表格、表单、弹窗、图表全部深色化；菜单与各页面标题图标全面更换。
- **首页数据大屏**：深色科技风运营大屏——实时时钟、核心指标、车位占用率仪表盘、近 7 天车流/收入趋势、在场车辆实时列表，答辩演示冲击力强。
- **在线支付模拟**：收费离场结算后进入"待支付"状态，弹出扫码支付窗口（模拟），支付成功才完成放行；免费时长内（0 元）自动免费放行；停车记录支持"补收"。
- **入场联动**：黑名单拦截 → 预约校验 → 月租判定 → 车位扣减，一次入场登记完成全部风控与业务逻辑。
- **工程能力**：新增 12 项自动化测试（计费单测 5 项 + 接口冒烟 7 项），全部通过；修复新版 Python/SQLAlchemy 兼容问题。

## 功能模块

| 模块 | 使用角色 | 前端页面 | 后端接口 | 功能说明 |
|---|---|---|---|---|
| 登录认证 | 管理员、操作员 | `Login.vue` | `/api/auth/login` | 登录、Token 下发、失败与禁用提示 |
| 首页概览 | 管理员、操作员 | `Dashboard.vue` | `/api/stats/overview`、`/api/parking/spaces`、`/api/parking/parked` | **数据大屏**：今日入场、收入、在场车辆、车位占用率仪表盘、车位网格、趋势图 |
| 车辆入场 | 管理员、操作员 | `Entry.vue` | `/api/lpr/recognize`、`/api/parking/enter` | 识别/录入车牌，**黑名单拦截、预约校验、月租标记**，扣减车位 |
| 车辆离场 | 管理员、操作员 | `Exit.vue` | `/api/lpr/recognize`、`/api/parking/exit-preview`、`/api/parking/exit`、`/api/parking/<id>/pay` | 费用预览、**应收离场待支付 + 扫码支付（模拟）**、月租/0 元免费放行、释放车位 |
| 停车记录 | 管理员、操作员 | `Records.vue` | `/api/records/`、`/api/export/records` | 筛选查询、详情、备注、**支付状态与补收**、导出 CSV |
| 数据统计 | 管理员、操作员 | `Stats.vue` | `/api/stats/flow`、`/api/stats/income`、`/api/stats/ai-advice` | 车流量/收入趋势、AI 运营建议 |
| 收费规则 | 管理员 | `FeeRules.vue` | `/api/fee-rules/` | 收费规则增删改 |
| 用户管理 | 管理员 | `Users.vue` | `/api/users/` | 用户增删改、角色、启停 |
| 车位管理 | 管理员 | `Spaces.vue` | `/api/parking/spaces` | 总车位数管理 |
| **月租管理** | 管理员 | `Monthly.vue` | `/api/monthly/` | 月租套餐维护、续费、到期提醒（V2 新增） |
| **车位预约** | 管理员 | `Reservations.vue` | `/api/reservations/` | 预约维护、状态跟踪（V2 新增） |
| **黑名单管理** | 管理员 | `Blacklist.vue` | `/api/blacklist/` | 拉黑/解除/拦截（V2 新增） |
| **操作日志** | 管理员 | `Logs.vue` | `/api/logs/` | 审计日志查询（V2 新增） |

## 用户角色与权限

| 角色 | 权限范围 |
|---|---|
| 管理员 `admin` | 全部功能，含收费规则、用户管理、车位管理、**月租管理、车位预约、黑名单、操作日志** |
| 操作员 `operator` | 登录、车辆入场/离场、停车记录查询、数据统计 |

权限控制分两层：前端路由 `meta.role = 'admin'` 限制 + 后端 `token_required` / `admin_required` 装饰器校验，仅隐藏菜单无法绕过权限。

默认账号：管理员 `admin / admin123`；操作员 `operator1 / admin123`。

## 快速启动

### 1. 启动后端

```bash
cd backend

# 创建虚拟环境（首次）
python -m venv .venv

# 安装依赖（Windows）
.venv\Scripts\pip install -r requirements.txt
# Linux/macOS: .venv/bin/pip install -r requirements.txt

# 启动服务
.venv\Scripts\python run.py
```

后端默认运行地址：`http://localhost:5000`。启动时自动建表并初始化：管理员/操作员账号、默认收费规则、默认车位、**月租演示数据、预约演示数据**。

也可使用 Flask 命令初始化数据库：

```bash
.venv\Scripts\flask --app run.py init-db
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行地址：`http://localhost:5173`，`/api` 请求自动代理到 `http://localhost:5000`。

### 3. 运行自动化测试

```bash
cd backend
.venv\Scripts\python tests\test_fee_service.py     # 计费单元测试（5 项）
.venv\Scripts\python tests\test_api_smoke.py      # 接口冒烟测试（7 项）
```

## 数据库设计（V2 共 8 张表）

| 表名 | 模型类 | 来源 | 作用 |
|---|---|---|---|
| `users` | `User` | V1 | 用户账号、角色、状态 |
| `parking_records` | `ParkingRecord` | V1 | 停车记录（入场/离场/时长/费用/状态/**支付状态**） |
| `fee_rules` | `FeeRule` | V1 | 收费规则 |
| `parking_spaces` | `ParkingSpace` | V1 | 车位总数/可用数 |
| `monthly_subscribers` | `MonthlySubscriber` | **V2 新增** | 月租车辆、套餐、起止日期、动态状态 |
| `parking_reservations` | `ParkingReservation` | **V2 新增** | 车位预约时段与状态 |
| `blacklist` | `Blacklist` | **V2 新增** | 黑名单车辆、原因、欠费金额、拦截开关 |
| `operation_logs` | `OperationLog` | **V2 新增** | 操作审计日志 |

默认使用 `backend/smart_parking.db`（SQLite）。切换 MySQL 时导入 `database/init.sql`（已同步 4 张新表与演示数据），并通过环境变量指定连接串，例如：

```bash
set SQLALCHEMY_DATABASE_URI=mysql+pymysql://root:123456@localhost:3306/smart_parking?charset=utf8mb4
```

## 后端结构

```text
backend/
|-- config.py                  # 配置：数据库、JWT、上传目录、识别模式、跨域
|-- run.py                     # 启动入口 + 种子数据（含 V2 演示数据）
|-- requirements.txt           # 依赖清单（兼容 Python 3.14）
|-- smart_parking.db           # 默认 SQLite 数据库
|-- uploads/                   # 识别图片保存目录
|-- tests/                     # 自动化测试（计费单测 + 接口冒烟）
`-- app/
    |-- __init__.py            # 应用工厂、蓝图注册（V2 新增 5 个蓝图）
    |-- api/                   # REST API
    |-- models/                # 数据模型（V2 新增 4 个）
    |-- services/              # fee_service 计费、log_service 审计日志（V2 新增）
    `-- utils/                 # 认证、数据库兼容、车牌识别
```

### 接口清单（V2 新增）

| 方法 | 地址 | 权限 | 说明 |
|---|---|---|---|
| `GET` | `/api/monthly/` | 登录用户 | 月租列表（支持车牌/状态筛选） |
| `POST` | `/api/monthly/` | 管理员 | 新增月租车辆 |
| `POST` | `/api/monthly/<id>/renew` | 管理员 | 月租续费（按月顺延或指定到期日） |
| `PUT` | `/api/monthly/<id>` | 管理员 | 修改月租信息 |
| `DELETE` | `/api/monthly/<id>` | 管理员 | 删除月租记录 |
| `GET` | `/api/monthly/check?plate=` | 登录用户 | 车牌月租状态校验（入离场联动） |
| `GET` | `/api/reservations/` | 登录用户 | 预约列表 |
| `POST` | `/api/reservations/` | 管理员 | 新增预约 |
| `PUT` | `/api/reservations/<id>/status` | 登录用户 | 变更预约状态（到达/取消/过期） |
| `DELETE` | `/api/reservations/<id>` | 管理员 | 删除预约 |
| `GET` | `/api/reservations/check?plate=` | 登录用户 | 预约时段校验（入场联动，到场自动标记） |
| `GET` | `/api/blacklist/` | 登录用户 | 黑名单列表 |
| `POST` | `/api/blacklist/` | 管理员 | 加入黑名单 |
| `PUT` | `/api/blacklist/<id>` | 管理员 | 修改/解除黑名单 |
| `DELETE` | `/api/blacklist/<id>` | 管理员 | 删除黑名单记录 |
| `GET` | `/api/blacklist/check?plate=` | 登录用户 | 黑名单校验（入场拦截） |
| `GET` | `/api/logs/` | 管理员 | 操作日志分页查询（操作人/类型/日期筛选） |
| `GET` | `/api/export/records` | 登录用户 | 停车记录导出 CSV |
| `GET` | `/api/export/monthly` | 登录用户 | 月租台账导出 CSV |
| `POST` | `/api/parking/<id>/pay` | 登录用户 | 模拟在线支付：待支付记录置为已支付 |

原有接口（V1）全部保留，其中 `POST /api/parking/enter`、`POST /api/parking/exit-preview`、`POST /api/parking/exit` 已加入 V2 联动逻辑（黑名单/预约/月租/支付状态）。

## 前端结构

```text
frontend/
`-- src/
    |-- api/index.js           # Axios 实例 + 全部接口封装（含 V2 新增）
    |-- router/index.js        # 路由 + 权限（含 4 个新页面路由）
    |-- store/user.js          # 登录状态
    `-- views/                 # 14 个业务页面
```

新增页面：`Monthly.vue`（月租管理）、`Reservations.vue`（车位预约）、`Blacklist.vue`（黑名单管理）、`Logs.vue`（操作日志）；菜单新增"运营管理"分组。

## AI 车牌识别说明

识别模式、流程与 V1 一致：

- 真实识别（`LPR_MOCK_MODE=false`，默认）：HyperLPR3 + OpenCV 多候选预处理。
- 模拟识别（`LPR_MOCK_MODE=true`）：随机生成车牌，适合演示与接口联调。
- 识别失败可手动录入，不阻塞业务。

修改模式后重启后端生效。

## V1 → V2 升级对照

| 维度 | V1 | V2 |
|---|---|---|
| 业务闭环 | 临停出入 + 计费 + 统计 | 临停 + 月租 + 预约 + 黑名单风控 + **在线支付** + 审计 |
| 数据表 | 4 张 | 8 张（新增月租/预约/黑名单/日志，**记录表加支付字段**） |
| 接口 | 23 个 | 40+ 个（新增 18 个，含支付接口） |
| 页面 | 9 个 | 14 个（新增 4 个管理页，改造 4 个，**首页升级为数据大屏**） |
| 首页 | 数字卡片 + 趋势图 | **深色科技风大屏**：仪表盘/车流/收入/在场列表/车位网格 |
| 数据导出 | 无 | 停车记录/月租台账 CSV |
| 支付能力 | 无 | **离场结算 → 待支付 → 扫码支付（模拟）→ 放行**，支持补收 |
| 自动化测试 | 无 | 13 项（计费 5 + 接口 8） |
| 运行环境 | Python 3.9+（固定依赖版本） | 兼容 Python 3.14，依赖版本放宽 |
| 审计能力 | 无 | 关键操作全程留痕可查 |

## V2.2 新增：面向课程实验二 / 四 / 五的能力补齐

V2.2 在 V2.1 基础上补齐三块能力，使项目可以直接作为《团队规范项目实训》个人项目的实验二、实验四、实验五成果。

### 1. 接口文档化（实验二）

- 反射 Flask 路由自动生成 OpenAPI 3.0 规范：`GET /api/openapi.json`
- 零依赖在线文档页：`GET /api/docs`（断网可用、支持搜索，菜单"系统管理 → 接口文档"可打开）
- 静态产物：`docs/openapi.json`、`docs/API.md`，改代码后执行 `python tools/gen_openapi.py` 重新生成
- 每个接口标注鉴权方式与所需权限码，便于前后端联调核对字段与错误边界

### 2. RBAC 角色权限（实验四）

新增 `roles`、`permissions`、`role_permissions` 三张表，与 `users.role` 共同构成完整的用户-角色-权限模型：

| 角色 | 权限数 | 说明 |
|---|---|---|
| admin 管理员 | 17 | 全部业务与系统管理权限 |
| operator 操作员 | 5 | 入离场、记录查询、统计、AI 建议与问答 |

- 接口鉴权从"仅判断管理员"升级为 `permission_required("权限码")`，等价 Spring Security 的 `@PreAuthorize`
- 新增接口：`GET /api/roles/`、`POST /api/roles/`、`PUT /api/roles/<id>`、`PUT /api/roles/<id>/permissions`、`DELETE /api/roles/<id>`、`GET /api/roles/permissions`、`GET /api/roles/me`
- 新增页面"角色权限"：权限矩阵勾选保存，权限变更即时生效
- 前端令牌从 localStorage 迁到 sessionStorage，关闭标签页即失效
- 管理员角色强制保留 `role:manage`，内置角色不可删除，避免把系统锁死

### 3. AI 安全与 RAG 知识库（实验四 AI 安全 + 实验五）

**提示注入防护**（`app/utils/security.py`）

- 用户输入进模型前做长度与控制字符校验
- 7 类注入意图识别（忽略指令、套取提示词、索要密钥、改写身份、越权指示、无限制角色、英文注入），命中即拦截且**不调用模型**，同时写入操作日志
- 审计内容与返回结果统一脱敏（`sk-*`、`Bearer`、`key=...`）
- AI 接口进程内限流 30 次/分钟

**RAG 知识库问答**（`app/services/rag_service.py`）

- 知识库：`backend/knowledge/*.md` 共 5 篇业务规则 → 切块（320 字 / 重叠 60）→ 稀疏 TF-IDF 索引（零外部依赖）
- 检索：余弦相似度 + 查询覆盖率双重门控，资料不足时返回空，模型回答"根据当前资料无法确定"
- 生成：DeepSeek 对话接口，system prompt 带版本（`rag-v2` / `advice-v2` / `general-v1`），强制标注 `[1]` 引用
- 降级：未配置密钥或调用失败时走离线抽取式回答，`provider` 字段区分 `deepseek` / `offline` / `local`
- 留痕：每次调用写入 `ai_calls` 表（模型、提示词版本、耗时、错误、脱敏后的输入输出）
- 复核：`ai_feedback` 表沉淀幻觉、引用错误、过度拒答案例，前端"举报为幻觉"入口
- 新增页面"AI 知识库问答"：展示回答模式、引用来源及相似度/覆盖率

### 4. 数据表与测试

- 数据表：8 → 15 张（新增 roles、permissions、role_permissions、ai_calls、ai_feedback、knowledge_documents、knowledge_chunks）
- 自动化测试：13 → 76 项（新增安全工具 15、RBAC 13、RAG 14、AI 接口 12、接口文档 9，并保留原有计费与接口回归）
- 实验逐条对照、启动取证步骤与截图清单见 `docs/EXPERIMENT_GUIDE.md`

## 环境与数据库配置

完整的环境变量清单、SQLite ↔ MySQL 切换、启动步骤与排错说明见 **[docs/ENVIRONMENT.md](docs/ENVIRONMENT.md)**。要点：

| 场景 | 操作 |
|---|---|
| 后端首次运行 | `cd backend` → `pip install -r requirements.txt` → `python run.py` |
| 前端 | `cd frontend` → `npm install` → `npm run dev` |
| 配置环境变量 | 复制 `backend/.env.example` 为 `backend/.env` 后修改 |
| 切换 MySQL 8 | 建库并导入 `database/init.sql`，在 `.env` 填写 `DATABASE_URL` |
| 启用真实大模型 | `.env` 填写 `DEEPSEEK_API_KEY` 后重启；不填自动离线降级 |
| 无图像识别依赖 | 设置 `LPR_MOCK_MODE=true` 使用模拟识别 |
| 重置数据库 | 停止后端，删除 `backend/smart_parking.db` 后重启 |

- 默认账号：`admin / admin123`（管理员）、`operator1 / admin123`（操作员）
- 接口文档：`http://localhost:5000/api/docs`
- 自动化测试：`cd backend && python -m unittest discover -s tests -v`（76 项）

## 常见问题

### 1. 依赖安装失败（新版 Python）

若使用 Python 3.12+，旧版固定版本（如 `numpy==1.26.4`）可能无预编译包。V2 已放宽 `requirements.txt` 版本约束，重新执行 `pip install -r requirements.txt` 即可。

### 2. 登录后接口失败

确认后端已启动（`http://localhost:5000`）、前端 Vite 代理正常。

### 3. 黑名单车辆无法入场

这是预期行为：黑名单拦截在入场接口中强制校验，管理员可在"黑名单管理"中解除。

### 4. 月租车离场仍显示费用

仅"生效期内"（生效日期 ≤ 今天 ≤ 到期日期）的月租车套餐内免费；已过期或未生效的月租车按临停计费，请及时续费。

### 5. 车位数量不正确

入场扣减、离场释放，管理员修改总车位数时保留已占用数。V2 首页车位网格与车位表数据实时一致。

## 后续可扩展方向

- 月租到期自动短信/站内提醒，微信小程序车主端。
- 预约车位与真实车位一对一绑定，超时未到自动释放。
- 支持微信/支付宝在线支付，支付完成后自动放行。
- 欠费车辆自动生成账单并推送催缴。
- 多停车场（多场地）架构与总部分级管理。
- 前后端部署到云服务器（Nginx + Gunicorn + MySQL）。
