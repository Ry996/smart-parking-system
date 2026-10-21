from datetime import datetime

from flask import Blueprint, jsonify, request

from app import db
from app.models import Blacklist, MonthlySubscriber, ParkingRecord, ParkingReservation, ParkingSpace
from app.services.fee_service import calculate_fee
from app.services.log_service import add_log
from app.utils.auth import permission_required, token_required

parking_bp = Blueprint("parking", __name__)


def _is_valid_monthly(plate_number: str) -> bool:
    """判断车牌是否为生效中的月租车辆。"""
    subscriber = MonthlySubscriber.query.filter_by(plate_number=plate_number).first()
    if not subscriber:
        return False
    today = datetime.utcnow().date()
    return subscriber.start_date <= today <= subscriber.end_date


def _parking_preview(record: ParkingRecord) -> dict:
    now = datetime.now()
    duration = max(int((now - record.entry_time).total_seconds() / 60), 0)
    fee = calculate_fee(duration)
    preview = {
        "record": record.to_dict(),
        "duration": duration,
        "fee": fee,
        "duration_text": f"{duration // 60}小时{duration % 60}分钟" if duration >= 60 else f"{duration}分钟",
    }
    # 月租车辆：套餐内停车不再按临停计费
    if _is_valid_monthly(record.plate_number):
        preview["fee"] = 0.0
        preview["is_monthly"] = True
        preview["monthly_tip"] = "月租车辆，套餐内离场不额外收费。"
    else:
        preview["is_monthly"] = False
    return preview


@parking_bp.route("/enter", methods=["POST"])
@permission_required("parking:operate")
def vehicle_enter(current_user):
    data = request.get_json() or {}
    plate_number = data.get("plate_number", "").strip().upper()
    plate_type = data.get("plate_type", "blue")
    entry_image = data.get("entry_image", "")
    entry_method = data.get("entry_method", "manual")

    if not plate_number:
        return jsonify({"code": 400, "msg": "车牌号不能为空。"}), 400

    # 黑名单拦截
    blacklisted = Blacklist.query.filter_by(plate_number=plate_number, is_active=1).first()
    if blacklisted:
        add_log("block", f"入场拦截 {plate_number}", f"黑名单车辆被拦截，原因：{blacklisted.reason}", user=current_user)
        db.session.commit()
        return jsonify({"code": 403, "msg": f"车辆 {plate_number} 在黑名单中（{blacklisted.reason}），禁止入场。"}), 403

    existing = ParkingRecord.query.filter_by(plate_number=plate_number, status="parked").first()
    if existing:
        return jsonify({"code": 400, "msg": f"车辆 {plate_number} 已在场内，请勿重复入场。"}), 400

    space = ParkingSpace.query.first()
    if space and space.available <= 0:
        return jsonify({"code": 400, "msg": "当前车位已满，无法入场。"}), 400

    remark = "图片识别入场" if entry_method == "recognize" else "手动录入入场"

    # 预约校验：预约时段内的车辆优先放行并标记已到达
    reservation = ParkingReservation.query.filter(
        ParkingReservation.plate_number == plate_number,
        ParkingReservation.status == "pending",
        ParkingReservation.start_time <= datetime.now(),
        ParkingReservation.end_time >= datetime.now(),
    ).order_by(ParkingReservation.start_time.asc()).first()
    if reservation:
        reservation.status = "arrived"
        remark += f"；预约车辆（预约时段 {reservation.start_time:%H:%M}-{reservation.end_time:%H:%M}）"

    # 月租车辆标记
    if _is_valid_monthly(plate_number):
        remark += "；月租车辆"

    record = ParkingRecord(
        plate_number=plate_number,
        plate_type=plate_type,
        entry_time=datetime.now(),
        status="parked",
        entry_image=entry_image,
        operator_id=current_user.id,
        remark=remark,
    )
    db.session.add(record)

    if space:
        space.available -= 1

    add_log("enter", plate_number, remark, user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "入场登记成功", "data": record.to_dict()})


@parking_bp.route("/exit-preview", methods=["POST"])
@permission_required("parking:operate")
def exit_preview(current_user):
    data = request.get_json() or {}
    plate_number = data.get("plate_number", "").strip().upper()

    if not plate_number:
        return jsonify({"code": 400, "msg": "车牌号不能为空。"}), 400

    record = ParkingRecord.query.filter_by(
        plate_number=plate_number,
        status="parked",
    ).order_by(ParkingRecord.entry_time.desc()).first()

    if not record:
        return jsonify({"code": 404, "msg": f"未找到车牌 {plate_number} 的在场记录。"}), 404

    return jsonify({"code": 200, "msg": "查询成功", "data": _parking_preview(record)})


