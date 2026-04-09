<p align="center">
  <strong><a href="#简体中文">简体中文</a></strong> | <strong><a href="#english">English</a></strong>
</p>

---

<a name="简体中文"></a>

# WaferCut MES

> 晶圆切割代工厂生产管理系统

面向晶圆切割代工厂的 MES（制造执行系统），管理切割参数配方、工单生命周期、质量检验与交付报告生成。

---

## 功能模块

| 模块 | 说明 |
|------|------|
| **配方管理** | 版本化切割参数库，支持材料/尺寸筛选 |
| **工单流转** | 6 阶段线性工作流 + 异常挂起处理 |
| **质量检验** | 良率统计、崩边测量、合格/不合格判定 |
| **PDF 报告** | 自动生成 A4 交付报告，支持中日韩字体 |
| **角色权限** | 管理员与操作员角色，细粒度权限控制 |
| **多语言** | 中文（默认）、英文、日文 — Flask-Babel 全量国际化 |
| **平板适配** | Bootstrap 5 响应式布局，针对 iPad（768-1024px）优化 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+ / Flask 3.0 |
| 数据库 | SQLite（WAL 模式）+ Flask-Migrate |
| 认证 | Flask-Login + werkzeug 密码哈希 |
| 表单 | Flask-WTF (WTForms) |
| 国际化 | Flask-Babel 4.x（中/英/日） |
| PDF | WeasyPrint 62.3 + Noto Sans CJK |
| 前端 | Bootstrap 5 (CDN) |
| 部署 | Ubuntu 24.04 / Gunicorn / Nginx / systemd |

---

## 项目架构

```
Flask Application Factory 模式
├── config.py                  # 开发/生产/测试 配置
├── wsgi.py                    # WSGI 入口
├── deploy.sh                  # Ubuntu 一键部署（首次 / --update 更新）
├── backup.sh                  # SQLite WAL 安全备份 + 7天轮转
├── .env.example               # 环境变量模板
├── app/
│   ├── __init__.py            # create_app() 工厂函数
│   ├── extensions.py          # 两步式扩展初始化
│   ├── models/                # SQLAlchemy ORM（5 张表）
│   │   ├── user.py            # 用户 + 密码哈希 + 角色控制
│   │   ├── recipe.py          # 版本化配方（单表设计）
│   │   ├── work_order.py      # 工单 + 状态日志
│   │   └── audit_log.py       # 审计日志 + log_action() 辅助函数
│   ├── forms/                 # WTForms 表单验证
│   │   ├── auth.py            # 登录 / 用户管理 / 改密码
│   │   ├── recipe.py          # 配方参数 + DISCO 参数
│   │   └── work_order.py      # 工单 / 检验 / 状态表单
│   ├── blueprints/            # 5 个 Flask 蓝图
│   │   ├── auth/              # 登录 / 登出 / 用户管理
│   │   ├── main/              # 仪表盘 + 语言切换
│   │   ├── recipe/            # 配方 CRUD + 版本历史
│   │   ├── work_order/        # 工单 CRUD + 状态流转 + 检验
│   │   └── report/            # PDF 交付报告
│   ├── utils/                 # 工具函数
│   │   ├── decorators.py      # @role_required 权限装饰器
│   │   ├── state_machine.py   # 状态枚举 + 转换验证
│   │   └── helpers.py         # 工单号生成 + API 响应
│   ├── templates/             # Jinja2 模板（Bootstrap 5）
│   ├── static/                # CSS + JS（平板触控优化）
│   └── translations/          # 国际化翻译（en, ja）
├── tests/                     # 集成测试（141 用例）
│   ├── conftest.py            # 共享 fixtures（app, db, users）
│   ├── helpers.py             # 测试辅助函数
│   ├── test_smoke.py          # 冒烟测试
│   ├── test_auth.py           # 认证测试
│   ├── test_recipe.py         # 配方测试
│   ├── test_work_order.py     # 工单测试
│   ├── test_exception.py      # 异常挂起测试
│   ├── test_report.py         # 报告测试
│   ├── test_permissions.py    # 权限测试
│   ├── test_i18n.py           # 国际化测试
│   └── test_audit.py          # 审计日志测试
└── migrations/                # Alembic 迁移脚本
```

---

## 数据库设计

### 5 张数据表

