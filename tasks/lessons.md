# WaferCut MES — 踩坑记录

## Flask-Babel 4.x
- `@babel.localeselector` 装饰器已废弃
- 正确用法: `babel.init_app(app, locale_selector=get_locale)`
- 不要调用两次 `init_app()`

## SQLite PRAGMA
- 必须通过 SQLAlchemy event listener 设置，不是 app config
- `PRAGMA journal_mode=WAL` 是持久化的，但每次连接设置更安全
- `render_as_batch=True` 必须传给 Migrate.init_app()
- 用 `@event.listens_for(Engine, "connect")` 而非 `@event.listens_for(db.engine, "connect")`
  - 后者会过早访问 `db.engine`，在 factory pattern 中导致问题

## 模型导入与 db.create_all()
- `db.create_all()` 只创建已注册到 `db.metadata` 的模型表
- 必须在调用 `db.create_all()` 之前导入所有模型
- 正确做法: `from app import models as _models`（不能用 `import app.models`）
  - `import app.models` 会把外层函数参数 `app`（Flask 实例）覆盖为 `app` 模块
  - 这是 Python 命名空间的陷阱

## pip 代理问题
- 系统 pip.ini 配置了 `proxy = http://127.0.0.1:10808`（本地代理）
- 代理不可用时安装依赖失败
- 解决: `PIP_PROXY='' PIP_NO_PROXY='*' pip install ...` 环境变量覆盖

## Alembic autogenerate 丢失 ondelete（SQLite）
- `flask db migrate` 对 SQLite 后端**不会**在迁移脚本中生成 `ondelete`/`onupdate` 参数
- 根因: SQLAlchemy 的 SQLite 方言不反射 FK 的 ondelete/onupdate 选项
- 已知 Alembic issue: #79, #92, #317（PostgreSQL/MySQL 已修复，SQLite 仍有此问题）
- **解决**: 每次 `flask db migrate` 后，**必须手动检查**所有 `ForeignKeyConstraint`，补上 `ondelete` 参数
- 影响范围: 项目中 4 个 FK 均需手动补充 ondelete

## env.py 批量迁移 FK 冲突
- SQLite batch mode 迁移执行 DROP TABLE + RENAME TABLE
- 如果 `PRAGMA foreign_keys=ON`，DROP 时会触发 FK 约束冲突
- **解决**: 在 `run_migrations_online()` 中迁移前 `PRAGMA foreign_keys=OFF`，迁移后恢复 `ON`

## Open Redirect 防护
- `startswith('/')` 不够！`//evil.com` 是协议相对 URL，浏览器会跳转到 `https://evil.com`
- **正确做法**: `urlparse(next_page).netloc` 检查，拒绝有 netloc 的 URL
- Flask-Login 自身也用类似检查

## 登出必须用 POST
- GET 登出容易被 CSRF 攻击: `<img src="/auth/logout">` 可静默登出任何用户
- **解决**: `@auth_bp.route('/logout', methods=['POST'])` + CSRF hidden field
- OWASP 建议: 任何状态变更操作都应使用 POST

## Admin 自我保护
- 管理员编辑自己时，必须阻止禁用/降级操作
- 否则系统可能失去最后一个 admin，进入死锁
- 在 `user_edit` POST 处理中加 `user.id == current_user.id` 守卫

## 审计日志 target_id
- `db.session.add(user)` 后 `user.id` 是 None（未 commit）
- 需要 `db.session.flush()` 先刷入数据库获取 id，再调用 `log_action()`
- `flush()` 不提交事务，user 和 audit_log 仍在同一事务中

## curl -L -X POST 的陷阱
- `curl -L -X POST` 在 follow 302 重定向时**仍然用 POST**
- 这会导致对 GET-only 的目标路由返回 405
- 测试时不要用 `-L -X POST` 组合，分步手动跟随重定向
