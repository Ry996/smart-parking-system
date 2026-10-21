"""RBAC 种子数据与权限目录。

权限编码设计：`资源:动作`，例如 parking:operate、user:manage。
管理员默认拥有全部权限；操作员只拥有日常值守所需权限，
这样"前端隐藏菜单 + 后端 permission_required 校验"两层控制才有意义。
"""
from app import db
from app.models import Permission, Role, RolePermission

# (权限编码, 中文名, 分组, 说明)
PERMISSION_CATALOG = [
    ("parking:operate",      "车辆入离场",     "停车业务", "车辆入场、离场、在场查询、车位查看"),
    ("parking:record:read",  "停车记录查询",   "停车业务", "查询停车记录、详情与备注"),
    ("space:manage",         "车位管理",       "停车业务", "修改总车位数与可用车位"),
    ("stats:read",           "数据统计",       "数据分析", "车流量、收入趋势与首页概览"),
    ("export:data",          "数据导出",       "数据分析", "导出停车记录与月租台账 CSV"),
    ("ai:advice",            "AI 运营建议",    "AI 能力",  "生成运营分析建议"),
    ("ai:ask",               "知识库问答",     "AI 能力",  "使用 RAG 知识库问答"),
    ("ai:feedback:read",     "AI 案例查看",    "AI 能力",  "查看 AI 复核案例与调用留痕"),
    ("ai:manage",            "AI 知识库管理",  "AI 能力",  "重建知识库向量索引"),
    ("fee:manage",           "收费规则管理",   "运营管理", "新增、修改、删除收费规则"),
    ("monthly:manage",       "月租车辆管理",   "运营管理", "月租车辆的增删改与续费"),
    ("reservation:manage",   "车位预约管理",   "运营管理", "预约的创建、状态变更与删除"),
    ("blacklist:manage",     "黑名单管理",     "运营管理", "黑名单增删改，入场时拦截"),
    ("user:manage",          "用户管理",       "系统管理", "用户的增删改与角色调整"),
    ("role:manage",          "角色权限管理",   "系统管理", "角色与权限矩阵的维护"),
    ("log:read",             "操作日志查看",   "系统管理", "查看系统审计日志"),
    ("system:docs",          "接口文档查看",   "系统管理", "查看 OpenAPI 接口文档"),
]

ROLE_DEFINITIONS = [
    {
        "code": "admin",
        "name": "管理员",
        "description": "系统配置与运营管理，拥有全部权限",
        "is_builtin": 1,
    },
    {
        "code": "operator",
        "name": "操作员",
        "description": "停车场出入口值守，只负责日常入离场与查询",
        "is_builtin": 1,
    },
]

ADMIN_PERMISSIONS = [code for code, _, _, _ in PERMISSION_CATALOG]

OPERATOR_PERMISSIONS = [
    "parking:operate",
    "parking:record:read",
    "stats:read",
    "ai:advice",
    "ai:ask",
]

DEFAULT_ROLE_PERMISSIONS = {
    "admin": ADMIN_PERMISSIONS,
    "operator": OPERATOR_PERMISSIONS,
}


def seed_rbac() -> dict:
    """幂等初始化权限、角色与角色-权限映射。"""
    permissions = {}
    for code, name, group, description in PERMISSION_CATALOG:
        permission = Permission.query.filter_by(code=code).first()
        if permission is None:
            permission = Permission(code=code)
            db.session.add(permission)
        permission.name = name
        permission.group_name = group
        permission.description = description
        permissions[code] = permission
    db.session.flush()

    roles = {}
    for definition in ROLE_DEFINITIONS:
        role = Role.query.filter_by(code=definition["code"]).first()
        if role is None:
            role = Role(code=definition["code"])
            db.session.add(role)
        role.name = definition["name"]
        role.description = definition["description"]
        role.is_builtin = definition["is_builtin"]
        roles[definition["code"]] = role
    db.session.flush()

    for role_code, granted in DEFAULT_ROLE_PERMISSIONS.items():
        role = roles[role_code]
        RolePermission.query.filter_by(role_id=role.id).delete()
        for code in granted:
            permission = permissions.get(code)
            if permission is not None:
                db.session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db.session.commit()
    return {
        "roles": len(ROLE_DEFINITIONS),
        "permissions": len(PERMISSION_CATALOG),
        "mappings": sum(len(value) for value in DEFAULT_ROLE_PERMISSIONS.values()),
    }


def permission_matrix() -> dict:
    """返回 {角色编码: [权限编码]}，供接口文档和报告使用。"""
    roles = Role.query.order_by(Role.id.asc()).all()
    result = {}
    for role in roles:
        rows = (
            db.session.query(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id == role.id)
            .all()
        )
        result[role.code] = [row[0] for row in rows]
    return result