| 表名 | 用途 |
|------|------|
| `users` | 认证、角色（admin/operator）、软禁用 |
| `recipes` | 切割参数 + 版本控制（group_id + version） |
| `work_orders` | 生产工单，绑定具体配方版本 |
| `work_order_status_logs` | 不可变的状态变更历史 |
| `audit_logs` | 完整审计日志（JSON 变更详情） |

### 配方版本化策略

单表设计，`recipe_group_id` 分组 + `version` 自增：

```
配方组 #1
├── v1 (is_active=False) ─── 工单 WO-20240101-0001（不可变绑定）
├── v2 (is_active=False) ─── 工单 WO-20240115-0003
└── v3 (is_active=True)  ─── 当前版本，供新工单使用
```

- 工单通过 `recipes.id`（主键）绑定，**绝不**通过 `recipe_group_id`
- 编辑时创建新版本行，旧版本永不修改
- `UNIQUE(recipe_group_id, version)` 约束防止竞态条件

### 工单状态机

```
来料 → 贴膜 → 切割 → 清洗 → 检验 → 完成
 │      │      │      │      │
 └──────┴──────┴──────┴──────┘
                ↓
           异常挂起
                ↓
          恢复到下一状态
```

- 6 个线性阶段 + 1 个异常状态
- 异常挂起时保存 `previous_status`，用于恢复
- 纯 Python dict 实现（零外部依赖）
- 三层校验：模型层 → 路由层 → 模板层

---

## 快速开始

### 环境要求

- Python 3.10+
- pip

### 安装

```bash
# 克隆仓库
git clone https://github.com/wuyutanhongyuxin-cell/IC_company_helper.git
cd IC_company_helper

# 创建虚拟环境
python -m venv venv
source venv/bin/activate          # Linux/Mac
# 或: venv\Scripts\activate       # Windows

# 安装依赖
pip install -r requirements.txt

# 初始化数据库（迁移 + 创建默认管理员）
flask db upgrade
flask init-db
```

### 运行

```bash
# 开发模式
flask run

# 生产模式（推荐使用 deploy.sh 一键部署）
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export FLASK_CONFIG=config.ProductionConfig
gunicorn -w 2 "wsgi:app"
```

### 默认管理员账号

| 字段 | 值 |
|------|------|
| 用户名 | `admin` |
| 密码 | `changeme` |

> 首次登录后请立即修改密码。

---

## 核心设计决策

### 为什么选择 SQLite？

- **目标环境**：工厂车间局域网单服务器部署
- **WAL 模式**：支持并发读 + 单写（2 个 Gunicorn worker 足够）
- **PRAGMA 配置**：`journal_mode=WAL`、`foreign_keys=ON`、`busy_timeout=5000`
- **备份**：`sqlite3 .backup` API 安全备份（WAL 模式兼容）+ gzip 压缩 + 7天轮转

### 为什么用单表配方版本化？

- ~15 个参数列 — 数据冗余成本可忽略
- 无需 JOIN — 查询模式最简
- 工单绑定不可变的 `recipes.id`（主键），而非 `recipe_group_id`
- SQLite 写锁天然提供版本号生成的序列化保证

### 为什么用 Flask-Babel 4.x？

- `locale_selector` 在 `init_app()` 时传入（4.x 移除了装饰器 API）
- 中文作为源语言 — 仅需翻译 en/ja
- 表单标签用 `lazy_gettext()`（渲染时求值，非定义时）
- 语言选择存储在 `session['language']`

### 安全措施

- **密码哈希**：werkzeug `generate_password_hash` / `check_password_hash`
- **CSRF 防护**：Flask-WTF CSRFProtect 保护所有表单
- **生产环境 SECRET_KEY**：非 DEBUG 模式下检测到默认密钥将阻止启动
- **角色权限**：`@role_required('admin')` 装饰器控制敏感操作
- **审计日志**：所有增删改操作记录用户 ID 和 JSON 变更详情

---

## 项目路线图

