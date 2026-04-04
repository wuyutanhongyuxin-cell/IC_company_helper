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
