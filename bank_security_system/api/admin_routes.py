from flask import Blueprint, request, jsonify
from services.rbac import role_required, admin_service
from services.user_service import UserService
from services.audit import audit_log
from models.user import User

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["GET"])
@role_required("admin")
def get_all_users():
    """获取所有用户信息（管理员专属）"""
    users = UserService.get_all_users()
    audit_log(action="query_users", resource="user_list")
    return jsonify([user.to_dict() for user in users])


@admin_bp.route("/users", methods=["POST"])
@role_required("admin")
def create_user():
    """创建新用户"""
    data = request.get_json()
    required_fields = ["username", "password", "role"]
    if not all(field in data for field in required_fields):
        return jsonify(error="Missing required fields"), 400

    user = UserService.create_user(
        username=data["username"], password=data["password"], role=data["role"]
    )
    audit_log(action="create_user", resource=f"user:{user.id}")
    return jsonify(user.to_dict()), 201


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@role_required("admin")
def update_user(user_id):
    """更新用户信息"""
    data = request.get_json()
    user = User.query.get_or_404(user_id)

    if "role" in data:
        UserService.update_user_role(user, data["role"])
    if "password" in data:
        UserService.update_password(user, data["password"])

    audit_log(action="update_user", resource=f"user:{user.id}")
    return jsonify(user.to_dict())


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@role_required("admin")
def delete_user(user_id):
    """删除用户"""
    user = User.query.get_or_404(user_id)
    UserService.delete_user(user)
    audit_log(action="delete_user", resource=f"user:{user.id}")
    return jsonify(message="User deleted"), 204


@admin_bp.route("/audit-logs", methods=["GET"])
@role_required("admin")
def get_audit_logs():
    """查询审计日志"""
    params = request.args.to_dict()
    logs = admin_service.query_audit_logs(params)
    return jsonify(logs)
