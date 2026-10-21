"""
黑名单管理接口：
- 黑名单维护（加入、解除、修改、删除）
- 车牌黑名单校验（供入场业务联动）
"""
from flask import Blueprint, jsonify, request

from app import db
from app.models import Blacklist
from app.utils.auth import permission_required, token_required
from app.services.log_service import add_log

blacklist_bp = Blueprint("blacklist", __name__)


@blacklist_bp.route("/", methods=["GET"])
@token_required
def list_blacklist(current_user):
    keyword = request.args.get("keyword", "").strip()
    query = Blacklist.query
    if keyword:
        query = query.filter(Blacklist.plate_number.like(f"%{keyword}%"))
    items = [item.to_dict() for item in query.order_by(Blacklist.id.desc()).all()]
    return jsonify({"code": 200, "data": items})


@blacklist_bp.route("/", methods=["POST"])
@permission_required("blacklist:manage")
def create_blacklist(current_user):
    data = request.get_json() or {}
    plate_number = data.get("plate_number", "").strip().upper()

    if not plate_number:
        return jsonify({"code": 400, "msg": "车牌号不能为空。"}), 400
    if Blacklist.query.filter_by(plate_number=plate_number).first():
        return jsonify({"code": 400, "msg": f"车牌 {plate_number} 已在黑名单中。"}), 400

    entry = Blacklist(
        plate_number=plate_number,
        reason=data.get("reason", "").strip() or "欠费/逃费",
        debt_amount=data.get("debt_amount") if data.get("debt_amount") is not None else 0,
        is_active=1,
    )
    db.session.add(entry)
    add_log("create", f"黑名单 {plate_number}", f"拉黑原因：{entry.reason}", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "已加入黑名单", "data": entry.to_dict()})


@blacklist_bp.route("/<int:entry_id>", methods=["PUT"])
@permission_required("blacklist:manage")
def update_blacklist(current_user, entry_id):
    entry = db.get_or_404(Blacklist, entry_id)
    data = request.get_json() or {}

    for field in ["reason", "debt_amount"]:
        if field in data:
            setattr(entry, field, data[field])
    if "is_active" in data:
        entry.is_active = 1 if int(data["is_active"]) else 0

    add_log("update", f"黑名单 {entry.plate_number}", "更新黑名单信息", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "更新成功", "data": entry.to_dict()})


@blacklist_bp.route("/<int:entry_id>", methods=["DELETE"])
@permission_required("blacklist:manage")
def delete_blacklist(current_user, entry_id):
    entry = db.get_or_404(Blacklist, entry_id)
    plate = entry.plate_number
    db.session.delete(entry)
    add_log("delete", f"黑名单 {plate}", "解除黑名单", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "已解除黑名单"})


@blacklist_bp.route("/check", methods=["GET"])
@token_required
def check_blacklist(current_user):
    """入场业务联动：校验车牌是否被拉黑。"""
    plate = request.args.get("plate", "").strip().upper()
    if not plate:
        return jsonify({"code": 400, "msg": "车牌号不能为空。"}), 400

    entry = Blacklist.query.filter_by(plate_number=plate, is_active=1).first()
    if not entry:
        return jsonify({"code": 200, "data": {"is_blocked": False}})
    return jsonify({"code": 200, "data": {"is_blocked": True, "entry": entry.to_dict()}})
