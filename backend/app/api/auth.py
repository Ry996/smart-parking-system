from flask import Blueprint, jsonify, request

from app import db
from app.models import User
from app.utils.auth import check_password, generate_token, hash_password, token_required
from app.services.log_service import add_log

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"code": 400, "msg": "用户名和密码不能为空。"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password(password, user.password):
        add_log("login_fail", username, "登录失败：用户名或密码错误")
        db.session.commit()
        return jsonify({"code": 401, "msg": "用户名或密码错误。"}), 401

    if user.status != 1:
        add_log("login_fail", username, "登录失败：账号已被禁用")
        db.session.commit()
        return jsonify({"code": 403, "msg": "账号已被禁用。"}), 403

    token = generate_token(user.id, user.role)
    add_log("login", username, "登录成功", user=user)
    db.session.commit()
    return jsonify({
        "code": 200,
        "msg": "登录成功",
        "data": {
            "token": token,
            "user_id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "role": user.role,
        },
    })


@auth_bp.route("/info", methods=["GET"])
@token_required
def get_info(current_user):
    return jsonify({"code": 200, "data": current_user.to_dict()})


@auth_bp.route("/change-password", methods=["POST"])
@token_required
def change_password(current_user):
    data = request.get_json() or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return jsonify({"code": 400, "msg": "请完整填写原密码和新密码。"}), 400

    if not check_password(old_password, current_user.password):
        return jsonify({"code": 400, "msg": "原密码错误。"}), 400

    current_user.password = hash_password(new_password)
    db.session.commit()
    return jsonify({"code": 200, "msg": "密码修改成功。"})
