from flask import Blueprint, request, jsonify
from app import db
from app.models import User
from app.utils.auth import hash_password, permission_required

users_bp = Blueprint('users', __name__)


def _normalize_status(value, default=1):
    try:
        return 1 if int(value) else 0
    except (TypeError, ValueError):
        return default


@users_bp.route('/', methods=['GET'])
@permission_required('user:manage')
def list_users(current_user):
    users = User.query.order_by(User.id.asc()).all()
    return jsonify({'code': 200, 'data': [u.to_dict() for u in users]})


@users_bp.route('/', methods=['POST'])
@permission_required('user:manage')
def create_user(current_user):
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role     = data.get('role', 'operator')
    status   = _normalize_status(data.get('status', 1))

    if not username or not password:
        return jsonify({'code': 400, 'msg': '用户名和密码不能为空'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'code': 400, 'msg': '用户名已存在'}), 400

    user = User(
        username  = username,
        password  = hash_password(password),
        real_name = data.get('real_name', username),
        role      = role,
        status    = status,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '创建成功', 'data': user.to_dict()})


@users_bp.route('/<int:user_id>', methods=['PUT'])
@permission_required('user:manage')
def update_user(current_user, user_id):
    user = db.get_or_404(User, user_id)
    data = request.get_json() or {}

    if 'real_name' in data:
        user.real_name = data['real_name']
    if 'role' in data:
        user.role = data['role']
    if 'status' in data:
        user.status = _normalize_status(data['status'], user.status)
    if 'password' in data and data['password']:
        user.password = hash_password(data['password'])

    db.session.commit()
    return jsonify({'code': 200, 'msg': '更新成功', 'data': user.to_dict()})


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@permission_required('user:manage')
def delete_user(current_user, user_id):
    if user_id == current_user.id:
        return jsonify({'code': 400, 'msg': '不能删除自己'}), 400
    user = db.get_or_404(User, user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'code': 200, 'msg': '删除成功'})
