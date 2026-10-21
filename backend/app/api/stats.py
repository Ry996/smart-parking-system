from datetime import datetime, timedelta
import calendar

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app import db
from app.models import ParkingRecord, ParkingSpace
from app.services.ai_service import ai_service
from app.utils.auth import permission_required, token_required

stats_bp = Blueprint("stats", __name__)


def _is_sqlite() -> bool:
    return db.engine.dialect.name == "sqlite"


def _hour_label_expr(column):
    if _is_sqlite():
        return func.strftime("%H", column)
    return func.hour(column)


def _overview_data():
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    today_count = ParkingRecord.query.filter(
        ParkingRecord.entry_time >= today_start,
        ParkingRecord.entry_time < today_end,
    ).count()

    today_income = ParkingRecord.query.with_entities(func.sum(ParkingRecord.fee)).filter(
        ParkingRecord.exit_time >= today_start,
        ParkingRecord.exit_time < today_end,
        ParkingRecord.status == "exited",
    ).scalar() or 0

    parked_now = ParkingRecord.query.filter_by(status="parked").count()
    space = ParkingSpace.query.first()

    return {
        "today_count": today_count,
        "today_income": float(today_income),
        "parked_now": parked_now,
        "total_spaces": int(space.total) if space else 0,
        "available_spaces": int(space.available) if space else 0,
    }


def _period_series(period):
    now = datetime.now()

    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        flow_rows = ParkingRecord.query.with_entities(
            _hour_label_expr(ParkingRecord.entry_time).label("label"),
            func.count().label("count"),
        ).filter(ParkingRecord.entry_time >= start).group_by("label").all()
        income_rows = ParkingRecord.query.with_entities(
            _hour_label_expr(ParkingRecord.exit_time).label("label"),
            func.sum(ParkingRecord.fee).label("income"),
        ).filter(
            ParkingRecord.exit_time >= start,
            ParkingRecord.status == "exited",
        ).group_by("label").all()

        labels = [f"{hour:02d}:00" for hour in range(24)]
        flow_map = {str(row.label): row.count for row in flow_rows}
        income_map = {str(row.label): float(row.income or 0) for row in income_rows}
        counts = [flow_map.get(str(hour), 0) for hour in range(24)]
        incomes = [income_map.get(f"{hour:02d}", 0) for hour in range(24)]
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        flow_rows = ParkingRecord.query.with_entities(
            func.date(ParkingRecord.entry_time).label("label"),
            func.count().label("count"),
        ).filter(ParkingRecord.entry_time >= start).group_by("label").all()
        income_rows = ParkingRecord.query.with_entities(
            func.date(ParkingRecord.exit_time).label("label"),
            func.sum(ParkingRecord.fee).label("income"),
        ).filter(
            ParkingRecord.exit_time >= start,
            ParkingRecord.status == "exited",
        ).group_by("label").all()

        days = calendar.monthrange(now.year, now.month)[1]
        labels = [f"{now.month}/{day}" for day in range(1, days + 1)]
        keys = [f"{now.year}-{now.month:02d}-{day:02d}" for day in range(1, days + 1)]
        flow_map = {str(row.label): row.count for row in flow_rows}
        income_map = {str(row.label): float(row.income or 0) for row in income_rows}
        counts = [flow_map.get(key, 0) for key in keys]
        incomes = [income_map.get(key, 0) for key in keys]
    else:
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        flow_rows = ParkingRecord.query.with_entities(
            func.date(ParkingRecord.entry_time).label("label"),
            func.count().label("count"),
        ).filter(ParkingRecord.entry_time >= start).group_by("label").all()
        income_rows = ParkingRecord.query.with_entities(
            func.date(ParkingRecord.exit_time).label("label"),
            func.sum(ParkingRecord.fee).label("income"),
        ).filter(
            ParkingRecord.exit_time >= start,
            ParkingRecord.status == "exited",
        ).group_by("label").all()

        labels = [(now - timedelta(days=index)).strftime("%m/%d") for index in range(6, -1, -1)]
        keys = [(now - timedelta(days=index)).strftime("%Y-%m-%d") for index in range(6, -1, -1)]
        flow_map = {str(row.label): row.count for row in flow_rows}
        income_map = {str(row.label): float(row.income or 0) for row in income_rows}
        counts = [flow_map.get(key, 0) for key in keys]
        incomes = [income_map.get(key, 0) for key in keys]

    return {"labels": labels, "counts": counts, "incomes": incomes}


def _local_ai_advice(summary):
    overview_data = summary["overview"]
    total_spaces = overview_data.get("total_spaces") or 0
    parked_now = overview_data.get("parked_now") or 0
    occupancy = round(parked_now / total_spaces * 100, 1) if total_spaces else 0
    traffic_total = sum(summary["series"]["counts"])
    income_total = sum(summary["series"]["incomes"])

    tips = [
        f"当前车位占用率约为 {occupancy}%，今日入场 {overview_data['today_count']} 辆，今日收入 {overview_data['today_income']:.2f} 元。",
    ]
    if occupancy >= 85:
        tips.append("车位接近满载，建议高峰期加强入口引导，并提前提示剩余车位。")
    elif occupancy <= 30:
        tips.append("当前车位较充足，可以结合周边活动或优惠策略提升停车利用率。")
    else:
        tips.append("当前车位使用较平稳，建议持续关注晚高峰和周末时段变化。")

    if traffic_total > 0 and income_total == 0:
        tips.append("近期有入场记录但收入较少，可重点检查离场结算流程是否完成。")
    else:
        tips.append("建议定期对比车流量和收入趋势，及时调整收费规则和人员排班。")

    return "\n".join(f"{index}. {tip}" for index, tip in enumerate(tips, start=1))


