# api/__init__.py

from flask import Blueprint
from flask_restful import Api
from .auth_routes import auth_bp
from .data_routes import data_bp
from .admin_routes import admin_bp

# 创建API蓝图
api_bp = Blueprint("api", __name__, url_prefix="/api")

# 绑定RESTful API
api = Api(api_bp)

# 注册子路由蓝图
api_bp.register_blueprint(auth_bp, url_prefix="/auth")
api_bp.register_blueprint(data_bp, url_prefix="/data")
api_bp.register_blueprint(admin_bp, url_prefix="/admin")


# 可在此处添加全局异常处理
@api_bp.errorhandler(404)
def not_found(error):
    return {"error": "Resource not found"}, 404


# 添加JWT验证钩子（示例）
from services.auth import jwt_required


@api_bp.before_request
def before_request():
    if request.endpoint and not request.endpoint.startswith("auth"):
        jwt_required()
