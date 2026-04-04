"""
WaferCut MES 配置模块
提供 Development / Production / Testing 三套配置
"""
import os

# 项目根目录绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """基础配置 — 所有环境共享"""

    # Flask 核心（开发环境允许默认值，生产环境在 create_app 中校验）
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

    # SQLAlchemy — SQLite 数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'instance', 'wafercut.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Babel 多语言
    BABEL_DEFAULT_LOCALE = 'zh'
    BABEL_SUPPORTED_LOCALES = ['zh', 'en', 'ja']

    # 分页
    ITEMS_PER_PAGE = 20

    # 默认管理员账号（首次初始化时使用）
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')


class DevelopmentConfig(Config):
    """开发环境"""
    DEBUG = True


class ProductionConfig(Config):
    """
    生产环境 — SECRET_KEY 校验在 create_app() 的 _validate_config() 中执行
    非 DEBUG 且非 TESTING 时，如果 SECRET_KEY 是默认值则启动失败
    """
    DEBUG = False


class TestingConfig(Config):
    """测试环境 — 使用内存数据库"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
