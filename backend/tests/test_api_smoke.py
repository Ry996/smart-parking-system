"""核心接口冒烟测试：登录、黑名单拦截、预约入场、入离场闭环、月租免费离场、日志、导出。"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB = os.path.join(tempfile.gettempdir(), "test_api_smoke_v2.db")
os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{TEST_DB}"
os.environ["LPR_MOCK_MODE"] = "true"

from app import create_app, db  # noqa: E402
from run import seed_database  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from app.models import MonthlySubscriber, ParkingRecord  # noqa: E402


class ApiSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.drop_all()
            seed_database()

    def setUp(self):
        with self.app.app_context():
            # 每个用例前清理在场记录，保持用例独立
            ParkingRecord.query.filter_by(status="parked").delete()
            db.session.commit()

    def _login(self, username="admin", password="admin123"):
        res = self.client.post("/api/auth/login", json={"username": username, "password": password})
        return res.get_json()

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_login_success_and_failure(self):
        ok = self._login("admin", "admin123")
        self.assertEqual(ok["code"], 200)
        self.assertIn("token", ok["data"])

        bad = self._login("admin", "wrong-password")
        self.assertEqual(bad["code"], 401)

    def test_blacklist_blocks_entry(self):
        token = self._login()["data"]["token"]
        headers = self._headers(token)

        res = self.client.post("/api/blacklist/", json={"plate_number": "皖A99999", "reason": "恶意逃费"}, headers=headers)
        self.assertEqual(res.get_json()["code"], 200)

        res = self.client.post("/api/parking/enter", json={"plate_number": "皖A99999"}, headers=headers)
        self.assertEqual(res.status_code, 403)
        self.assertIn("黑名单", res.get_json()["msg"])

    def test_reservation_vehicle_enters_first(self):
        token = self._login()["data"]["token"]
        headers = self._headers(token)

        now = datetime.now()
        res = self.client.post("/api/reservations/", json={
            "plate_number": "皖C11111",
            "owner_name": "测试预约人",
            "start_time": (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
        }, headers=headers)
        self.assertEqual(res.get_json()["code"], 200)

        res = self.client.post("/api/parking/enter", json={"plate_number": "皖C11111"}, headers=headers)
        self.assertEqual(res.get_json()["code"], 200)
        self.assertIn("预约车辆", res.get_json()["data"]["remark"])

    def test_enter_exit_full_flow(self):
        token = self._login()["data"]["token"]
        headers = self._headers(token)

        res = self.client.post("/api/parking/enter", json={"plate_number": "皖B12345", "entry_method": "manual"}, headers=headers)
        self.assertEqual(res.get_json()["code"], 200)

        # 重复入场被拦截
        res = self.client.post("/api/parking/enter", json={"plate_number": "皖B12345"}, headers=headers)
        self.assertEqual(res.get_json()["code"], 400)

        # 模拟已停车 2 小时，产生费用
        with self.app.app_context():
            rec = ParkingRecord.query.filter_by(plate_number="皖B12345", status="parked").first()
            rec.entry_time = datetime.now() - timedelta(hours=2)
            db.session.commit()

        # 离场预览
        res = self.client.post("/api/parking/exit-preview", json={"plate_number": "皖B12345"}, headers=headers)
        self.assertEqual(res.get_json()["code"], 200)
        self.assertIn("fee", res.get_json()["data"])

        # 确认离场
        res = self.client.post("/api/parking/exit", json={"plate_number": "皖B12345"}, headers=headers)
        data = res.get_json()
        self.assertEqual(data["code"], 200)
        self.assertEqual(data["data"]["status"], "exited")
        self.assertGreater(data["data"]["fee"], 0)
        # 应收离场默认待支付，需在线支付
        self.assertEqual(data["data"]["payment_status"], "unpaid")
        self.assertTrue(data["data"]["need_pay"])

        # 模拟支付
        res = self.client.post(f"/api/parking/{data['data']['id']}/pay", headers=headers)
        pay_data = res.get_json()
        self.assertEqual(pay_data["code"], 200)
        self.assertEqual(pay_data["data"]["payment_status"], "paid")

        # 重复支付被拒绝
        res = self.client.post(f"/api/parking/{data['data']['id']}/pay", headers=headers)
        self.assertEqual(res.get_json()["code"], 400)

    def test_zero_fee_exit_is_free(self):
        """免费时长内离场（0 元）直接免费放行，不进入待支付。"""
        token = self._login()["data"]["token"]
        headers = self._headers(token)

        self.client.post("/api/parking/enter", json={"plate_number": "皖F44444"}, headers=headers)
        res = self.client.post("/api/parking/exit", json={"plate_number": "皖F44444"}, headers=headers)
        data = res.get_json()
        self.assertEqual(data["code"], 200)
        self.assertEqual(data["data"]["payment_status"], "free")
        self.assertFalse(data["data"]["need_pay"])

    def test_monthly_vehicle_free_exit(self):
        token = self._login()["data"]["token"]
        headers = self._headers(token)

        today = datetime.utcnow().date()
        with self.app.app_context():
            if not MonthlySubscriber.query.filter_by(plate_number="皖A88888").first():
                db.session.add(MonthlySubscriber(
                    plate_number="皖A88888", owner_name="测试月租",
                    package_name="测试套餐",
                    start_date=today - timedelta(days=10),
                    end_date=today + timedelta(days=10),
                    fee=300, remark="",
                ))
                db.session.commit()

        self.client.post("/api/parking/enter", json={"plate_number": "皖A88888"}, headers=headers)
        res = self.client.post("/api/parking/exit", json={"plate_number": "皖A88888"}, headers=headers)
        data = res.get_json()
        self.assertEqual(data["code"], 200)
        self.assertTrue(data["data"]["is_monthly"])
        self.assertEqual(data["data"]["fee"], 0.0)
        self.assertEqual(data["data"]["payment_status"], "free")

    def test_operation_logs_recorded(self):
        token = self._login()["data"]["token"]
        headers = self._headers(token)

        self.client.post("/api/parking/enter", json={"plate_number": "皖D22222"}, headers=headers)
        res = self.client.get("/api/logs/?page=1&per_page=10", headers=headers)
        data = res.get_json()
        self.assertEqual(data["code"], 200)
        actions = [item["action"] for item in data["data"]["items"]]
        self.assertIn("enter", actions)

    def test_export_records_csv(self):
        token = self._login()["data"]["token"]
        headers = self._headers(token)

        res = self.client.get("/api/export/records", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.content_type)
        self.assertIn("车牌号", res.data.decode("utf-8-sig"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
