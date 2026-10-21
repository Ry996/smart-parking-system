"""
操作日志查询接口：分页审计日志，支持按操作人、操作类型、日期筛选。
"""
from flask import Blueprint, jsonify, request

from app.models import OperationLog
from app.utils.auth import permission_required

logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/", methods=["GET"])
@permission_required("log:read")
def list_logs(current_user):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 15, type=int)
    username = request.args.get("username", "").strip()
    action = request.args.get("action", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    query = OperationLog.query
    if username:
        query = query.filter(OperationLog.username.like(f"%{username}%"))
    if action:
        query = query.filter(OperationLog.action == action)
    if date_from:
        query = query.filter(OperationLog.created_at >= f"{date_from} 00:00:00")
    if date_to:
        query = query.filter(OperationLog.created_at <= f"{date_to} 23:59:59")

    pagination = query.order_by(OperationLog.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return jsonify({
        "code": 200,
        "data": {
            "items": [log.to_dict() for log in pagination.items],
            "total": pagination.total,
            "page": page,
            "pages": pagination.pages,
        },
    })
