from . import db, BaseModel
from .permission import Permission


class Role(BaseModel):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    # 权限关系（一对多）
    permissions = db.relationship(
        "Permission", back_populates="role", cascade="all, delete-orphan"
    )

    # 角色继承（可选）
    parent_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    children = db.relationship(
        "Role", backref=db.backref("parent", remote_side=[id]), cascade="all"
    )

    def add_permission(self, resource_type, actions, constraints=None):
        """添加权限"""
        perm = Permission(
            resource_type=resource_type,
            allowed_actions=actions,
            constraints=constraints or {},
        )
        self.permissions.append(perm)
        return perm

    def remove_permission(self, permission_id):
        """移除权限"""
        perm = next((p for p in self.permissions if p.id == permission_id), None)
        if perm:
            self.permissions.remove(perm)

    def get_permissions(self, include_inherited=True):
        """获取所有权限（包含继承的）"""
        perms = list(self.permissions)
        if include_inherited and self.parent:
            perms += self.parent.get_permissions(include_inherited=True)
        return perms

    def has_permission(self, resource_type, action):
        """检查权限（含继承）"""
        for perm in self.get_permissions():
            if perm.resource_type == resource_type and perm.has_action(action):
                return True
        return False
