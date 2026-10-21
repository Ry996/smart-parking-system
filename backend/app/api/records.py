from flask import Blueprint, jsonify, request

from app import db
from app.models import ParkingRecord
from app.utils.auth import token_required

records_bp = Blueprint("records", __name__)


@records_bp.route("/", methods=["GET"])
@token_required
def list_records(current_user):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 15, type=int)
    plate = request.args.get("plate", "").strip()
    status = request.args.get("status", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    query = ParkingRecord.query
    if plate:
        query = query.filter(ParkingRecord.plate_number.like(f"%{plate}%"))
    if status:
        query = query.filter(ParkingRecord.status == status)
    if date_from:
        query = query.filter(ParkingRecord.entry_time >= f"{date_from} 00:00:00")
    if date_to:
        query = query.filter(ParkingRecord.entry_time <= f"{date_to} 23:59:59")

    pagination = query.order_by(ParkingRecord.entry_time.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return jsonify({
        "code": 200,
        "data": {
            "items": [record.to_dict() for record in pagination.items],
            "total": pagination.total,
            "page": page,
            "pages": pagination.pages,
        },
    })


@records_bp.route("/<int:record_id>", methods=["GET"])
@token_required
def get_record(current_user, record_id):
    record = db.get_or_404(ParkingRecord, record_id)
    return jsonify({"code": 200, "data": record.to_dict()})


@records_bp.route("/<int:record_id>/remark", methods=["PUT"])
@token_required
def update_remark(current_user, record_id):
    data = request.get_json() or {}
    record = db.get_or_404(ParkingRecord, record_id)
    record.remark = data.get("remark", "").strip()
    db.session.commit()
    return jsonify({"code": 200, "msg": "备注已更新。"})
