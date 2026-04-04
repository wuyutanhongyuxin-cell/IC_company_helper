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
├── app/
│   ├── __init__.py            # create_app() factory
│   ├── extensions.py          # Two-step extension initialization
│   ├── models/                # SQLAlchemy ORM (5 tables)
│   │   ├── user.py            # User + password hashing + RBAC
│   │   ├── recipe.py          # Versioned recipe (single-table design)
│   │   ├── work_order.py      # Work order + status log
│   │   └── audit_log.py       # Audit trail + log_action() helper
│   ├── blueprints/            # 5 Flask Blueprints
│   │   ├── auth/              # Login / Logout / User CRUD
│   │   ├── main/              # Dashboard + Language switch
│   │   ├── recipe/            # Recipe CRUD + version history
│   │   ├── work_order/        # Work order CRUD + state machine
│   │   └── report/            # PDF generation
│   ├── utils/                 # Decorators, state machine, helpers
│   ├── templates/             # Jinja2 templates (Bootstrap 5)
│   ├── static/                # CSS + JS
│   └── translations/          # i18n (en, ja)
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

# Initialize database
flask init-db
```

### Running

```bash
# Development
flask run

# Production
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
- **Backup**: Simple file copy via cron job

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
| 2. Data Models | Planned | Full model implementation + migrations |
| 3. Auth Blueprint | Planned | Login/logout, user CRUD, password change |
| 4. Recipe Blueprint | Planned | CRUD + version history + filtering |
| 5. Work Order + State Machine | Planned | CRUD + status transitions + inspection |
| 6. Dashboard | Planned | Statistics cards + recent orders |
| 7. PDF Reports | Planned | WeasyPrint delivery reports (CJK) |
| 8. i18n | Planned | English + Japanese translations |
| 9. Deployment | Planned | Ubuntu + Gunicorn + Nginx + systemd |
| 10. Testing | Planned | Integration tests + polish |

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

```bash
# System dependencies
sudo apt install -y python3-venv fonts-noto-cjk libpango-1.0-0

# Application setup
sudo useradd -r -s /bin/false wafercut
sudo mkdir -p /opt/wafercut
# ... (deploy.sh automates this)

# Gunicorn (2 workers for SQLite compatibility)
gunicorn -w 2 --bind unix:/run/wafercut/wafercut.sock "wsgi:app"

# Nginx reverse proxy + systemd service
# See deploy.sh for full automation
```

---

## License

MIT

---

*Built with Flask, powered by Python.*
