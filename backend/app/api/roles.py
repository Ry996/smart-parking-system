"""角色与权限管理接口（实验四 RBAC 的可演示入口）。

    GET    /api/roles/                  角色列表（含权限矩阵）
    POST   /api/roles/                  新增自定义角色
    PUT    /api/roles/<id>              修改角色名称/描述
    PUT    /api/roles/<id>/permissions  整体替换角色的权限集合
    DELETE /api/roles/<id>              删除自定义角色
    GET    /api/roles/permissions       权限字典（按分组）
    GET    /api/roles/me                当前登录用户的角色与权限

所有写操作都要求 `role:manage` 权限；管理员角色是内置角色，不允许删除，
且必须保留 `role:manage`，避免把系统锁死。
"""
from flask import Blueprint, jsonify, request

from app import db
from app.models import Permission, Role, RolePermission, User
from app.services.log_service import add_log
from app.services.rbac_service import PERMISSION_CATALOG
from app.utils.auth import current_permissions, permission_required, token_required

roles_bp = Blueprint("roles", __name__)


def _role_payload(role: Role) -> dict:
    rows = (
        db.session.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == role.id)
        .all()
    )
    return role.to_dict(permissions=[row[0] for row in rows])


def _find_role(role_id: int) -> Role:
    role = db.session.get(Role, role_id)
    if role is None:
        raise LookupError("角色不存在")
    return role


def _apply_permissions(role: Role, codes: list) -> list:
    known = {permission.code: permission.id for permission in Permission.query.all()}
    ordered = list(dict.fromkeys(str(code) for code in codes))

    unknown = [code for code in ordered if code not in known]
    if unknown:
        raise ValueError(f"存在未知权限：{'、'.join(unknown)}")

    RolePermission.query.filter_by(role_id=role.id).delete()
    for code in ordered:
        db.session.add(RolePermission(role_id=role.id, permission_id=known[code]))

    if role.code == "admin" and "role:manage" not in ordered:
        raise ValueError("管理员角色必须保留 role:manage 权限，否则将无法再管理系统")
    return ordered


@roles_bp.route("/", methods=["GET"])
@permission_required("role:manage")
def list_roles(current_user):
    """角色列表，附带每个角色已授予的权限编码。"""
    roles = Role.query.order_by(Role.id.asc()).all()
    payload = []
    for role in roles:
        data = _role_payload(role)
        data["user_count"] = User.query.filter_by(role=role.code).count()
        payload.append(data)
    return jsonify({"code": 200, "data": payload})


@roles_bp.route("/", methods=["POST"])
@permission_required("role:manage")
def create_role(current_user):
    """新增自定义角色。"""
    data = request.get_json(silent=True) or {}
    code = str(data.get("code") or "").strip()
    name = str(data.get("name") or "").strip()
    description = str(data.get("description") or "").strip()

    if not code or not name:
        return jsonify({"code": 400, "msg": "角色编码和名称不能为空"}), 400
    if not code.replace("_", "").isalnum():
        return jsonify({"code": 400, "msg": "角色编码只能包含字母、数字和下划线"}), 400
    if Role.query.filter_by(code=code).first():
        return jsonify({"code": 400, "msg": "角色编码已存在"}), 400

    role = Role(code=code, name=name, description=description, is_builtin=0)
    db.session.add(role)
    db.session.flush()

    codes = data.get("permissions") or []
    if codes:
        try:
            _apply_permissions(role, list(codes))
        except ValueError as exc:
            db.session.rollback()
            return jsonify({"code": 400, "msg": str(exc)}), 400

    add_log("role_create", code, f"新增角色：{name}", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "创建成功", "data": _role_payload(role)})


@roles_bp.route("/permissions", methods=["GET"])
@permission_required("role:manage")
def list_permissions(current_user):
    """权限字典，按业务分组返回，供前端渲染权限矩阵。"""
    grouped = {}
    for code, name, group, description in PERMISSION_CATALOG:
        grouped.setdefault(group, []).append(
            {"code": code, "name": name, "description": description}
        )
    return jsonify(
        {
            "code": 200,
            "data": {
                "total": len(PERMISSION_CATALOG),
                "groups": [{"group": group, "items": items} for group, items in grouped.items()],
            },
        }
    )


@roles_bp.route("/me", methods=["GET"])
@token_required
def my_permissions(current_user):
    """当前登录用户的角色与权限，前端据此控制菜单与按钮。"""
    granted = sorted(current_permissions(current_user))
    role = Role.query.filter_by(code=current_user.role).first()
    return jsonify(
        {
            "code": 200,
            "data": {
                "role": current_user.role,
                "roleName": role.name if role else current_user.role,
                "permissions": granted,
                "isAdmin": current_user.role == "admin",
            },
        }
    )


@roles_bp.route("/<int:role_id>", methods=["PUT"])
@permission_required("role:manage")
def update_role(current_user, role_id):
    """修改角色名称与描述。"""
    try:
        role = _find_role(role_id)
    except LookupError as exc:
        return jsonify({"code": 404, "msg": str(exc)}), 404

    data = request.get_json(silent=True) or {}
    if data.get("name"):
        role.name = str(data["name"]).strip()
    if "description" in data:
        role.description = str(data.get("description") or "").strip()

    add_log("role_update", role.code, f"修改角色：{role.name}", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "更新成功", "data": _role_payload(role)})


@roles_bp.route("/<int:role_id>/permissions", methods=["PUT"])
@permission_required("role:manage")
def set_role_permissions(current_user, role_id):
    """整体替换角色的权限集合。"""
    try:
        role = _find_role(role_id)
    except LookupError as exc:
        return jsonify({"code": 404, "msg": str(exc)}), 404

    data = request.get_json(silent=True) or {}
    codes = data.get("permissions")
    if not isinstance(codes, list):
        return jsonify({"code": 400, "msg": "permissions 必须是权限编码数组"}), 400

    try:
        _apply_permissions(role, codes)
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"code": 400, "msg": str(exc)}), 400

    add_log("role_permissions", role.code, f"更新权限：{len(codes)} 项", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "权限已更新", "data": _role_payload(role)})


@roles_bp.route("/<int:role_id>", methods=["DELETE"])
@permission_required("role:manage")
def delete_role(current_user, role_id):
    """删除自定义角色（内置角色与在用角色不可删）。"""
    try:
        role = _find_role(role_id)
    except LookupError as exc:
        return jsonify({"code": 404, "msg": str(exc)}), 404

    if role.is_builtin:
        return jsonify({"code": 400, "msg": "内置角色不允许删除"}), 400
    if User.query.filter_by(role=role.code).count() > 0:
        return jsonify({"code": 400, "msg": "该角色仍有用户在用，无法删除"}), 400

    RolePermission.query.filter_by(role_id=role.id).delete()
    db.session.delete(role)
    add_log("role_delete", role.code, f"删除角色：{role.name}", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "删除成功"})
