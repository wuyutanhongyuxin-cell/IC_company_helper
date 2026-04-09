#!/bin/bash
# WaferCut MES — SQLite WAL 安全备份脚本
# 使用 sqlite3 .backup API，安全处理 WAL 模式
# Cron 示例: 0 2 * * * /opt/wafercut/backup.sh
set -euo pipefail
trap 'echo "$(date "+%Y-%m-%d %H:%M:%S") FAIL: backup failed at line $LINENO" >> "$LOG_FILE"' ERR

# ── 可调常量 ──────────────────────────────────────
RETAIN_DAYS=7
APP_DIR=/opt/wafercut
DB_PATH="$APP_DIR/instance/wafercut.db"
BACKUP_DIR="$APP_DIR/backups"
LOG_FILE="/var/log/wafercut/backup.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── 日志函数 ──────────────────────────────────────
log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

# ── 备份 ──────────────────────────────────────────
do_backup() {
    local backup_file="$BACKUP_DIR/wafercut_${TIMESTAMP}.db"
    mkdir -p "$BACKUP_DIR"

    # sqlite3 .backup 使用在线备份 API，WAL 模式安全
    sqlite3 "$DB_PATH" ".backup '${backup_file}'"
    gzip "${backup_file}"

    log_msg "OK: ${backup_file}.gz ($(du -h "${backup_file}.gz" | cut -f1))"
}

# ── 清理旧备份 ────────────────────────────────────
cleanup_old() {
    local count
    count=$(find "$BACKUP_DIR" -name "wafercut_*.db.gz" -mtime +"$RETAIN_DAYS" | wc -l)
    if [ "$count" -gt 0 ]; then
        find "$BACKUP_DIR" -name "wafercut_*.db.gz" -mtime +"$RETAIN_DAYS" -delete
        log_msg "CLEANUP: deleted $count backups older than $RETAIN_DAYS days"
    fi
}

# ── 主流程 ────────────────────────────────────────
do_backup
cleanup_old