| 阶段 | 状态 | 说明 |
|------|------|------|
| 1. 骨架 + 配置 | 已完成 | 应用工厂、扩展、模型、配置 |
| 2. 数据模型 | 已完成 | 5 张表 + Flask-Migrate 迁移 |
| 3. 认证蓝图 | 已完成 | 登录/登出、用户管理、密码修改 |
| 4. 配方蓝图 | 已完成 | CRUD + 版本历史 + 材料/尺寸筛选 |
| 5. 工单 + 状态机 | 已完成 | CRUD + 6 阶段状态流转 + 异常挂起 |
| 6. 仪表盘 | 已完成 | 统计卡片 + 最近工单 |
| 7. PDF 报告 | 已完成 | WeasyPrint A4 交付报告（CJK） |
| 8. 国际化 | 已完成 | 中/英/日三语全量翻译 |
| 9. 部署 | 已完成 | deploy.sh 一键部署 + backup.sh 自动备份 |
| 10. 测试 | 已完成 | 141 个 pytest 集成测试，覆盖全部功能模块 |

---

## 开发指南

### 文件行数限制

| 类型 | 最大行数 |
|------|----------|
| 源代码文件 | 200 |
| 模块（目录） | 2000 |
| 测试文件 | 300 |
| 配置文件 | 100 |

### 编码规范

- 注释使用中文（面向国内团队）
- 所有用户可见字符串用 `_()` 或 `lazy_gettext()` 包裹
- 单函数不超过 30 行
- 所有外部调用（数据库、API、文件 IO）必须 `try-except`
- 禁止硬编码密钥 — 一律通过环境变量

### Flask-Migrate 工作流

```bash
flask db migrate -m "描述"   # 生成迁移脚本
flask db upgrade             # 执行迁移
flask db downgrade           # 回滚
```

> 执行前务必检查自动生成的迁移脚本。
> SQLite 需要 `render_as_batch=True`（已自动配置）。

---

## 部署（Ubuntu 24.04）

### 一键部署

```bash
# 首次部署（自动完成：系统依赖 → 用户创建 → venv → .env → 数据库 → systemd → Nginx → cron 备份）
sudo bash deploy.sh

# 代码更新（仅同步代码 + 迁移 + 重启服务）
sudo bash deploy.sh --update
```

### deploy.sh 自动配置

| 组件 | 配置 |
|------|------|
| Gunicorn | 2 workers + Unix socket + `--preload` |
| Nginx | 反向代理 + 静态文件缓存 30天 + 安全头 |
| systemd | `Restart=on-failure` + 安全加固（ProtectSystem/PrivateTmp/NoNewPrivileges） |
| 备份 | 每日 02:00 自动执行 `backup.sh`，SQLite `.backup` API + gzip + 保留 7天 |
| 安全 | SECRET_KEY 自动生成、.env 权限 600、dotfiles 禁止 HTTP 访问 |

### 环境变量

复制 `.env.example` 为 `.env` 并修改（deploy.sh 首次运行时自动完成）：

```bash
FLASK_APP=wsgi.py
FLASK_DEBUG=0
FLASK_CONFIG=config.ProductionConfig
SECRET_KEY=<自动生成>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme    # 部署后立即修改！
```

---

## 许可证

MIT

---

*基于 Flask 构建，由 Python 驱动。*

---

<p align="center"><a href="#简体中文">回到顶部</a> | <a href="#english">Switch to English</a></p>

---

<a name="english"></a>

# WaferCut MES

> Manufacturing Execution System for Wafer Dicing Operations

A production-grade MES (Manufacturing Execution System) designed for wafer dicing factories. Manages cutting recipes, work order lifecycle, quality inspection, and delivery report generation.

---

## Features

| Module | Description |
|--------|-------------|
| **Recipe Management** | Versioned cutting parameter library with material/size filtering |
| **Work Order Lifecycle** | 6-stage linear workflow with exception handling |
| **Quality Inspection** | Yield rate, chipping measurement, pass/fail determination |
| **PDF Reports** | Auto-generated A4 delivery reports with CJK font support |
| **Role-Based Access** | Admin and Operator roles with granular permissions |
| **Multi-Language** | Chinese (default), English, Japanese — full i18n via Flask-Babel |
| **Tablet-Ready** | Bootstrap 5 responsive layout optimized for iPad (768-1024px) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+ / Flask 3.0 |
| Database | SQLite (WAL mode) + Flask-Migrate |
| Auth | Flask-Login + werkzeug password hashing |
| Forms | Flask-WTF (WTForms) |
| i18n | Flask-Babel 4.x (zh/en/ja) |
| PDF | WeasyPrint 62.3 + Noto Sans CJK |
| Frontend | Bootstrap 5 (CDN) |
| Deployment | Ubuntu 24.04 / Gunicorn / Nginx / systemd |

