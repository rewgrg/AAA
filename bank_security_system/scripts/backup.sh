#!/bin/bash
# 银行系统备份脚本（符合PCI-DSS标准）

# 配置参数
BACKUP_DIR="/secure_backups"
ENCRYPTION_KEY=$(aws ssm get-parameter --name "/prod/backup/key" --with-decryption --query Parameter.Value)
RETENTION_DAYS=30
LOG_FILE="/var/log/backup.log"
MYSQL_USER="backup_user"
MYSQL_PASSWORD=$(aws ssm get-parameter --name "/prod/db/password" --with-decryption --query Parameter.Value)
DATABASES=("bank_db" "audit_db")
S3_BUCKET="bank-backups"

# 安全初始化
umask 077
mkdir -p ${BACKUP_DIR}/{tmp,encrypted}
chmod 700 ${BACKUP_DIR}

# 审计日志函数
audit_log() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "${timestamp} [backup] $1" >> ${LOG_FILE}
    logger -t bank-backup "$1"
}

# 开始备份
audit_log "Starting backup process"

# 数据库备份
for DB in "${DATABASES[@]}"; do
    TIMESTAMP=$(date +"%Y%m%d%H%M%S")
    BACKUP_FILE="${BACKUP_DIR}/tmp/${DB}_${TIMESTAMP}.sql.gz"
    
    # 执行mysqldump并压缩
    mysqldump --single-transaction --quick \
              -u ${MYSQL_USER} -p${MYSQL_PASSWORD} ${DB} | \
    gzip -9 > ${BACKUP_FILE}
    
    # 验证备份完整性
    if [ $? -eq 0 ] && gzip -t ${BACKUP_FILE}; then
        audit_log "Database ${DB} backup successful"
    else
        audit_log "ERROR: Database ${DB} backup failed"
        rm -f ${BACKUP_FILE}
        exit 1
    fi

    # 加密备份文件
    ENCRYPTED_FILE="${BACKUP_DIR}/encrypted/${DB}_${TIMESTAMP}.enc"
    openssl enc -aes-256-cbc -salt -in ${BACKUP_FILE} \
               -out ${ENCRYPTED_FILE} -k ${ENCRYPTION_KEY}
    
    # 验证加密文件
    if openssl enc -d -aes-256-cbc -in ${ENCRYPTED_FILE} \
                  -k ${ENCRYPTION_KEY} -nopad -noout 2>/dev/null; then
        audit_log "Encryption successful for ${DB}"
        rm -f ${BACKUP_FILE}
    else
        audit_log "ERROR: Encryption failed for ${DB}"
        exit 1
    fi
done

# 文件系统备份（配置文件等）
tar -czf ${BACKUP_DIR}/tmp/configs_${TIMESTAMP}.tar.gz \
    -C /opt/bank_security_system config/ scripts/ --exclude=*.log

# 加密文件系统备份
openssl enc -aes-256-cbc -salt \
    -in ${BACKUP_DIR}/tmp/configs_${TIMESTAMP}.tar.gz \
    -out ${BACKUP_DIR}/encrypted/configs_${TIMESTAMP}.enc \
    -k ${ENCRYPTION_KEY}

# 生成校验文件
sha256sum ${BACKUP_DIR}/encrypted/* > ${BACKUP_DIR}/backup_checksums.sha256

# 传输到S3（使用AWS KMS加密）
aws s3 cp ${BACKUP_DIR}/encrypted/ s3://${S3_BUCKET}/ \
    --recursive --sse aws:kms --kms-key-id arn:aws:kms:...

# 清理旧备份
find ${BACKUP_DIR}/encrypted -type f -mtime +${RETENTION_DAYS} -exec rm {} \;

# 完成审计
audit_log "Backup completed successfully with $(ls ${BACKUP_DIR}/encrypted | wc -l) files"