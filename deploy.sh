#!/bin/bash
# WaferCut MES — Ubuntu 24.04 一键部署脚本
# 用法: sudo bash deploy.sh          # 首次安装
#       sudo bash deploy.sh --update  # 代码更新（跳过用户/nginx/systemd/cron）
set -euo pipefail

# ── 常量 ──────────────────────────────────────────
APP_DIR=/opt/wafercut
APP_USER=wafercut
VENV="$APP_DIR/venv"
LOG_DIR=/var/log/wafercut
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
UPDATE_MODE=false
[[ "${1:-}" == "--update" ]] && UPDATE_MODE=true

# ── 辅助函数 ──────────────────────────────────────
info()  { echo -e "\033[1;32m[INFO]\033[0m  $1"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $1"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $1"; exit 1; }

check_root() {
    [[ $EUID -eq 0 ]] || error "请使用 sudo 运行此脚本"
}

# ── 1. 系统依赖 ───────────────────────────────────
install_system_deps() {
    info "安装系统依赖..."
    apt-get update -qq
    apt-get install -y -qq \
        python3 python3-venv python3-pip python3-dev \
        nginx sqlite3 \
        fonts-noto-cjk libpango-1.0-0 libharfbuzz-subset0 \
        > /dev/null
    info "系统依赖安装完成"
}

# ── 2. 应用用户 ───────────────────────────────────
create_app_user() {
    if id "$APP_USER" &>/dev/null; then
        info "用户 $APP_USER 已存在，跳过"
    else
        useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" "$APP_USER"
        info "创建系统用户 $APP_USER"
    fi
    mkdir -p "$LOG_DIR"
    chown "$APP_USER":"$APP_USER" "$LOG_DIR"
}

# ── 3. 部署代码 ───────────────────────────────────
deploy_code() {
    info "同步代码到 $APP_DIR..."
    mkdir -p "$APP_DIR"
    rsync -a --delete \
        --exclude '.git' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.env' \
        --exclude '.flaskenv' \
        --exclude 'instance/' \
        --exclude 'venv/' \
        --exclude 'backups/' \
        "$SRC_DIR/" "$APP_DIR/"

    # 虚拟环境 + 依赖
    if [ ! -d "$VENV" ]; then
        python3 -m venv "$VENV"
        info "创建虚拟环境"
    fi
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
    info "Python 依赖安装完成"

    chown -R "$APP_USER":"$APP_USER" "$APP_DIR"
}

# ── 4. 环境变量 ───────────────────────────────────
setup_env() {
    local env_file="$APP_DIR/.env"
    if [ -f "$env_file" ]; then
        info ".env 已存在，跳过（如需重置请手动删除）"
        return
    fi
    # 从模板复制并生成随机 SECRET_KEY
    cp "$APP_DIR/.env.example" "$env_file"
    local secret_key
    secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${secret_key}/" "$env_file"
    chmod 600 "$env_file"
    chown "$APP_USER":"$APP_USER" "$env_file"
    info "生成 .env（SECRET_KEY 已自动填充）"
    warn "请修改 .env 中的 ADMIN_PASSWORD！"
}

# ── 5. 数据库初始化 ───────────────────────────────
init_database() {
    mkdir -p "$APP_DIR/instance"
    chown "$APP_USER":"$APP_USER" "$APP_DIR/instance"

    cd "$APP_DIR"
    # flask CLI 需要 FLASK_APP 环境变量
    export FLASK_APP=wsgi.py
    export FLASK_CONFIG=config.ProductionConfig
    if [ -f "$APP_DIR/instance/wafercut.db" ]; then
        info "数据库已存在，执行迁移..."
        sudo -u "$APP_USER" -E "$VENV/bin/flask" db upgrade
    else
        info "首次初始化数据库..."
        sudo -u "$APP_USER" -E "$VENV/bin/flask" db upgrade
        sudo -u "$APP_USER" -E "$VENV/bin/flask" init-db
        info "数据库初始化完成（默认管理员已创建）"
    fi
}

# ── 6. systemd 服务 ───────────────────────────────
setup_systemd() {
    info "配置 systemd 服务..."
    cat > /etc/systemd/system/wafercut.service << 'EOF'
[Unit]
Description=WaferCut MES Gunicorn daemon
After=network.target

[Service]
User=wafercut
Group=wafercut
WorkingDirectory=/opt/wafercut
EnvironmentFile=/opt/wafercut/.env
ExecStart=/opt/wafercut/venv/bin/gunicorn \
    --workers 2 \
    --bind unix:/run/wafercut/wafercut.sock \
    --access-logfile /var/log/wafercut/access.log \
    --error-logfile /var/log/wafercut/error.log \
    --timeout 120 \
    --preload \
    "wsgi:app"
ExecReload=/bin/kill -s HUP $MAINPID
RuntimeDirectory=wafercut
Restart=on-failure
RestartSec=5s
SyslogIdentifier=wafercut

# 安全加固
ProtectSystem=full
PrivateTmp=true
NoNewPrivileges=true
ProtectHome=true
ReadWritePaths=/opt/wafercut/instance /var/log/wafercut

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable wafercut
    systemctl restart wafercut
    info "systemd 服务已启动"
}

# ── 7. Nginx 配置 ─────────────────────────────────
setup_nginx() {
    info "配置 Nginx 反向代理..."
    cat > /etc/nginx/sites-available/wafercut << 'EOF'
upstream wafercut {
    server unix:/run/wafercut/wafercut.sock fail_timeout=0;
}

server {
    listen 80;
    server_name _;

    # 静态文件由 Nginx 直接服务
    location /static/ {
        alias /opt/wafercut/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # 代理到 Gunicorn
    location / {
        proxy_pass http://wafercut;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    # 安全头
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 隐藏文件禁止访问
    location ~ /\. { deny all; }

    client_max_body_size 16M;
}
EOF

    ln -sf /etc/nginx/sites-available/wafercut /etc/nginx/sites-enabled/wafercut
    rm -f /etc/nginx/sites-enabled/default
    nginx -t
    systemctl reload nginx
    info "Nginx 配置完成"
}

# ── 8. 备份定时任务 ───────────────────────────────
setup_backup() {
    chmod +x "$APP_DIR/backup.sh"
    # 每日凌晨 2 点执行备份
    local cron_job="0 2 * * * $APP_DIR/backup.sh"
    (crontab -u "$APP_USER" -l 2>/dev/null | grep -v "$APP_DIR/backup.sh"; echo "$cron_job") \
        | crontab -u "$APP_USER" -
    info "备份定时任务已配置（每日 02:00）"
}

# ── 主流程 ────────────────────────────────────────
main() {
    check_root

    if $UPDATE_MODE; then
        info "=== 更新模式 ==="
        install_system_deps
        deploy_code
        init_database
        systemctl restart wafercut
        info "=== 更新完成 ==="
    else
        info "=== 首次部署 ==="
        install_system_deps
        create_app_user
        deploy_code
        setup_env
        init_database
        setup_systemd
        setup_nginx
        setup_backup
        info "=== 部署完成 ==="
        info "访问 http://$(hostname -I | awk '{print $1}') 开始使用"
        warn "请立即修改 .env 中的 ADMIN_PASSWORD 并重启服务"
    fi
}

main
