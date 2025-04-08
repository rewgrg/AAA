# 删除手动添加 PATH 的代码（新版本不再需要）
# cryptography 43.0+ 已重构底层实现，直接使用标准导入方式

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from config import Config
from services.rbac import RBACService
from services.auth import jwt
from cryptography.hazmat.primitives import hashes, serialization  # 使用标准API入口
from cryptography.hazmat.backends import default_backend  # 显式指定后端

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化扩展
    RBACService.init_app(db, app=app)
    RBACService.init_app(self, app=app)
    RBACService.init_app(jwt, app=app)

    # CORS配置保持不变
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    @app.route("/api/<path:path>", methods=["OPTIONS"])
    def handle_options(path):
        return jsonify({"status": "success"}), 200

    # 注册蓝图保持不变
    from api.auth_routes import auth_bp
    from api.data_routes import data_bp
    from api.admin_routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(data_bp, url_prefix="/api/data")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    return app
