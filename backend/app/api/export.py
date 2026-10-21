"""
数据导出接口：停车记录、月租台账导出为 CSV（UTF-8 BOM，Excel 可直接打开）。
"""
import csv
import io

from flask import Blueprint, jsonify, request, Response

from app import db
from app.models import ParkingRecord, MonthlySubscriber
from app.utils.auth import permission_required
from app.services.log_service import add_log

export_bp = Blueprint("export", __name__)


def _csv_response(rows, filename):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    # 添加 UTF-8 BOM，保证 Excel 正确识别中文
    data = "\ufeff" + output.getvalue()
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@export_bp.route("/records", methods=["GET"])
@permission_required("export:data")
def export_records(current_user):
    """导出停车记录 CSV，支持与记录页一致的筛选条件。"""
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

    records = query.order_by(ParkingRecord.entry_time.desc()).all()
    rows = [
        ["记录ID", "车牌号", "车牌类型", "入场时间", "离场时间", "停车时长(分钟)", "费用(元)", "状态", "操作员ID", "备注"],
    ]
    status_map = {"parked": "在场", "exited": "已离场", "exception": "异常"}
    for record in records:
        rows.append([
            record.id,
            record.plate_number,
            record.plate_type,
            record.entry_time.strftime("%Y-%m-%d %H:%M:%S") if record.entry_time else "",
            record.exit_time.strftime("%Y-%m-%d %H:%M:%S") if record.exit_time else "",
            record.duration if record.duration is not None else "",
            float(record.fee) if record.fee is not None else "",
            status_map.get(record.status, record.status),
            record.operator_id or "",
            record.remark or "",
        ])

    add_log("export", "停车记录", f"导出 {len(records)} 条停车记录", user=current_user)
    db.session.commit()
    return _csv_response(rows, "停车记录导出.csv")


@export_bp.route("/monthly", methods=["GET"])
@permission_required("export:data")
def export_monthly(current_user):
    """导出月租台账 CSV。"""
    subscribers = MonthlySubscriber.query.order_by(MonthlySubscriber.id.desc()).all()
    rows = [
        ["月租ID", "车牌号", "车主姓名", "联系电话", "套餐名称", "生效日期", "到期日期", "费用(元)", "状态", "备注"],
    ]
    for sub in subscribers:
        rows.append([
            sub.id,
            sub.plate_number,
            sub.owner_name,
            sub.phone or "",
            sub.package_name,
            sub.start_date.strftime("%Y-%m-%d") if sub.start_date else "",
            sub.end_date.strftime("%Y-%m-%d") if sub.end_date else "",
            float(sub.fee) if sub.fee is not None else 0,
            sub.to_dict()["status"],
            sub.remark or "",
        ])

    add_log("export", "月租台账", f"导出 {len(subscribers)} 条月租记录", user=current_user)
    db.session.commit()
    return _csv_response(rows, "月租台账导出.csv")
