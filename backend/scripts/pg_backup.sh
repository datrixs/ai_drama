#!/bin/bash
# ============================================
# PostgreSQL 定时备份脚本
# 通过 docker exec 调用容器内的 pg_dump 完成
# ============================================

# ---------- 配置 ----------
CONTAINER_NAME="drama_pg"
DB_USER="postgres"
DB_NAME="pipixia-drama"
DB_PASSWORD="${DB_PASSWORD:?请通过环境变量 DB_PASSWORD 提供数据库密码}"

# 备份保留天数
RETENTION_DAYS=15

# 备份目录（相对于脚本所在目录的上两级，即项目根目录的同级）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/backup"
LOG_FILE="${SCRIPT_DIR}/backup.log"

# 日期标记
DATE_TAG=$(date +"%Y%m%d_%H%M%S")
FILENAME="${DB_NAME}_${DATE_TAG}.sql.gz"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

# ---------- 日志 ----------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# ---------- 前置检查 ----------
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log "错误：容器 ${CONTAINER_NAME} 未运行"
    exit 1
fi

mkdir -p "${BACKUP_DIR}"

# ---------- 执行备份 ----------
log "开始备份数据库 ${DB_NAME} ..."

PGPASSWORD="${DB_PASSWORD}" docker exec "${CONTAINER_NAME}" \
    pg_dump -U "${DB_USER}" -d "${DB_NAME}" --format=plain --no-owner --no-privileges \
    | gzip > "${FILEPATH}"

if [ $? -ne 0 ]; then
    log "错误：备份失败"
    rm -f "${FILEPATH}"
    exit 1
fi

SIZE=$(du -h "${FILEPATH}" | cut -f1)
log "备份完成：${FILEPATH} (${SIZE})"

# ---------- 清理过期备份 ----------
DELETED=$(find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -mtime +${RETENTION_DAYS} -print -delete | wc -l)
if [ "${DELETED}" -gt 0 ]; then
    log "已清理 ${DELETED} 个超过 ${RETENTION_DAYS} 天的旧备份"
fi

log "备份流程结束"
