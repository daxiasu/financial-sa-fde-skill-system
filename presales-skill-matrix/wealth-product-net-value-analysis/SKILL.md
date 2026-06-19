---
name: fund-advisor
version: 5.0.0
description: |
  基金投资智能顾问 — 口语化对话、有温度的陪伴。
  支持：Web UI 交互仪表盘、文件上传持仓识别、持仓分析、基金查询、量化预估、市场行情、新闻资讯、智能对话。
  内置基金经理话术引擎（4,203人）+ 用户量化评估（8维模型）+ 投资心态跟踪。
  截图OCR识别、Word/PDF/Excel/CSV导入、浏览器链接爬取、Excel/CSV表格导出、客户持仓仓库。
  触发词：客户经理、持仓怎么样、亏了、推荐基金、晚报、周报、PPT报告、量化分析、导入持仓、导出Excel、启动Web、Web界面、上传持仓
author: 个人开发者
tags:
  - 基金
  - 基金经理
  - 投资顾问
  - 量化分析
  - A股
  - 投资组合
  - 业绩跟踪
  - 财经新闻
  - 止盈止损
  - Web UI
  - 市场行情
  - 智能对话
  - 文件上传
  - 持仓识别
triggers:
  - 客户经理
  - 持仓怎么样
  - 亏了
  - 推荐基金
  - 晚报
  - 周报
  - PPT报告
  - 量化分析
  - 导入持仓
  - 导出Excel
  - 启动Web
  - Web界面
  - 基金查询
  - 市场行情
  - 净值走势
  - 上传持仓
  - 上传截图
  - 上传文件
---

# 基金投资AI客户经理

> 口语化对话 | 有温度的辅助 | 专业投顾建议 | 量化分析支持 | Web UI 仪表盘 | 文件上传持仓识别

---

## 快速启动

```bash
# 安装依赖
pip install requests beautifulsoup4 akshare pandas python-dateutil openpyxl flask flask-cors
```

**使用方式：**

| 方式 | 操作 | 适用场景 |
|------|------|---------|
| **Web UI** | 调用 `launch_web_ui` 或 `python scripts/web_server.py` → 浏览器打开 http://localhost:5002 | 可视化交互、文件上传、图表展示 |

---

## Web UI 交互仪表盘（v5.0）

> 浏览器访问 http://localhost:5002，6大功能模块一站式交互。

### 启动方式

| 方式 | 操作 | 说明 |
|------|------|------|
| MCP 工具 | 调用 `launch_web_ui` | 通过 Claude 启动 Flask，端口 5002 |
| 命令行 | `python scripts/web_server.py` | 独立启动，后台运行 |

### 仪表盘功能模块

| 模块 | 功能 | 数据源 |
|------|------|--------|
| **市场概览** | 沪深300/创业板/上证50/深证成指/红利指数/中证500 实时行情 + 30日走势折线图 | akshare / 腾讯财经 |
| **持仓分析** | 客户持仓明细 + 盈亏汇总卡片 + 饼图 + 持仓净值走势 | 本地JSON + akshare实时净值 |
| **基金查询** | 基金/经理/公司搜索 + 净值走势图 + 同类归一化对比 | 本地JSON + akshare |
| **量化分析** | 7维量化信号 + 净值预测（线性回归+置信区间） | fund_quant_analyzer |
| **资讯** | 财经新闻聚合（新浪财经/腾讯财经/和讯网/东财股吧） | 多渠道实时抓取 |
| **智能对话** | 自然语言对话 + 文件上传持仓识别 | conversation_engine + HoldingsImporter |

### 文件上传（对话框内）

客户可在对话框直接上传持仓文件，系统自动识别并分析：

| 文件类型 | 格式 | 说明 |
|---------|------|------|
| 截图 | `.png` `.jpg` `.jpeg` `.bmp` | OCR识别截图中的基金代码、名称、份额 |
| Word | `.docx` | 解析文档表格中的持仓数据 |
| PDF | `.pdf` | 解析对账单/持仓报告 |
| Excel | `.xlsx` `.xls` | 自动识别列名（中英文），保留基金代码前导零 |
| CSV | `.csv` | 同Excel，支持UTF-8编码 |

