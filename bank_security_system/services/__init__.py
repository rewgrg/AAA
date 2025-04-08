from flask import Flask
from cryptography.hazmat.backends import default_backend  # 新增显式后端声明
from .encryption import EncryptionService
from .rbac import RBACService
from .auth import AuthService
from .audit import audit_service
from .backup import BackupScheduler

# 服务实例化（增加后端配置传递）
encryption = EncryptionService()  # 注入后端backend=default_backend()
rbac = RBACService()
auth = AuthService()
audit = audit_service()
backup_scheduler = BackupScheduler()

def init_services(app: Flask):
    """初始化所有服务（适配 cryptography 43.x 的依赖注入）"""
    
    # 加密服务初始化（需传递 backend）
    encryption.init_app(
        app,
        key_derivation_backend=default_backend(),  # 示例参数
        asymmetric_backend=default_backend()
    )
    
    # RBAC服务初始化（强制类型校验）
    if not isinstance(encryption, EncryptionService):
        raise RuntimeError("RBAC 必须依赖有效的 EncryptionService 实例")
    rbac.encryption_service = encryption
    rbac.init_app(app)
    
    # 认证服务初始化（依赖校验）
    if not hasattr(rbac, 'check_permission'):
        raise AttributeError("AuthService 需要 RBACService 实现权限检查方法")
    auth.rbac_service = rbac
    auth.init_app(app)
    
    # 审计服务初始化（加密上下文传递）
    audit.encryption_service = encryption.with_context(
        backend=default_backend()  # 确保审计使用独立上下文
    )
    audit.init_app(app)
    
    # 备份服务初始化（异步兼容处理）
    backup_scheduler.audit_service = audit
    backup_scheduler.init_app(
        app,
        encryption_context=encryption.get_backend_context()  # 获取加密上下文
    )
    
    # 注册服务到应用上下文（增加版本元数据）
    app.extensions['services'] = {
        'encryption': encryption,
        'rbac': rbac,
        'auth': auth,
        'audit': audit,
        'backup': backup_scheduler,
        'cryptography_version': '43.0.3'  # 版本标识
    }