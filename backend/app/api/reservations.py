"""
车位预约管理接口：
- 预约信息维护（新增、取消、完成、删除）
- 车牌预约校验（供入场业务联动）
"""
from datetime import datetime

from flask import Blueprint, jsonify, request

from app import db
from app.models import ParkingReservation
from app.utils.auth import permission_required, token_required
from app.services.log_service import add_log

reservation_bp = Blueprint("reservation", __name__)


def _parse_dt(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@reservation_bp.route("/", methods=["GET"])
@token_required
def list_reservations(current_user):
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()

    query = ParkingReservation.query
    if keyword:
        query = query.filter(
            db.or_(
                ParkingReservation.plate_number.like(f"%{keyword}%"),
                ParkingReservation.owner_name.like(f"%{keyword}%"),
            )
        )
    if status:
        query = query.filter(ParkingReservation.status == status)

    items = [item.to_dict() for item in query.order_by(ParkingReservation.start_time.desc()).all()]
    return jsonify({"code": 200, "data": items})


@reservation_bp.route("/", methods=["POST"])
@permission_required("reservation:manage")
def create_reservation(current_user):
    data = request.get_json() or {}
    plate_number = data.get("plate_number", "").strip().upper()
    start_time = _parse_dt(data.get("start_time"))
    end_time = _parse_dt(data.get("end_time"))

    if not plate_number:
        return jsonify({"code": 400, "msg": "车牌号不能为空。"}), 400
    if not start_time or not end_time:
        return jsonify({"code": 400, "msg": "请填写预约开始和结束时间。"}), 400
    if end_time <= start_time:
        return jsonify({"code": 400, "msg": "预约结束时间必须晚于开始时间。"}), 400

    # 同一车牌存在未结束的预约时不允许重复预约
    active = ParkingReservation.query.filter(
        ParkingReservation.plate_number == plate_number,
        ParkingReservation.status.in_(["pending", "arrived"]),
    ).first()
    if active:
        return jsonify({"code": 400, "msg": f"车牌 {plate_number} 已有未完成的预约。"}), 400

    reservation = ParkingReservation(
        plate_number=plate_number,
        owner_name=data.get("owner_name", "").strip(),
        phone=data.get("phone", "").strip(),
        start_time=start_time,
        end_time=end_time,
        status="pending",
        remark=data.get("remark", "").strip(),
    )
    db.session.add(reservation)
    add_log("create", f"预约 {plate_number}", f"预约时段 {start_time:%Y-%m-%d %H:%M} ~ {end_time:%H:%M}", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "预约创建成功", "data": reservation.to_dict()})


@reservation_bp.route("/<int:res_id>/status", methods=["PUT"])
@token_required
def update_status(current_user, res_id):
    """变更预约状态：pending->arrived(已入场) / cancelled(取消) / expired(过期)。"""
    reservation = db.get_or_404(ParkingReservation, res_id)
    data = request.get_json() or {}
    status = data.get("status", "").strip()

    if status not in ("arrived", "cancelled", "expired", "pending"):
        return jsonify({"code": 400, "msg": "无效的预约状态。"}), 400

    reservation.status = status
    add_log("update", f"预约 {reservation.plate_number}", f"预约状态变更为 {status}", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "状态更新成功", "data": reservation.to_dict()})


@reservation_bp.route("/<int:res_id>", methods=["DELETE"])
@permission_required("reservation:manage")
def delete_reservation(current_user, res_id):
    reservation = db.get_or_404(ParkingReservation, res_id)
    plate = reservation.plate_number
    db.session.delete(reservation)
    add_log("delete", f"预约 {plate}", "删除预约记录", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "删除成功"})


@reservation_bp.route("/check", methods=["GET"])
@token_required
def check_reservation(current_user):
    """入场业务联动：校验车牌是否在预约时段内。"""
    plate = request.args.get("plate", "").strip().upper()
    if not plate:
        return jsonify({"code": 400, "msg": "车牌号不能为空。"}), 400

    now = datetime.now()
    reservation = ParkingReservation.query.filter(
        ParkingReservation.plate_number == plate,
        ParkingReservation.status == "pending",
        ParkingReservation.start_time <= now,
        ParkingReservation.end_time >= now,
    ).order_by(ParkingReservation.start_time.asc()).first()

    if not reservation:
        return jsonify({"code": 200, "data": {"is_reserved": False}})

    # 预约车辆到场后标记为 arrived
    reservation.status = "arrived"
    db.session.commit()
    return jsonify({"code": 200, "data": {"is_reserved": True, "reservation": reservation.to_dict()}})
