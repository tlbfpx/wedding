#!/bin/bash
set -e

# MySQL Backup Script for Wedding Management System
# Supports local file or S3 backup

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DB_HOST="${DB_HOST:-mysql}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASS="${DB_PASS:-${MYSQL_ROOT_PASSWORD}}"
DB_NAME="${DB_NAME:-wedding}"
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-wedding-backup}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "[backup] Starting MySQL backup at $(date)"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Run mysqldump
echo "[backup] Dumping database ${DB_NAME}..."
mysqldump -h "${DB_HOST}" -P "${DB_PORT}" -u "${DB_USER}" -p"${DB_PASS}" \
    --single-transaction --quick --lock-tables=false \
    --routines --triggers --events \
    "${DB_NAME}" | gzip > "${BACKUP_FILE}"

# Verify backup file
if [ -f "${BACKUP_FILE}" ] && [ -s "${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "[backup] Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"
else
    echo "[backup] ERROR: Backup file is empty or missing!"
    exit 1
fi

# Upload to S3 if configured
if [ -n "${S3_BUCKET}" ]; then
    echo "[backup] Uploading to S3: s3://${S3_BUCKET}/${S3_PREFIX}/${DB_NAME}_${TIMESTAMP}.sql.gz"
    aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/${S3_PREFIX}/${DB_NAME}_${TIMESTAMP}.sql.gz"
    echo "[backup] S3 upload complete"
fi

# Cleanup old backups (local)
echo "[backup] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# If S3 is configured, also cleanup S3 old backups
if [ -n "${S3_BUCKET}" ]; then
    echo "[backup] Cleaning up S3 backups older than ${RETENTION_DAYS} days..."
    aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | while read -r line; do
        file=$(echo "$line" | awk '{print $4}')
        # Extract timestamp from filename
        if [[ "$file" =~ ${DB_NAME}_[0-9]{8}_[0-9]{6}.sql.gz ]]; then
            # Check if file is older than retention days
            aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${file}" --recursive 2>/dev/null || true
        fi
    done
fi

echo "[backup] Backup completed at $(date)"