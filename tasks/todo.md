# WaferCut MES — 任务进度跟踪

> 最后更新: 2026-04-05
> GitHub: https://github.com/wuyutanhongyuxin-cell/IC_company_helper

---

## 总体进度

| Step | 内容 | 状态 | 预估 LOC | 完成日期 |
|------|------|------|----------|----------|
| 1 | 项目骨架 + 配置 | **已完成** | ~625 | 2026-04-04 |
| 1.5 | 迁移修复 + DISCO 参数 | **已完成** | — | 2026-04-04 |
| 2 | 数据模型 | **已完成** (随 Step 1 交付) | ~215 | 2026-04-04 |
| 3 | 认证蓝图 | **已完成** | ~766 | 2026-04-04 |
| 4 | 参数库蓝图 | **已完成** | ~620 | 2026-04-04 |
| 5 | 工单蓝图 + 状态机 | **已完成** | ~815 | 2026-04-05 |
| 6 | 仪表盘 | 未开始 | ~130 | — |
| 7 | PDF 报告 | 未开始 | ~185 | — |
| 8 | 国际化 | 未开始 | ~300 | — |
| 9 | 部署脚本 | 未开始 | ~115 | — |
| 10 | 集成测试与打磨 | 未开始 | — | — |

**当前进度: Step 1-5 已完成并推送，下一步 Step 6 仪表盘。**

---

## Git 提交历史

| 提交 | 说明 |
|------|------|
| `13dacad` | feat: Step 3 — 认证蓝图 (登录/登出/用户管理/改密码) |
| `e11eaa8` | fix: 迁移脚本与模型对齐 + Recipe 增加 DISCO 参数 |
| `6f471a3` | docs: add bilingual README |
| `ea0fbf4` | fix: round 2 review (Sonnet + Codex 审查修复) |
| `a03f014` | docs: update todo.md with Phase 1 summary |
| `4c89d34` | feat: Phase 1 — project skeleton + configuration + data models |

---

## 已完成步骤详情

### Step 1: 项目骨架 + 配置 (2026-04-04)

**交付物:**
- `config.py` — Dev/Prod/Test 三套配置 + 生产环境 SECRET_KEY 校验
- `wsgi.py` — Gunicorn 入口
- `app/__init__.py` — create_app() 工厂函数 (189 LOC)
- `app/extensions.py` — 两步初始化 + login_message i18n
- 5 个蓝图 + 占位路由
- Flask-Migrate 初始迁移脚本
- README.md — 中英双语文档

**审查修复 (Sonnet 4.6 + Codex → Opus 4.6 拍板):**
- SECRET_KEY 生产环境校验
- 模型导入顺序调整
- Flask-Babel 初始化提前
- `lazy='dynamic'` → `lazy='select'` (SQLAlchemy 2.x)
- login_message 用 lazy_gettext 包裹
- set_language 使用 request.referrer 回跳
- Recipe.created_by 显式 nullable=True
- User.is_active 覆盖 UserMixin 注释
- log_action() 不 commit 的 docstring

### Step 2: 数据模型 (2026-04-04, 随 Step 1 交付)

**5 个表:**
- `users` — 7 列，密码哈希 + 角色 + 软禁用
- `recipes` — 20 列 (含 4 个 DISCO 参数)，版本化单表设计
- `work_orders` — 15 列，工单 + 检验数据
- `work_order_status_logs` — 7 列，状态变更记录
- `audit_logs` — 7 列，操作审计

### Step 1.5: 迁移修复 (2026-04-04)

**修复清单:**
- `password_hash` String(512) → String(256)，与迁移对齐
- `order_number` 迁移重新生成，自动对齐为 String(32)
- 4 个 FK ondelete 正确包含 (SET NULL x3, RESTRICT x1)
- `env.py` SQLite 批量迁移 try/finally 关闭/恢复 FK 约束
- Recipe 新增 DISCO 参数 + CheckConstraint(cut_direction)
- emoji 替换修复 Windows GBK 编码崩溃
- 文档 3 处 `@babel.localeselector` 更新
- `lessons.md` 添加 Alembic ondelete 踩坑记录

