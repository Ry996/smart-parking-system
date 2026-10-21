"""Backend startup entry."""

from app import create_app, db
from app.models import FeeRule, MonthlySubscriber, ParkingReservation, ParkingSpace, User
from app.services.rag_service import ensure_index, sync_documents_from_dir
from app.services.rbac_service import seed_rbac
from app.utils.auth import hash_password
from app.utils.db_compat import ensure_sqlite_compatibility
from datetime import datetime, timedelta

app = create_app()


def seed_database():
    db.create_all()
    ensure_sqlite_compatibility()

    # 实验四：初始化 RBAC 角色与权限（admin 全量、operator 值守权限）
    seed_rbac()

    # 实验五：把 knowledge/*.md 同步进知识库并建立 RAG 向量索引
    sync_documents_from_dir(app.config.get("KNOWLEDGE_DIR"))
    ensure_index()

    if not User.query.filter_by(username="admin").first():
        db.session.add(
            User(
                username="admin",
                password=hash_password("admin123"),
                real_name="系统管理员",
                role="admin",
                status=1,
            )
        )

    if not User.query.filter_by(username="operator1").first():
        db.session.add(
            User(
                username="operator1",
                password=hash_password("admin123"),
                real_name="停车场操作员",
                role="operator",
                status=1,
            )
        )

    if not FeeRule.query.first():
        db.session.add(
            FeeRule(
                rule_name="默认按小时收费",
                vehicle_type="all",
                fee_type="hourly",
                free_minutes=15,
                price_per_hour=5.0,
                max_daily=50.0,
                is_active=1,
            )
        )

    if not ParkingSpace.query.first():
        db.session.add(ParkingSpace(total=100, available=100))

    # 演示数据：月租车辆（V2 新增模块）
    if not MonthlySubscriber.query.first():
        today = datetime.utcnow().date()
        db.session.add_all([
            MonthlySubscriber(
                plate_number="皖A88888",
                owner_name="张先生",
                phone="13800000001",
                package_name="标准月租套餐",
                start_date=today - timedelta(days=20),
                end_date=today + timedelta(days=40),
                fee=300.0,
                remark="演示数据：月租车",
            ),
            MonthlySubscriber(
                plate_number="皖B66666",
                owner_name="李女士",
                phone="13800000002",
                package_name="季度优惠套餐",
                start_date=today - timedelta(days=90),
                end_date=today + timedelta(days=5),
                fee=800.0,
                remark="演示数据：即将到期",
            ),
        ])

    # 演示数据：车位预约（V2 新增模块）
    if not ParkingReservation.query.first():
        now = datetime.now()
        db.session.add_all([
            ParkingReservation(
                plate_number="皖C12345",
                owner_name="王先生",
                phone="13800000003",
                start_time=now + timedelta(hours=1),
                end_time=now + timedelta(hours=3),
                status="pending",
                remark="演示数据：预约2小时后入场",
            ),
            ParkingReservation(
                plate_number="皖D56789",
                owner_name="赵女士",
                phone="13800000004",
                start_time=now - timedelta(minutes=30),
                end_time=now + timedelta(hours=2),
                status="pending",
                remark="演示数据：预约时段内",
            ),
        ])

    db.session.commit()


@app.cli.command("init-db")
def init_db():
    """Initialize database and seed default data."""
    with app.app_context():
        seed_database()
        print("数据库初始化完成，默认账号：admin / admin123")


if __name__ == "__main__":
    with app.app_context():
        seed_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
