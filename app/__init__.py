"""
WaferCut MES — Flask Application Factory
使用 create_app() 工厂函数初始化应用
"""
import os
import click
from flask import Flask, session

from app.extensions import db, login_manager, babel, migrate, csrf


def create_app(config_class=None):
    """
    创建并配置 Flask 应用实例

    Args:
        config_class: 配置类路径字符串，默认 DevelopmentConfig
    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)

    # 加载配置
    if config_class is None:
        config_class = os.environ.get(
            'FLASK_CONFIG', 'config.DevelopmentConfig'
        )
    app.config.from_object(config_class)

    # 生产环境安全检查: SECRET_KEY 不能使用默认值
    _validate_config(app)

    # 初始化扩展（注意: babel 在此一并初始化，传入 locale_selector）
    _register_extensions(app)

    # 配置 SQLite PRAGMA（WAL + 外键 + busy_timeout）
    _configure_sqlite()

    # 导入所有模型（必须在蓝图注册之前，确保路由中可引用模型）
    from app import models  # noqa: F401

    # 注册蓝图（在模型导入之后，确保路由可安全引用模型）
    _register_blueprints(app)

    # 注册 CLI 命令
    _register_cli(app)

    # 注册 user_loader
    _configure_login(app)

    return app


def _validate_config(app):
    """
    校验关键配置项
    生产环境（非 DEBUG 且非 TESTING）必须设置安全的 SECRET_KEY
    """
    is_production = not app.config.get('DEBUG') and not app.config.get('TESTING')
    secret = app.config.get('SECRET_KEY', '')

    if is_production and (not secret or secret == 'dev-secret-change-in-production'):
        raise RuntimeError(
            '生产环境必须设置 SECRET_KEY 环境变量！'
            '请运行: export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")'
        )


def _register_extensions(app):
    """
    注册所有 Flask 扩展
    Babel 在此初始化（Flask-Babel 4.x 要求 locale_selector 在 init_app 时传入）
    """
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    csrf.init_app(app)

    # Flask-Babel 4.x: locale_selector 必须在 init_app 时传入
    # 必须在 _register_blueprints 之前完成，否则表单中 lazy_gettext() 会出错
    def get_locale():
        return session.get('language', app.config['BABEL_DEFAULT_LOCALE'])

    babel.init_app(app, locale_selector=get_locale)


# 全局标志: Engine 级事件监听器只需注册一次（进程级别）
# 即使多次调用 create_app()（如测试场景），PRAGMA 也只注册一次
# 因为监听器挂在 SQLAlchemy Engine 基类上，对所有引擎生效
_sqlite_pragma_registered = False


def _configure_sqlite():
    """
    启用 SQLite WAL 模式 + 外键约束 + 忙等待超时
    使用 Engine 级别事件监听（进程全局，只注册一次）
    """
    global _sqlite_pragma_registered
    if _sqlite_pragma_registered:
        return
    _sqlite_pragma_registered = True

    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    import sqlite3

    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        # 仅对 SQLite 连接执行 PRAGMA
        if isinstance(dbapi_conn, sqlite3.Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()


def _register_blueprints(app):
    """延迟导入并注册所有蓝图（在模型导入之后调用）"""
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.recipe import recipe_bp
    from app.blueprints.work_order import work_order_bp
    from app.blueprints.report import report_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(recipe_bp)
    app.register_blueprint(work_order_bp)
    app.register_blueprint(report_bp)


def _configure_login(app):
    """配置 Flask-Login 的 user_loader 回调"""
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return db.session.get(User, int(user_id))


def _register_cli(app):
    """注册自定义 Flask CLI 命令"""

    @app.cli.command('init-db')
    @click.option('--drop', is_flag=True, help='先删除所有表再创建')
    def init_db(drop):
        """初始化数据库并创建默认管理员"""
        if drop:
            click.confirm('确认删除所有数据？', abort=True)
            db.drop_all()
            click.echo('已删除所有表。')

        db.create_all()
        click.echo('数据库表已创建。')

        # 创建默认管理员（如果不存在）
        _seed_admin(app)
        click.echo('初始化完成。')


def _seed_admin(app):
    """创建默认管理员账号（如果不存在）"""
    from app.models.user import User

    admin_username = app.config.get('ADMIN_USERNAME', 'admin')
    admin_password = app.config.get('ADMIN_PASSWORD', 'changeme')

    # 使用 SQLAlchemy 2.x 推荐的查询方式
    existing = db.session.execute(
        db.select(User).filter_by(username=admin_username)
    ).scalar_one_or_none()

    if existing is None:
        # 默认密码警告
        if admin_password == 'changeme':
            click.echo('⚠ 警告: 使用默认密码，生产环境请设置 ADMIN_PASSWORD 环境变量！')

        admin = User(
            username=admin_username,
            display_name='系统管理员',
            role='admin',
            is_active=True,
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f'已创建管理员: {admin_username}')
    else:
        click.echo(f'管理员 {admin_username} 已存在，跳过。')
