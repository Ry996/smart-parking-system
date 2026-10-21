from sqlalchemy import text

from app import db


def _column_names(conn, table: str):
    rows = conn.execute(text(f"PRAGMA table_info({table})")).mappings().all()
    return [row["name"] for row in rows]


def ensure_sqlite_compatibility():
    if db.engine.dialect.name != "sqlite":
        return

    with db.engine.begin() as conn:
        table_sql = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='parking_records'")
        ).scalar()
        if not table_sql:
            return

        columns = _column_names(conn, "parking_records")
        id_column = next((column for column in columns if column == "id"), None)

        # 1) 历史结构迁移：旧版 id 为 BIGINT/非 INTEGER 时重建为 INTEGER AUTOINCREMENT
        if id_column is not None:
            id_type_row = conn.execute(
                text("SELECT type FROM pragma_table_info('parking_records') WHERE name='id'")
            ).scalar()
        else:
            id_type_row = None

        if id_type_row and str(id_type_row).upper() != "INTEGER":
            conn.execute(text("DROP TABLE IF EXISTS parking_records__migration"))
            conn.execute(
                text(
                    """
                    CREATE TABLE parking_records__migration (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        plate_number VARCHAR(20) NOT NULL,
                        plate_type VARCHAR(20),
                        entry_time DATETIME NOT NULL,
                        exit_time DATETIME,
                        duration INTEGER,
                        fee NUMERIC(10, 2),
                        status VARCHAR(9),
                        payment_status VARCHAR(10),
                        payment_time DATETIME,
                        entry_image VARCHAR(255),
                        exit_image VARCHAR(255),
                        operator_id INTEGER,
                        remark VARCHAR(255),
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO parking_records__migration (
                        id, plate_number, plate_type, entry_time, exit_time, duration, fee,
                        status, entry_image, exit_image, operator_id, remark, created_at, updated_at
                    )
                    SELECT
                        id, plate_number, plate_type, entry_time, exit_time, duration, fee,
                        status, entry_image, exit_image, operator_id, remark, created_at, updated_at
                    FROM parking_records
                    ORDER BY id
                    """
                )
            )
            conn.execute(text("DROP TABLE parking_records"))
            conn.execute(text("ALTER TABLE parking_records__migration RENAME TO parking_records"))

        # 2) V2.1 迁移：补充支付状态列（老库无此列时）
        columns = _column_names(conn, "parking_records")
        if "payment_status" not in columns:
            conn.execute(text("ALTER TABLE parking_records ADD COLUMN payment_status VARCHAR(10) DEFAULT 'unpaid'"))
        if "payment_time" not in columns:
            conn.execute(text("ALTER TABLE parking_records ADD COLUMN payment_time DATETIME"))

        # 3) 历史数据回填：已离场且费用>0 视为已支付；免费放行视为免费；在场保持待支付
        conn.execute(
            text(
                """
                UPDATE parking_records
                SET payment_status = 'paid'
                WHERE status = 'exited' AND fee > 0 AND payment_status = 'unpaid'
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE parking_records
                SET payment_status = 'free'
                WHERE status = 'exited' AND fee = 0 AND payment_status = 'unpaid'
                """
            )
        )

        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_records_plate_number ON parking_records (plate_number)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_records_status ON parking_records (status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parking_records_payment_status ON parking_records (payment_status)"))
