from flask import current_app, g
from flask_pymongo import PyMongo
from datetime import datetime
from .encryption import EncryptionService
import hmac
import hashlib
import json
from bson import ObjectId  # 用于 MongoDB ObjectId 转换

class audit_service:#————————————
    def __init__(self):
        self.mongo = None          # MongoDB 客户端
        self.encryption_service = None
        self.audit_collection = "audit_logs"  # MongoDB 集合名
        self.signing_key = None

    def init_app(self, app):
        """初始化服务"""
        self.mongo = PyMongo(app)  # 初始化 MongoDB 连接
        self.signing_key = app.config['AUDIT_SIGNING_KEY']
        self.encryption_service = EncryptionService()
        self.create_audit_collection()  # 创建集合（可选）

    def create_audit_collection(self):
        """创建 MongoDB 集合并添加索引（可选）"""
        # 创建时间戳索引
        self.mongo.db[self.audit_collection].create_index("timestamp")
        # 可选：其他验证规则或索引

    def log_activity(
        self,
        user_id: str,
        action: str,
        resource: str,
        sensitive_data: dict = None
    ) -> str:
        """记录带签名和加密的审计日志"""
        log = {
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "signature": None,
            "encrypted_data": None,
        }

        # 处理敏感数据
        if sensitive_data:
            encrypted_data = self.encryption_service.encrypt(
                json.dumps(sensitive_data).encode()
            )
            log["encrypted_data"] = encrypted_data

        # 生成签名（排除 signature 字段）
        data_without_sig = {
            k: v for k, v in log.items() if k != "signature"
        }
        log["signature"] = self._generate_signature(data_without_sig)

        # 写入 MongoDB
        result = self.mongo.db[self.audit_collection].insert_one(log)
        return str(result.inserted_id)  # 返回 MongoDB 的 ObjectID

    def verify_log_integrity(self, log_id: str) -> bool:
        """验证日志条目签名是否被篡改"""
        log = self.mongo.db[self.audit_collection].find_one(
            {"_id": ObjectId(log_id)}
        )
        if not log:
            return False  # 日志不存在

        # 移除 signature 字段重新计算
        stored_sig = log.pop("signature")
        calculated_sig = self._generate_signature(log)
        return hmac.compare_digest(stored_sig, calculated_sig)

    def _generate_signature(self, data: dict) -> str:
        """生成 HMAC-SHA256 签名"""
        msg = json.dumps(data, sort_keys=True).encode()
        return hmac.new(
            self.signing_key.encode(),  # 确保签名密钥为 bytes
            msg,
            hashlib.sha256
        ).hexdigest()

    def search_logs(self, query: dict, verify_signature: bool = True) -> list:
        """查询日志并验证签名（可选）"""
        results = list(
            self.mongo.db[self.audit_collection].find(query)
        )
        if verify_signature:
            for log in results:
                if not self.verify_log_integrity(str(log["_id"])):
                    current_app.logger.error(
                        f"Tampered log detected: {log['_id']}"
                    )
        return results