**上传流程：**
1. 输入客户名称（可选）
2. 点击「上传文件」或拖拽文件到上传区
3. 系统自动解析 → 聊天中展示持仓明细表格
4. 自动送入对话引擎进行持仓分析

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 仪表盘主页面 |
| `/api/search` | GET | 基金/经理/公司搜索（`?q=关键词&type=fund\|manager\|company`）|
| `/api/market/overview` | GET | 六大市场指数行情 |
| `/api/nav/chart` | GET | 基金历史净值走势（`?code=001924&period=1y\|6m\|3m\|1m`）|
| `/api/holdings` | GET | 客户持仓概览（`?client_id=张先生`）|
| `/api/news` | GET | 财经新闻资讯（`?limit=20`）|
| `/api/quant/forecast` | POST | 量化预估分析（`{code, forecast_days}`）|
| `/api/compare` | POST | 同类基金对比（`{codes: [...]}`）|
| `/api/chat` | POST | 智能对话（`{query}`）|
| `/api/upload` | POST | 文件上传（multipart/form-data: file + client_id）|
| `/api/health` | GET | 健康检查 |

### 数据源覆盖

| 数据源 | 用途 | 接口 |
|--------|------|------|
| akshare | 指数行情、基金净值、实时估值 | `ak.stock_zh_index_daily_em` / `ak.fund_open_fund_info_em` |
| 东方财富 | 实时估值、基金概况 | JSONP接口 / 详情页JS |
| 新浪基金 | 净值数据fallback | Sina Fund API |
| 腾讯财经 | 指数数据fallback | `web.ifzq.gtimg.cn` |
| 和讯网 | 新闻fallback | HTML抓取 |
| 新浪财经 | 新闻聚合 | HTML抓取 |
| 腾讯财经新闻 | 新闻聚合 | HTML抓取 |

---

## 客户持仓导入

> 支持7种方式导入客户持仓：Web上传、截图OCR、Word、PDF、Excel、CSV、链接爬取。

### 导入方式总览

| 导入方式 | 触发示例 | 适用场景 |
|---------|---------|---------|
| Web上传 | 对话框拖拽文件 / 点击上传按钮 | 客户直接在Web界面上传 |
| 截图OCR | "导入截图" / 发送图片路径 | 客户发送持仓页面截图 |
| Word导入 | "导入Word" / 发送.docx路径 | 客户提供Word版持仓清单 |
| PDF导入 | "导入PDF" / 发送.pdf路径 | 客户提供PDF对账单/报告 |
| Excel导入 | "导入Excel" / 发送.xlsx路径 | 客户提供Excel持仓表 |
| CSV导入 | "导入CSV" / 发送.csv路径 | 其他系统导出的CSV文件 |
| 链接爬取 | "导入链接" / 提供URL | 登录后的基金平台链接 |

### 编程接口

```python
from client_manager.holdings_importer import HoldingsImporter

importer = HoldingsImporter()

# 截图OCR
result = importer.import_from_screenshot("D:\\客户资料\\持仓截图.png", client_id="张先生")

# Word/PDF
result = importer.import_from_docx("D:\\客户资料\\持仓表.docx", client_id="张先生")
result = importer.import_from_pdf("D:\\客户资料\\对账单.pdf", client_id="张先生")

# 链接爬取
result = importer.import_from_url("https://fund.eastmoney.com/001924.html", client_id="张先生")

# 查看持仓
holdings = importer.load_client_holdings("张先生")

# 导出
importer.export_to_excel(holdings, client_id="张先生")
importer.export_to_csv(holdings, client_id="张先生")
```

### 客户持仓仓库

