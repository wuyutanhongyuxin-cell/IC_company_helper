"""工单测试 — CRUD + 完整状态流转 + 检验"""
import re

from app.models.work_order import WorkOrder, WorkOrderStatusLog
from helpers import make_order_data, make_inspection_data, advance_order_to


class TestOrderCreate:
    """创建工单"""

    def test_create_success(self, admin_client, sample_recipe, db):
        """创建工单成功"""
        resp = admin_client.post(
            '/orders/create',
            data=make_order_data(sample_recipe.id),
        )
        assert resp.status_code == 302
        order = db.session.execute(db.select(WorkOrder)).scalar_one()
        assert order.customer == 'Test Corp'
        assert order.status == 'incoming'
        assert order.recipe_id == sample_recipe.id

    def test_order_number_format(self, admin_client, sample_recipe, db):
        """工单号格式 WO-YYYYMMDD-XXXX"""
        admin_client.post(
            '/orders/create',
            data=make_order_data(sample_recipe.id),
        )
        order = db.session.execute(db.select(WorkOrder)).scalar_one()
        assert re.match(r'^WO-\d{8}-\d{4}$', order.order_number)

    def test_order_number_sequential(self, admin_client, sample_recipe, db):
        """同日工单号自增"""
        admin_client.post(
            '/orders/create',
            data=make_order_data(sample_recipe.id),
        )
        admin_client.post(
            '/orders/create',
            data=make_order_data(sample_recipe.id, customer='Corp B'),
        )
        orders = db.session.execute(
            db.select(WorkOrder).order_by(WorkOrder.id)
        ).scalars().all()
        assert len(orders) == 2
        # 第二个序号比第一个大 1
        seq1 = int(orders[0].order_number.split('-')[-1])
        seq2 = int(orders[1].order_number.split('-')[-1])
        assert seq2 == seq1 + 1

    def test_create_form_page(self, admin_client, sample_recipe):
        """创建表单可访问"""
        resp = admin_client.get('/orders/create')
        assert resp.status_code == 200