@parking_bp.route("/exit", methods=["POST"])
@permission_required("parking:operate")
def vehicle_exit(current_user):
    data = request.get_json() or {}
    plate_number = data.get("plate_number", "").strip().upper()
    exit_image = data.get("exit_image", "")
    is_free_release = bool(data.get("is_free_release", False))
    exit_method = data.get("exit_method", "manual")

    if not plate_number:
        return jsonify({"code": 400, "msg": "车牌号不能为空。"}), 400

    record = ParkingRecord.query.filter_by(
        plate_number=plate_number,
        status="parked",
    ).order_by(ParkingRecord.entry_time.desc()).first()

    if not record:
        return jsonify({"code": 404, "msg": f"未找到车牌 {plate_number} 的在场记录。"}), 404

    now = datetime.now()
    duration = max(int((now - record.entry_time).total_seconds() / 60), 0)

    is_monthly = _is_valid_monthly(plate_number)
    if is_monthly:
        # 月租车辆：套餐内停车不再按临停计费
        fee = 0.0
        is_free_release = True
        monthly_tip = "月租车辆，套餐内离场不额外收费。"
    else:
        fee = 0.0 if is_free_release else calculate_fee(duration)
        monthly_tip = ""

    remark_parts = []
    if record.remark:
        remark_parts.append(record.remark)
    remark_parts.append("图片识别离场" if exit_method == "recognize" else "手动录入离场")
    if is_free_release:
        remark_parts.append("人工免费放行")
    if is_monthly:
        remark_parts.append("月租车辆套餐内放行")

    record.exit_time = now
    record.duration = duration
    record.fee = fee
    record.status = "exited"
    if is_free_release or is_monthly or fee <= 0:
        # 免费放行 / 月租套餐 / 免费时长内：直接结清
        record.payment_status = "free"
        record.payment_time = now
    else:
        # 正常收费离场：先完成结算，状态为待支付，需在线支付后放行
        record.payment_status = "unpaid"
        record.payment_time = None
    record.exit_image = exit_image
    record.operator_id = current_user.id
    record.remark = "；".join(remark_parts)

    space = ParkingSpace.query.first()
    if space:
        space.available = min(space.total, space.available + 1)

    add_log("exit", plate_number, f"离场结算{'（月租免费）' if is_monthly else ''}，时长 {duration} 分钟，费用 {fee:.2f} 元，待支付", user=current_user)
    db.session.commit()
    data = record.to_dict()
    data["is_monthly"] = is_monthly
    data["monthly_tip"] = monthly_tip
    data["need_pay"] = data["payment_status"] == "unpaid"
    return jsonify({"code": 200, "msg": "离场结算成功", "data": data})


@parking_bp.route("/<int:record_id>/pay", methods=["POST"])
@permission_required("parking:operate")
def pay_record(current_user, record_id):
    """模拟在线支付：将待支付记录置为已支付。"""
    record = db.get_or_404(ParkingRecord, record_id)

    if record.status != "exited":
        return jsonify({"code": 400, "msg": "该车辆尚未完成离场结算。"}), 400
    if record.payment_status == "paid":
        return jsonify({"code": 400, "msg": "该记录已支付，请勿重复支付。"}), 400
    if record.payment_status == "free":
        return jsonify({"code": 400, "msg": "该记录为免费放行，无需支付。"}), 400

    record.payment_status = "paid"
    record.payment_time = datetime.now()
    add_log("pay", f"停车记录 #{record.id} {record.plate_number}", f"在线支付 {record.fee} 元", user=current_user)
    db.session.commit()
    return jsonify({"code": 200, "msg": "支付成功", "data": record.to_dict()})


@parking_bp.route("/spaces", methods=["GET"])
@token_required
def get_spaces(current_user):
    space = ParkingSpace.query.first()
    if not space:
        return jsonify({"code": 200, "data": {"total": 0, "available": 0, "occupied": 0}})

    return jsonify(
        {
            "code": 200,
            "data": {
                "total": space.total,
                "available": space.available,
                "occupied": max(space.total - space.available, 0),
            },
        }
    )


@parking_bp.route("/spaces", methods=["PUT"])
@permission_required("space:manage")
def update_spaces(current_user):
    data = request.get_json() or {}
    total = data.get("total")

    if total is None or int(total) <= 0:
        return jsonify({"code": 400, "msg": "总车位数必须大于 0。"}), 400

    total = int(total)
    space = ParkingSpace.query.first()
    if not space:
        space = ParkingSpace(total=total, available=total)
        db.session.add(space)
    else:
        occupied = max(space.total - space.available, 0)
        if total < occupied:
            return jsonify({"code": 400, "msg": "新的总车位数不能小于当前已占用车位数。"}), 400
        space.total = total
        space.available = total - occupied

    db.session.commit()
    return jsonify({"code": 200, "msg": "车位配置已更新。"})


@parking_bp.route("/parked", methods=["GET"])
@token_required
def get_parked_vehicles(current_user):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    keyword = request.args.get("keyword", "").strip()

    query = ParkingRecord.query.filter_by(status="parked")
    if keyword:
        query = query.filter(ParkingRecord.plate_number.like(f"%{keyword}%"))

    pagination = query.order_by(ParkingRecord.entry_time.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return jsonify(
        {
            "code": 200,
            "data": {
                "items": [record.to_dict() for record in pagination.items],
                "total": pagination.total,
                "page": page,
                "pages": pagination.pages,
            },
        }
    )
