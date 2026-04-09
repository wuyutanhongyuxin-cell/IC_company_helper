"""冒烟测试 — 应用创建、页面可访问性"""


class TestAppCreation:
    """应用初始化验证"""

    def test_app_exists(self, app):
        assert app is not None

    def test_app_is_testing(self, app):
        assert app.config['TESTING'] is True

    def test_csrf_disabled(self, app):
        assert app.config['WTF_CSRF_ENABLED'] is False

    def test_in_memory_db(self, app):
        assert ':memory:' in app.config['SQLALCHEMY_DATABASE_URI']


class TestPublicPages:
    """无需登录的页面"""

    def test_login_page(self, client):
        resp = client.get('/auth/login')
        assert resp.status_code == 200

    def test_set_language(self, client):
        resp = client.get('/set-language/en')
        assert resp.status_code == 302


class TestProtectedPages:
    """受保护页面 — 未登录重定向到登录页"""

    def test_dashboard(self, client):
        resp = client.get('/')
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_recipes(self, client):
        resp = client.get('/recipes/')
        assert resp.status_code == 302

    def test_orders(self, client):
        resp = client.get('/orders/')
        assert resp.status_code == 302

    def test_users(self, client):
        resp = client.get('/auth/users')
        assert resp.status_code == 302


class TestAuthenticatedAccess:
    """登录后页面正常访问"""

    def test_dashboard(self, admin_client):
        resp = admin_client.get('/')
        assert resp.status_code == 200

    def test_recipes_list(self, admin_client):
        resp = admin_client.get('/recipes/')
        assert resp.status_code == 200

    def test_orders_list(self, admin_client):
        resp = admin_client.get('/orders/')
        assert resp.status_code == 200

    def test_users_list(self, admin_client):
        resp = admin_client.get('/auth/users')
        assert resp.status_code == 200

    def test_recipe_create_page(self, admin_client):
        resp = admin_client.get('/recipes/create')
        assert resp.status_code == 200

    def test_order_create_page(self, admin_client, sample_recipe):
        resp = admin_client.get('/orders/create')
        assert resp.status_code == 200

    def test_change_password_page(self, admin_client):
        resp = admin_client.get('/auth/change-password')
        assert resp.status_code == 200
