"""RAG 服务单元测试：切块、分词向量化、余弦相似度、检索相关性、覆盖率门控、索引幂等。"""
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB = os.path.join(tempfile.gettempdir(), "test_rag_v2.db")
os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{TEST_DB}"
os.environ["LPR_MOCK_MODE"] = "true"

from app import create_app, db  # noqa: E402
from app.services import rag_service  # noqa: E402


class RagServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.drop_all()
        db.create_all()
        rag_service.sync_documents_from_dir(cls.app.config["KNOWLEDGE_DIR"])
        cls.index = rag_service.rebuild_index()

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

    # -- 切块 -------------------------------------------------------------
    def test_chunk_text_respects_size(self):
        text = "。".join(f"第{i}条停车场规则说明" for i in range(200))
        chunks = rag_service.chunk_text(text)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), rag_service.CHUNK_SIZE)
            self.assertTrue(chunk.strip())

    def test_chunk_text_empty(self):
        self.assertEqual(rag_service.chunk_text(""), [])
        self.assertEqual(rag_service.chunk_text(None), [])

    # -- 分词与向量化 -----------------------------------------------------
    def test_vector_is_normalized_sparse_dict(self):
        vector = rag_service.vectorize("停车场计费规则")
        self.assertIsInstance(vector, dict)
        self.assertTrue(vector)
        norm = math.sqrt(sum(value * value for value in vector.values()))
        self.assertAlmostEqual(norm, 1.0, places=6)

    def test_vectorize_is_deterministic(self):
        self.assertEqual(rag_service.vectorize("月租车辆"), rag_service.vectorize("月租车辆"))

    def test_tokens_use_chinese_bigrams(self):
        tokens = rag_service._tokens("停车场")
        self.assertEqual(tokens, ["停车", "车场"])

    def test_cosine_identity_and_empty(self):
        vector = rag_service.vectorize("黑名单拦截")
        self.assertAlmostEqual(rag_service.cosine(vector, vector), 1.0, places=6)
        self.assertEqual(rag_service.cosine({}, vector), 0.0)
        self.assertEqual(rag_service.cosine({"a": 1.0}, {"b": 1.0}), 0.0)

    # -- 索引 -------------------------------------------------------------
    def test_index_built(self):
        self.assertEqual(self.index["documents"], 5)
        self.assertGreater(self.index["chunks"], 5)
        self.assertTrue(self.index["rebuilt"])

    def test_ensure_index_is_idempotent(self):
        state = rag_service.ensure_index()
        self.assertFalse(state["rebuilt"])
        self.assertEqual(state["documents"], 5)

    # -- 检索 -------------------------------------------------------------
    def test_search_relevance_for_fee_rule(self):
        results = rag_service.search("停车 20 分钟要收多少钱", top_k=3)
        self.assertTrue(results)
        self.assertIn("计费", results[0]["title"])
        self.assertGreaterEqual(results[0]["score"], rag_service.MIN_SCORE)
        self.assertGreaterEqual(results[0]["coverage"], rag_service.MIN_COVERAGE)

    def test_search_relevance_for_blacklist(self):
        results = rag_service.search("黑名单车辆能入场吗", top_k=3)
        self.assertTrue(results)
        self.assertIn("黑名单", results[0]["title"])

    def test_search_relevance_for_monthly(self):
        results = rag_service.search("月租车辆怎么续费", top_k=3)
        self.assertTrue(results)
        self.assertIn("月租", results[0]["title"])

    def test_search_unrelated_queries_return_empty(self):
        """覆盖率门控：与停车场业务无关的问题不应检索到资料。"""
        for question in ("量子引力波的传播速度", "如何做红烧肉", "今天天气怎么样"):
            self.assertEqual(rag_service.search(question, top_k=3), [], question)

    def test_public_sources_payload(self):
        results = rag_service.search("月租车辆续费", top_k=2)
        payload = rag_service.public_sources(results)
        self.assertEqual(len(payload), len(results))
        first = payload[0]
        for key in ("index", "title", "locator", "score", "coverage", "excerpt"):
            self.assertIn(key, first)
        self.assertEqual(first["index"], 1)
        self.assertLessEqual(len(first["excerpt"]), 160)

    def test_format_context_has_numbered_citations(self):
        results = rag_service.search("免费时长", top_k=2)
        context = rag_service.format_context(results)
        self.assertIn("[1]", context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
