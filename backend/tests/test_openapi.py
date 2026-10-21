"""接口文档测试：OpenAPI 规范完整性与在线文档页可用性。"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB = os.path.join(tempfile.gettempdir(), "test_openapi_v2.db")
os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{TEST_DB}"
os.environ["LPR_MOCK_MODE"] = "true"

from app import create_app  # noqa: E402


class OpenApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.spec = cls.client.get("/api/openapi.json").get_json()

    def test_spec_version_and_info(self):
        self.assertTrue(self.spec["openapi"].startswith("3.0"))
        self.assertIn("智慧停车场", self.spec["info"]["title"])

    def test_all_business_paths_documented(self):
        paths = self.spec["paths"]
        self.assertGreater(len(paths), 40)
        for expected in ("/api/auth/login", "/api/parking/enter", "/api/ai/ask", "/api/roles/"):
            self.assertIn(expected, paths, expected)

    def test_docs_endpoints_not_documented(self):
        self.assertNotIn("/api/openapi.json", self.spec["paths"])
        self.assertNotIn("/api/docs", self.spec["paths"])

    def test_bearer_security_scheme(self):
        scheme = self.spec["components"]["securitySchemes"]["bearerAuth"]
        self.assertEqual(scheme["type"], "http")
        self.assertEqual(scheme["scheme"], "bearer")

    def test_login_is_public(self):
        self.assertNotIn("security", self.spec["paths"]["/api/auth/login"]["post"])

    def test_ai_ask_requires_permission(self):
        operation = self.spec["paths"]["/api/ai/ask"]["post"]
        self.assertEqual(operation["security"], [{"bearerAuth": []}])
        self.assertIn("ai:ask", operation["description"])

    def test_path_parameter_declared(self):
        operation = self.spec["paths"]["/api/users/<int:user_id>"]["put"]
        names = [parameter["name"] for parameter in operation["parameters"]]
        self.assertIn("user_id", names)

    def test_upload_endpoint_uses_multipart(self):
        operation = self.spec["paths"]["/api/lpr/recognize"]["post"]
        self.assertIn("multipart/form-data", operation["requestBody"]["content"])

    def test_docs_page_renders(self):
        res = self.client.get("/api/docs")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.content_type)
        self.assertIn("智慧停车场管理系统 API", res.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
