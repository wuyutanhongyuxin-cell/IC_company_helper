"""权限测试 — 角色访问控制 (admin/operator/匿名)"""
from helpers import make_recipe_data, make_order_data


class TestAnonymousAccess:
    """匿名用户 — 全部重定向到登录页"""

    def test_dashboard(self, client):
        assert client.get('/').status_code == 302

    def test_recipe_list(self, client):
        assert client.get('/recipes/').status_code == 302

    def test_recipe_create(self, client):
        assert client.get('/recipes/create').status_code == 302

    def test_order_list(self, client):
        assert client.get('/orders/').status_code == 302

    def test_order_create(self, client):
        assert client.get('/orders/create').status_code == 302

    def test_user_list(self, client):
        assert client.get('/auth/users').status_code == 302

    def test_change_password(self, client):
        assert client.get('/auth/change-password').status_code == 302

    def test_report_preview(self, client):
        assert client.get('/reports/delivery/1/preview').status_code == 302


class TestOperatorRestrictions:
    """Operator 角色限制 — 不能执行 admin 操作"""

    def test_cannot_list_users(self, operator_client):
        """不能查看用户列表"""
        resp = operator_client.get('/auth/users')
        assert resp.status_code == 403

    def test_cannot_create_user(self, operator_client):
        """不能创建用户"""
        resp = operator_client.get('/auth/users/create')
        assert resp.status_code == 403

    def test_cannot_create_user_post(self, operator_client):
        """不能 POST 创建用户"""
        resp = operator_client.post('/auth/users/create', data={
            'username': 'hack',
            'display_name': 'Hack',
            'password': 'hack123456',
            'password2': 'hack123456',
            'role': 'admin',
        })
        assert resp.status_code == 403

    def test_cannot_edit_user(self, operator_client, admin_user):
        """不能编辑用户"""
        resp = operator_client.get(f'/auth/users/{admin_user.id}/edit')
        assert resp.status_code == 403

    def test_cannot_create_recipe(self, operator_client):
        """不能创建配方"""
        resp = operator_client.get('/recipes/create')
        assert resp.status_code == 403

    def test_cannot_create_recipe_post(self, operator_client):
        """不能 POST 创建配方"""
        resp = operator_client.post(
            '/recipes/create', data=make_recipe_data(),
        )
        assert resp.status_code == 403

    def test_cannot_edit_recipe(self, operator_client, sample_recipe):
        """不能编辑配方"""
        resp = operator_client.get(f'/recipes/{sample_recipe.id}/edit')
        assert resp.status_code == 403


class TestOperatorAllowed:
    """Operator 允许的操作"""

    def test_can_view_dashboard(self, operator_client):
        assert operator_client.get('/').status_code == 200

    def test_can_list_recipes(self, operator_client):
        assert operator_client.get('/recipes/').status_code == 200

    def test_can_view_recipe(self, operator_client, sample_recipe):
        resp = operator_client.get(f'/recipes/{sample_recipe.id}')
        assert resp.status_code == 200

    def test_can_view_history(self, operator_client, sample_recipe):
        gid = sample_recipe.recipe_group_id
        resp = operator_client.get(f'/recipes/group/{gid}/history')
        assert resp.status_code == 200

    def test_can_list_orders(self, operator_client):
        assert operator_client.get('/orders/').status_code == 200

    def test_can_create_order(self, operator_client, sample_recipe):
        resp = operator_client.post(
            '/orders/create',
            data=make_order_data(sample_recipe.id),
        )
        assert resp.status_code == 302

    def test_can_view_order(self, operator_client, sample_order):
        resp = operator_client.get(f'/orders/{sample_order.id}')
        assert resp.status_code == 200

    def test_can_advance_status(self, operator_client, sample_order):
        """Operator 可以推进工单状态"""
        resp = operator_client.post(
            f'/orders/{sample_order.id}/status',
            data={'target_status': 'filming'},
        )
        assert resp.status_code == 302

    def test_can_change_password(self, operator_client):
        assert operator_client.get('/auth/change-password').status_code == 200

    def test_can_preview_report(self, operator_client, completed_order):
        resp = operator_client.get(
            f'/reports/delivery/{completed_order.id}/preview'
        )
        assert resp.status_code == 200
