# from flask import g
# from flask_rbac import RBAC
# from functools import wraps
# from models.role import Role
# from models.permission import Permission

# rbac = RBAC()

# def role_required(role_name):
#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             if not hasattr(g, 'user') or role_name not in [r.name for r in g.user.roles]:
#                 return {'error': 'Forbidden'}, 403
#             return f(*args, **kwargs)
#         return decorated_function
#     return decorator


from functools import wraps
from flask import g, abort
from models.role import Role
from models.permission import Permission


class RBACService:
    def __init__(self):
        self.encryption_service = None  # 依赖加密服务

    def init_app(self, app):
        # 1. 从应用配置中获取加密服务实例
        # 假设加密服务在应用配置的 'ENCRYPTION_SERVICE' 中定义

        self.encryption_service = app.config.get("ENCRYPTION_SERVICE")
        if not self.encryption_service:
            raise RuntimeError(
                "Encryption service must be provided in app.config['ENCRYPTION_SERVICE']"
            )

        # 2. 将 RBACService 实例注册到 Flask 应用的 extensions 中
        app.extensions["rbac"] = self

        # pass   初始化逻辑

    def check_permission(self, user, permission):
        """检查用户是否有指定权限"""
        encrypted_perms = self.encryption_service.decrypt(user.permissions)
        return permission in encrypted_perms

    def role_required(self, role_name):
        """角色装饰器"""

        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not hasattr(g, "user"):
                    abort(401)  # Unauthorized
                user = g.user
                if not any(r.name == role_name for r in user.roles):
                    abort(403)  # Forbidden
                return f(*args, **kwargs)

            return decorated_function

        return decorator
