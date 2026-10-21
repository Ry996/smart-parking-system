"""认证与授权工具：密码哈希、JWT 签发校验、RBAC 权限校验。

实验四（登录、权限与 AI 安全）对应关系：
- 密码安全：bcrypt 加盐哈希（不可逆，绝不存明文）；
- 身份认证：JWT(HS256) 签发与校验，Token 过期自动失效；
- 接口授权：token_required / admin_required / permission_required 三级装饰器，
  等价于 Spring Security 的 @PreAuthorize，最终以后端校验为准，前端菜单隐藏只是体验优化；
- 权限模型：用户在 users.role 上保存角色编码，角色与权限的对应关系落在
  roles / permissions / role_permissions 三张表中。
"""
import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps

from flask import current_app, jsonify, request

from app import db
from app.models import Permission, Role, RolePermission, User


# 装饰器在被包装函数上留下的元数据键，OpenAPI 生成器据此标注鉴权要求
AUTH_META_KEY = "__auth_meta__"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def generate_token(user_id: int, role: str) -> str:
    payload = {
        'user_id': user_id,
        'role':    role,
        'exp':     datetime.utcnow() + timedelta(hours=current_app.config['JWT_EXPIRATION_HOURS']),
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def decode_token(token: str):
    return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])


def _bearer_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    return None


def _resolve_user():
    """解析 Bearer Token 并加载用户，返回 (user, error_response)。"""
    token = _bearer_token()
    if not token:
        return None, (jsonify({'code': 401, 'msg': '未提供认证Token'}), 401)
    try:
        data = decode_token(token)
        current_user = db.session.get(User, data['user_id'])
    except Exception as exc:
        return None, (jsonify({'code': 401, 'msg': f'Token无效: {str(exc)}'}), 401)
    if not current_user or current_user.status != 1:
        return None, (jsonify({'code': 401, 'msg': '用户不存在或已禁用'}), 401)
    return current_user, None


def current_permissions(user) -> set:
    """查询用户所属角色被授予的权限编码集合。"""
    if user is None:
        return set()
    role = Role.query.filter_by(code=user.role).first()
    if role is None:
        return set()
    rows = (
        db.session.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == role.id)
        .all()
    )
    return {row[0] for row in rows}


def has_permission(user, permission_code: str) -> bool:
    return permission_code in current_permissions(user)


def _mark(func, **meta):
    setattr(func, AUTH_META_KEY, meta)
    return func


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user, error = _resolve_user()
        if error:
            return error
        return f(current_user, *args, **kwargs)

    return _mark(decorated, auth=True)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        current_user, error = _resolve_user()
        if error:
            return error
        if current_user.role != 'admin':
            return jsonify({'code': 403, 'msg': '权限不足，需要管理员权限'}), 403
        return f(current_user, *args, **kwargs)

    return _mark(decorated, auth=True, role='admin')


def permission_required(permission_code: str):
    """按 RBAC 权限编码校验接口访问权限。

    权限表尚未初始化时回退到历史角色判断（admin 放行），避免升级过程中把系统锁死。
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            current_user, error = _resolve_user()
            if error:
                return error

            granted = current_permissions(current_user)
            if not granted:
                if current_user.role == 'admin':
                    return f(current_user, *args, **kwargs)
                return jsonify({'code': 403, 'msg': f'权限不足，需要权限：{permission_code}'}), 403

            if permission_code not in granted:
                return jsonify({'code': 403, 'msg': f'权限不足，需要权限：{permission_code}'}), 403
            return f(current_user, *args, **kwargs)

        return _mark(decorated, auth=True, permission=permission_code)

    return decorator
