"""
测试辅助函数 — 登录、表单数据构造、状态推进
"""


def login(client, username, password):
    """POST 登录并返回响应"""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    })


def make_recipe_data(**overrides):
    """构造 Recipe 表单提交数据（字符串值，模拟浏览器表单）"""
    data = {
        'wafer_material': 'Silicon',
        'wafer_size': '8inch',
        'thickness': '300.0',
        'blade_model': 'NBC-ZH2050',
        'spindle_speed': '30000',
        'feed_rate': '10.0',
        'cut_depth': '200.0',
        'coolant_flow': '1.5',
        'max_chipping': '15.0',
        'cut_direction': '',
        'notes': '',
    }
    data.update(overrides)
    return data


def make_order_data(recipe_id, **overrides):
    """构造工单表单提交数据"""
    data = {
        'customer': 'Test Corp',
        'wafer_spec': '8inch Silicon 300um',
        'quantity': '100',
        'recipe_id': str(recipe_id),
    }
    data.update(overrides)
    return data


def make_inspection_data(**overrides):
    """构造检验表单提交数据"""
    data = {
        'yield_rate': '95.5',
        'max_chipping_actual': '12.0',
        'inspection_result': 'pass',
        'inspection_notes': 'All good',
    }
    data.update(overrides)
    return data


def advance_order_to(client, order_id, target_status):
    """
    从 incoming 逐步推进工单到目标状态
    如果目标是 completed，自动填写检验数据
    """
    from app.utils.state_machine import STATUS_ORDER

    for i in range(len(STATUS_ORDER) - 1):
        next_s = STATUS_ORDER[i + 1]
        # 到达 completed 前必须先填检验
        if next_s == 'completed':
            client.post(
                f'/orders/{order_id}/inspection',
                data=make_inspection_data(),
            )
        client.post(
            f'/orders/{order_id}/status',
            data={'target_status': next_s},
        )
        if next_s == target_status:
            break
