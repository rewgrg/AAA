from flask import Blueprint, request, jsonify
from services.rbac import role_required
from services.encryption import EncryptionService
from services.audit import audit_log
from models.account import Account
from models.transaction import Transaction
from decimal import Decimal
import json

data_bp = Blueprint("data", __name__)

# 初始化加密服务
encryption_service = EncryptionService()


@data_bp.route("/accounts/<int:account_id>", methods=["GET"])
@role_required("teller")  # 柜台人员可查看账户信息
def get_account_info(account_id):
    """获取账户详细信息"""
    account = Account.query.get_or_404(account_id)

    # 解密敏感数据
    decrypted_balance = encryption_service.decrypt_data(
        account.encrypted_balance, private_key=encryption_service.get_private_key()
    )

    audit_log(action="view_account", resource=f"account:{account.id}")
    return jsonify(
        {
            "id": account.id,
            "owner": account.owner,
            "balance": str(Decimal(decrypted_balance.decode())),
            "currency": account.currency,
        }
    )


@data_bp.route("/transactions", methods=["POST"])
@role_required("teller")
def create_transaction():
    """执行转账操作"""
    data = request.get_json()
    required_fields = ["from_account", "to_account", "amount"]
    if not all(field in data for field in required_fields):
        return jsonify(error="Missing required fields"), 400

    # 验证账户有效性
    from_account = Account.query.get(data["from_account"])
    to_account = Account.query.get(data["to_account"])
    if not from_account or not to_account:
        return jsonify(error="Invalid account"), 404

    # 执行转账逻辑
    amount = Decimal(data["amount"])
    if from_account.balance < amount:
        return jsonify(error="Insufficient funds"), 400

    # 更新账户余额（加密存储）
    from_account.balance -= amount
    to_account.balance += amount

    # 创建交易记录
    transaction = Transaction(
        from_account_id=from_account.id,
        to_account_id=to_account.id,
        amount=encryption_service.encrypt_data(str(amount).encode()),
        status="completed",
    )
    db.session.add(transaction)
    db.session.commit()

    audit_log(action="transfer_funds", resource=f"transaction:{transaction.id}")
    return jsonify(transaction.to_dict()), 201


@data_bp.route("/accounts/<int:account_id>/transactions", methods=["GET"])
@role_required(["teller", "customer"])  # 允许用户查询自己的交易记录
def get_transaction_history(account_id):
    """获取账户交易记录"""
    # 权限验证：用户只能查看自己的账户
    if (
        current_user.role == "customer"
        and current_user.id != Account.query.get(account_id).user_id
    ):
        return jsonify(error="Forbidden"), 403

    transactions = Transaction.query.filter(
        (Transaction.from_account_id == account_id)
        | (Transaction.to_account_id == account_id)
    ).all()

    audit_log(action="view_transactions", resource=f"account:{account_id}")
    return jsonify([tx.to_dict() for tx in transactions])


@data_bp.route("/accounts", methods=["POST"])
@role_required("admin")
def create_account():
    """创建银行账户（管理员权限）"""
    data = request.get_json()
    account = Account(
        owner=data["owner"],
        currency=data.get("currency", "CNY"),
        encrypted_balance=encryption_service.encrypt_data(b"0.00"),
    )
    db.session.add(account)
    db.session.commit()

    audit_log(action="create_account", resource=f"account:{account.id}")
    return jsonify(account.to_dict()), 201
