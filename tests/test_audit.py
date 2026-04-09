"""审计日志测试 — 操作记录验证"""
from app.models.audit_log import AuditLog
from app.models.work_order import WorkOrderStatusLog
from helpers import (
    make_recipe_data, make_order_data,
    make_inspection_data, advance_order_to,
)


class TestLoginAudit:
    """登录/登出审计"""

    def test_login_creates_log(self, app, admin_user, db):
        """登录产生审计日志"""
        c = app.test_client()
        c.post('/auth/login', data={
            'username': 'testadmin', 'password': 'admin123',
        })
        logs = db.session.execute(
            db.select(AuditLog).filter_by(action='login')
        ).scalars().all()
        assert len(logs) == 1
        assert logs[0].target_type == 'user'
        assert logs[0].user_id == admin_user.id

    def test_logout_creates_log(self, admin_client, db):
        """登出产生审计日志"""
        admin_client.post('/auth/logout')
        logs = db.session.execute(
            db.select(AuditLog).filter_by(action='logout')
        ).scalars().all()
        assert len(logs) == 1


class TestUserAudit:
    """用户管理审计"""

    def test_create_user_log(self, admin_client, db):
        """创建用户记录审计日志"""
        admin_client.post('/auth/users/create', data={
            'username': 'audituser',
            'display_name': 'Audit User',
            'password': 'pass123456',
            'password2': 'pass123456',
            'role': 'operator',
        })
        logs = db.session.execute(
            db.select(AuditLog).filter_by(
                action='create', target_type='user',
            )
        ).scalars().all()
        assert len(logs) == 1
        details = logs[0].get_details()
        assert details['username'] == 'audituser'
        assert details['role'] == 'operator'

    def test_edit_user_log(self, admin_client, operator_user, db):
        """编辑用户记录审计日志"""
        admin_client.post(
            f'/auth/users/{operator_user.id}/edit',
            data={
                'display_name': 'New Name',
                'role': 'operator',
                'is_active': 'y',
            },
        )
        logs = db.session.execute(
            db.select(AuditLog).filter_by(
                action='update', target_type='user',
            )
        ).scalars().all()
        assert len(logs) == 1


class TestRecipeAudit:
    """配方审计"""

    def test_create_recipe_log(self, admin_client, db):
        """创建配方记录审计日志"""
        admin_client.post('/recipes/create', data=make_recipe_data())
        logs = db.session.execute(
            db.select(AuditLog).filter_by(
                action='create', target_type='recipe',
            )
        ).scalars().all()
        assert len(logs) == 1
        details = logs[0].get_details()
        assert details['material'] == 'Silicon'

    def test_edit_recipe_log(self, admin_client, sample_recipe, db):
        """编辑配方记录审计日志（含版本信息）"""
        admin_client.post(
            f'/recipes/{sample_recipe.id}/edit',
            data=make_recipe_data(wafer_material='GaN'),
        )
        logs = db.session.execute(
            db.select(AuditLog).filter_by(
                action='update', target_type='recipe',
            )
        ).scalars().all()
        assert len(logs) == 1
        details = logs[0].get_details()
        assert details['from_version'] == 1


class TestOrderAudit:
    """工单审计"""

    def test_create_order_log(self, admin_client, sample_recipe, db):
        """创建工单记录审计日志"""
        admin_client.post(
            '/orders/create',
            data=make_order_data(sample_recipe.id),
        )
        logs = db.session.execute(
            db.select(AuditLog).filter_by(
                action='create', target_type='work_order',
            )
        ).scalars().all()
        assert len(logs) == 1
        details = logs[0].get_details()
        assert 'order_number' in details


class TestStatusAudit:
    """状态变更审计"""

    def test_status_change_audit_log(self, admin_client, sample_order, db):
        """状态变更产生审计日志"""
        admin_client.post(
            f'/orders/{sample_order.id}/status',
            data={'target_status': 'filming'},
        )
        logs = db.session.execute(
            db.select(AuditLog).filter_by(action='status_change')
        ).scalars().all()
        assert len(logs) == 1
        details = logs[0].get_details()
        assert details['from'] == 'incoming'
        assert details['to'] == 'filming'

    def test_status_change_creates_status_log(
        self, admin_client, sample_order, db,
    ):
        """状态变更同时产生 WorkOrderStatusLog"""
        admin_client.post(
            f'/orders/{sample_order.id}/status',
            data={'target_status': 'filming'},
        )
        logs = db.session.execute(
            db.select(WorkOrderStatusLog)
            .filter_by(work_order_id=sample_order.id)
        ).scalars().all()
        assert len(logs) == 1
        assert logs[0].from_status == 'incoming'
        assert logs[0].to_status == 'filming'
        assert logs[0].operator_id is not None

    def test_inspection_audit(self, admin_client, sample_order, db):
        """检验数据记录审计日志"""
        advance_order_to(admin_client, sample_order.id, 'inspection')
        admin_client.post(
            f'/orders/{sample_order.id}/inspection',
            data=make_inspection_data(),
        )
        logs = db.session.execute(
            db.select(AuditLog).filter_by(
                action='update', target_type='work_order',
            )
        ).scalars().all()
        # 至少一条 inspection update
        assert len(logs) >= 1
        # 找到包含 inspection_result 的那条
        insp_log = [
            l for l in logs
            if l.get_details() and 'inspection_result' in l.get_details()
        ]
        assert len(insp_log) == 1

    def test_full_flow_audit_count(self, admin_client, sample_order, db):
        """完整流转产生多条审计日志"""
        advance_order_to(admin_client, sample_order.id, 'completed')
        # 5 次状态变更 + 1 次检验
        sc_logs = db.session.execute(
            db.select(AuditLog).filter_by(action='status_change')
        ).scalars().all()
        assert len(sc_logs) == 5  # incoming→...→completed
