"""计费服务单元测试：验证免费时长、按小时/按次计费、封顶、无规则兜底。"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB = os.path.join(tempfile.gettempdir(), "test_fee_service_v2.db")
os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{TEST_DB}"

from app import create_app, db  # noqa: E402
from app.models import FeeRule  # noqa: E402
from app.services.fee_service import calculate_fee  # noqa: E402


class FeeServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.drop_all()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        cls.ctx.pop()
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except OSError:
                pass

    def _clear_rules(self):
        FeeRule.query.delete()
        db.session.commit()

    def _add_rule(self, **kwargs):
        rule = FeeRule(**kwargs)
        db.session.add(rule)
        db.session.commit()
        return rule

    def test_free_within_threshold(self):
        """15 分钟内免费。"""
        self._clear_rules()
        self._add_rule(
            rule_name="测试规则", fee_type="hourly", free_minutes=15,
            price_per_hour=5, max_daily=50, is_active=1,
        )
        self.assertEqual(calculate_fee(5), 0.0)
        self.assertEqual(calculate_fee(15), 0.0)

    def test_hourly_ceil_by_hour(self):
        """超过免费时长后不足 1 小时按 1 小时计。"""
        self._clear_rules()
        self._add_rule(
            rule_name="测试规则", fee_type="hourly", free_minutes=15,
            price_per_hour=5, max_daily=50, is_active=1,
        )
        # 20 分钟：扣 15 分钟免费，剩余 5 分钟按 1 小时 → 5 元
        self.assertEqual(calculate_fee(20), 5.0)
        # 75 分钟：剩余 60 分钟 → 5 元
        self.assertEqual(calculate_fee(75), 5.0)
        # 135 分钟：剩余 120 分钟 → 10 元
        self.assertEqual(calculate_fee(135), 10.0)

    def test_flat_fee(self):
        """按次收费：超过免费时长后收取固定金额。"""
        self._clear_rules()
        self._add_rule(
            rule_name="按次测试", fee_type="flat", free_minutes=0,
            flat_price=20, is_active=1,
        )
        self.assertEqual(calculate_fee(10), 20.0)

    def test_max_daily_cap(self):
        """单日封顶金额生效。"""
        self._clear_rules()
        self._add_rule(
            rule_name="封顶测试", fee_type="hourly", free_minutes=0,
            price_per_hour=10, max_daily=30, is_active=1,
        )
        # 5 小时 = 50 元，被封顶为 30 元
        self.assertEqual(calculate_fee(300), 30.0)

    def test_fallback_without_rule(self):
        """无启用规则时使用兜底：15 分钟免费，之后 5 元/小时。"""
        self._clear_rules()
        self.assertEqual(calculate_fee(10), 0.0)
        self.assertEqual(calculate_fee(20), 5.0)
        self.assertEqual(calculate_fee(80), 10.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
