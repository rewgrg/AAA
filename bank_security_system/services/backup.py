import os
import subprocess
import shutil
import logging
import boto3
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
from .encryption import EncryptionService
from .audit import audit_service


class BackupScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.encryption_service = EncryptionService()
        self.backup_dir = None
        self.s3_client = None
        self.retention_days = 30

    def init_app(self, app):
        """初始化备份服务"""
        self.backup_dir = app.config["BACKUP_DIR"]
        self.retention_days = app.config["BACKUP_RETENTION_DAYS"]
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=app.config["AWS_ACCESS_KEY"],
            aws_secret_access_key=app.config["AWS_SECRET_KEY"],
        )
        os.makedirs(self.backup_dir, exist_ok=True)

        # 启动调度器
        if not self.scheduler.running:
            self.scheduler.add_job(self.perform_backup, "cron", hour=2, minute=0)
            self.scheduler.start()

    def perform_backup(self):
        """执行完整备份流程"""
        backup_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        temp_dir = os.path.join(self.backup_dir, f"temp_{backup_id}")
        os.makedirs(temp_dir)

        try:
            # 数据库备份
            self._backup_database(temp_dir)

            # 文件系统备份
            self._backup_filesystem(temp_dir)

            # 加密处理
            encrypted_dir = os.path.join(self.backup_dir, f"encrypted_{backup_id}")
            os.makedirs(encrypted_dir)
            self._encrypt_backup(temp_dir, encrypted_dir)

            # 校验和生成
            checksum = self._generate_checksum(encrypted_dir)

            # 上传到S3
            self._upload_to_s3(encrypted_dir, checksum)

            # 清理临时文件
            shutil.rmtree(temp_dir)
            shutil.rmtree(encrypted_dir)

            # 记录审计日志
            audit_service.log_activity(
                action="backup_success",
                resource="system",
                sensitive_data={"backup_id": backup_id, "checksum": checksum},
            )

        except Exception as e:
            audit_service.log_activity(
                action="backup_failed",
                resource="system",
                sensitive_data={"error": str(e)},
            )
            raise

    def _backup_database(self, temp_dir):
        """执行数据库备份"""
        databases = current_app.config["DATABASES"]
        for db in databases:
            dump_file = os.path.join(temp_dir, f"{db}.sql.gz")
            cmd = (
                f"mysqldump -u {current_app.config['DB_USER']} "
                f"-p{current_app.config['DB_PASSWORD']} {db} | gzip -9 > {dump_file}"
            )
            subprocess.run(cmd, shell=True, check=True)

    def _backup_filesystem(self, temp_dir):
        """备份配置文件等"""
        config_backup = os.path.join(temp_dir, "config.tar.gz")
        shutil.make_archive(
            config_backup[:-7],
            "gztar",
            root_dir="/opt/bank_security_system",
            base_dir="config",
            verbose=False,
        )

    def _encrypt_backup(self, source_dir, target_dir):
        """加密备份文件"""
        for filename in os.listdir(source_dir):
            plain_path = os.path.join(source_dir, filename)
            encrypted_path = os.path.join(target_dir, f"{filename}.enc")
            self.encryption_service.encrypt_file(plain_path, encrypted_path)

    def _generate_checksum(self, directory):
        """生成校验和文件"""
        checksum_file = os.path.join(directory, "checksum.sha256")
        sha256_cmd = f"sha256sum {directory}/* > {checksum_file}"
        subprocess.run(sha256_cmd, shell=True, check=True)
        return checksum_file

    def _upload_to_s3(self, directory, checksum_file):
        """上传到S3并验证"""
        s3_bucket = current_app.config["S3_BUCKET"]
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            s3_key = f"backups/{datetime.utcnow().date()}/{filename}"
            self.s3_client.upload_file(
                file_path,
                s3_bucket,
                s3_key,
                ExtraArgs={
                    "ServerSideEncryption": "aws:kms",
                    "SSEKMSKeyId": current_app.config["KMS_KEY_ID"],
                },
            )

        # 验证上传
        with open(checksum_file, "rb") as f:
            self.s3_client.put_object(
                Bucket=s3_bucket,
                Key=f"backups/{datetime.utcnow().date()}/checksum.sha256",
                Body=f.read(),
            )

    def cleanup_old_backups(self):
        """清理过期备份"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        s3_bucket = current_app.config["S3_BUCKET"]
        response = self.s3_client.list_objects_v2(Bucket=s3_bucket)

        for obj in response.get("Contents", []):
            if obj["LastModified"].replace(tzinfo=None) < cutoff_date:
                self.s3_client.delete_object(Bucket=s3_bucket, Key=obj["Key"])
                audit_service.log_activity(action="backup_cleanup", resource=obj["Key"])
