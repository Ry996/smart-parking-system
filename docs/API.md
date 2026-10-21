# 智慧停车场管理系统 API

V2.2 在 V2.1 基础上补齐：RBAC 角色权限、提示注入防护、RAG 知识库问答、AI 调用留痕与人工复核反馈。

所有业务接口统一返回 `{code, msg, data}`；认证方式为 `Authorization: Bearer <token>`。

- 版本：2.2.0
- 服务地址：http://localhost:5000
- 认证：`Authorization: Bearer <token>`

> 本文档由 `tools/gen_openapi.py` 从 Flask 路由自动生成，改代码后重新生成即可。

## AI 能力

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| POST | `/api/ai/ask` | 基于知识库的 RAG 问答，答案带引用来源。 | Bearer |
| GET | `/api/ai/calls` | 查看大模型调用留痕（模型、提示词版本、耗时、错误）。 | Bearer |
| POST | `/api/ai/feedback` | 提交一条 AI 输出的人工复核记录（幻觉案例沉淀）。 | Bearer |
| GET | `/api/ai/feedback` | 查看已沉淀的 AI 复核案例，可直接用于实验报告。 | Bearer |
| POST | `/api/ai/reindex` | 重建知识库向量索引（修改 knowledge/*.md 后调用）。 | Bearer |
| GET | `/api/ai/status` | 查询大模型与知识库的当前状态。 | Bearer |

### POST /api/ai/ask

基于知识库的 RAG 问答，答案带引用来源。

所需权限：`ai:ask`

### GET /api/ai/calls

查看大模型调用留痕（模型、提示词版本、耗时、错误）。

所需权限：`ai:feedback:read`

### POST /api/ai/feedback

提交一条 AI 输出的人工复核记录（幻觉案例沉淀）。

### GET /api/ai/feedback

查看已沉淀的 AI 复核案例，可直接用于实验报告。

所需权限：`ai:feedback:read`

### POST /api/ai/reindex

重建知识库向量索引（修改 knowledge/*.md 后调用）。

所需权限：`ai:manage`

### GET /api/ai/status

查询大模型与知识库的当前状态。

## 停车业务

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| POST | `/api/parking/<int:record_id>/pay` | 模拟在线支付：将待支付记录置为已支付。 | Bearer |
| POST | `/api/parking/enter` | POST /api/parking/enter | Bearer |
| POST | `/api/parking/exit` | POST /api/parking/exit | Bearer |
| POST | `/api/parking/exit-preview` | POST /api/parking/exit-preview | Bearer |
| GET | `/api/parking/parked` | GET /api/parking/parked | Bearer |
| GET | `/api/parking/spaces` | GET /api/parking/spaces | Bearer |
| PUT | `/api/parking/spaces` | PUT /api/parking/spaces | Bearer |

### POST /api/parking/<int:record_id>/pay

模拟在线支付：将待支付记录置为已支付。

所需权限：`parking:operate`

路径参数：`record_id`(integer)

### POST /api/parking/enter

POST /api/parking/enter

所需权限：`parking:operate`

### POST /api/parking/exit

POST /api/parking/exit

所需权限：`parking:operate`

### POST /api/parking/exit-preview

POST /api/parking/exit-preview

所需权限：`parking:operate`

### GET /api/parking/parked

GET /api/parking/parked

### GET /api/parking/spaces

GET /api/parking/spaces

### PUT /api/parking/spaces

PUT /api/parking/spaces

所需权限：`space:manage`

## 停车记录

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/records/` | GET /api/records/ | Bearer |
| GET | `/api/records/<int:record_id>` | GET /api/records/<int:record_id> | Bearer |
| PUT | `/api/records/<int:record_id>/remark` | PUT /api/records/<int:record_id>/remark | Bearer |

### GET /api/records/

GET /api/records/

### GET /api/records/<int:record_id>

GET /api/records/<int:record_id>

路径参数：`record_id`(integer)

### PUT /api/records/<int:record_id>/remark

PUT /api/records/<int:record_id>/remark

路径参数：`record_id`(integer)

## 操作日志

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/logs/` | GET /api/logs/ | Bearer |

### GET /api/logs/

GET /api/logs/

所需权限：`log:read`

## 收费规则

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/fee-rules/` | GET /api/fee-rules/ | Bearer |
| POST | `/api/fee-rules/` | POST /api/fee-rules/ | Bearer |
| PUT | `/api/fee-rules/<int:rule_id>` | PUT /api/fee-rules/<int:rule_id> | Bearer |
| DELETE | `/api/fee-rules/<int:rule_id>` | DELETE /api/fee-rules/<int:rule_id> | Bearer |

### GET /api/fee-rules/

GET /api/fee-rules/

### POST /api/fee-rules/

POST /api/fee-rules/

所需权限：`fee:manage`

### PUT /api/fee-rules/<int:rule_id>

PUT /api/fee-rules/<int:rule_id>

所需权限：`fee:manage`

路径参数：`rule_id`(integer)

### DELETE /api/fee-rules/<int:rule_id>

DELETE /api/fee-rules/<int:rule_id>

所需权限：`fee:manage`

路径参数：`rule_id`(integer)

## 数据导出

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/export/monthly` | 导出月租台账 CSV。 | Bearer |
| GET | `/api/export/records` | 导出停车记录 CSV，支持与记录页一致的筛选条件。 | Bearer |

### GET /api/export/monthly

导出月租台账 CSV。

所需权限：`export:data`

### GET /api/export/records

导出停车记录 CSV，支持与记录页一致的筛选条件。

所需权限：`export:data`

## 数据统计

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/stats/ai-advice` | GET /api/stats/ai-advice | Bearer |
| GET | `/api/stats/flow` | GET /api/stats/flow | Bearer |
| GET | `/api/stats/income` | GET /api/stats/income | Bearer |
| GET | `/api/stats/overview` | GET /api/stats/overview | Bearer |

### GET /api/stats/ai-advice

GET /api/stats/ai-advice

所需权限：`ai:advice`

### GET /api/stats/flow

GET /api/stats/flow

### GET /api/stats/income

GET /api/stats/income

### GET /api/stats/overview

GET /api/stats/overview

## 月租管理

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/monthly/` | 列表查询，支持按车牌/状态筛选。 | Bearer |
| POST | `/api/monthly/` | POST /api/monthly/ | Bearer |
| PUT | `/api/monthly/<int:sub_id>` | PUT /api/monthly/<int:sub_id> | Bearer |
| DELETE | `/api/monthly/<int:sub_id>` | DELETE /api/monthly/<int:sub_id> | Bearer |
| POST | `/api/monthly/<int:sub_id>/renew` | 续费：在现有到期日基础上顺延，或直接指定新的到期日期。 | Bearer |
| GET | `/api/monthly/check` | 查询车牌是否为月租车辆（入场/离场业务联动使用）。 | Bearer |

### GET /api/monthly/

列表查询，支持按车牌/状态筛选。

### POST /api/monthly/

POST /api/monthly/

所需权限：`monthly:manage`

### PUT /api/monthly/<int:sub_id>

PUT /api/monthly/<int:sub_id>

所需权限：`monthly:manage`

路径参数：`sub_id`(integer)

### DELETE /api/monthly/<int:sub_id>

DELETE /api/monthly/<int:sub_id>

所需权限：`monthly:manage`

路径参数：`sub_id`(integer)

### POST /api/monthly/<int:sub_id>/renew

续费：在现有到期日基础上顺延，或直接指定新的到期日期。

所需权限：`monthly:manage`

路径参数：`sub_id`(integer)

### GET /api/monthly/check

查询车牌是否为月租车辆（入场/离场业务联动使用）。

## 用户管理

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/users/` | GET /api/users/ | Bearer |
| POST | `/api/users/` | POST /api/users/ | Bearer |
| PUT | `/api/users/<int:user_id>` | PUT /api/users/<int:user_id> | Bearer |
| DELETE | `/api/users/<int:user_id>` | DELETE /api/users/<int:user_id> | Bearer |

### GET /api/users/

GET /api/users/

所需权限：`user:manage`

### POST /api/users/

POST /api/users/

所需权限：`user:manage`

### PUT /api/users/<int:user_id>

PUT /api/users/<int:user_id>

所需权限：`user:manage`

路径参数：`user_id`(integer)

### DELETE /api/users/<int:user_id>

DELETE /api/users/<int:user_id>

所需权限：`user:manage`

路径参数：`user_id`(integer)

## 角色权限

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/roles/` | 角色列表，附带每个角色已授予的权限编码。 | Bearer |
| POST | `/api/roles/` | 新增自定义角色。 | Bearer |
| PUT | `/api/roles/<int:role_id>` | 修改角色名称与描述。 | Bearer |
| DELETE | `/api/roles/<int:role_id>` | 删除自定义角色（内置角色与在用角色不可删）。 | Bearer |
| PUT | `/api/roles/<int:role_id>/permissions` | 整体替换角色的权限集合。 | Bearer |
| GET | `/api/roles/me` | 当前登录用户的角色与权限，前端据此控制菜单与按钮。 | Bearer |
| GET | `/api/roles/permissions` | 权限字典，按业务分组返回，供前端渲染权限矩阵。 | Bearer |

### GET /api/roles/

角色列表，附带每个角色已授予的权限编码。

所需权限：`role:manage`

### POST /api/roles/

新增自定义角色。

所需权限：`role:manage`

### PUT /api/roles/<int:role_id>

修改角色名称与描述。

所需权限：`role:manage`

路径参数：`role_id`(integer)

### DELETE /api/roles/<int:role_id>

删除自定义角色（内置角色与在用角色不可删）。

所需权限：`role:manage`

路径参数：`role_id`(integer)

### PUT /api/roles/<int:role_id>/permissions

整体替换角色的权限集合。

所需权限：`role:manage`

路径参数：`role_id`(integer)

### GET /api/roles/me

当前登录用户的角色与权限，前端据此控制菜单与按钮。

### GET /api/roles/permissions

权限字典，按业务分组返回，供前端渲染权限矩阵。

所需权限：`role:manage`

## 认证

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| POST | `/api/auth/change-password` | POST /api/auth/change-password | Bearer |
| GET | `/api/auth/info` | GET /api/auth/info | Bearer |
| POST | `/api/auth/login` | POST /api/auth/login | 公开 |

### POST /api/auth/change-password

POST /api/auth/change-password

### GET /api/auth/info

GET /api/auth/info

### POST /api/auth/login

POST /api/auth/login

## 车位预约

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/reservations/` | GET /api/reservations/ | Bearer |
| POST | `/api/reservations/` | POST /api/reservations/ | Bearer |
| DELETE | `/api/reservations/<int:res_id>` | DELETE /api/reservations/<int:res_id> | Bearer |
| PUT | `/api/reservations/<int:res_id>/status` | 变更预约状态：pending->arrived(已入场) / cancelled(取消) / expired(过期)。 | Bearer |
| GET | `/api/reservations/check` | 入场业务联动：校验车牌是否在预约时段内。 | Bearer |

### GET /api/reservations/

GET /api/reservations/

### POST /api/reservations/

POST /api/reservations/

所需权限：`reservation:manage`

### DELETE /api/reservations/<int:res_id>

DELETE /api/reservations/<int:res_id>

所需权限：`reservation:manage`

路径参数：`res_id`(integer)

### PUT /api/reservations/<int:res_id>/status

变更预约状态：pending->arrived(已入场) / cancelled(取消) / expired(过期)。

路径参数：`res_id`(integer)

### GET /api/reservations/check

入场业务联动：校验车牌是否在预约时段内。

## 车牌识别

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/lpr/mode` | GET /api/lpr/mode | Bearer |
| POST | `/api/lpr/recognize` | POST /api/lpr/recognize | Bearer |

### GET /api/lpr/mode

GET /api/lpr/mode

### POST /api/lpr/recognize

POST /api/lpr/recognize

## 黑名单

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/api/blacklist/` | GET /api/blacklist/ | Bearer |
| POST | `/api/blacklist/` | POST /api/blacklist/ | Bearer |
| PUT | `/api/blacklist/<int:entry_id>` | PUT /api/blacklist/<int:entry_id> | Bearer |
| DELETE | `/api/blacklist/<int:entry_id>` | DELETE /api/blacklist/<int:entry_id> | Bearer |
| GET | `/api/blacklist/check` | 入场业务联动：校验车牌是否被拉黑。 | Bearer |

### GET /api/blacklist/

GET /api/blacklist/

### POST /api/blacklist/

POST /api/blacklist/

所需权限：`blacklist:manage`

### PUT /api/blacklist/<int:entry_id>

PUT /api/blacklist/<int:entry_id>

所需权限：`blacklist:manage`

路径参数：`entry_id`(integer)

### DELETE /api/blacklist/<int:entry_id>

DELETE /api/blacklist/<int:entry_id>

所需权限：`blacklist:manage`

路径参数：`entry_id`(integer)

### GET /api/blacklist/check

入场业务联动：校验车牌是否被拉黑。
