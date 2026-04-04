# CLAUDE.md — WaferCut MES 项目 AI 编程规范

> 把这个文件放在项目根目录。Claude Code 每次启动自动读取。

---

## [项目专属区域]

### 项目名称
WaferCut MES — 晶圆切割代工厂管理系统

### 一句话描述
为晶圆切割代工厂建设的 MES 生产管理系统，管理切割参数(Recipe)、工单流转、交付报告。局域网部署，平板适配，中/英/日三语。

### 技术栈
- **后端**: Python 3.10+ / Flask 3.0.3 / Flask-SQLAlchemy 3.1.1
- **数据库**: SQLite (WAL 模式) + Flask-Migrate 4.0.7
- **认证**: Flask-Login 0.6.3 + werkzeug 密码哈希
- **表单**: Flask-WTF 1.2.1 (WTForms)
- **多语言**: Flask-Babel 4.0.0 (中文默认/英文/日文)
- **PDF**: WeasyPrint 62.3 (CJK 需 Noto Sans CJK 字体)
- **前端**: Bootstrap 5 (CDN) + 自定义 CSS/JS
- **部署**: Ubuntu 24.04 / Gunicorn 22.0.0 (2 workers) / Nginx / systemd
- **不要引入以上未列出的依赖**，需要新库先问我

### 项目结构
```
E:/claude_ask/company_helper_/
├── CLAUDE.md                    # 本文件 — AI 编程规范
├── config.py                    # 配置类 (Dev/Prod/Test)
├── wsgi.py                      # Gunicorn 入口
├── .flaskenv                    # FLASK_APP=wsgi.py
├── requirements.txt             # 依赖锁定
├── babel.cfg                    # Babel 提取配置
├── deploy.sh                    # Ubuntu 一键部署
├── backup.sh                    # SQLite 每日备份
├── docs/
│   └── architecture-and-research.md  # 架构设计与技术研究文档（详细参考）
├── app/
│   ├── __init__.py              # create_app() 工厂函数
│   ├── extensions.py            # db, login_manager, babel, migrate, csrf
│   ├── models/                  # 数据模型（5 个表）
│   │   ├── user.py              # User + 密码哈希
│   │   ├── recipe.py            # Recipe + 版本分组
│   │   ├── work_order.py        # WorkOrder + StatusLog
│   │   └── audit_log.py         # AuditLog + log_action()
│   ├── forms/                   # WTForms 表单
│   │   ├── auth.py              # 登录/用户管理表单
│   │   ├── recipe.py            # Recipe 表单
│   │   └── work_order.py        # 工单/检验表单
│   ├── utils/                   # 工具函数
│   │   ├── decorators.py        # @role_required 装饰器
│   │   ├── state_machine.py     # 状态枚举 + 转换验证
│   │   └── helpers.py           # 工单号生成 + API 响应
│   ├── blueprints/              # Flask 蓝图（5 个模块）
│   │   ├── auth/routes.py       # 登录/登出/用户管理
│   │   ├── main/routes.py       # Dashboard + 语言切换
│   │   ├── recipe/routes.py     # Recipe CRUD + 版本历史
│   │   ├── work_order/routes.py # 工单 CRUD + 状态流转
│   │   └── report/routes.py     # PDF 生成
│   ├── templates/               # Jinja2 模板
│   │   ├── base.html            # Bootstrap 5 基础布局
│   │   ├── _macros.html         # 表单渲染/分页宏
│   │   ├── auth/                # login, users, user_form, change_password
│   │   ├── main/                # dashboard
│   │   ├── recipe/              # list, form, detail
│   │   ├── work_order/          # list, form, detail
│   │   └── report/              # delivery_report (PDF 独立 HTML)
│   ├── static/
│   │   ├── css/style.css        # 自定义样式 + 平板触控优化
│   │   └── js/app.js            # 确认对话框 + AJAX
│   └── translations/            # i18n 翻译文件
│       ├── en/LC_MESSAGES/      # 英文
│       └── ja/LC_MESSAGES/      # 日文
├── migrations/                  # Flask-Migrate 自动生成
├── instance/
│   └── wafercut.db              # SQLite 数据库
└── tasks/
    ├── todo.md                  # 当前任务进度
    └── lessons.md               # 踩坑记录
```