class TestOrderEdit:
    """编辑工单"""

    def test_edit_incoming_ok(self, admin_client, sample_order, sample_recipe, db):
        """incoming 状态可编辑"""
        resp = admin_client.post(
            f'/orders/{sample_order.id}/edit',
            data=make_order_data(sample_recipe.id, customer='Updated Corp'),
        )
        assert resp.status_code == 302
        db.session.expire_all()
        order = db.session.get(WorkOrder, sample_order.id)
        assert order.customer == 'Updated Corp'

    def test_edit_non_incoming_blocked(self, admin_client, sample_order, db):
        """非 incoming 状态不可编辑"""
        advance_order_to(admin_client, sample_order.id, 'filming')
        resp = admin_client.get(
            f'/orders/{sample_order.id}/edit',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert '仅来料状态' in resp.data.decode('utf-8')


class TestOrderList:
    """工单列表"""

    def test_empty_list(self, admin_client):
        """无工单时列表为空"""
        resp = admin_client.get('/orders/')
        assert resp.status_code == 200

    def test_list_shows_orders(self, admin_client, sample_order):
        """列表显示工单"""
        resp = admin_client.get('/orders/')
        html = resp.data.decode('utf-8')
        assert 'Test Corp' in html

    def test_filter_by_status(self, admin_client, sample_order):
        """按状态筛选"""
        resp = admin_client.get('/orders/?status=incoming')
        assert resp.status_code == 200
        assert 'Test Corp' in resp.data.decode('utf-8')

    def test_filter_no_match(self, admin_client, sample_order):
        """筛选无匹配"""
        resp = admin_client.get('/orders/?status=completed')
        assert resp.status_code == 200

    def test_search_by_customer(self, admin_client, sample_order):
        """按客户搜索"""
        resp = admin_client.get('/orders/?q=Test')
        assert resp.status_code == 200
        assert 'Test Corp' in resp.data.decode('utf-8')

    def test_search_by_order_number(self, admin_client, sample_order):
        """按工单号搜索"""
        resp = admin_client.get('/orders/?q=WO-2026')
        assert resp.status_code == 200


class TestOrderDetail:
    """工单详情"""

    def test_detail_page(self, admin_client, sample_order):
        """详情页显示工单信息"""
        resp = admin_client.get(f'/orders/{sample_order.id}')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Test Corp' in html

    def test_detail_not_found(self, admin_client):
        """不存在的工单"""
        resp = admin_client.get('/orders/999')
        assert resp.status_code == 404


class TestStatusFlow:
    """状态流转"""

    def test_full_linear_flow(self, admin_client, sample_order, db):
        """完整线性流转 incoming → completed"""
        oid = sample_order.id
        statuses = ['filming', 'cutting', 'cleaning', 'inspection']

        for target in statuses:
            resp = admin_client.post(
                f'/orders/{oid}/status',
                data={'target_status': target},
            )
            assert resp.status_code == 302

        # 填写检验数据
        resp = admin_client.post(
            f'/orders/{oid}/inspection',
            data=make_inspection_data(),
        )
        assert resp.status_code == 302

        # 推进到 completed
        resp = admin_client.post(
            f'/orders/{oid}/status',
            data={'target_status': 'completed'},
        )
        assert resp.status_code == 302

        db.session.expire_all()
        order = db.session.get(WorkOrder, oid)
        assert order.status == 'completed'
        assert order.completed_at is not None
        assert order.yield_rate == 95.5
        assert order.inspection_result == 'pass'

    def test_invalid_transition_blocked(self, admin_client, sample_order, db):
        """非法状态转换被拒绝"""
        # incoming 不能直接到 cutting
        resp = admin_client.post(
            f'/orders/{sample_order.id}/status',
            data={'target_status': 'cutting'},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        db.session.expire_all()
        order = db.session.get(WorkOrder, sample_order.id)
        assert order.status == 'incoming'

    def test_completed_requires_inspection(self, admin_client, sample_order, db):
        """未填检验数据不能完成"""
        oid = sample_order.id
        advance_order_to(admin_client, oid, 'inspection')

        # 不填检验直接尝试完成
        resp = admin_client.post(
            f'/orders/{oid}/status',
            data={'target_status': 'completed'},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert '请先填写检验数据' in resp.data.decode('utf-8')

    def test_status_logs_created(self, admin_client, sample_order, db):
        """状态变更产生日志"""
        oid = sample_order.id
        admin_client.post(
            f'/orders/{oid}/status',
            data={'target_status': 'filming'},
        )
        logs = db.session.execute(
            db.select(WorkOrderStatusLog)
            .filter_by(work_order_id=oid)
        ).scalars().all()
        assert len(logs) == 1
        assert logs[0].from_status == 'incoming'
        assert logs[0].to_status == 'filming'


class TestInspection:
    """检验数据"""

    def test_fill_inspection(self, admin_client, sample_order, db):
        """填写检验数据"""
        oid = sample_order.id
        advance_order_to(admin_client, oid, 'inspection')

        resp = admin_client.post(
            f'/orders/{oid}/inspection',
            data=make_inspection_data(),
        )
        assert resp.status_code == 302

        db.session.expire_all()
        order = db.session.get(WorkOrder, oid)
        assert order.yield_rate == 95.5
        assert order.max_chipping_actual == 12.0
        assert order.inspection_result == 'pass'

    def test_zero_values_accepted(self, admin_client, sample_order, db):
        """0 值合法（InputRequired 允许）"""
        oid = sample_order.id
        advance_order_to(admin_client, oid, 'inspection')

        resp = admin_client.post(
            f'/orders/{oid}/inspection',
            data=make_inspection_data(
                yield_rate='0', max_chipping_actual='0',
            ),
        )
        assert resp.status_code == 302

        db.session.expire_all()
        order = db.session.get(WorkOrder, oid)
        assert order.yield_rate == 0.0
        assert order.max_chipping_actual == 0.0

    def test_fail_result(self, admin_client, sample_order, db):
        """检验不通过"""
        oid = sample_order.id
        advance_order_to(admin_client, oid, 'inspection')

        resp = admin_client.post(
            f'/orders/{oid}/inspection',
            data=make_inspection_data(inspection_result='fail'),
        )
        assert resp.status_code == 302

        db.session.expire_all()
        order = db.session.get(WorkOrder, oid)
        assert order.inspection_result == 'fail'

    def test_inspection_wrong_status(self, admin_client, sample_order):
        """非 inspection 状态不能填检验"""
        resp = admin_client.post(
            f'/orders/{sample_order.id}/inspection',
            data=make_inspection_data(),
            follow_redirects=True,
        )
        assert '仅检验状态' in resp.data.decode('utf-8')

    def test_inspection_form_page(self, admin_client, sample_order):
        """检验表单页面 — 需要在 inspection 状态"""
        oid = sample_order.id
        advance_order_to(admin_client, oid, 'inspection')
        resp = admin_client.get(f'/orders/{oid}/inspection')
        assert resp.status_code == 200
