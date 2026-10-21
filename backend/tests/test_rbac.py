"""RBAC 权限模型测试：角色矩阵、接口鉴权、权限变更即时生效、管理员保护。"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB = os.path.join(tempfile.gettempdir(), "test_rbac_v2.db")
os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{TEST_DB}"
os.environ["LPR_MOCK_MODE"] = "true"

from app import create_app, db  # noqa: E402
from app.models import Role, RolePermission, User  # noqa: E402
from app.services.rbac_service import (  # noqa: E402
    ADMIN_PERMISSIONS,
    OPERATOR_PERMISSIONS,
    PERMISSION_CATALOG,
    seed_rbac,
)
from app.utils.auth import hash_password  # noqa: E402


class RbacTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.drop_all()
        db.create_all()
        cls.client = cls.app.test_client()
        cls._ensure_users()

    @classmethod
    def _ensure_users(cls):
        seed_rbac()
        if not User.query.filter_by(username="admin").first():
            db.session.add(User(username="admin", password=hash_password("admin123"),
                                real_name="管理员", role="admin", status=1))
        if not User.query.filter_by(username="operator1").first():
            db.session.add(User(username="operator1", password=hash_password("admin123"),
                                real_name="操作员", role="operator", status=1))
        db.session.commit()

    def setUp(self):
        # 每个用例前重置为出厂权限矩阵，避免用例之间互相污染
        for role in Role.query.filter_by(is_builtin=0).all():
            RolePermission.query.filter_by(role_id=role.id).delete()
            db.session.delete(role)
        db.session.commit()
        seed_rbac()

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

    def _login(self, username="admin"):
        res = self.client.post("/api/auth/login", json={"username": username, "password": "admin123"})
        body = res.get_json()
        self.assertEqual(body["code"], 200, body)
        return {"Authorization": f"Bearer {body['data']['token']}"}

    def _role_id(self, code):
        return Role.query.filter_by(code=code).first().id

    # -- 权限矩阵 ---------------------------------------------------------
    def test_permission_catalog_size(self):
        res = self.client.get("/api/roles/permissions", headers=self._login())
        body = res.get_json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["total"], len(PERMISSION_CATALOG))

    def test_role_matrix(self):
        res = self.client.get("/api/roles/", headers=self._login())
        roles = {item["code"]: item for item in res.get_json()["data"]}
        self.assertEqual(sorted(roles["admin"]["permissions"]), sorted(ADMIN_PERMISSIONS))
        self.assertEqual(sorted(roles["operator"]["permissions"]), sorted(OPERATOR_PERMISSIONS))
        self.assertEqual(roles["admin"]["user_count"], 1)
        self.assertEqual(roles["admin"]["is_builtin"], 1)

    def test_me_returns_permissions(self):
        body = self.client.get("/api/roles/me", headers=self._login("operator1")).get_json()
        self.assertEqual(body["data"]["role"], "operator")
        self.assertIn("parking:operate", body["data"]["permissions"])
        self.assertNotIn("user:manage", body["data"]["permissions"])
        self.assertFalse(body["data"]["isAdmin"])

    # -- 接口鉴权 ---------------------------------------------------------
    def test_anonymous_rejected(self):
        self.assertEqual(self.client.get("/api/users/").status_code, 401)

    def test_operator_forbidden_on_user_manage(self):
        res = self.client.get("/api/users/", headers=self._login("operator1"))
        self.assertEqual(res.status_code, 403)
        self.assertIn("user:manage", res.get_json()["msg"])

    def test_admin_allowed(self):
        self.assertEqual(self.client.get("/api/users/", headers=self._login()).status_code, 200)

    def test_operator_allowed_on_parking(self):
        res = self.client.post("/api/parking/enter", json={"plate_number": "皖A55555"},
                               headers=self._login("operator1"))
        self.assertEqual(res.get_json()["code"], 200)

    def test_operator_forbidden_on_export(self):
        res = self.client.get("/api/export/records", headers=self._login("operator1"))
        self.assertEqual(res.status_code, 403)

    # -- 权限变更即时生效 -------------------------------------------------
    def test_grant_permission_takes_effect_immediately(self):
        operator_headers = self._login("operator1")
        res = self.client.post("/api/fee-rules/", json={"rule_name": "测试规则", "fee_type": "hourly"},
                               headers=operator_headers)
        self.assertEqual(res.status_code, 403)

        admin_headers = self._login()
        role_id = self._role_id("operator")
        granted = sorted(set(OPERATOR_PERMISSIONS) | {"fee:manage"})
        res = self.client.put(f"/api/roles/{role_id}/permissions",
                              json={"permissions": granted}, headers=admin_headers)
        self.assertEqual(res.get_json()["code"], 200, res.get_json())

        res = self.client.post("/api/fee-rules/", json={"rule_name": "测试规则", "fee_type": "hourly"},
                               headers=operator_headers)
        self.assertEqual(res.get_json()["code"], 200, res.get_json())

    def test_unknown_permission_code_rejected(self):
        res = self.client.put(f"/api/roles/{self._role_id('operator')}/permissions",
                              json={"permissions": ["not:exist"]}, headers=self._login())
        self.assertEqual(res.status_code, 400)

    def test_admin_role_must_keep_role_manage(self):
        res = self.client.put(f"/api/roles/{self._role_id('admin')}/permissions",
                              json={"permissions": ["user:manage"]}, headers=self._login())
        self.assertEqual(res.status_code, 400)
        self.assertIn("role:manage", res.get_json()["msg"])

    def test_builtin_role_cannot_be_deleted(self):
        res = self.client.delete(f"/api/roles/{self._role_id('admin')}", headers=self._login())
        self.assertEqual(res.status_code, 400)

    def test_custom_role_lifecycle(self):
        headers = self._login()
        res = self.client.post("/api/roles/", json={
            "code": "auditor",
            "name": "审计员",
            "description": "只读审计",
            "permissions": ["log:read", "ai:feedback:read"],
        }, headers=headers)
        body = res.get_json()
        self.assertEqual(body["code"], 200, body)
        role_id = body["data"]["id"]
        self.assertEqual(sorted(body["data"]["permissions"]), ["ai:feedback:read", "log:read"])

        res = self.client.delete(f"/api/roles/{role_id}", headers=headers)
        self.assertEqual(res.get_json()["code"], 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
