import os
import base64
import logging
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend  # 保留但可能不再需要
from flask import current_app
import hmac

# 在调用 cryptography 前添加环境路径配置（可能已不再需要）
# （注意：从43.0.0开始，Rust绑定不再需要额外路径配置）
# import os
# venv_path = os.path.dirname(os.path.dirname(os.__file__))
# os.environ['PATH'] = os.path.join(venv_path, 'Scripts') + os.pathsep + os.environ['PATH']


class EncryptionService:
    def __init__(self):
        self.symmetric_key = None
        self.private_key = None
        self.public_key = None
        self.signing_key = None

    def init_app(self, app):
        """初始化加密服务配置"""
        # 对称加密密钥（从环境变量加载）
        symmetric_key = app.config.get("SYMMETRIC_KEY")
        if symmetric_key:
            self.symmetric_key = base64.urlsafe_b64decode(symmetric_key)

        # 非对称密钥对
        self._load_rsa_keys(
            private_key_path=app.config.get("PRIVATE_KEY_PATH"),
            public_key_path=app.config.get("PUBLIC_KEY_PATH"),
        )

        # 签名密钥
        self.signing_key = app.config.get("SIGNING_KEY", os.urandom(32))

    def _load_rsa_keys(self, private_key_path: str, public_key_path: str):
        """加载RSA密钥对"""
        if private_key_path:
            with open(private_key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(), password=None  # 如果有密码需要处理
                )

        if public_key_path:
            with open(public_key_path, "rb") as f:
                self.public_key = serialization.load_pem_public_key(f.read())

    def generate_rsa_keypair(self, key_size=4096) -> tuple:
        """生成RSA密钥对"""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        return (private_key, private_key.public_key())

    def encrypt_symmetric(self, plaintext: bytes) -> dict:
        """AES-256-GCM对称加密"""
        if not self.symmetric_key:
            raise ValueError("Symmetric key not initialized")

        iv = os.urandom(12)
        cipher = Cipher(algorithms.AES(self.symmetric_key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return {"ciphertext": ciphertext, "iv": iv, "tag": encryptor.tag}

    def decrypt_symmetric(self, ciphertext: bytes, iv: bytes, tag: bytes) -> bytes:
        """AES-256-GCM对称解密"""
        cipher = Cipher(algorithms.AES(self.symmetric_key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    def encrypt_asymmetric(self, plaintext: bytes) -> bytes:
        """RSA-OAEP非对称加密"""
        if not self.public_key:
            raise ValueError("Public key not available")
        return self.public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    def decrypt_asymmetric(self, ciphertext: bytes) -> bytes:
        """RSA-OAEP非对称解密"""
        if not self.private_key:
            raise ValueError("Private key not available")
        return self.private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    def generate_hmac(self, data: bytes) -> bytes:
        """生成HMAC-SHA256签名"""
        hmac_obj = hmac.new(self.signing_key, data, hashes.SHA256())
        return hmac_obj.digest()

    def verify_hmac(self, data: bytes, signature: bytes) -> bool:
        """验证HMAC-SHA256签名"""
        expected_sig = self.generate_hmac(data)
        return hmac.compare_digest(signature, expected_sig)

    def derive_key(self, password: bytes, salt: bytes) -> bytes:
        """基于PBKDF2的密钥派生"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000
        )
        return kdf.derive(password)

    def encrypt_file(self, input_path: str, output_path: str):
        """加密文件（AES-256-GCM）"""
        with open(input_path, "rb") as f:
            plaintext = f.read()

        encrypted = self.encrypt_symmetric(plaintext)

        with open(output_path, "wb") as f:
            # 使用更安全的分隔符（避免数据污染）
            f.write(
                base64.urlsafe_b64encode(
                    encrypted["iv"]
                    + b":"
                    + encrypted["tag"]
                    + b":"
                    + encrypted["ciphertext"]
                )
            )

    def decrypt_file(self, input_path: str, output_path: str):
        """解密文件"""
        with open(input_path, "rb") as f:
            encrypted_data = base64.urlsafe_b64decode(f.read())

        parts = encrypted_data.split(b":", 2)
        iv, tag, ciphertext = parts
        plaintext = self.decrypt_symmetric(ciphertext, iv, tag)

        with open(output_path, "wb") as f:
            f.write(plaintext)
