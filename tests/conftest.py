"""
共享测试 fixtures — 应用、数据库、用户、测试数据
每个测试函数独立 create_all/drop_all，完全隔离
"""
import sys
import os
import pytest
from datetime import datetime, timezone

# 确保 test 文件可以 from helpers import ...
sys.path.insert(0, os.path.dirname(__file__))

from config import TestingConfig
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.recipe import Recipe
from app.models.work_order import WorkOrder, WorkOrderStatusLog


# ---- 应用 & 数据库 ----

@pytest.fixture(scope='session')
def app():
    """Session 级别共享的 Flask 应用实例"""
    application = create_app(TestingConfig)
    return application


@pytest.fixture(autouse=True)
def db(app):
    """
    每个测试函数独立的数据库环境
    SQLite 内存库 + StaticPool，5 张表开销极小
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


# ---- 测试客户端 ----

@pytest.fixture
def client(app):
    """未登录的测试客户端"""
    return app.test_client()


@pytest.fixture
def admin_client(app, admin_user):
    """已登录 admin 的测试客户端"""
    c = app.test_client()
    c.post('/auth/login', data={
        'username': 'testadmin',
        'password': 'admin123',
    })
    return c


@pytest.fixture
def operator_client(app, operator_user):
    """已登录 operator 的测试客户端"""
    c = app.test_client()
    c.post('/auth/login', data={
        'username': 'testoper',
        'password': 'oper123',
    })
    return c


# ---- 用户 ----

@pytest.fixture
def admin_user(db):
    """管理员用户"""
    user = User(
        username='testadmin',
        display_name='Test Admin',
        role='admin',
    )
    user.set_password('admin123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def operator_user(db):
    """操作员用户"""
    user = User(
        username='testoper',
        display_name='Test Operator',
        role='operator',
    )
    user.set_password('oper123')
    db.session.add(user)
    db.session.commit()
    return user


# ---- 测试数据 ----

@pytest.fixture
def sample_recipe(db, admin_user):
    """活跃配方 v1"""
    recipe = Recipe(
        recipe_group_id=1,
        version=1,
        created_by=admin_user.id,
        wafer_material='Silicon',
        wafer_size='8inch',
        thickness=300.0,
        blade_model='NBC-ZH2050',
        spindle_speed=30000,
        feed_rate=10.0,
        cut_depth=200.0,
        coolant_flow=1.5,
        max_chipping=15.0,
    )
    db.session.add(recipe)
    db.session.commit()
    return recipe


@pytest.fixture
def sample_order(db, sample_recipe, admin_user):
    """incoming 状态工单"""
    order = WorkOrder(
        order_number='WO-20260409-0001',
        customer='Test Corp',
        wafer_spec='8inch Silicon 300um',
        quantity=100,
        recipe_id=sample_recipe.id,
        operator_id=admin_user.id,
    )
    db.session.add(order)
    db.session.commit()
    return order


@pytest.fixture
def completed_order(db, sample_recipe, admin_user):
    """已完成工单 — 含检验数据与完整状态日志"""
    order = WorkOrder(
        order_number='WO-20260409-0099',
        customer='Completed Corp',
        wafer_spec='8inch Silicon 300um',
        quantity=50,
        recipe_id=sample_recipe.id,
        operator_id=admin_user.id,
        status='completed',
        yield_rate=95.5,
        max_chipping_actual=12.0,
        inspection_result='pass',
        inspection_notes='All parameters within spec',
        completed_at=datetime.now(timezone.utc),
    )
    db.session.add(order)
    db.session.flush()

    # 完整状态时间线
    statuses = [
        'incoming', 'filming', 'cutting',
        'cleaning', 'inspection', 'completed',
    ]
    for i in range(len(statuses) - 1):
        log = WorkOrderStatusLog(
            work_order_id=order.id,
            from_status=statuses[i],
            to_status=statuses[i + 1],
            operator_id=admin_user.id,
        )
        db.session.add(log)
    db.session.commit()
    return order
