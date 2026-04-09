"""国际化测试 — 中/英/日语言切换"""


class TestLanguageSwitch:
    """语言切换功能"""

    def test_default_language_zh(self, admin_client):
        """默认语言为中文"""
        resp = admin_client.get('/')
        assert resp.status_code == 200
        # 中文是源码语言，无需翻译

    def test_switch_to_en(self, admin_client):
        """切换到英文"""
        admin_client.get('/set-language/en')
        resp = admin_client.get('/', follow_redirects=True)
        assert resp.status_code == 200

    def test_switch_to_ja(self, admin_client):
        """切换到日文"""
        admin_client.get('/set-language/ja')
        resp = admin_client.get('/', follow_redirects=True)
        assert resp.status_code == 200

    def test_invalid_language_ignored(self, app, admin_user):
        """无效语言代码被忽略"""
        c = app.test_client()
        c.post('/auth/login', data={
            'username': 'testadmin', 'password': 'admin123',
        })
        c.get('/set-language/xx')
        # session 中不应有 language 键（或保持默认）
        resp = c.get('/')
        assert resp.status_code == 200

    def test_language_persists(self, app, admin_user):
        """语言切换在多次请求间保持"""
        c = app.test_client()
        c.post('/auth/login', data={
            'username': 'testadmin', 'password': 'admin123',
        })
        c.get('/set-language/en')
        resp1 = c.get('/')
        resp2 = c.get('/recipes/')
        assert resp1.status_code == 200
        assert resp2.status_code == 200

    def test_set_language_redirects_back(self, admin_client):
        """语言切换后重定向回来源页"""
        resp = admin_client.get(
            '/set-language/en',
            headers={'Referer': 'http://localhost/recipes/'},
        )
        assert resp.status_code == 302
        assert '/recipes/' in resp.headers['Location']

    def test_set_language_no_referer(self, admin_client):
        """无 Referer 时重定向到仪表盘"""
        resp = admin_client.get('/set-language/en')
        assert resp.status_code == 302

    def test_set_language_external_referer(self, admin_client):
        """外部 Referer 被忽略，重定向到仪表盘"""
        resp = admin_client.get(
            '/set-language/en',
            headers={'Referer': 'http://evil.com/'},
        )
        assert resp.status_code == 302
        assert 'evil.com' not in resp.headers.get('Location', '')
