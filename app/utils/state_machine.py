"""
工单状态机 — 6 个线性状态 + 1 个异常挂起状态
用 Python dict 实现，不引入外部状态机库

状态流转:
  incoming -> filming -> cutting -> cleaning -> inspection -> completed
  任意状态 -> exception_hold
  exception_hold -> 恢复到 previous_status 的下一个状态
"""
from flask_babel import lazy_gettext as _l

# 线性状态顺序（用于异常恢复时计算"下一个状态"）
STATUS_ORDER = [
    'incoming', 'filming', 'cutting',
    'cleaning', 'inspection', 'completed',
]

# 状态的中文显示名（用于模板渲染）
STATUS_LABELS = {
    'incoming':       _l('来料'),
    'filming':        _l('贴膜'),
    'cutting':        _l('切割'),
    'cleaning':       _l('清洗'),
    'inspection':     _l('检验'),
    'completed':      _l('完成'),
    'exception_hold': _l('异常挂起'),
}

# 状态对应的 Bootstrap 颜色 class
STATUS_COLORS = {
    'incoming':       'secondary',
    'filming':        'info',
    'cutting':        'primary',
    'cleaning':       'dark',
    'inspection':     'warning',
    'completed':      'success',
    'exception_hold': 'danger',
}

# 合法状态转换表
VALID_TRANSITIONS = {
    'incoming':       ['filming', 'exception_hold'],
    'filming':        ['cutting', 'exception_hold'],
    'cutting':        ['cleaning', 'exception_hold'],
    'cleaning':       ['inspection', 'exception_hold'],
    'inspection':     ['completed', 'exception_hold'],
    'completed':      [],
    'exception_hold': [],  # 恢复逻辑由 get_resume_target() 单独处理
}


def can_transition(current, target):
    """检查状态转换是否合法"""
    return target in VALID_TRANSITIONS.get(current, [])


def get_next_status(current):
    """获取线性流程中的下一个状态（不含 exception_hold）"""
    if current not in STATUS_ORDER:
        return None
    idx = STATUS_ORDER.index(current)
    if idx + 1 < len(STATUS_ORDER):
        return STATUS_ORDER[idx + 1]
    return None


def get_resume_target(previous_status):
    """
    从异常挂起恢复: 返回 previous_status 的下一个线性状态

    例: previous_status='cutting' -> 恢复到 'cleaning'
    返回 None 表示无法恢复（previous_status 无效或已是最后状态）
    """
    return get_next_status(previous_status)
