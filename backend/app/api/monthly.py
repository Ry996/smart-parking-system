"""
月租车辆管理接口：
- 月租套餐维护（新增、续费、修改、删除）
- 车牌月租状态查询（供入场/离场业务联动）
"""
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from app import db
from app.models import MonthlySubscriber
from app.utils.auth import permission_required, token_required
from app.services.log_service import add_log

monthly_bp = Blueprint("monthly", __name__)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@monthly_bp.route("/", methods=["GET"])
@token_required
def list_subscribers(current_user):
    """列表查询，支持按车牌/状态筛选。"""
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()

    query = MonthlySubscriber.query
    if keyword:
        query = query.filter(
            db.or_(
                MonthlySubscriber.plate_number.like(f"%{keyword}%"),
                MonthlySubscriber.owner_name.like(f"%{keyword}%"),
                MonthlySubscriber.phone.like(f"%{keyword}%"),
            )
        )

    items = [item.to_dict() for item in query.order_by(MonthlySubscriber.id.desc()).all()]
    if status:
        items = [item for item in items if item["status"] == status]

    return jsonify({"code": 200, "data": items})


@monthly_bp.route("/", methods=["POST"])
@permission_required("monthly:manage")
def create_subscriber(current_user):
    data = request.get_json() or {}
    plate_number = data.get("plate_number", "").strip().upper()
    start_date = _parse_date(data.get("start_date"))
    end_date = _parse_date(data.get("end_date"))

    if not plate_number:
        return jsonify({"code": 400, "msg": "车牌号不能为空。"}), 400
    if MonthlySubscriber.query.filter_by(plate_number=plate_number).first():
        return jsonify({"code": 400, "msg": f"车牌 {plate_number} 已是月租车辆，请直接续费。"}), 400
    if not start_date or not end_date:
        return jsonify({"code": 400, "msg": "请填写生效日期和到期日期。"}), 400
    if end_date < start_date:
        return jsonify({"code": 400, "msg": "到期日期不能早于生效日期。"}), 400

    subscriber = MonthlySubscriber(
        plate_number=plate_number,
        owner_name=data.get("owner_name", "").strip() or plate_number,
        phone=data.get("phone", "").strip(),
        package_name=data.get("package_name", "标准月租").strip() or "标准月租",
        start_date=start_date,
        end_date=end_date,
        fee=data.get("fee") if data.get("fee") is not None else 0,
        remark=data.get("remark", "").strip(),
    )
    db.session.add(subscriber)
    add_log("create", f"月租车辆 {plate_number}", f"新增月租套餐：{subscriber.package_name}", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "月租车辆创建成功", "data": subscriber.to_dict()})


@monthly_bp.route("/<int:sub_id>/renew", methods=["POST"])
@permission_required("monthly:manage")
def renew_subscriber(current_user, sub_id):
    """续费：在现有到期日基础上顺延，或直接指定新的到期日期。"""
    subscriber = db.get_or_404(MonthlySubscriber, sub_id)
    data = request.get_json() or {}
    new_end = _parse_date(data.get("end_date"))

    if new_end:
        if new_end <= subscriber.end_date:
            return jsonify({"code": 400, "msg": "新的到期日期必须晚于当前到期日期。"}), 400
        subscriber.end_date = new_end
    else:
        months = int(data.get("months", 1))
        if months < 1:
            return jsonify({"code": 400, "msg": "续费月数必须大于 0。"}), 400
        subscriber.end_date = subscriber.end_date + timedelta(days=30 * months)

    if data.get("fee") is not None:
        subscriber.fee = data["fee"]
    if data.get("remark") is not None:
        subscriber.remark = data["remark"]

    add_log("update", f"月租车辆 {subscriber.plate_number}", f"续费至 {subscriber.end_date}", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "续费成功", "data": subscriber.to_dict()})


@monthly_bp.route("/<int:sub_id>", methods=["PUT"])
@permission_required("monthly:manage")
def update_subscriber(current_user, sub_id):
    subscriber = db.get_or_404(MonthlySubscriber, sub_id)
    data = request.get_json() or {}

    for field in ["owner_name", "phone", "package_name", "fee", "remark"]:
        if field in data:
            setattr(subscriber, field, data[field])
    if "start_date" in data:
        d = _parse_date(data["start_date"])
        if d:
            subscriber.start_date = d
    if "end_date" in data:
        d = _parse_date(data["end_date"])
        if d:
            subscriber.end_date = d

    add_log("update", f"月租车辆 {subscriber.plate_number}", "更新月租信息", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "更新成功", "data": subscriber.to_dict()})


@monthly_bp.route("/<int:sub_id>", methods=["DELETE"])
@permission_required("monthly:manage")
def delete_subscriber(current_user, sub_id):
    subscriber = db.get_or_404(MonthlySubscriber, sub_id)
    plate = subscriber.plate_number
    db.session.delete(subscriber)
    add_log("delete", f"月租车辆 {plate}", "删除月租记录", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "删除成功"})


@monthly_bp.route("/check", methods=["GET"])
@token_required
def check_subscriber(current_user):
    """查询车牌是否为月租车辆（入场/离场业务联动使用）。"""
    plate = request.args.get("plate", "").strip().upper()
    if not plate:
        return jsonify({"code": 400, "msg": "车牌号不能为空。"}), 400

    subscriber = MonthlySubscriber.query.filter_by(plate_number=plate).first()
    if not subscriber:
        return jsonify({"code": 200, "data": {"is_monthly": False}})

    data = subscriber.to_dict()
    return jsonify({"code": 200, "data": {"is_monthly": True, "subscriber": data}})
