# tests/

## 用途
WaferCut MES 集成测试套件，验证所有功能模块的端到端行为。

## 文件清单
- `conftest.py` — 共享 fixtures: app, db, users, sample data (~130 行)
- `helpers.py` — 登录辅助、表单数据构造、状态推进 (~68 行)
- `test_smoke.py` — 冒烟测试: 应用创建、页面可访问 (~65 行)
- `test_auth.py` — 登录/登出/用户管理/改密码 (~220 行)
- `test_recipe.py` — Recipe CRUD + 版本化 + 筛选 (~175 行)
- `test_work_order.py` — 工单 CRUD + 完整状态流转 + 检验 (~240 行)
- `test_exception.py` — 异常挂起 + 恢复 (~120 行)
- `test_report.py` — HTML 预览 + WeasyPrint mock PDF (~80 行)
- `test_permissions.py` — 角色权限 (admin/operator/匿名) (~130 行)
- `test_i18n.py` — 中/英/日语言切换 (~70 行)
- `test_audit.py` — 审计日志验证 (~120 行)

## 运行方式
```bash
# 全部测试
python -m pytest tests/ -v

# 单个文件
python -m pytest tests/test_auth.py -v

# 按关键字
python -m pytest tests/ -k "status_flow" -v
```

## 依赖关系
- 本目录依赖：app, config (项目源码)
- 外部依赖：pytest