```
data/clients/
├── _index.json                        # 仓库索引
├── {客户ID}/
│   ├── holdings.json                  # 当前持仓（按基金代码合并去重）
│   ├── history/holdings_{时间戳}.json  # 历史快照
│   ├── imports/import_{时间戳}.json   # 导入记录
│   └── reports/                       # 导出报告
```

---

## 对话引擎

### 支持的意图

| 意图 | 触发示例 |
|------|---------|
| 情绪安抚 | "亏了15%怎么办" "心态崩了" "好焦虑" |
| 持仓分析 | "帮我看看持仓" "我的基金怎样了" |
| 基金推荐 | "推荐个基金" "我35岁想买基金" |
| 基金经理 | "张坤经理怎么样" "萧楠介绍" |
| 基金公司 | "华夏基金怎么样" |
| 板块预测 | "科技板块后面怎么走" |
| 股票分析 | "帮我分析茅台" "600519怎么样" |
| 宏观分析 | "宏观经济怎么样" "CPI走势" |
| 报告生成 | "给我一份周报" "生成月报" |
| PPT报告 | "生成PPT报告" "可视化演示" |
| 止盈止损 | "设置止损10%" "止盈20%" |
| 量化评估 | "我能承受多大亏损" "适合什么基金" |
| 心态跟踪 | "记录心情" "心态分析" |
| 费率查询 | "管理费多少" "申购费率" |
| 持仓导入 | "导入截图" "导入Word" "上传持仓" |
| 表格导出 | "导出Excel" "导出CSV" |
| 客户管理 | "查看客户列表" |

### 使用示例

```python
from client_manager.conversation_engine import ClientManager

cm = ClientManager()

# 基金查询
print(cm.chat("user_001", "001924怎么样"))

# 持仓分析
print(cm.chat("user_001", "我买了000858，亏了15%怎么办"))

# 推荐基金
print(cm.chat("user_001", "我35岁，能承受15%亏损，推荐基金"))

# 生成报告
print(cm.chat("user_001", "生成PPT报告"))
```

---

## 量化分析

### 7维信号模型

| 信号 | 权重 | 说明 |
|------|------|------|
| 均线偏离 | 15% | 净值与MA5/MA10/MA20/MA60偏离程度 |
| RSI | 15% | 超买超卖判断（>70超买 / <30超卖）|
| 布林带 | 10% | 净值在布林带中的位置 |
| 动量 | 15% | N日累计涨幅 |
| 波动率 | 10% | 年化波动率评估 |
| 趋势 | 20% | 均线多空排列判断 |
| 持仓集中度 | 15% | 基金经理持仓分散度 + 风格匹配 |

### 使用示例

```python
from analysis.fund_quant_analyzer import FundQuantAnalyzer

analyzer = FundQuantAnalyzer()

# 单基金分析
result = analyzer.analyze_fund('001924', client_risk='积极型')
print(analyzer.format_analysis_report(result))

# 组合分析
holdings = [{'fund_code': '001924', 'shares': 10000, 'cost': 1.5}]
portfolio = analyzer.analyze_portfolio(holdings, client_risk='稳健型')
print(analyzer.format_portfolio_analysis_report(portfolio))
```

---

## 基金对比与可视化

```python
from analysis.comparison_engine import ComparisonEngine

engine = ComparisonEngine()
result = engine.compare_managers(['张坤', '萧楠', '葛兰'])
```

Web UI 中：搜索基金后输入对比代码，自动生成归一化走势对比图。

---

## 其他能力

### 投资组合推荐
```python
from analysis.portfolio_recommender_v2 import PortfolioRecommenderV2

rec = PortfolioRecommenderV2()
result = rec.recommend_portfolio_v2(
    age=35, risk_tolerance='积极型', target_return=15,
    investment_period=5, max_loss=20, investment_amount=20
)
print(rec.format_portfolio_report_v2(result))
```

### 止盈止损告警
```python
from client_manager.alert_system import AlertSystem

alert = AlertSystem()
alert.set_user_alert_settings('user_001', stop_loss=10, stop_profit=20)
alerts = alert.daily_check('user_001', holdings)
```

