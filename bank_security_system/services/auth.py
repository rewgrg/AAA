from flask import current_app, g
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    verify_jwt_in_request,
    get_jwt_identity,
)
from flask_jwt_extended.exceptions import JWTDecodeError
from flask_jwt_extended.utils import decode_token
from urllib.parse import unquote  # 保留
from .encryption import EncryptionService
from .rbac import RBACService
from .audit import audit_service
from models.user import User
import pyotp
import datetime

jwt = JWTManager()
encryption_service = EncryptionService()


class AuthService:
    def __init__(self):
        self.rbac_service = None
        self.token_blacklist = set()  # 记录被撤销的 Token

    def init_app(self, app):
        """初始化 JWT 和 RBAC 服务"""
        jwt.init_app(app)
        self.rbac_service = RBACService()  # 初始化 RBAC

        # 自定义 JWT 负载（添加角色和 MFA 状态）
        @jwt.additional_claims_loader
        def add_claims_to_access_token(user):
            return {
                "roles": [role.name for role in user.roles],
                "mfa_enabled": user.mfa_enabled,
            }

        # 检查 Token 是否在黑名单中
        @jwt.token_in_blocklist_loader
        def check_token_revoked(jwt_header, jwt_payload):
            jti = jwt_payload.get("jti")
            return jti in self.token_blacklist

    def authenticate_user(self, username: str, password: str, otp: str = None) -> dict:
        """用户认证（含 MFA）"""
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            audit_service.log_activity(
                None, "login_failed", f"user:{username}"  # 匿名用户
            )
            return {"error": "Invalid credentials"}, 401

        if user.mfa_enabled:
            if not otp:
                return {"mfa_required": True}, 401
            if not pyotp.TOTP(user.mfa_secret).verify(otp):
                audit_service.log_activity(user.id, "mfa_failed", f"user:{username}")
                return {"error": "Invalid OTP"}, 401

        # 记录成功登录
        audit_service.log_activity(user.id, "login_success", f"user:{username}")
        return {
            "access_token": self._create_tokens(user)["access_token"],
            "refresh_token": self._create_tokens(user)["refresh_token"],
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].seconds,
        }

    def _create_tokens(self, user):
        """生成带编码的 Token"""
        access_token = create_access_token(identity=user)
        refresh_token = create_refresh_token(identity=user)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].seconds,
        }

    def refresh_access_token(self, refresh_token: str) -> dict:
        """刷新 Access Token"""
        try:
            # 验证 Refresh Token（需确保 token 在请求头中）
            verify_jwt_in_request(locations=["headers"])
            payload = get_jwt()
            user_id = payload["sub"]
            user = User.query.get(user_id)
            if not user:
                audit_service.log_activity(None, "refresh_failed", "Invalid user")
                return {"error": "Invalid user"}, 401

            # 记录刷新操作
            audit_service.log_activity(user.id, "token_refreshed", f"user:{user.id}")
            new_access_token = create_access_token(identity=user)
            return {"access_token": new_access_token}
        except JWTDecodeError as e:
            audit_service.log_activity(None, "refresh_failed", str(e))
            return {"error": "Invalid refresh token"}, 401

    def revoke_token(self, token: str):
        """撤销 Token"""
        try:
            # 验证 Token 并获取 payload
            verify_jwt_in_request(locations=["headers"])
            payload = get_jwt()
            jti = payload.get("jti")
            if jti:
                self.token_blacklist.add(jti)
                audit_service.log_activity(None, "token_revoked", f"jti:{jti}")
        except Exception as e:
            audit_service.log_activity(None, "revoke_failed", str(e))

    def get_current_user(self) -> User:
        """获取当前认证用户"""
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        return User.query.get(user_id)

    def check_permission(self, resource: str, action: str) -> bool:
        """检查用户权限（RBAC）"""
        user = self.get_current_user()
        return self.rbac_service.has_permission(user, resource, action)