@stats_bp.route("/overview", methods=["GET"])
@token_required
def overview(current_user):
    return jsonify({
        "code": 200,
        "data": _overview_data(),
    })


@stats_bp.route("/flow", methods=["GET"])
@token_required
def traffic_flow(current_user):
    period = request.args.get("period", "week")
    now = datetime.now()

    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        rows = ParkingRecord.query.with_entities(
            _hour_label_expr(ParkingRecord.entry_time).label("label"),
            func.count().label("count"),
        ).filter(ParkingRecord.entry_time >= start).group_by("label").all()
        labels = [f"{hour:02d}:00" for hour in range(24)]
        data_map = {str(row.label): row.count for row in rows}
        counts = [data_map.get(str(hour), 0) for hour in range(24)]
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rows = ParkingRecord.query.with_entities(
            func.date(ParkingRecord.entry_time).label("label"),
            func.count().label("count"),
        ).filter(ParkingRecord.entry_time >= start).group_by("label").all()
        days = calendar.monthrange(now.year, now.month)[1]
        labels = [f"{now.month}/{day}" for day in range(1, days + 1)]
        data_map = {str(row.label): row.count for row in rows}
        counts = [data_map.get(f"{now.year}-{now.month:02d}-{day:02d}", 0) for day in range(1, days + 1)]
    else:
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        rows = ParkingRecord.query.with_entities(
            func.date(ParkingRecord.entry_time).label("label"),
            func.count().label("count"),
        ).filter(ParkingRecord.entry_time >= start).group_by("label").all()
        labels = [(now - timedelta(days=index)).strftime("%m/%d") for index in range(6, -1, -1)]
        data_map = {str(row.label): row.count for row in rows}
        counts = [data_map.get((now - timedelta(days=index)).strftime("%Y-%m-%d"), 0) for index in range(6, -1, -1)]

    return jsonify({"code": 200, "data": {"labels": labels, "counts": counts}})


@stats_bp.route("/income", methods=["GET"])
@token_required
def income_stats(current_user):
    period = request.args.get("period", "week")
    now = datetime.now()

    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        rows = ParkingRecord.query.with_entities(
            _hour_label_expr(ParkingRecord.exit_time).label("label"),
            func.sum(ParkingRecord.fee).label("income"),
        ).filter(
            ParkingRecord.exit_time >= start,
            ParkingRecord.status == "exited",
        ).group_by("label").all()
        labels = [f"{hour:02d}:00" for hour in range(24)]
        data_map = {str(row.label): float(row.income or 0) for row in rows}
        incomes = [data_map.get(f"{hour:02d}", 0) for hour in range(24)]
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rows = ParkingRecord.query.with_entities(
            func.date(ParkingRecord.exit_time).label("label"),
            func.sum(ParkingRecord.fee).label("income"),
        ).filter(
            ParkingRecord.exit_time >= start,
            ParkingRecord.status == "exited",
        ).group_by("label").all()
        days = calendar.monthrange(now.year, now.month)[1]
        labels = [f"{now.month}/{day}" for day in range(1, days + 1)]
        data_map = {str(row.label): float(row.income or 0) for row in rows}
        incomes = [data_map.get(f"{now.year}-{now.month:02d}-{day:02d}", 0) for day in range(1, days + 1)]
    else:
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        rows = ParkingRecord.query.with_entities(
            func.date(ParkingRecord.exit_time).label("label"),
            func.sum(ParkingRecord.fee).label("income"),
        ).filter(
            ParkingRecord.exit_time >= start,
            ParkingRecord.status == "exited",
        ).group_by("label").all()
        labels = [(now - timedelta(days=index)).strftime("%m/%d") for index in range(6, -1, -1)]
        data_map = {str(row.label): float(row.income or 0) for row in rows}
        incomes = [data_map.get((now - timedelta(days=index)).strftime("%Y-%m-%d"), 0) for index in range(6, -1, -1)]

    return jsonify({"code": 200, "data": {"labels": labels, "incomes": incomes}})


@stats_bp.route("/ai-advice", methods=["GET"])
@permission_required("ai:advice")
def ai_advice(current_user):
    period = request.args.get("period", "week")
    if period not in ("day", "week", "month"):
        period = "week"

    summary = {
        "period": period,
        "overview": _overview_data(),
        "series": _period_series(period),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 真实模型优先，失败时自动降级为本地规则；provider 字段让前端与报告都能区分来源
    advice, provider = ai_service.advice(summary)
    if not advice:
        provider = "local"
        advice = _local_ai_advice(summary)

    return jsonify({
        "code": 200,
        "data": {
            "provider": provider,
            "advice": advice,
            "summary": summary,
        },
    })
