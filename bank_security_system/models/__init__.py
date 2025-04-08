from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from datetime import datetime
from config import Config

# 初始化数据库实例
# db = SQLAlchemy()


# models/__init__.py——————
from .base_model import db, BaseModel
from .role import Role
from .user import User  # Add other models as needed

__all__ = ["db", "BaseModel", "Role", "User"]


# 解决SQLAlchemy 1.4与Flask 2.3的兼容性
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)

# 导入所有模型类
from .user import User
from .role import Role
from .permission import Permission

# 定义多对多关联表
user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
)


# 公共基类（可选）
class BaseModel(db.Model):
    __abstract__ = True
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_deleted = db.Column(db.Boolean, default=False)

    def soft_delete(self):
        self.is_deleted = True
        db.session.commit()


# 初始化数据库（在应用工厂中调用）
def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
