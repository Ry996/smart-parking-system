import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    # 默认密钥 40 字节（≥32 字节，满足 HS256 安全长度建议）
    SECRET_KEY = os.environ.get("SECRET_KEY", "smart-parking-v2-secret-key-2026-10")

    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "123456")
    DB_NAME = os.environ.get("DB_NAME", "smart_parking")

    BASE_DIR = os.path.dirname(__file__)
    SQLITE_PATH = os.path.join(BASE_DIR, "smart_parking.db")
    DATABASE_URL = os.environ.get("DATABASE_URL")

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or os.environ.get(
        "SQLALCHEMY_DATABASE_URI",
        f"sqlite:///{SQLITE_PATH}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_EXPIRATION_HOURS = 24

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    LPR_MOCK_MODE = os.environ.get("LPR_MOCK_MODE", "false").lower() in ("1", "true", "yes", "on")

    DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_TIMEOUT = int(os.environ.get("DEEPSEEK_TIMEOUT", 30))

    # 实验五：RAG 知识库目录与检索参数
    KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
    RAG_TOP_K = int(os.environ.get("RAG_TOP_K", 4))
    RAG_MIN_SCORE = float(os.environ.get("RAG_MIN_SCORE", 0.02))

    CORS_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
