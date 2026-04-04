# WaferCut MES - 架构设计与技术研究文档

> 生成日期: 2026-04-04
> 项目: 晶圆切割代工厂管理系统 (WaferCut MES)
> 技术栈: Python 3.10+ / Flask / SQLite / Bootstrap 5 / WeasyPrint / Flask-Babel

---

## 目录

1. [项目概述与需求](#1-项目概述与需求)
2. [项目结构设计](#2-项目结构设计)
3. [数据库设计](#3-数据库设计)
4. [Recipe 版本化方案研究](#4-recipe-版本化方案研究)
5. [工单状态机设计](#5-工单状态机设计)
6. [WeasyPrint CJK PDF 方案研究](#6-weasyprint-cjk-pdf-方案研究)
7. [Flask-Babel 国际化方案](#7-flask-babel-国际化方案)
8. [Flask Application Factory 最佳实践](#8-flask-application-factory-最佳实践)
9. [部署方案研究](#9-部署方案研究)
10. [路由与表单设计](#10-路由与表单设计)
11. [分步构建计划](#11-分步构建计划)
12. [依赖清单](#12-依赖清单)
13. [风险与应对](#13-风险与应对)
14. [验证计划](#14-验证计划)

---

## 1. 项目概述与需求

### 1.1 业务目标
为晶圆切割代工厂建设 MES 生产管理系统，管理切割参数(Recipe)、工单流转、交付报告。

### 1.2 技术栈
- 后端: Python 3.10+ / Flask / Flask-SQLAlchemy / SQLite
- 前端: Bootstrap 5 (响应式，适配平板)
- PDF: Flask-WeasyPrint
- 多语言: Flask-Babel (中文/英文/日文，默认中文)
- 部署: Ubuntu 24.04 / Gunicorn / Nginx / systemd
- 数据库迁移: Flask-Migrate

### 1.3 第一期功能范围
- **用户与权限**: Flask-Login 认证，admin/operator 角色，操作日志
- **切割参数库 (Recipe)**: CRUD + 版本管理 + 材料/尺寸筛选
- **工单管理**: 创建/状态流转/分页筛选/Dashboard
- **交付报告 PDF**: 一键生成，跟随界面语言

### 1.4 代码规范
- 所有可翻译字符串用 `_()` 或 `gettext()` 包裹
- 表单使用 WTForms 做后端验证
- 前端表单加 HTML5 验证 (required, min, max)
- 统一 API 响应格式 (AJAX 场景)
- 代码注释用英文

### 1.5 预估代码量
约 **2,700 行** (Python + HTML + CSS + JS + Shell)

---

## 2. 项目结构设计

```
E:/claude_ask/company_helper_/
├── config.py                    # 配置类 (Dev/Prod/Test)
├── wsgi.py                      # Gunicorn 入口: from app import create_app; app = create_app()
├── .flaskenv                    # FLASK_APP=wsgi.py, FLASK_ENV=development
├── requirements.txt             # 依赖锁定
├── babel.cfg                    # Babel 提取配置 (Jinja2 + Python)
├── deploy.sh                    # Ubuntu 一键部署脚本
├── backup.sh                    # SQLite 每日备份脚本
├── docs/
│   └── architecture-and-research.md  # 本文档
├── app/
│   ├── __init__.py              # create_app() 工厂函数
│   ├── extensions.py            # db, login_manager, babel, migrate, csrf 实例化
│   ├── models/
│   │   ├── __init__.py          # 导入所有模型 (供 Alembic 发现)
│   │   ├── user.py              # User 模型 + 密码哈希
│   │   ├── recipe.py            # Recipe 模型 + 版本分组
│   │   ├── work_order.py        # WorkOrder + WorkOrderStatusLog 模型
│   │   └── audit_log.py         # AuditLog 模型 + log_action() 工具函数
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── auth.py              # LoginForm, UserCreateForm, UserEditForm, ChangePasswordForm
│   │   ├── recipe.py            # RecipeForm (全部切割参数字段)
│   │   └── work_order.py        # WorkOrderCreateForm, StatusChangeForm, InspectionForm
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── decorators.py        # @role_required('admin'), @audit_action(...)
│   │   ├── state_machine.py     # WorkOrderStatus 枚举 + VALID_TRANSITIONS + transition()
│   │   └── helpers.py           # generate_order_number(), api_response(), 分页辅助
│   ├── blueprints/
│   │   ├── auth/                # 认证蓝图
│   │   │   ├── __init__.py      # Blueprint 注册
│   │   │   └── routes.py        # 登录/登出/用户 CRUD (~110 LOC)
│   │   ├── main/                # 仪表盘蓝图
│   │   │   ├── __init__.py
│   │   │   └── routes.py        # Dashboard + 语言切换 (~55 LOC)
│   │   ├── recipe/              # 参数库蓝图
│   │   │   ├── __init__.py
│   │   │   └── routes.py        # CRUD + 版本历史 + 筛选 (~130 LOC)
│   │   ├── work_order/          # 工单蓝图
│   │   │   ├── __init__.py
│   │   │   └── routes.py        # CRUD + 状态流转 + 检验 (~180 LOC)
│   │   └── report/              # 报告蓝图
│   │       ├── __init__.py
│   │       └── routes.py        # PDF 生成端点 (~60 LOC)
│   ├── templates/
│   │   ├── base.html            # Bootstrap 5 基础布局 + 导航栏 + 语言切换 + Flash (~120 LOC)
│   │   ├── _macros.html         # Jinja2 宏: render_field, pagination, flash (~60 LOC)
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   ├── users.html
│   │   │   ├── user_form.html
│   │   │   └── change_password.html
│   │   ├── main/
│   │   │   └── dashboard.html   # 统计卡片 + 最近工单表
│   │   ├── recipe/
│   │   │   ├── list.html        # 配方列表 + 筛选
│   │   │   ├── form.html        # 创建/编辑表单
│   │   │   └── detail.html      # 查看配方 + 版本历史
│   │   ├── work_order/
│   │   │   ├── list.html        # 工单列表 + 分页/筛选/搜索
│   │   │   ├── form.html        # 创建/编辑工单
│   │   │   └── detail.html      # 工单详情 + 状态时间线 + 状态变更表单
│   │   └── report/
│   │       └── delivery_report.html  # PDF 模板 (独立 HTML，不继承 base.html)
│   ├── static/
│   │   ├── css/style.css        # 自定义样式 + 平板触控优化 (~80 LOC)
│   │   └── js/app.js            # 确认对话框 + AJAX 辅助 (~60 LOC)
│   └── translations/
│       ├── en/LC_MESSAGES/messages.po  # 英文翻译
│       └── ja/LC_MESSAGES/messages.po  # 日文翻译
├── migrations/                  # Flask-Migrate 自动生成
└── instance/
    └── wafercut.db              # SQLite 数据库文件 (运行时生成)
```

---

## 3. 数据库设计

### 3.1 users 表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| username | VARCHAR(64) | UNIQUE NOT NULL | 登录名 |
| password_hash | VARCHAR(256) | NOT NULL | werkzeug generate_password_hash |
| display_name | VARCHAR(64) | NOT NULL | UI 显示名 |
| role | VARCHAR(16) | NOT NULL DEFAULT 'operator' | 'admin' 或 'operator' |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | 软禁用 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | |

### 3.2 recipes 表 (版本化单表设计)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | 不可变行 ID，工单 FK 引用此字段 |
| recipe_group_id | INTEGER | NOT NULL INDEX | 同一配方的所有版本共享此 ID |
| version | INTEGER | NOT NULL DEFAULT 1 | 组内自增 |
| wafer_material | VARCHAR(64) | NOT NULL | 材料类型 (Silicon, SiC, GaN 等) |
| wafer_size | VARCHAR(32) | NOT NULL | 晶圆尺寸 (4/6/8/12 inch) |
| thickness | FLOAT | NOT NULL | 晶圆厚度 (um) |
| blade_model | VARCHAR(64) | NOT NULL | 刀片型号 |
| spindle_speed | INTEGER | NOT NULL | 主轴转速 (RPM) |
| feed_rate | FLOAT | NOT NULL | 进给速度 (mm/s) |
| cut_depth | FLOAT | NOT NULL | 切割深度 (um) |
| coolant_flow | FLOAT | NOT NULL | 冷却水流量 (L/min) |
| max_chipping | FLOAT | NOT NULL | 最大允许崩边 (um) |
| notes | TEXT | NULLABLE | 备注 |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | 最新版本 = active |
| created_by | INTEGER | FK → users.id | 创建者 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | |

**约束:**
- `UNIQUE(recipe_group_id, version)` — 同组内版本号唯一
- `INDEX(wafer_material, wafer_size)` — 筛选查询加速

### 3.3 work_orders 表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| order_number | VARCHAR(20) | UNIQUE NOT NULL | 格式: WO-YYYYMMDD-XXXX |
| customer | VARCHAR(128) | NOT NULL | 客户名 |
| wafer_spec | VARCHAR(256) | NOT NULL | 晶圆规格 (自由文本) |
| quantity | INTEGER | NOT NULL | 片数 |
| recipe_id | INTEGER | FK → recipes.id NOT NULL | 绑定到具体版本的配方 |
| status | VARCHAR(32) | NOT NULL DEFAULT 'incoming' | 当前状态 (枚举) |
| previous_status | VARCHAR(32) | NULLABLE | 进入异常挂起时保存前状态 |
| operator_id | INTEGER | FK → users.id | 操作员 |
| yield_rate | FLOAT | NULLABLE | 良率 (%) |
| max_chipping_actual | FLOAT | NULLABLE | 崩边实测值 (um) |
| inspection_result | VARCHAR(16) | NULLABLE | 'pass' 或 'fail' |
| inspection_notes | TEXT | NULLABLE | 检验备注 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | |
| completed_at | DATETIME | NULLABLE | 完成时间 |

### 3.4 work_order_status_logs 表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| work_order_id | INTEGER | FK → work_orders.id NOT NULL | |
| from_status | VARCHAR(32) | NOT NULL | 变更前状态 |
| to_status | VARCHAR(32) | NOT NULL | 变更后状态 |
| operator_id | INTEGER | FK → users.id NOT NULL | 操作员 |
| notes | TEXT | NULLABLE | 备注 (进入异常时必填) |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | |

### 3.5 audit_logs 表

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK AUTOINCREMENT | |
| user_id | INTEGER | FK → users.id NULLABLE | NULL = 系统操作 |
| action | VARCHAR(64) | NOT NULL | create/update/delete/login/status_change |
| target_type | VARCHAR(64) | NOT NULL | work_order/recipe/user |
| target_id | INTEGER | NULLABLE | 目标对象 ID |
| details | TEXT | NULLABLE | JSON 格式变更详情 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | |

**索引:** `INDEX(target_type, target_id)`, `INDEX(user_id)`, `INDEX(created_at)`

---

## 4. Recipe 版本化方案研究

### 4.1 三种方案对比

#### 方案 A: 单表 + (recipe_id, version) 复合键
- 每个版本是一个完整行副本
- **优点**: 最简单，无需 JOIN，查询直观，每个版本自包含
- **缺点**: 数据重复 (改一个参数复制其余所有); schema 变更影响所有版本
- **适用**: 参数列较少 (<50 列) 且追求查询简洁的系统

#### 方案 B: 分表 recipe_master + recipe_versions
- master 表存身份信息，versions 表存参数
- **优点**: 身份与历史分离; master 表保存不变元数据; 标准 MES/ERP 模式
- **缺点**: 需要 JOIN; 插入逻辑稍复杂 (需更新 master 的 current_version)
- **适用**: 有大量不变元数据或预期扩展审批流程的系统

#### 方案 C: 时态表 (valid_from / valid_to)
- 用时间范围标识版本
- **优点**: 天然支持 "T 时刻的配方是什么" 查询
- **缺点**: SQLite **无原生时态表支持**; 查询复杂; 工单引用脆弱; 时区问题
- **适用**: 有强监管要求 (制药/航空) 的系统，对 SQLite 项目过度复杂

### 4.2 最终选择: 方案 A (单表设计)

**理由:**
- 晶圆切割配方的参数列数量适中 (~15 列)，数据重复代价很小
- 无需 JOIN，查询最简单，适合 SQLite 小型系统
- `recipe_group_id` 分组 + `version` 自增，逻辑清晰
- 工单通过 `recipes.id` (PK) 不可变绑定到具体版本

### 4.3 版本号安全自增

```sql
INSERT INTO recipes (recipe_group_id, version, ...)
VALUES (
  :recipe_group_id,
  (SELECT COALESCE(MAX(version), 0) + 1 FROM recipes WHERE recipe_group_id = :group_id),
  ...
);
```

**为什么在 SQLite 中安全:** SQLite WAL 模式下同时只有一个写入者，SELECT 子查询和 INSERT 在单语句内是原子的，无竞态条件。加 `UNIQUE(recipe_group_id, version)` 约束作为最后防线。

### 4.4 工单引用的参照完整性

- 工单通过 `FK(recipe_id) → recipes.id` 引用具体版本，不是 recipe_group_id
- Recipe 版本一旦创建就**永不 UPDATE**，只追加新版本
- FK 约束默认 RESTRICT 行为，防止删除被工单引用的配方版本
- **不要**在工单表中复制参数副本 — 总是 JOIN 到 recipes 表获取参数

### 4.5 版本变更历史/Diff

- **主方案**: 运行时计算 diff (对比两个版本行的各字段值)
- **辅助**: 创建新版本时，在应用层生成变更记录存入 audit_logs (JSON 格式)
- 包含 `change_reason` 字段让工程师记录变更原因 (质量审计和 ISO 合规)

---

## 5. 工单状态机设计

### 5.1 三种实现方案对比

#### 方案 A: 简单 Enum + Dict (无外部库)
- Python Enum 定义状态, dict 定义合法转换
- **优点**: 零依赖, ~40 行代码, 任何人 5 分钟内看懂, 完全控制
- **缺点**: 需自写校验/回调/错误消息; 无内置可视化
- **适用**: 状态少 (<20), 流转简单的系统

#### 方案 B: `pytransitions` 库
- 5.6k GitHub stars, 提供 `add_ordered_transitions()` 专用于线性流程
- **优点**: 内置无效转换异常; 支持条件守卫; 有 GUI 扩展
- **缺点**: 异常挂起/恢复模式**不原生支持**, 仍需自定义 previous_status; 对 7 个状态过度设计

#### 方案 C: `python-statemachine` 库
- 声明式类 API, 继承 StateMachine
- **优点**: 语法清晰, 强验证器/守卫系统
- **缺点**: 同方案 B, 异常挂起仍需自定义处理; 类继承结构对简单流程过重

### 5.2 最终选择: 方案 A (Enum + Dict)

**理由:**
- 6 个线性状态 + 1 个异常分支，是最简单的状态机之一
- 异常挂起/恢复需要 `previous_status` 字段，任何方案都需要自定义
- 零依赖 = 零升级风险
- 制造系统追求**简单性和明确性**, 每个开发者应能 5 分钟内理解状态机

### 5.3 状态流转定义

```python
from enum import Enum

class WorkOrderStatus(str, Enum):
    INCOMING = 'incoming'           # 来料
    FILMING = 'filming'             # 贴膜
    CUTTING = 'cutting'             # 切割
    CLEANING = 'cleaning'           # 清洗
    INSPECTION = 'inspection'       # 检验
    COMPLETED = 'completed'         # 完成
    EXCEPTION_HOLD = 'exception_hold'  # 异常挂起

VALID_TRANSITIONS = {
    'incoming':       ['filming', 'exception_hold'],
    'filming':        ['cutting', 'exception_hold'],
    'cutting':        ['cleaning', 'exception_hold'],
    'cleaning':       ['inspection', 'exception_hold'],
    'inspection':     ['completed', 'exception_hold'],
    'completed':      [],
    'exception_hold': []   # 恢复逻辑单独处理
}

STATUS_ORDER = ['incoming', 'filming', 'cutting', 'cleaning', 'inspection', 'completed']
```

### 5.4 异常挂起/恢复逻辑

- **进入异常**: 保存 `current_status` 到 `previous_status`, 然后设 `status = exception_hold`
- **恢复**: 读取 `previous_status`, 在 `STATUS_ORDER` 中找到下一个状态作为恢复目标, 清除 `previous_status`
- 进入异常时 **notes 必填** — 操作员必须解释原因
- 异常挂起**只能**恢复到 `previous_status` 对应的下一个状态, 不能跳转到任意状态

### 5.5 transition() 函数设计

```python
def transition(work_order, new_status, operator_id, notes=None):
    """Validate and execute state transition. Returns (success, error_message)."""
    # 1. 检查 new_status 是否在 VALID_TRANSITIONS[work_order.status] 中
    #    (或处理 exception_hold 恢复逻辑)
    # 2. 进入 exception_hold 时保存 previous_status
    # 3. 创建 WorkOrderStatusLog 记录
    # 4. 创建 AuditLog 记录
    # 5. 转换到 completed 时设置 completed_at
    # 6. 返回 (success, error_message) 元组
```

### 5.6 多层防护

| 层级 | 职责 |
|------|------|
| **模型层** (transition 函数) | 权威校验源, 验证转换合法性, 抛出 InvalidTransitionError |
| **API 层** (路由) | 捕获错误, 返回友好 HTTP 响应 (400 + 错误消息) |
| **UI 层** (模板) | 只显示当前状态的合法 "下一步" 按钮 |

### 5.7 状态进度条 UI (Bootstrap 5)

- 使用 `<ol>` + flexbox 布局的自定义步进器
- 已完成步骤: 绿色填充圆 + 勾选图标
- 当前步骤: 蓝色高亮 + 可选脉冲动画
- 待处理步骤: 灰色空心圆
- 异常挂起: 橙色警告色 + 感叹号图标
- 移动端 (<500px): 切换为垂直时间线或折叠显示
- 约 30 行自定义 CSS, 无需额外库

---

## 6. WeasyPrint CJK PDF 方案研究

### 6.1 CJK 字体选择

**推荐: Noto Sans CJK (Google) / Source Han Sans (Adobe)**

这两个是同一字体家族, 以不同名字发布:
- 覆盖简体中文 (SC), 繁体中文 (TC), 日文 (JP), 韩文 (KR)
- 包含拉丁/英文字形, 单一字体家族处理所有三种文字
- 7 种字重 (Thin - Black)
- 最新版本: 2.004

**字体文件大小 (性能关键):**
| 类型 | 大小 |
|------|------|
| 全语言静态字体 (所有字重) | ~593 MB |
| 单语言 Variable OTF | ~8 MB |
| 语言专属 Subset OTF (单字重, 如 NotoSansCJKsc-Regular.otf) | ~15-17 MB |

**建议**: 使用**语言专属 Subset OTF** 而非全语言字体, 大幅减小文件体积并提升渲染性能。

### 6.2 CSS @font-face 嵌入

**关键发现: 使用 `url()` 而非 `local()`**

使用 `local()` 加载 CJK 字体在 WeasyPrint 中会导致乱码 (mojibake)。使用 `url()` 配合直接文件路径可正常工作。

```css
@font-face {
    font-family: 'Noto Sans CJK SC';
    src: url('/path/to/NotoSansCJKsc-Regular.otf') format('opentype');
    font-weight: 400;
    font-style: normal;
}
```

**FontConfiguration 必须:**
```python
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

font_config = FontConfiguration()
css = CSS(string='@font-face { ... }', font_config=font_config)
html.write_pdf(stylesheets=[css], font_config=font_config)
```

WeasyPrint 自动将字体嵌入 PDF 并做子集化 (只包含实际使用的字形), 即使源字体很大输出 PDF 也不会膨胀。

### 6.3 Ubuntu 24.04 字体安装

```bash
sudo apt-get update
sudo apt-get install -y \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fontconfig \
    libharfbuzz-subset0 \
    libpango-1.0-0

fc-cache -fv  # 重建字体缓存
```

| 包名 | 作用 |
|------|------|
| `fonts-noto-cjk` | Noto Sans/Serif CJK 字体 |
| `fonts-noto-cjk-extra` | 额外字重 (Regular/Bold 之外) |
| `fontconfig` | 字体配置和发现 (WeasyPrint 通过 Pango 依赖) |
| `libharfbuzz-subset0` | HarfBuzz 子集化库, WeasyPrint 优先使用 (比 fontTools 快很多) |

### 6.4 PDF 模板最佳实践

#### A4 页面设置
```css
@page {
    size: A4;                          /* 210mm x 297mm */
    margin: 20mm 15mm 25mm 15mm;       /* top right bottom left */
}
@page :first {
    margin-top: 10mm;
}
```

#### 表格处理
```css
table { width: 100%; border-collapse: collapse; }
thead { display: table-header-group; }       /* 每页重复表头 */
tr    { page-break-inside: avoid; }          /* 不拆分行 */
```

#### 公司 Logo
- 使用文件路径 (绝对或相对于 base_url), **不用 base64 编码**
- base64 图片在某些 WeasyPrint 版本中导致 PDF 体积增大 30x
- Flask 中使用 `url_for('static', filename='img/logo.png')`

#### 签名区域
- WeasyPrint **不支持** PDF 表单字段或数字签名
- 用 CSS 创建视觉签名框 (边框 + 占位文字 "授权签名")
- 如需实际数字签名, 后处理 PDF 使用 `pyhanko` 或 `endesive`

### 6.5 CJK 性能问题

**已知问题** (WeasyPrint Issue #2120): CJK 字体导致 PDF 生成速度约慢 **6 倍**。

| 优化措施 | 效果 |
|----------|------|
| 安装 HarfBuzz 子集化 (`libharfbuzz-subset0`) | 显著加速子集化过程 |
| 使用语言专属 Subset OTF | 源字体小 = 子集化快 |
| 应用层缓存生成的 PDF | 重复请求零等待 |
| 异步生成 (Celery) | 不阻塞 HTTP 请求 |
| 控制文档长度 | 避免超长表格 (5000 行会有内存问题) |

**预期性能:**
- 优化后 (HarfBuzz + Subset 字体): 1-3 页报告约 **2-5 秒**
- 未优化 (全语言字体 + fontTools): 约 **10-30 秒**

### 6.6 PDF 模板结构

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: A4; margin: 20mm; }
        @font-face {
            font-family: 'Noto Sans CJK SC';
            src: url('/path/to/NotoSansCJKsc-Regular.otf') format('opentype');
        }
        body {
            font-family: 'Noto Sans CJK SC', sans-serif;
            font-size: 10pt;
        }
    </style>
</head>
<body>
    <!-- 公司 Header + Logo -->
    <!-- 报告编号 + 日期 -->
    <!-- 客户信息表格 -->
    <!-- 晶圆规格 + 切割参数表格 -->
    <!-- 检验结果: 良率, 崩边, pass/fail, 备注 -->
    <!-- 操作员签名区 (空白行) -->
    <!-- Footer -->
</body>
</html>
```

---

## 7. Flask-Babel 国际化方案

### 7.1 目录结构

```
app/translations/
├── en/LC_MESSAGES/
│   ├── messages.po    # 英文翻译 (手工/预翻译)
│   └── messages.mo    # 编译后的二进制文件
└── ja/LC_MESSAGES/
    ├── messages.po    # 日文翻译
    └── messages.mo
```

中文为默认语言, 直接从源码提取, 不需要单独翻译目录。

### 7.2 lazy_gettext vs gettext

| 场景 | 使用 |
|------|------|
| 请求上下文内 (路由函数, 模板) | `gettext()` 即 `_()` |
| 模块级字符串 (表单默认消息, 类属性) | `lazy_gettext()` 即 `_l()` |
| Flash 消息 | `gettext()` |
| 表单标签 | `lazy_gettext()` |

**关键**: `lazy_gettext()` 在**实际使用时** (转为字符串时) 才求值, 不是定义时。在模板 `render_template()` 中使用时, 会在渲染时正确求值。

### 7.3 Babel 工作流

```bash
# babel.cfg 配置
[python: **.py]
[jinja2: **/templates/**.html]

# 提取字符串
pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .

# 初始化语言
pybabel init -i messages.pot -d app/translations -l en
pybabel init -i messages.pot -d app/translations -l ja

# 翻译 .po 文件 (手工或自动化)

# 编译
pybabel compile -d app/translations

# 代码变更后更新
pybabel update -i messages.pot -d app/translations
```

### 7.4 语言切换

```python
# Flask-Babel 4.x: 通过 init_app 参数注册 locale_selector
# babel.init_app(app, locale_selector=get_locale)
def get_locale():
    return session.get('language', 'zh')

# 语言切换路由
@main_bp.route('/set-language/<lang>')
def set_language(lang):
    if lang in app.config['BABEL_SUPPORTED_LOCALES']:
        session['language'] = lang
    return redirect(request.referrer or url_for('main.dashboard'))
```

### 7.5 PDF 中的国际化

- PDF 在 Flask 请求内生成, `render_template()` 使用当前请求的 locale
- 如需强制指定语言: 使用 `flask_babel.force_locale()` 上下文管理器
- **注意**: 不要在 `force_locale` 块内调用 `flask_babel.refresh()` — 会过早恢复强制的 locale

---

## 8. Flask Application Factory 最佳实践

### 8.1 两步扩展初始化

在 `extensions.py` 中创建模块级对象, 在工厂函数中初始化:

```python
# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_babel import Babel
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
babel = Babel()
migrate = Migrate()
csrf = CSRFProtect()
```

### 8.2 create_app() 工厂函数

```python
# app/__init__.py
def create_app(config_class=None):
    app = Flask(__name__)
    app.config.from_object(config_class or 'config.DevelopmentConfig')

    # 注册扩展
    db.init_app(app)
    login_manager.init_app(app)
    babel.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # SQLite WAL 模式 + 外键
    from sqlalchemy import event
    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    # 注册蓝图
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.recipe import recipe_bp
    from app.blueprints.work_order import work_order_bp
    from app.blueprints.report import report_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(recipe_bp)
    app.register_blueprint(work_order_bp)
    app.register_blueprint(report_bp)

    # Babel locale 选择器 — Flask-Babel 4.x 用 init_app 参数注册
    # babel.init_app(app, locale_selector=get_locale)
    def get_locale():
        return session.get('language', 'zh')

    # CLI: 初始化数据库 + 种子数据
    @app.cli.command('init-db')
    def init_db():
        db.create_all()
        _seed_admin()

    return app
```

### 8.3 配置管理

```python
# config.py
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL',
        'sqlite:///' + os.path.join(basedir, 'instance', 'wafercut.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BABEL_DEFAULT_LOCALE = 'zh'
    BABEL_SUPPORTED_LOCALES = ['zh', 'en', 'ja']
    ITEMS_PER_PAGE = 20

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
```

### 8.4 Flask-Migrate + SQLite 注意事项

**SQLite ALTER TABLE 限制:**
- SQLite 只支持添加/重命名列, 不能删除或修改列
- Flask-Migrate 4.0+ 自动启用 `render_as_batch=True` (Alembic 使用 "移动并复制" 工作流)
- **始终手动审查生成的迁移脚本**
- Alembic 不能自动检测: 表名变更, 列名变更, 未命名约束

```bash
flask db init                          # 初始化迁移目录
flask db migrate -m "initial schema"   # 生成迁移脚本 (需审查!)
flask db upgrade                       # 应用迁移
flask db downgrade                     # 回滚 (如需)
```

### 8.5 WTForms 最佳实践

- **内置验证器**: DataRequired, Length, NumberRange, Regexp, Optional
- **自定义验证器**: 用于业务规则 (如版本唯一性检查)
- **CSRF 保护**: Flask-WTF 自动包含 CSRF token
- **模板渲染**: 使用 Bootstrap 5 的 `is-invalid` / `invalid-feedback` 类

```python
# 示例: Recipe 表单
class RecipeForm(FlaskForm):
    wafer_material = StringField(_l('Material'), validators=[DataRequired()])
    wafer_size = SelectField(_l('Wafer Size'),
        choices=[('4', '4 inch'), ('6', '6 inch'), ('8', '8 inch'), ('12', '12 inch')])
    spindle_speed = IntegerField(_l('Spindle Speed (RPM)'),
        validators=[DataRequired(), NumberRange(min=0, max=100000)])
    # ... 其他字段
```

---

## 9. 部署方案研究

### 9.1 Gunicorn + SQLite 并发

#### 核心问题
SQLite 使用文件级锁定, 默认 journal 模式下写入时阻塞所有读写。多 Gunicorn worker 会导致 `database is locked` 错误。

#### WAL 模式 — 强烈推荐

| 特性 | 说明 |
|------|------|
| 读写并发 | 读者不阻塞写者, 写者不阻塞读者 |
| 写并发 | 仍然只允许一个写者, 但不阻塞读者 |
| 启用方式 | `PRAGMA journal_mode=WAL` (持久化, 只需设一次) |
| busy_timeout | `PRAGMA busy_timeout=5000` (遇锁重试 5 秒) |

#### Worker 数量建议

| 配置 | 安全性 | 适用场景 |
|------|--------|----------|
| `--workers 1 --threads 4` | **最安全** | 单进程多线程, 完全避免多进程竞争 |
| `--workers 2 --threads 2` | 安全 | WAL + busy_timeout 下低中写入负载 |
| `--workers 4` | **有风险** | 仅读密集型, 写密集会频繁锁冲突 |

**最终建议**: `--workers 2` (原需求的 4 降为 2), 配合 WAL + busy_timeout=5000。

#### --preload 标志
- 加载应用代码后再 fork worker, 共享内存 (COW), 减少内存占用
- Flask-SQLAlchemy 默认每请求创建连接, `--preload` **安全**
- 建议使用以节省内存

### 9.2 systemd 服务配置

```ini
[Unit]
Description=WaferCut MES Gunicorn daemon
After=network.target

[Service]
User=wafercut
Group=wafercut
WorkingDirectory=/opt/wafercut
EnvironmentFile=/opt/wafercut/.env
ExecStart=/opt/wafercut/venv/bin/gunicorn \
    --workers 2 \
    --bind unix:/run/wafercut/wafercut.sock \
    --access-logfile /var/log/wafercut/access.log \
    --error-logfile /var/log/wafercut/error.log \
    --timeout 120 \
    "wsgi:app"
ExecReload=/bin/kill -s HUP $MAINPID
RuntimeDirectory=wafercut
Restart=on-failure
RestartSec=5s
SyslogIdentifier=wafercut

# 安全加固
ProtectSystem=full
PrivateTmp=true
NoNewPrivileges=true
ProtectHome=true
ReadWritePaths=/opt/wafercut/instance /var/log/wafercut

[Install]
WantedBy=multi-user.target
```

**重启策略:**
- `Restart=on-failure` (非 `always`) — 配置错误时不会无限重启循环
- `RestartSec=5s` — 5 秒延迟避免密集重启
- 可选: `StartLimitIntervalSec=60`, `StartLimitBurst=5` — 60 秒内失败 5 次则停止重启

**密钥管理:**
- 使用 `EnvironmentFile=/opt/wafercut/.env` + `chmod 600` 保护
- **不要**在 unit 文件中用 `Environment=` 存密钥 (unit 文件全局可读)

### 9.3 Nginx 反向代理

```nginx
upstream wafercut {
    server unix:/run/wafercut/wafercut.sock fail_timeout=0;
}

server {
    listen 80;
    server_name wafercut.lan;

    # 静态文件由 Nginx 直接服务
    location /static/ {
        alias /opt/wafercut/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # 代理到 Gunicorn
    location / {
        proxy_pass http://wafercut;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    # 安全头 (LAN 也需要)
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 隐藏文件禁止访问
    location ~ /\. { deny all; }

    client_max_body_size 16M;
}
```

**Unix Socket vs TCP:**
- Unix socket 优于 TCP (`127.0.0.1:5000`), 避免 TCP 开销
- `RuntimeDirectory=wafercut` 自动创建 `/run/wafercut/` 并设置权限

### 9.4 SQLite 备份策略

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR=/opt/wafercut/backups
DB_PATH=/opt/wafercut/instance/wafercut.db
RETAIN_DAYS=30

mkdir -p "$BACKUP_DIR"

# 使用 sqlite3 .backup 命令 (WAL 安全)
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/wafercut_$(date +%Y%m%d_%H%M%S).db'"

# 压缩备份
gzip "$BACKUP_DIR/wafercut_$(date +%Y%m%d_%H%M%S).db"

# 删除 30 天前的备份
find "$BACKUP_DIR" -name "wafercut_*.db.gz" -mtime +$RETAIN_DAYS -delete

echo "$(date): Backup completed" >> /var/log/wafercut/backup.log
```

**Cron 配置 (每日凌晨 2 点):**
```
0 2 * * * /opt/wafercut/backup.sh
```

**关键**: **永远不要直接复制 SQLite 文件** — 写入进行中可能捕获损坏状态。`sqlite3 .backup` 使用 SQLite 在线备份 API, 正确处理锁定。

### 9.5 LAN 安全措施

**仍然必需:**
| 措施 | 原因 |
|------|------|
| **CSRF 保护** | 浏览器可被跨站请求欺骗 (Flask-WTF CSRFProtect) |
| **Session 安全** | `HTTPONLY=True`, `SAMESITE='Lax'`, 强 SECRET_KEY (32+ 字节) |
| **参数化查询** | SQLAlchemy 默认使用, 防 SQL 注入 |
| **用户认证** | 不依赖 "只有可信人员在网络上" |
| **输入验证** | WTForms 后端验证 + HTML5 前端验证 |

**可放松:**
| 措施 | 说明 |
|------|------|
| HTTPS | LAN 内不强制, 除非数据高度敏感 |
| 严格 CSP | 可比公网应用更宽松 |
| DDoS/Bot 防护 | LAN 无需 |

**Nginx LAN 限制 (如服务器有公网接口):**
```nginx
allow 192.168.0.0/16;
allow 10.0.0.0/8;
allow 172.16.0.0/12;
deny all;
```

### 9.6 deploy.sh 脚本大纲

```bash
#!/bin/bash
set -euo pipefail

APP_DIR=/opt/wafercut
APP_USER=wafercut
VENV=$APP_DIR/venv

# 1. 创建系统用户
# 2. 复制代码到 $APP_DIR
# 3. 创建 venv, 安装 requirements.txt
# 4. 安装系统字体: fonts-noto-cjk + libharfbuzz-subset0
# 5. flask db upgrade (或 flask init-db 首次运行)
# 6. 创建 systemd 服务: wafercut.service
# 7. 创建 nginx 配置: 反代 80 -> unix socket
# 8. 启用并启动服务
# 9. 设置 cron 备份任务
```

---

## 10. 路由与表单设计

### 10.1 Auth 蓝图 `/auth`

| 方法 | 路由 | 函数 | 权限 | 说明 |
|------|------|------|------|------|
| GET/POST | /auth/login | login() | 公开 | 登录表单 |
| GET | /auth/logout | logout() | 已登录 | 登出 |
| GET | /auth/users | user_list() | Admin | 用户列表 |
| GET/POST | /auth/users/create | user_create() | Admin | 创建用户 |
| GET/POST | /auth/users/<id>/edit | user_edit(id) | Admin | 编辑用户 |
| GET/POST | /auth/change-password | change_password() | 已登录 | 修改密码 |

### 10.2 Main 蓝图 `/`

| 方法 | 路由 | 函数 | 权限 | 说明 |
|------|------|------|------|------|
| GET | / | dashboard() | 已登录 | 仪表盘 (统计卡片 + 最近工单) |
| GET | /set-language/<lang> | set_language(lang) | 公开 | 切换语言 (zh/en/ja) |

### 10.3 Recipe 蓝图 `/recipes`

| 方法 | 路由 | 函数 | 权限 | 说明 |
|------|------|------|------|------|
| GET | /recipes/ | recipe_list() | 已登录 | 列表 (每组最新版) + 筛选 |
| GET/POST | /recipes/create | recipe_create() | Admin | 新建配方 (新组) |
| GET | /recipes/<id> | recipe_detail(id) | 已登录 | 查看具体版本 |
| GET/POST | /recipes/<id>/edit | recipe_edit(id) | Admin | 编辑 → 创建新版本 |
| GET | /recipes/group/<gid>/history | recipe_history(gid) | 已登录 | 版本历史 |

### 10.4 WorkOrder 蓝图 `/orders`

| 方法 | 路由 | 函数 | 权限 | 说明 |
|------|------|------|------|------|
| GET | /orders/ | order_list() | 已登录 | 分页列表 + 状态/客户筛选 + 搜索 |
| GET/POST | /orders/create | order_create() | 已登录 | 创建工单 |
| GET | /orders/<id> | order_detail(id) | 已登录 | 详情 + 状态时间线 |
| GET/POST | /orders/<id>/edit | order_edit(id) | 已登录 | 编辑 (仅 incoming 状态) |
| POST | /orders/<id>/status | order_status_change(id) | 已登录 | 推进状态/进入异常 |
| POST | /orders/<id>/resume | order_resume(id) | 已登录 | 从异常恢复 |
| GET/POST | /orders/<id>/inspection | order_inspection(id) | 已登录 | 填写检验数据 |

### 10.5 Report 蓝图 `/reports`

| 方法 | 路由 | 函数 | 权限 | 说明 |
|------|------|------|------|------|
| GET | /reports/delivery/<order_id> | delivery_report(order_id) | 已登录 | 生成下载 PDF |
| GET | /reports/delivery/<order_id>/preview | delivery_report_preview(order_id) | 已登录 | HTML 预览 |

### 10.6 表单定义

#### auth.py
- **LoginForm**: username (StringField, required), password (PasswordField, required)
- **UserCreateForm**: username, display_name, password, password_confirm, role (SelectField: admin/operator)
- **UserEditForm**: display_name, role, is_active (BooleanField)
- **ChangePasswordForm**: old_password, new_password, confirm_password

#### recipe.py
- **RecipeForm**: wafer_material (StringField), wafer_size (SelectField: 4/6/8/12 inch), thickness (FloatField, min=0), blade_model (StringField), spindle_speed (IntegerField, min=0), feed_rate (FloatField, min=0), cut_depth (FloatField, min=0), coolant_flow (FloatField, min=0), max_chipping (FloatField, min=0), notes (TextAreaField)

#### work_order.py
- **WorkOrderCreateForm**: customer (StringField, required), wafer_spec (StringField, required), quantity (IntegerField, min=1), recipe_id (SelectField, 动态填充最新版配方)
- **StatusChangeForm**: notes (TextAreaField, optional)
- **InspectionForm**: yield_rate (FloatField, 0-100), max_chipping_actual (FloatField, min=0), inspection_result (SelectField: pass/fail), inspection_notes (TextAreaField)

所有表单标签使用 `lazy_gettext()`。

---

## 11. 分步构建计划

### Step 1: 项目骨架 + 配置 (~220 LOC)
**文件**: config.py, wsgi.py, .flaskenv, requirements.txt, babel.cfg, app/__init__.py, app/extensions.py
**验证**: `pip install -r requirements.txt && flask run` → 启动无错误, / 返回 404

### Step 2: 数据模型 (~215 LOC)
**文件**: app/models/ (user.py, recipe.py, work_order.py, audit_log.py, __init__.py)
**验证**: `flask shell` → 导入所有模型 → `db.create_all()` 无错误 → `flask db init && flask db migrate && flask db upgrade`

### Step 3: 认证蓝图 (~510 LOC)
**文件**: utils/decorators.py, forms/auth.py, blueprints/auth/, templates/base.html, templates/_macros.html, templates/auth/*, static/css/style.css
**验证**: 登录 admin/changeme → 创建 operator 用户 → 权限控制 → 登出/重登

### Step 4: 参数库蓝图 (~385 LOC)
**文件**: forms/recipe.py, blueprints/recipe/, templates/recipe/*
**验证**: 创建配方 → 编辑产生新版本 → 旧版本只读 → 版本历史 → 材料+尺寸筛选

### Step 5: 工单蓝图 + 状态机 (~595 LOC)
**文件**: utils/state_machine.py, utils/helpers.py, forms/work_order.py, blueprints/work_order/, templates/work_order/*
**验证**: 创建工单 → 完整状态流转 → 异常挂起/恢复 → 分页/筛选 → 工单号格式

### Step 6: 仪表盘 (~130 LOC)
**文件**: blueprints/main/, templates/main/dashboard.html
**验证**: 在制数/完成数/异常数 → 最近工单列表 → 语言切换

### Step 7: PDF 报告 (~185 LOC)
**文件**: blueprints/report/, templates/report/delivery_report.html
**验证**: 完成工单 → 生成 PDF → A4 排版 → CJK 字符正确 → 非完成工单返回 400

### Step 8: 国际化 (~300 LOC 翻译)
**操作**: pybabel extract → init en/ja → 翻译 → compile
**验证**: 切换三种语言 → UI/PDF 都随语言变化

### Step 9: 部署脚本 (~115 LOC)
**文件**: deploy.sh, backup.sh
**验证**: Ubuntu VM → systemd 运行 → Nginx 反代 → 备份 → 崩溃恢复

### Step 10: 集成测试与打磨
全流程: 建单 → 完整流转 → PDF → 多语言 → 平板响应式 → 并发 → 审计日志

---

## 12. 依赖清单

```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
Flask-Babel==4.0.0
Flask-Migrate==4.0.7
WeasyPrint==62.3
gunicorn==22.0.0
python-dotenv==1.0.1
```

---

## 13. 风险与应对

| 风险 | 应对措施 |
|------|----------|
| **WeasyPrint CJK 渲染慢/乱码** | Ubuntu 装 fonts-noto-cjk + libharfbuzz-subset0; CSS 用 `url()` 非 `local()`; Windows 开发需装 GTK |
| **SQLite 并发写锁** | WAL 模式 + busy_timeout=5000 + 2 workers (非 4) |
| **Flask-Babel 4.x API 变化** | `babel.init_app(app, locale_selector=get_locale)` 方式注册, `@babel.localeselector` 已废弃 |
| **Recipe 版本竞态** | SQLite 写锁天然序列化, 事务内操作, UNIQUE 约束兜底 |
| **Flask-Migrate + SQLite ALTER TABLE** | 自动 batch mode (4.0+), 但必须手动审查迁移脚本 |
| **Windows 开发环境** | WeasyPrint 需要 GTK (MSYS2 安装); 或用 Docker |
| **PDF 生成性能** | HarfBuzz 子集化 + Subset 字体 + 应用层缓存; Phase 1 低量级同步即可 |
| **工单号竞态** | SQLite 写锁序列化, generate_order_number() 在请求事务内执行 |

---

## 14. 验证计划

### 14.1 冒烟测试
启动应用 → 登录 → 各页面可访问

### 14.2 Recipe 全流程
创建 → 编辑 (新版本) → 查看历史 → 材料+尺寸筛选 → operator 只读

### 14.3 工单全流程
创建 → 来料 → 贴膜 → 切割 → 清洗 → 检验 (填数据) → 完成 → 生成 PDF

### 14.4 异常流程
任意状态 → 异常挂起 (必填备注) → 恢复 → 继续流转

### 14.5 权限测试
operator 不能管理用户/创建配方; admin 可以; 未登录重定向到登录页

### 14.6 多语言
切换中/英/日 → UI + PDF 均正确显示

### 14.7 响应式
Chrome DevTools iPad 模式 → 布局正常, 触控目标 ≥ 44px

### 14.8 并发
两浏览器窗口同时操作 → 无数据库锁错误

### 14.9 审计日志
检查所有操作 (登录/创建/编辑/状态变更) 都有日志记录

### 14.10 部署验证
systemd 服务运行 → Nginx 反代 → 备份脚本 → 崩溃后自动恢复

---

## 参考资料

### Flask 架构
- [Flask Application Factory Pattern](https://flask.palletsprojects.com/en/stable/patterns/appfactories/)
- [Flask Mega-Tutorial Part XV: Better Application Structure](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xv-a-better-application-structure)

### 数据库与迁移
- [Fixing ALTER TABLE errors with Flask-Migrate and SQLite](https://blog.miguelgrinberg.com/post/fixing-alter-table-errors-with-flask-migrate-and-sqlite)
- [SQLite Concurrency Handling](https://moldstud.com/articles/p-solving-concurrency-challenges-in-multi-user-sqlite-environments)

### 国际化
- [Flask-Babel Documentation](https://python-babel.github.io/flask-babel/)
- [Flask Mega-Tutorial Part XIII: I18n and L10n](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xiii-i18n-and-l10n)

### PDF 生成
- [Flask-WeasyPrint Documentation](https://doc.courtbouillon.org/flask-weasyprint/stable/)
- [WeasyPrint CJK Performance Issue #2120](https://github.com/Kozea/WeasyPrint/issues/2120)
- [Noto CJK GitHub Repository](https://github.com/notofonts/noto-cjk)

### 状态机
- [pytransitions/transitions GitHub](https://github.com/pytransitions/transitions)
- [python-statemachine Documentation](https://python-statemachine.readthedocs.io/en/latest/)

### 部署
- [Flask RBAC Implementation](https://www.permit.io/blog/implement-role-based-access-control-in-flask)
- [WTForms Validation Best Practices](https://flask.palletsprojects.com/en/stable/patterns/wtforms/)
