from . import db
from datetime import datetime
from enum import Enum

class ResourceType(Enum):
    USER_MANAGEMENT = 'user_management'
    TRANSACTION = 'transaction'
    ACCOUNT = 'account'
    AUDIT_LOG = 'audit_log'
    SYSTEM_CONFIG = 'system_config'

class Action(Enum):
    CREATE = 'create'
    READ = 'read'
    UPDATE = 'update'
    DELETE = 'delete'
    APPROVE = 'approve'

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    
    # 资源类型（如用户管理、交易等）
    resource_type = db.Column(db.Enum(ResourceType), nullable=False)
    
    # 允许的操作（位掩码存储）
    allowed_actions = db.Column(db.Integer, default=0)
    
    # 限制条件（JSON格式存储）
    constraints = db.Column(db.JSON)
    
    # 审计字段
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联角色
    role = db.relationship('Role', back_populates='permissions')

    def add_action(self, action: Action):
        self.allowed_actions |= action.value

    def remove_action(self, action: Action):
        self.allowed_actions &= ~action.value

    def has_action(self, action: Action) -> bool:
        return (self.allowed_actions & action.value) == action.value

    def set_constraint(self, key: str, value: any):
        if not self.constraints:
            self.constraints = {}
        self.constraints[key] = value

    def get_constraint(self, key: str) -> any:
        return self.constraints.get(key) if self.constraints else None