**验证结果:**
- [x] `flask db upgrade` 无错误
- [x] `flask init-db` 创建管理员成功
- [x] `flask run` 启动正常
- [x] SQLite PRAGMA 验证 ondelete 值全部正确
- [x] 密码哈希 162 字符 < 256
- [x] CheckConstraint 拒绝非法 cut_direction
- [x] 已推送到 GitHub

### Step 3: 认证蓝图 (2026-04-04)

**交付物 (15 文件, 766 行):**
- `app/utils/decorators.py` — @role_required 装饰器 (30 行)
- `app/forms/auth.py` — 4 个表单 + ROLE_CHOICES 常量 (97 行)
- `app/blueprints/auth/routes.py` — 6 个路由 + 审计日志 (162 行)
- `app/templates/base.html` — Bootstrap 5 布局 + 导航栏 (127 行)
- `app/templates/_macros.html` — render_field + render_pagination (60 行)
- `app/templates/auth/` — 4 个模板 (login/users/user_form/change_password)
- `app/static/css/style.css` — 平板触控优化 44px (73 行)
- `app/static/js/app.js` — 确认对话框 + CSRF AJAX 注入 (44 行)
- 4 个占位路由添加 @login_required

**审查修复 (3 轮 Agent 并行审查):**
- ROLE_CHOICES 常量提取，消除两处硬编码
- CSRF meta tag 添加到 base.html head
- 确认 role_required 已含 is_authenticated 检查

**验证结果:**
- [x] 登录 admin/changeme 成功跳转仪表盘
- [x] Admin 创建/编辑/禁用 operator 用户
- [x] Operator 访问用户管理页返回 403
- [x] 改密码功能正常 (旧密码验证 + 新密码生效)
- [x] 禁用用户无法登录
- [x] 登出后重定向到登录页
- [x] 审计日志正确记录 10 条操作
- [x] 已推送到 GitHub (`13dacad`)

### Step 4: 参数库蓝图 (2026-04-04)

**交付物 (6 文件, 620 行):**
- `app/forms/recipe.py` — RecipeForm + DISCO 参数 + _str_or_empty coerce (80 行)
- `app/blueprints/recipe/routes.py` — 5 路由 + 版本化逻辑 + try/except (197 行)
- `app/templates/recipe/list.html` — 列表 + 材料/尺寸筛选 + aria-label (103 行)
- `app/templates/recipe/form.html` — 表单 + DISCO 可折叠 (85 行)
- `app/templates/recipe/detail.html` — 详情 + DISCO 区块条件显示 (108 行)
- `app/templates/recipe/history.html` — 版本历史 (57 行)

**审查修复 (Sonnet + Codex → Opus 拍板, 8 项):**
- try/except 包裹 create/edit commit — 防止并发竞态导致 500
- joinedload(Recipe.creator) — 消除 list/history 的 N+1 查询
- DISCO 折叠判断改用 `is not none` — 修复 0.0 值被折叠的 bug
- 取消按钮: 编辑时跳回详情页
- aria-label 筛选下拉框
- _RECIPE_FIELDS 同步警告注释

**验证结果:**
- [x] 创建配方 → 编辑产生新版本 (v1→v2)
- [x] 旧版本只读, is_active=False, 编辑被拒绝
- [x] 版本历史正确显示同组所有版本
- [x] 材料 + 尺寸筛选功能正常
- [x] DISCO 参数可选填写, 无值时隐藏区块
- [x] Operator 无法创建/编辑 (403)
- [x] 审计日志记录创建和编辑变更详情

### Step 5: 工单蓝图 + 状态机 (2026-04-05)

