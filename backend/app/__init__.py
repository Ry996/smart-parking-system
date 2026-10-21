from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import Config
import os

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化扩展
    db.init_app(app)
    CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 注册蓝图
    from app.api.auth      import auth_bp
    from app.api.parking   import parking_bp
    from app.api.records   import records_bp
    from app.api.stats     import stats_bp
    from app.api.fee_rules import fee_bp
    from app.api.users     import users_bp
    from app.api.lpr_api   import lpr_bp
    from app.api.monthly   import monthly_bp
    from app.api.reservations import reservation_bp
    from app.api.blacklist import blacklist_bp
    from app.api.logs      import logs_bp
    from app.api.export    import export_bp
    from app.api.ai        import ai_bp
    from app.api.roles     import roles_bp
    from app.api.docs      import docs_bp

    app.register_blueprint(auth_bp,    url_prefix='/api/auth')
    app.register_blueprint(parking_bp, url_prefix='/api/parking')
    app.register_blueprint(records_bp, url_prefix='/api/records')
    app.register_blueprint(stats_bp,   url_prefix='/api/stats')
    app.register_blueprint(fee_bp,     url_prefix='/api/fee-rules')
    app.register_blueprint(users_bp,   url_prefix='/api/users')
    app.register_blueprint(lpr_bp,     url_prefix='/api/lpr')
    app.register_blueprint(monthly_bp, url_prefix='/api/monthly')
    app.register_blueprint(reservation_bp, url_prefix='/api/reservations')
    app.register_blueprint(blacklist_bp, url_prefix='/api/blacklist')
    app.register_blueprint(logs_bp,    url_prefix='/api/logs')
    app.register_blueprint(export_bp,  url_prefix='/api/export')
    app.register_blueprint(ai_bp,      url_prefix='/api/ai')
    app.register_blueprint(roles_bp,   url_prefix='/api/roles')
    app.register_blueprint(docs_bp,    url_prefix='/api')

    return app