---

## Architecture

```
Flask Application Factory Pattern
├── config.py                  # Dev/Prod/Test configurations
├── wsgi.py                    # WSGI entry point
├── deploy.sh                  # Ubuntu one-click deploy (initial / --update)
├── backup.sh                  # SQLite WAL-safe backup + 7-day rotation
├── .env.example               # Environment variable template
├── app/
│   ├── __init__.py            # create_app() factory
│   ├── extensions.py          # Two-step extension initialization
│   ├── models/                # SQLAlchemy ORM (5 tables)
│   │   ├── user.py            # User + password hashing + RBAC
│   │   ├── recipe.py          # Versioned recipe (single-table design)
│   │   ├── work_order.py      # Work order + status log
│   │   └── audit_log.py       # Audit trail + log_action() helper
│   ├── forms/                 # WTForms validation
│   │   ├── auth.py            # Login / user management / password change
│   │   ├── recipe.py          # Recipe params + DISCO params
│   │   └── work_order.py      # Work order / inspection / status forms
│   ├── blueprints/            # 5 Flask Blueprints
│   │   ├── auth/              # Login / Logout / User CRUD
│   │   ├── main/              # Dashboard + Language switch
│   │   ├── recipe/            # Recipe CRUD + version history
│   │   ├── work_order/        # Work order CRUD + status transitions + inspection
│   │   └── report/            # PDF delivery report
│   ├── utils/                 # Utility functions
│   │   ├── decorators.py      # @role_required permission decorator
│   │   ├── state_machine.py   # Status enum + transition validation
│   │   └── helpers.py         # Work order number generation + API response
│   ├── templates/             # Jinja2 templates (Bootstrap 5)
│   ├── static/                # CSS + JS (tablet touch-optimized)
│   └── translations/          # i18n (en, ja)
├── tests/                     # Integration tests (141 cases)
│   ├── conftest.py            # Shared fixtures (app, db, users)
│   ├── helpers.py             # Test utility functions
│   ├── test_smoke.py          # Smoke tests
│   ├── test_auth.py           # Authentication tests
│   ├── test_recipe.py         # Recipe tests
│   ├── test_work_order.py     # Work order tests
│   ├── test_exception.py      # Exception hold tests
│   ├── test_report.py         # Report tests
│   ├── test_permissions.py    # Permission tests
│   ├── test_i18n.py           # i18n tests
│   └── test_audit.py          # Audit log tests
└── migrations/                # Alembic migration scripts
```

---

## Database Design

### 5 Tables

| Table | Purpose |
|-------|---------|
| `users` | Authentication, roles (admin/operator), soft-disable |
| `recipes` | Cutting parameters with version control (group_id + version) |
| `work_orders` | Production orders bound to specific recipe versions |
| `work_order_status_logs` | Immutable state transition history |
| `audit_logs` | Full audit trail (JSON change details) |

### Recipe Versioning Strategy

Single-table design with `recipe_group_id` grouping + `version` auto-increment:

```
Recipe Group #1
├── v1 (is_active=False) ─── Work Order WO-20240101-0001 (immutable binding)
├── v2 (is_active=False) ─── Work Order WO-20240115-0003
└── v3 (is_active=True)  ─── Current version for new orders
```

- Work orders bind to `recipes.id` (PK), never `recipe_group_id`
- Editing creates a new version row; old versions are never modified
- `UNIQUE(recipe_group_id, version)` constraint prevents race conditions

### Work Order State Machine

```
incoming → filming → cutting → cleaning → inspection → completed
    │          │         │          │           │
    └──────────┴─────────┴──────────┴───────────┘
                         ↓
                  exception_hold
                         ↓
               resume to next_status
```

- 6 linear stages + 1 exception state
- Exception hold saves `previous_status` for recovery
- Pure Python dict implementation (zero external dependencies)
- Triple-layer validation: Model → Route → Template

---

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone
git clone https://github.com/wuyutanhongyuxin-cell/IC_company_helper.git
cd IC_company_helper

# Virtual environment
python -m venv venv
source venv/bin/activate          # Linux/Mac
# or: venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database (migrate + create default admin)
flask db upgrade
flask init-db
```

### Running

```bash
# Development
flask run

