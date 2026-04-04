# WaferCut MES — 任务进度跟踪

## 10 步构建计划

- [x] Step 1: 项目骨架 + 配置 (~625 LOC) — 已完成 + 审查通过
- [ ] Step 2: 数据模型 (~215 LOC)
- [ ] Step 3: 认证蓝图 (~510 LOC)
- [ ] Step 4: 参数库蓝图 (~385 LOC)
- [ ] Step 5: 工单蓝图 + 状态机 (~595 LOC)
- [ ] Step 6: 仪表盘 (~130 LOC)
- [ ] Step 7: PDF 报告 (~185 LOC)
- [ ] Step 8: 国际化 (~300 LOC)
- [ ] Step 9: 部署脚本 (~115 LOC)
- [ ] Step 10: 集成测试与打磨

## Step 1 完成总结 (2026-04-04)

### 交付物
- config.py — Dev/Prod/Test 三套配置 + 生产环境 SECRET_KEY 校验
- wsgi.py — Gunicorn 入口
- app/__init__.py — create_app() 工厂函数 (189 LOC)
- app/extensions.py — 两步初始化 + login_message i18n
- 5 个蓝图 + 占位路由
- 4 个模型文件（User/Recipe/WorkOrder/AuditLog）
- Flask-Migrate 初始迁移脚本
- README.md — 教学文档

### 审查修复 (Sonnet 4.6 + Codex 审查 → Opus 4.6 拍板)
- SECRET_KEY 生产环境校验（非 DEBUG 时默认值启动失败）
- 模型导入顺序调整（models 在 blueprints 之前）
- Flask-Babel 初始化提前（在蓝图注册之前）
- lazy='dynamic' → lazy='select'（SQLAlchemy 2.x 兼容）
- login_message 用 lazy_gettext 包裹（多语言支持）
- set_language 使用 request.referrer 回跳
- Recipe.created_by 显式 nullable=True
- User.is_active 覆盖 UserMixin 的注释说明
- log_action() 不 commit 的 docstring 说明

### 验证
- [x] flask run 启动无错误
- [x] flask init-db 创建 5 个表 + 管理员
- [x] SQLite WAL + foreign_keys + busy_timeout 正确
- [x] 所有路由 200 OK
- [x] 语言切换 + referrer 回跳
- [x] 多次 create_app() 不崩溃
- [x] ProductionConfig 安全检查拦截默认 SECRET_KEY
- [x] 已推送到 GitHub
