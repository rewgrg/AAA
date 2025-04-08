# models/base_model.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class BaseModel(db.Model):
    __abstract__ = True
    # Add your base model fields here