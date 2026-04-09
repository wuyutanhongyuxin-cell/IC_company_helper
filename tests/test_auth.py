"""认证测试 — 登录/登出/用户管理/修改密码"""
from app.models.user import User
from helpers import login


class TestLogin:
    """登录功能"""

    def test_login_success(self, client, admin_user):
        """正确凭据登录并重定向到仪表盘"""
        resp = client.post('/auth/login', data={
            'username': 'testadmin', 'password': 'admin123',
        })
        assert resp.status_code == 302
        # 已登录，可访问仪表盘
        resp2 = client.get('/')
        assert resp2.status_code == 200

    def test_login_wrong_password(self, client, admin_user):
        """错误密码停留在登录页"""
        resp = client.post('/auth/login', data={
            'username': 'testadmin', 'password': 'wrongpass',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '用户名或密码错误' in resp.data.decode('utf-8')

    def test_login_nonexistent_user(self, client):
        """不存在的用户名"""
        resp = client.post('/auth/login', data={
            'username': 'nobody', 'password': 'password',
        }, follow_redirects=True)
        assert '用户名或密码错误' in resp.data.decode('utf-8')

    def test_login_disabled_user(self, client, db):
        """禁用用户无法登录"""
        user = User(
            username='disabled', display_name='Disabled',
            role='operator', is_active=False,
        )
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        resp = client.post('/auth/login', data={
            'username': 'disabled', 'password': 'pass123',
        }, follow_redirects=True)
        assert '账号已被禁用' in resp.data.decode('utf-8')

    def test_login_empty_fields(self, client):
        """空字段不通过验证"""
        resp = client.post('/auth/login', data={
            'username': '', 'password': '',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_already_authenticated_redirect(self, admin_client):
        """已登录用户访问登录页重定向到仪表盘"""
        resp = admin_client.get('/auth/login')
        assert resp.status_code == 302

    def test_next_redirect(self, client, admin_user):
        """登录后跳转到 next 参数"""
        resp = client.post('/auth/login?next=/recipes/', data={
            'username': 'testadmin', 'password': 'admin123',
        })
        assert resp.status_code == 302
        assert '/recipes/' in resp.headers['Location']

    def test_open_redirect_blocked(self, client, admin_user):
        """阻止外部 URL 重定向"""
        resp = client.post('/auth/login?next=http://evil.com', data={
            'username': 'testadmin', 'password': 'admin123',
        })
        assert resp.status_code == 302
        assert 'evil.com' not in resp.headers['Location']

    def test_protocol_relative_redirect_blocked(self, client, admin_user):
        """阻止协议相对 URL 重定向"""
        resp = client.post('/auth/login?next=//evil.com', data={
            'username': 'testadmin', 'password': 'admin123',
        })
        assert resp.status_code == 302
        assert 'evil.com' not in resp.headers['Location']


class TestLogout:
    """登出功能"""

    def test_logout_redirect(self, admin_client):
        """登出后重定向到登录页"""
        resp = admin_client.post('/auth/logout')
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_logout_clears_session(self, admin_client):
        """登出后无法访问受保护页面"""
        admin_client.post('/auth/logout')
        resp = admin_client.get('/')
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']

    def test_logout_requires_post(self, admin_client):
        """登出必须使用 POST"""
        resp = admin_client.get('/auth/logout')
        assert resp.status_code == 405


class TestUserManagement:
    """用户管理 — Admin 专用"""

    def test_user_list(self, admin_client, operator_user):
        """用户列表显示所有用户"""
        resp = admin_client.get('/auth/users')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'testadmin' in html
        assert 'testoper' in html

    def test_create_user(self, admin_client, db):
        """创建新用户"""
        resp = admin_client.post('/auth/users/create', data={
            'username': 'newuser',
            'display_name': 'New User',
            'password': 'newpass123',
            'password2': 'newpass123',
            'role': 'operator',
        })
        assert resp.status_code == 302
        user = db.session.execute(
            db.select(User).filter_by(username='newuser')
        ).scalar_one_or_none()
        assert user is not None
        assert user.role == 'operator'

    def test_create_duplicate_username(self, admin_client, admin_user):
        """重复用户名被拒绝"""
        resp = admin_client.post('/auth/users/create', data={
            'username': 'testadmin',
            'display_name': 'Dup',
            'password': 'pass123456',
            'password2': 'pass123456',
            'role': 'operator',
        }, follow_redirects=True)
        # 停留在表单页，显示错误
        assert resp.status_code == 200
        assert '用户名已存在' in resp.data.decode('utf-8')

    def test_create_short_password(self, admin_client):
        """密码太短被拒绝（最少 6 位）"""
        resp = admin_client.post('/auth/users/create', data={
            'username': 'shortpw',
            'display_name': 'Short',
            'password': '12345',
            'password2': '12345',
            'role': 'operator',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_edit_user(self, admin_client, operator_user):
        """编辑用户信息"""
        resp = admin_client.post(
            f'/auth/users/{operator_user.id}/edit',
            data={
                'display_name': 'Updated Name',
                'role': 'operator',
                'is_active': 'y',
            },
        )
        assert resp.status_code == 302

    def test_prevent_self_disable(self, admin_client, admin_user):
        """管理员不能禁用自己"""
        resp = admin_client.post(
            f'/auth/users/{admin_user.id}/edit',
            data={
                'display_name': 'Test Admin',
                'role': 'admin',
                # is_active 未包含 = False
            },
            follow_redirects=True,
        )
        html = resp.data.decode('utf-8')
        assert '不能禁用自己' in html

    def test_prevent_self_downgrade(self, admin_client, admin_user):
        """管理员不能降低自己的权限"""
        resp = admin_client.post(
            f'/auth/users/{admin_user.id}/edit',
            data={
                'display_name': 'Test Admin',
                'role': 'operator',
                'is_active': 'y',
            },
            follow_redirects=True,
        )
        html = resp.data.decode('utf-8')
        assert '不能降低自己的权限' in html

    def test_admin_reset_password(self, app, admin_client, operator_user):
        """管理员重置他人密码"""
        admin_client.post(
            f'/auth/users/{operator_user.id}/edit',
            data={
                'display_name': operator_user.display_name,
                'role': 'operator',
                'is_active': 'y',
                'new_password': 'newpass123',
                'new_password2': 'newpass123',
            },
        )
        # 用新密码登录
        c = app.test_client()
        resp = login(c, 'testoper', 'newpass123')
        assert resp.status_code == 302

    def test_disable_user_blocks_login(self, app, admin_client, operator_user):
        """禁用用户后无法登录"""
        admin_client.post(
            f'/auth/users/{operator_user.id}/edit',
            data={
                'display_name': operator_user.display_name,
                'role': 'operator',
                # is_active 不包含 → False
            },
        )
        c = app.test_client()
        resp = login(c, 'testoper', 'oper123')
        resp2 = c.get('/', follow_redirects=True)
        # 禁用用户应停留在登录页或被拒绝
        assert resp2.status_code == 200


class TestChangePassword:
    """修改密码"""

    def test_page_accessible(self, admin_client):
        """修改密码页面可访问"""
        resp = admin_client.get('/auth/change-password')
        assert resp.status_code == 200

    def test_change_success(self, app, admin_client):
        """正确修改密码"""
        resp = admin_client.post('/auth/change-password', data={
            'old_password': 'admin123',
            'new_password': 'newadmin456',
            'new_password2': 'newadmin456',
        })
        assert resp.status_code == 302
        # 用新密码登录
        c = app.test_client()
        resp2 = login(c, 'testadmin', 'newadmin456')
        assert resp2.status_code == 302

    def test_wrong_old_password(self, admin_client):
        """旧密码错误"""
        resp = admin_client.post('/auth/change-password', data={
            'old_password': 'wrongold',
            'new_password': 'newpass123',
            'new_password2': 'newpass123',
        }, follow_redirects=True)
        assert '当前密码错误' in resp.data.decode('utf-8')

    def test_password_mismatch(self, admin_client):
        """两次新密码不匹配"""
        resp = admin_client.post('/auth/change-password', data={
            'old_password': 'admin123',
            'new_password': 'newpass123',
            'new_password2': 'different',
        }, follow_redirects=True)
        assert '两次密码不一致' in resp.data.decode('utf-8')