### 基金经理话术
```python
from analysis.fund_advisor_speech import FundAdvisorSpeech

gen = FundAdvisorSpeech()
print(gen.ask("张明经理怎么样？", manager_name="张明"))
```

### 基金经理互动
```python
from client_manager.invitation_engine import InvitationEngine

engine = InvitationEngine()
result = engine.invite_managers_for_products(holdings, 'user_001')
print(engine.get_manager_self_introduction(manager_name='萧楠'))
```

### 用户量化评估
```python
from client_manager.user_profile_manager import UserQuantitativeAssessment

assessment = UserQuantitativeAssessment()
result = assessment.assess_investment_profile(
    age=35, risk_tolerance='积极型', investment_amount=20,
    investment_horizon=5, target_companies=['华夏基金'], target_managers=['张坤']
)
print(assessment.format_assessment_report(result))
```

### 投资心态跟踪
```python
from client_manager.emotional_tracker import EmotionalTracker

tracker = EmotionalTracker()
tracker.record_emotion('user_001', {
    'emotion': '焦虑', 'cause': '亏损15%', 'intensity': 7, 'profit_pct': -15
})
print(tracker.get_emotion_analysis('user_001'))
```

### 基金经理互动
```python
from client_manager.invitation_engine import InvitationEngine

engine = InvitationEngine()
# 邀请持仓对应的基金经理
result = engine.invite_managers_for_products(holdings, 'user_001')
# 获取经理自我介绍
intro = engine.get_manager_self_introduction(manager_name='萧楠')
```

### 报告导出
```python
from client_manager.report_generator import ReportGenerator
from client_manager.ppt_report_generator import PPTReportGenerator

# 文本报告
gen = ReportGenerator()
report = gen.generate_portfolio_report(user_id='user_001', holdings=holdings)

# PPT报告
ppt = PPTReportGenerator()
ppt.generate_report(holdings, output_path='report.pptx')
```

---

## 数据文件

| 文件 | 内容 | 数量 |
|------|------|------|
| `fund_managers_distilled.json` | 基金经理档案 | 4,203人 |
| `fund_companies_distilled.json` | 基金公司档案 | 164家 |
| `holdings_database.json` | 经理持仓明细 | 1,794条 |
| `manager_views.json` | 经理观点（季报/年报） | 3,000条 |
| `style_profiles.json` | 风格画像 | 成长/均衡/价值 |
| `external_data.json` | 基金评级+分析 | 1,231条 |
| `user_holdings.json` | 用户持仓 | 自定义 |
| `alert_settings.json` | 告警设置 | 用户配置 |
| `emotional_records.json` | 心态记录 | 情绪追踪 |
| `clients/` | 客户持仓仓库 | 按客户ID组织 |

---

## 数据时效

| 数据类型 | 滞后 | 说明 |
|---------|------|------|
| 基金净值 | T+1~T+2 | 估算值，非实时 |
| 持仓明细 | 季度末后4-8周 | 半年报/年报披露延迟 |
| 经理档案 | 实时更新 | 任职/离职状态 |
| 指数行情 | 实时（交易时段）| akshare/东财/腾讯 |
| 新闻资讯 | 实时抓取 | 多渠道聚合 |

**月度更新**：每月第1工作日自动执行 `monthly_updater.py`，更新全量经理名单和管理产品。

**核心原则：所有数据仅供辅助参考，不构成投资建议。**

---

## 脚本结构

