"""异常挂起测试 — 进入异常 + 恢复"""
from app.models.work_order import WorkOrder
from helpers import advance_order_to


class TestEnterException:
    """进入异常挂起"""

    def test_from_incoming(self, admin_client, sample_order, db):
        """incoming → exception_hold"""
        resp = admin_client.post(
            f'/orders/{sample_order.id}/status',
            data={'target_status': 'exception_hold'},
        )
        assert resp.status_code == 302
        db.session.expire_all()
        order = db.session.get(WorkOrder, sample_order.id)
        assert order.status == 'exception_hold'
        assert order.previous_status == 'incoming'

    def test_from_filming(self, admin_client, sample_order, db):
        """filming → exception_hold"""
        advance_order_to(admin_client, sample_order.id, 'filming')
        admin_client.post(
            f'/orders/{sample_order.id}/status',
            data={'target_status': 'exception_hold'},
        )
        db.session.expire_all()
        order = db.session.get(WorkOrder, sample_order.id)
        assert order.status == 'exception_hold'
        assert order.previous_status == 'filming'

    def test_from_cutting(self, admin_client, sample_order, db):
        """cutting → exception_hold"""
        advance_order_to(admin_client, sample_order.id, 'cutting')
        admin_client.post(
            f'/orders/{sample_order.id}/status',
            data={'target_status': 'exception_hold'},
        )
        db.session.expire_all()
        order = db.session.get(WorkOrder, sample_order.id)
        assert order.status == 'exception_hold'
        assert order.previous_status == 'cutting'

    def test_from_inspection(self, admin_client, sample_order, db):
        """inspection → exception_hold"""
        advance_order_to(admin_client, sample_order.id, 'inspection')
        admin_client.post(
            f'/orders/{sample_order.id}/status',
            data={'target_status': 'exception_hold'},
        )
        db.session.expire_all()
        order = db.session.get(WorkOrder, sample_order.id)
        assert order.status == 'exception_hold'
        assert order.previous_status == 'inspection'

    def test_completed_cannot_hold(self, admin_client, sample_order, db):
        """completed 不能进入异常挂起"""
        advance_order_to(admin_client, sample_order.id, 'completed')
        admin_client.post(
            f'/orders/{sample_order.id}/status',
            data={'target_status': 'exception_hold'},
        )
        db.session.expire_all()
        order = db.session.get(WorkOrder, sample_order.id)
        assert order.status == 'completed'  # 未变


class TestResumeFromException:
    """从异常恢复"""

    def test_resume_from_incoming(self, admin_client, sample_order, db):
        """incoming 挂起 → 恢复到 filming"""
        oid = sample_order.id
        admin_client.post(
            f'/orders/{oid}/status',
            data={'target_status': 'exception_hold'},
        )
        resp = admin_client.post(f'/orders/{oid}/resume', data={})
        assert resp.status_code == 302

        db.session.expire_all()
        order = db.session.get(WorkOrder, oid)
        assert order.status == 'filming'
        assert order.previous_status is None

    def test_resume_from_cutting(self, admin_client, sample_order, db):
        """cutting 挂起 → 恢复到 cleaning"""
        oid = sample_order.id
        advance_order_to(admin_client, oid, 'cutting')
        admin_client.post(
            f'/orders/{oid}/status',
            data={'target_status': 'exception_hold'},
        )
        resp = admin_client.post(f'/orders/{oid}/resume', data={})
        assert resp.status_code == 302

        db.session.expire_all()
        order = db.session.get(WorkOrder, oid)
        assert order.status == 'cleaning'

    def test_resume_only_from_exception(self, admin_client, sample_order, db):
        """非异常挂起状态不能恢复"""
        resp = admin_client.post(
            f'/orders/{sample_order.id}/resume',
            data={},
            follow_redirects=True,
        )
        assert '仅异常挂起状态可恢复' in resp.data.decode('utf-8')

    def test_resume_then_continue(self, admin_client, sample_order, db):
        """恢复后可继续正常流转"""
        oid = sample_order.id
        # incoming → exception → resume → filming
        admin_client.post(
            f'/orders/{oid}/status',
            data={'target_status': 'exception_hold'},
        )
        admin_client.post(f'/orders/{oid}/resume', data={})
        # filming → cutting
        admin_client.post(
            f'/orders/{oid}/status',
            data={'target_status': 'cutting'},
        )
        db.session.expire_all()
        order = db.session.get(WorkOrder, oid)
        assert order.status == 'cutting'