**交付物 (10 文件, 815 行):**
- `app/utils/state_machine.py` — 状态枚举 + 转换验证 + 恢复逻辑 (74 行)
- `app/utils/helpers.py` — 工单号生成 WO-YYYYMMDD-XXXX (36 行)
- `app/forms/work_order.py` — 3 个表单 WorkOrder/Inspection/Status (57 行)
- `app/blueprints/work_order/routes.py` — 4 CRUD 路由 + N+1 修复 (163 行)
- `app/blueprints/work_order/routes_status.py` — 状态推进/恢复/检验 (141 行)
- `app/templates/work_order/list.html` — 列表 + 状态筛选 + 搜索 (91 行)
- `app/templates/work_order/form.html` — 创建/编辑表单 (36 行)
- `app/templates/work_order/detail.html` — 详情 + 操作按钮 + 时间线 (172 行)
- `app/templates/work_order/inspection.html` — 检验数据表单 (39 行)

**审查修复 (Sonnet + Codex → Opus 拍板, 10 项):**
- CSRF 校验: change_status/resume_order 加 form.validate()
- 检验前置: inspection → completed 必须先有 inspection_result
- InputRequired: yield_rate/max_chipping_actual 允许 0 值
- N+1 修复: detail_order 预加载 status_logs + operator
- 孤立字段: 删除 WorkOrderForm.notes (无对应模型列)
- 硬编码消除: 模板用 can_hold 变量替代状态列表
- 时区修正: 工单号日期使用服务器本地时间
- 解析防御: try/except 防止脏数据导致 500
- 颜色区分: cleaning(dark) 与 filming(info) 区分
- flash 安全: 用默认文本替代原始用户输入

**验证结果:**
- [x] 创建工单 → 工单号格式 WO-YYYYMMDD-XXXX
- [x] 完整状态流转 incoming → filming → cutting → cleaning → inspection → completed
- [x] 异常挂起 (filming) → 恢复到正确的下一状态 (cutting)
- [x] 仅 incoming 可编辑，其他状态编辑被拒绝
- [x] 状态筛选 + 工单号/客户搜索功能正常
- [x] 状态时间线正确记录 6 次变更
- [x] 未填检验数据时阻止完成工单
- [x] yield_rate=0 / max_chipping_actual=0 可正常提交
- [x] 非法状态转换被拒绝
- [x] CSRF 校验生效

---

## 待实施步骤详细规划

### Step 6: 仪表盘 (~130 LOC)

**交付文件:**

**交付文件:**

| 文件 | 内容 | 预估行数 |
|------|------|----------|
| `app/blueprints/main/routes.py` | 仪表盘数据查询 + 语言切换 | ~50 |
| `app/templates/main/dashboard.html` | 统计卡片 + 最近工单列表 | ~80 |

**仪表盘内容:**
- 统计卡片: 在制工单数 / 今日完成数 / 异常挂起数 / 总工单数
- 最近工单列表 (最近 10 条，带状态标签)
- 快捷操作按钮: 创建工单 / 查看参数库

**验证标准:**
- [ ] 统计数据正确反映数据库状态
- [ ] 最近工单列表可点击跳转
- [ ] 语言切换 zh/en/ja 正常

---

### Step 7: PDF 报告 (~185 LOC)

**交付文件:**

| 文件 | 内容 | 预估行数 |
|------|------|----------|
| `app/blueprints/report/routes.py` | PDF 生成 + HTML 预览 2 个路由 | ~55 |
| `app/templates/report/delivery_report.html` | PDF 独立模板 (不继承 base.html) | ~130 |

**PDF 内容:**
- 公司抬头 + 报告编号 (工单号)
- 客户信息 + 晶圆规格
- 切割参数 (含 DISCO 参数)
- 检验结果 (良率 / 崩边 / 判定)
- 状态流转时间线
- 页脚: 生成时间 + 页码

**技术要点:**
- WeasyPrint 渲染，`@page { size: A4; margin: 20mm; }`
- CSS 字体用 `url()` 引用 Noto Sans CJK
- 仅 `completed` 状态工单可生成 PDF

**验证标准:**
- [ ] 完成工单生成 PDF 正常下载
- [ ] A4 排版正确，CJK 字符无乱码
- [ ] 非完成工单返回 400
- [ ] HTML 预览页面正常

---

### Step 8: 国际化 (~300 LOC 翻译)

