"""
Flask 扩展实例化模块（两步初始化模式）
在此创建扩展对象，在 create_app() 中调用 init_app() 绑定
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_babel import Babel, lazy_gettext as _l
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# 数据库 ORM
db = SQLAlchemy()

# 用户认证
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # 未登录时跳转到登录页
login_manager.login_message = _l('请先登录')  # 用 lazy_gettext 支持多语言
login_manager.login_message_category = 'warning'

# 国际化
babel = Babel()

# 数据库迁移
migrate = Migrate()

# CSRF 保护
csrf = CSRFProtect()
