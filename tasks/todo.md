# WaferCut MES — 任务进度跟踪

## 10 步构建计划

- [x] Step 1: 项目骨架 + 配置 (~220 LOC) — 进行中
- [ ] Step 2: 数据模型 (~215 LOC)
- [ ] Step 3: 认证蓝图 (~510 LOC)
- [ ] Step 4: 参数库蓝图 (~385 LOC)
- [ ] Step 5: 工单蓝图 + 状态机 (~595 LOC)
- [ ] Step 6: 仪表盘 (~130 LOC)
- [ ] Step 7: PDF 报告 (~185 LOC)
- [ ] Step 8: 国际化 (~300 LOC)
- [ ] Step 9: 部署脚本 (~115 LOC)
- [ ] Step 10: 集成测试与打磨

## Step 1 详细清单

- [x] config.py — 三套配置类
- [x] wsgi.py — Gunicorn 入口
- [x] .flaskenv — Flask 环境变量
- [x] requirements.txt — 依赖锁定
- [x] babel.cfg — Babel 提取配置
- [x] .env — 敏感配置
- [x] .gitignore — Git 忽略规则
- [x] app/__init__.py — create_app() 工厂函数
- [x] app/extensions.py — 扩展两步初始化
- [x] 5 个蓝图 __init__.py + 占位路由
- [x] 4 个模型文件（User/Recipe/WorkOrder/AuditLog）
- [x] forms / utils 占位文件
- [ ] 验证：flask run 启动无错误
- [ ] 验证：flask init-db 创建数据库 + 管理员