**操作流程:**
```bash
pybabel extract -F babel.cfg -o messages.pot .
pybabel init -i messages.pot -d app/translations -l en
pybabel init -i messages.pot -d app/translations -l ja
# 翻译 en/ja 的 messages.po
pybabel compile -d app/translations
```

**翻译范围:**
- 所有模板中的用户可见字符串
- Flash 消息
- 表单标签 (lazy_gettext)
- PDF 报告标题/表头
- 状态名称 (incoming → "来料" / "Incoming" / "入荷")

**验证标准:**
- [ ] 切换三种语言 UI 全部正确
- [ ] PDF 报告随语言变化
- [ ] 表单验证错误消息多语言

---

### Step 9: 部署脚本 (~115 LOC)

**交付文件:**

| 文件 | 内容 | 预估行数 |
|------|------|----------|
| `deploy.sh` | Ubuntu 一键部署 (Gunicorn + Nginx + systemd) | ~80 |
| `backup.sh` | SQLite 每日备份 + 保留 7 天 | ~35 |

**deploy.sh 流程:**
1. 安装系统依赖 (Python, Nginx, fonts-noto-cjk)
2. 创建 venv + 安装 pip 依赖
3. 配置 .env (SECRET_KEY, ADMIN_PASSWORD)
4. flask db upgrade + flask init-db
5. 配置 Gunicorn systemd 服务 (2 workers)
6. 配置 Nginx 反向代理
7. 启用服务 + 防火墙

**验证标准:**
- [ ] Ubuntu VM 执行一键部署成功
- [ ] systemd 服务正常运行
- [ ] Nginx 反代 + HTTPS (可选)
- [ ] 备份脚本 cron 定时执行
- [ ] 进程崩溃自恢复 (Restart=always)

---

### Step 10: 集成测试与打磨

**端到端测试清单:**
- [ ] 冒烟测试: 启动 → 登录 → 各页面可访问
- [ ] Recipe 流程: 创建 → 编辑(新版本) → 历史 → 筛选
- [ ] 工单全流程: 创建 → 来料 → 贴膜 → 切割 → 清洗 → 检验 → 完成 → PDF
- [ ] 异常流程: 任意状态 → 异常挂起 → 恢复 → 继续
- [ ] 权限测试: operator 不能管理用户/创建配方
- [ ] 多语言: 切换 zh/en/ja → UI + PDF 均正确
- [ ] 响应式: Chrome DevTools iPad 模式 → 布局正常, 触控 >= 44px
- [ ] 并发: 两浏览器窗口同时操作 → 无数据库锁错误
- [ ] 审计日志: 所有操作有日志记录

---

## 依赖关系图

```
Step 1 骨架 ──→ Step 2 模型 ──→ Step 3 认证 ──→ Step 4 参数库 ──→ Step 5 工单
                                     │                                    │
                                     └─────── Step 6 仪表盘 ←─────────────┤
                                                                          │
                                              Step 7 PDF ←────────────────┘
                                                   │
                                              Step 8 i18n (依赖 3-7 全部)
                                                   │
Step 9 部署 (可独立) ──────────────────────→ Step 10 集成测试
```

---

## 技术决策备忘

| 决策 | 选择 | 理由 |
|------|------|------|
| 密码哈希长度 | VARCHAR(256) | scrypt 输出恒定 163 字符，256 有 57% 余量 |
| 工单号长度 | VARCHAR(32) | `WO-YYYYMMDD-XXXX` = 17 字符，32 预留扩展 |
| FK ondelete | 手动审查 | Alembic + SQLite 不自动生成 ondelete |
| env.py FK 处理 | try/finally OFF/ON | batch mode DROP TABLE 时 FK 冲突 |
| cut_direction | CheckConstraint('X','Y') | 数据库层面防非法值 |
| Recipe DISCO 参数 | nullable=True 列 | 兼容非 DISCO 设备，避免过早建子表 |
| 第二期再做 | 刀具管理、客户独立表 | 第一期用字符串字段够用 |