### 当前阶段
**研究规划已完成，待开始实现。** 详见 `docs/architecture-and-research.md`。

10 步构建计划：
1. ☐ 项目骨架 + 配置 (~220 LOC)
2. ☐ 数据模型 (~215 LOC)
3. ☐ 认证蓝图 (~510 LOC)
4. ☐ 参数库蓝图 (~385 LOC)
5. ☐ 工单蓝图 + 状态机 (~595 LOC)
6. ☐ 仪表盘 (~130 LOC)
7. ☐ PDF 报告 (~185 LOC)
8. ☐ 国际化 (~300 LOC)
9. ☐ 部署脚本 (~115 LOC)
10. ☐ 集成测试与打磨

进度跟踪: `tasks/todo.md`

---

## 开发者背景

我不是专业开发者，使用 Claude Code 辅助编程。请：
- 代码加中文注释，关键逻辑额外解释
- 遇到复杂问题先给方案让我确认，不要直接大改
- 报错时解释原因 + 修复方案，不要只贴代码
- 优先最简实现，不要过度工程化

---

## 项目专属规则

### 数据库相关
- SQLite 必须启用 WAL 模式 + `PRAGMA foreign_keys=ON` + `PRAGMA busy_timeout=5000`
- Flask-Migrate 的 `env.py` 必须配置 `render_as_batch=True`（SQLite ALTER TABLE 限制）
- 工单号格式: `WO-YYYYMMDD-XXXX`，同日序号自增

### Recipe 版本化
- 单表设计，`recipe_group_id` 分组 + `version` 自增
- 编辑 = 复制所有字段到新行（version+1），旧行 `is_active=False`
- 工单通过 `recipes.id`（PK）绑定不可变版本，**绝不通过 group_id 绑定**

### 状态机
- 6 个线性状态: incoming → filming → cutting → cleaning → inspection → completed
- 1 个特殊状态: exception_hold（任意状态可进入，恢复到 previous_status 的下一个状态）
- 用 Python dict 实现，不引入外部状态机库

### 多语言 (i18n)
- 所有用户可见字符串用 `_()` 或 `gettext()` 包裹
- 表单标签用 `lazy_gettext()`
- 中文是源码默认语言，只需翻译 en/ja
- 语言选择存 `session['language']`

### PDF 生成
- PDF 模板用独立 HTML（不继承 base.html）
- CSS 中字体用 `url()` 不用 `local()`，防止 CJK 乱码
- A4 页面: `@page { size: A4; margin: 20mm; }`
- 仅完成状态的工单可生成 PDF

### 前端
- Bootstrap 5 通过 CDN 引入
- 平板触控优化: 按钮/链接最小 44px 触控目标
- 响应式: 优先适配 iPad (768px-1024px)

### 角色权限
- `admin`: 用户管理、Recipe 创建/编辑、所有工单操作
- `operator`: 工单创建/状态推进/检验填写，Recipe 只读
- 用 `@role_required('admin')` 装饰器控制

---

## 上下文管理规范（核心）

### 1. 文件行数硬限制

| 文件类型 | 最大行数 | 超限动作 |
|----------|----------|----------|
| 单个源代码文件 | **200 行** | 立即拆分为多个文件 |
| 单个模块（目录内所有文件） | **2000 行** | 拆分为子模块 |
| 测试文件 | **300 行** | 按功能拆分测试文件 |
| 配置文件 | **100 行** | 拆分为多个配置文件 |

**每次创建或修改文件后，检查行数。接近限制时主动提醒我。**

### 2. 每个目录必须有 README.md

当一个目录下有 3 个以上文件时，创建 `README.md`，内容：
```markdown
# 目录名

## 用途
一句话说明这个目录做什么。

## 文件清单
- `xxx.py` — 做什么（~行数）
- `yyy.py` — 做什么（~行数）

## 依赖关系
- 本目录依赖：xxx 模块
- 被以下模块依赖：yyy
```

### 3. 定期清理（每 2-3 天新功能开发后执行一次）

当我说 **"清理一下"** 时，执行以下检查：