# Production (recommended: use deploy.sh for one-click deploy)
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export FLASK_CONFIG=config.ProductionConfig
gunicorn -w 2 "wsgi:app"
```

### Default Admin Account

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `changeme` |

> Change the password immediately after first login.

---

## Key Design Decisions

### Why SQLite?

- **Target environment**: Single-server LAN deployment (factory floor)
- **WAL mode**: Enables concurrent reads + single writer (sufficient for 2 Gunicorn workers)
- **PRAGMA configuration**: `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`
- **Backup**: `sqlite3 .backup` API (WAL-safe) + gzip compression + 7-day rotation

### Why Single-Table Recipe Versioning?

- ~15 parameter columns — data duplication cost is negligible
- No JOINs needed — simplest query pattern
- Work orders bind to immutable `recipes.id` (PK), not `recipe_group_id`
- SQLite write lock provides natural serialization for version number generation

### Why Flask-Babel 4.x?

- `locale_selector` passed at `init_app()` time (decorator API removed in 4.x)
- Chinese as source language — only en/ja need translation files
- `lazy_gettext()` for form labels (evaluated at render time, not definition time)
- Session-based language selection (`session['language']`)

### Security Measures

- **Password hashing**: werkzeug `generate_password_hash` / `check_password_hash`
- **CSRF protection**: Flask-WTF CSRFProtect on all forms
- **Production SECRET_KEY**: Startup fails if default key detected in non-DEBUG mode
- **Role-based access**: `@role_required('admin')` decorator for sensitive operations
- **Audit logging**: All CRUD operations recorded with user ID and JSON change details

---

## Project Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Skeleton + Config | Done | Application factory, extensions, models, config |
| 2. Data Models | Done | 5 tables + Flask-Migrate migrations |
| 3. Auth Blueprint | Done | Login/logout, user CRUD, password change |
| 4. Recipe Blueprint | Done | CRUD + version history + material/size filtering |
| 5. Work Order + State Machine | Done | CRUD + 6-stage status transitions + exception hold |
| 6. Dashboard | Done | Statistics cards + recent orders |
| 7. PDF Reports | Done | WeasyPrint A4 delivery reports (CJK) |
| 8. i18n | Done | Chinese/English/Japanese full translations |
| 9. Deployment | Done | deploy.sh one-click deploy + backup.sh auto backup |
| 10. Testing | Done | 141 pytest integration tests covering all modules |

---

## Development Guide

### File Size Limits

| Type | Max Lines |
|------|-----------|
| Source file | 200 |
| Module (directory) | 2000 |
| Test file | 300 |
| Config file | 100 |

### Code Conventions

- Comments in Chinese (target team audience)
- All user-facing strings wrapped with `_()` or `lazy_gettext()`
- Functions under 30 lines
- `try-except` on all external calls (DB, API, file I/O)
- No hardcoded secrets — all via environment variables

### Flask-Migrate Workflow

```bash
flask db migrate -m "description"   # Generate migration
flask db upgrade                     # Apply migration
flask db downgrade                   # Rollback
```

> Always review generated migration scripts before applying.
> SQLite requires `render_as_batch=True` (configured automatically).

---

## Deployment (Ubuntu 24.04)

### One-Click Deploy

```bash
# First-time deploy (auto: system deps → user → venv → .env → database → systemd → Nginx → cron backup)
sudo bash deploy.sh

# Code update (sync code + migrate + restart only)
sudo bash deploy.sh --update
```

### What deploy.sh Configures

| Component | Configuration |
|-----------|---------------|
| Gunicorn | 2 workers + Unix socket + `--preload` |
| Nginx | Reverse proxy + 30-day static cache + security headers |
| systemd | `Restart=on-failure` + hardening (ProtectSystem/PrivateTmp/NoNewPrivileges) |
| Backup | Daily 02:00 via `backup.sh`, SQLite `.backup` API + gzip + 7-day retention |
| Security | Auto-generated SECRET_KEY, .env chmod 600, dotfiles blocked via HTTP |

### Environment Variables

Copy `.env.example` to `.env` and edit (deploy.sh does this automatically on first run):

```bash
FLASK_APP=wsgi.py
FLASK_DEBUG=0
FLASK_CONFIG=config.ProductionConfig
SECRET_KEY=<auto-generated>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme    # Change immediately after deploy!
```

---

## License

MIT

---

*Built with Flask, powered by Python.*

<p align="center"><a href="#简体中文">简体中文</a> | <a href="#english">Back to top</a></p>