```
fund-advisor/
├── mcp_server.py                       # MCP Server 入口（含 launch_web_ui 工具）
├── scripts/
│   ├── web_server.py                   # Flask Web 服务（v5.0 新增）
│   ├── client_manager/
│   │   ├── conversation_engine.py      # 对话引擎（总入口）
│   │   ├── holdings_importer.py        # 持仓导入（截图OCR/文档/Excel/CSV/链接）
│   │   ├── client_portfolio_evaluator.py # 持仓评测
│   │   ├── alert_system.py            # 止盈止损告警
│   │   ├── sector_predictor.py        # 板块预测
│   │   ├── invitation_engine.py       # 经理邀约
│   │   ├── user_profile_manager.py    # 用户画像 + 8维量化评估
│   │   ├── emotional_tracker.py       # 心态跟踪
│   │   ├── report_generator.py        # 报告生成
│   │   └── ppt_report_generator.py    # PPT报告
│   ├── analysis/
│   │   ├── fund_quant_analyzer.py     # 基金量化分析（7维信号）
│   │   ├── comparison_engine.py       # 横向对比引擎
│   │   ├── portfolio_recommender_v2.py # 组合推荐 v2
│   │   ├── performance_tracker.py     # 业绩跟踪 + 量化调仓建议
│   │   ├── fund_advisor_speech.py     # 基金经理话术引擎 v4.0
│   │   ├── news_advisor.py            # 新闻顾问
│   │   ├── macro_analyzer.py          # 宏观分析
│   │   ├── stock_quant_analyzer.py    # 股票量化分析
│   │   ├── style_analyzer.py          # 风格分析
│   │   └── ...（共24个分析脚本）
│   ├── data_collection/
│   │   ├── eastmoney_collector.py     # 东方财富采集
│   │   ├── news_collector.py          # 新闻采集
│   │   ├── manager_full_collector.py  # 全量经理采集
│   │   └── ...（共22个采集脚本）
│   └── maintenance/
│       ├── monthly_updater.py         # 月度数据更新
│       └── update_scheduler.py        # 更新调度
├── templates/
│   └── index.html                     # Web UI 前端（v5.0 新增）
├── data/                              # 本地JSON数据库
├── references/                        # API文档
├── .claude-plugin/plugin.json         # Claude Code插件清单
├── .skillhub.json                     # SkillHub发布清单
├── _meta.json                         # Skill元数据
├── SKILL.md                           # 本文件
├── requirements.txt                   # 依赖列表
└── pyproject.toml                     # Python打包配置
```

---

## 依赖安装

```bash
# 全量安装
pip install requests beautifulsoup4 akshare pandas python-dateutil \
    flask flask-cors mcp openpyxl python-docx pdfplumber Pillow

# 按需追加
pip install pytesseract   # 截图OCR（还需安装Tesseract系统包）
pip install selenium      # 浏览器爬取（还需ChromeDriver）
pip install PyPDF2        # PDF导入
pip install python-pptx   # PPT报告
```

**依赖检查脚本：**
```python
from importlib import util as _u
for name, spec in {
    "akshare": _u.find_spec("akshare"),
    "flask": _u.find_spec("flask"),
    "pytesseract": _u.find_spec("pytesseract"),
    "python-docx": _u.find_spec("docx"),
    "pdfplumber": _u.find_spec("pdfplumber"),
    "selenium": _u.find_spec("selenium"),
    "openpyxl": _u.find_spec("openpyxl"),
    "python-pptx": _u.find_spec("pptx"),
}.items():
    print(f"  {'✓' if spec else '✗'} {name}")
```

---

## FAQ

**Q: 净值和实际看到的不一致？**
A: 正常。净值数据滞后1-2天，是估算值。如需实时估值请查看天天基金或支付宝。

**Q: 截图识别结果不对？**
A: 截图尽量高清、包含基金代码列、背景干净无水印。也可以直接用Excel/CSV导入。

**Q: Web UI 打不开？**
A: 确认端口5002未被占用，检查 `python scripts/web_server.py` 启动日志。

**Q: 上传Excel没识别到数据？**
A: 确认第一列为基金代码（6位数字），常见列名：基金代码/代码、基金名称/名称、持有份额/份额、成本净值/成本。支持中英文列名。

**Q: 数据安全吗？**
A: 所有数据存储在本地，不会上传至任何服务器。Web UI 仅监听 localhost。