1. **行数审计**：列出所有超过 150 行的文件，建议拆分方案
2. **死代码检测**：找出没有被 import/调用的函数和文件
3. **TODO 清理**：列出所有 TODO/FIXME/HACK 注释，建议处理方案
4. **一次性脚本**：找出不属于正式功能的临时脚本，建议删除
5. **描述同步**：检查 CLAUDE.md 的项目结构是否与实际目录一致，不一致则更新
6. **依赖检查**：requirements.txt 中有无未使用的依赖

---

## Sub-Agent 并行调度规则

### 什么时候并行

**并行派遣**（所有条件满足时）：
- 3+ 个不相关任务
- 不操作同一个文件
- 无输入输出依赖

**顺序派遣**（任一条件触发时）：
- B 需要 A 的输出
- 操作同一文件（合并冲突风险）
- 范围不明确

### Sub-Agent 调用要求

每次派遣 sub-agent 必须指明：
1. 操作哪些文件（写）
2. 读取哪些文件（只读）
3. 完成标准是什么
4. 不许碰哪些文件

### 后台 Agent

研究/分析类任务（不修改文件的）应该后台运行，不阻塞主对话。

---

## 编码规范

### 错误处理
- 所有外部调用（API、文件 IO、数据库）必须 try-except
- 失败时 graceful degradation：显示友好提示 + 使用缓存/默认值，不崩溃
- 日志记录错误详情，但不向用户暴露堆栈信息

### 函数设计
- 单个函数不超过 30 行（超过就拆）
- 函数名用动词开头：`get_prices()`, `parse_feed()`, `calculate_spread()`
- 每个函数有 docstring，说明输入输出和可能的异常

### 依赖管理
- 不要自行引入新依赖。需要新库时先问我
- 优先使用标准库，其次是项目已有的依赖（见技术栈）
- 每次新增依赖立即更新 requirements.txt

### 配置管理
- 敏感信息（SECRET_KEY、密码）放 `.env`，通过环境变量读取
- 非敏感配置放 `config.py` 的配置类中
- 绝不在代码中硬编码任何密钥

### 代码注释
- 注释用中文（项目面向中国团队）
- 关键逻辑额外解释 why，不只注释 what
- 所有可翻译字符串用 `_()` 包裹

---

## Git 规范

### Commit 信息格式
```
<类型>: <一句话描述>

类型：feat(新功能) | fix(修复) | refactor(重构) | docs(文档) | chore(杂项)
```

### 每次 commit 前
- 确认没有把 .env、instance/、__pycache__/ 提交进去
- 确认代码能正常运行（至少不报错）

---

## 沟通规范

### 当你（AI）不确定时
- **直接说不确定**，不要编造
- 给出 2-3 个可能的方案让我选
- 标明每个方案的优缺点

### 当任务太大时
- 不要一口气全做完
- 先给出拆分计划，让我确认后再逐步执行
- 每完成一步告诉我进度

### 当代码出问题时
- 先说是什么问题（一句话）
- 再说为什么出了这个问题（原因分析）
- 最后给修复方案

### 当我说以下关键词时
| 我说 | 你做 |
|------|------|
| "清理一下" | 执行上面的定期清理流程 |
| "拆一下" | 检查指定文件/模块的行数，给出拆分方案 |
| "健康检查" | 运行完整的项目健康度检查 |
| "现在到哪了" | 总结当前进度，参考 tasks/todo.md |
| "省着点" | 减少 token 消耗：回复更简短、不重复输出完整文件 |
| "全力跑" | 可以并行、可以大改、不用每步确认 |

---

## 性能优化规范

### Token 节省策略
1. 修改文件时只输出变更部分，不要重复输出整个文件
2. 如果我只问一个简单问题，不要把相关代码全部贴出来
3. 长文件只输出相关函数，不要全文输出
4. 使用 `// ... existing code ...` 标记未修改部分

### 上下文保鲜策略
1. 对话超过 20 轮后，主动建议 `/compact` 压缩上下文
2. 切换到完全不同的模块时，建议开新 session
3. 需要大量探索代码库时，使用 sub-agent
4. Debug 时使用 Explore sub-agent 搜索代码

---

## 关键参考文档

- **架构设计与技术研究**: `docs/architecture-and-research.md` — 包含数据库设计、状态机、版本化方案、部署方案等所有技术决策的详细研究
- **任务进度**: `tasks/todo.md`
- **踩坑记录**: `tasks/lessons.md`
