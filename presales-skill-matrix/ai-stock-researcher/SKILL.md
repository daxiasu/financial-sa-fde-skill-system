---
name: ai-stock-researcher
description: |
  AI股票研究员 — A股智能投研工具，数据来源：东方财富/腾讯财经/雪球，国内网络直接可用。
  核心能力：Web UI 交互仪表盘、TradingAgents多智能体分析（7位AI分析师）、三维评分预测、短/中/长期研报、量化Alpha信号、板块轮动分析、产业链分析。
  内置巴菲特/格雷厄姆/彼得林奇投资范式，支持全市场股票筛选、持仓导入（截图OCR/PPT/Word/PDF）、PPT/PDF报告导出。
  MCP Server 集成，可直接调用股票研究/持仓导入/技术分析/产业链分析功能。
  触发词：股票研究、个股报告、技术分析、投资价值、短期/中期/长期预测、股票跟踪、指数分析、板块轮动、情绪分析、PPT报告、量化信号、导入持仓、导出Excel、产业链分析、国产替代、上下游分析、启动Web、Web界面
---

# AI股票研究员

> 技术分析 | 三维预测 | 投资大师分析 | 量化模型 | 短中长报告 | 股票跟踪 | 指数板块

---

## 快速开始

### 安装依赖

**最少依赖**（技术分析+指数+板块+情绪）：
```bash
pip install requests beautifulsoup4 lxml pandas akshare
```

**按需追加**：
```bash
pip install python-pptx       # PPT报告导出
pip install reportlab          # PDF报告导出
pip install pytesseract pillow # 截图OCR（还需安装Tesseract系统包）
pip install python-docx        # Word导入
pip install pdfplumber         # PDF导入
pip install openpyxl           # Excel导出
pip install selenium           # 浏览器爬取
pip install mcp                # MCP Server 集成
```

**检查哪些功能可用**：
```python
from importlib import util as _u
checks = {
    "核心(requests)": _u.find_spec("requests"),
    "数据(akshare)": _u.find_spec("akshare"),
    "PPT导出(pptx)": _u.find_spec("pptx"),
    "PDF导出(reportlab)": _u.find_spec("reportlab"),
    "OCR(pytesseract)": _u.find_spec("pytesseract"),
    "Word(python-docx)": _u.find_spec("docx"),
    "PDF解析(pdfplumber)": _u.find_spec("pdfplumber"),
    "Excel(openpyxl)": _u.find_spec("openpyxl"),
    "浏览器(selenium)": _u.find_spec("selenium"),
    "MCP(mcp)": _u.find_spec("mcp"),
}
for name, ok in checks.items():
    print(f"  {'✅' if ok else '❌'} {name}")
```

### 基本使用

```bash
# 分析单只股票（短期）
python scripts/stock_researcher.py --codes 600519 --period short

# 分析多只股票
python scripts/stock_researcher.py --codes 600519 000858 --period medium

# 指数分析
python scripts/stock_researcher.py --index sh000001

# 板块分析
python scripts/stock_researcher.py --sector 银行
```

### Web UI 启动

```bash
# 安装 Web UI 依赖
pip install flask flask-cors

# 启动 Web 仪表盘
python scripts/web_server.py

# 或指定端口
python scripts/web_server.py 5003
```

启动后浏览器打开 **http://localhost:5003**，包含4个功能模块：

| 模块 | 功能 |
|------|------|
| **市场概览** | 上证/沪深300/创业板/科创50/上证50/中小板实时行情 + 60日走势折线图 |
| **股票分析** | 输入6位代码查询行情/K线/技术指标（MA/RSI/MACD） |
| **多智能体研究** | 配置LLM提供商和模型 → 启动7位AI分析师协调分析 → SSE实时进度 → 完整报告 |
| **板块分析** | 申万15个一级行业板块强弱排行 + 资金流向 |

**多智能体分析需要额外依赖**（可选）：
```bash
pip install langchain-core langchain-openai langgraph stockstats python-dotenv mootdx
```

**通过 MCP 启动**（调用 `launch_web_ui` 工具）。

### 运行后会输出什么

运行分析命令后，你会看到类似这样的输出：

```
【贵州茅台 600519 短期分析报告】
━━━━━━━━━━━━━━━━━━━━━━━
▶ 基本信息
  行业: 食品饮料 | 市值: 2.1万亿 | PE: 28.5

▶ 技术指标
  MA5: 1785.20 ↑  MA20: 1752.30 ↑  MA60: 1698.50 ↑
  RSI(14): 62.3 (中性偏强)
  MACD: DIF=12.5 DEA=8.3 柱=4.2 (金叉)
  布林带位置: 72% (中上轨之间)

▶ 三维预测评分: 73/100
  情绪面: 70/100 (资金净流入，股吧偏乐观)
  估值面: 65/100 (PE处于历史60%分位)
  历史案例: 78/100 (12个相似案例中9个上涨)

▶ 操作建议: 适量买入
  短期(1-5日): 震荡偏强，支撑位1750
  止损位: 1700  止盈位: 1850
━━━━━━━━━━━━━━━━━━━━━━━
```

> 注意：实际输出内容会因市场数据变化而不同。如果看到空白或报错，参考文末"FAQ — 常见问题与故障排查"。

---

## 能力边界与实际可用性

### 功能可靠性分级

| 功能 | 可靠度 | 说明 |
|------|--------|------|
| 个股技术分析（MA/RSI/MACD/布林） | ★★★★★ | 核心功能，数据来自腾讯财经，稳定可靠 |
| 指数分析（上证/沪深300/创业板） | ★★★★☆ | 数据稳定，偶有网络波动 |
| 板块轮动分析 | ★★★★☆ | 申万行业分类，数据可靠 |
| 三维预测评分 | ★★★★☆ | 模型成熟，但预测仅供参考 |
| 股吧情绪分析 | ★★★★☆ | 东方财富数据，无需登录 |
| 股票跟踪与告警 | ★★★★☆ | 本地存储，稳定可靠 |
| 全市场股票筛选 | ★★★☆☆ | 依赖东方财富API，网络不好时可能超时 |
| 雪球情绪分析 | ★★★☆☆ | 需要登录cookie，配置较麻烦 |
| PPT/PDF报告导出 | ★★★☆☆ | 需额外安装 python-pptx / reportlab |
| 截图OCR持仓识别 | ★★☆☆☆ | 需装 Tesseract 系统包 + pytesseract，准确率取决于截图质量 |

### 预测结果怎么看

> **重要**：三维预测给出的是"历史相似案例的统计概率"，不是确定性判断。

- 评分 70+：历史上类似条件下上涨概率较高，但不代表一定涨
- 评分 30-70：信号不明，建议观望
- 评分 <30：历史上类似条件下下跌概率较高
- **永远不要把本工具的预测当作买卖唯一依据**

### 数据时效

| 数据类型 | 来源 | 更新频率 | 注意 |
|---------|------|---------|------|
| 实时行情 | 腾讯财经 | 实时 | 网络不好时可能获取失败 |
| 历史K线 | 腾讯财经 | 日频 | 至少需要20个数据点 |
| 财务数据 | 东方财富 | 季报后更新 | 存在4-8周延迟 |
| 股吧帖子 | 东方财富 | 实时 | 可匿名访问 |
| 雪球讨论 | 雪球 | 实时 | 需要登录cookie |

---

## 1. 股票分析

### 1.1 综合研究分析

```bash
# 短期报告（1-5日）
python scripts/stock_researcher.py --codes 600519 --period short

# 中期报告（20-60日）
python scripts/stock_researcher.py --codes 600519 --period medium

# 长期报告（120+日）
python scripts/stock_researcher.py --codes 600519 --period long

# 分析多只股票
python scripts/stock_researcher.py --codes 600519 000858 000001 --period short
```

### 1.2 三维预测引擎

| 维度 | 权重 | 分析内容 |
|------|------|---------|
| 情绪面 | 25% | 新闻舆情、资金流向、涨跌幅 |
| 估值面 | 25% | PE/PB历史分位、估值中枢、安全边际 |
| 历史案例 | 30% | 同类股票相似条件下的走势 |
| 技术面 | 20% | 均线、MACD、RSI综合信号 |

### 1.3 技术指标体系

| 指标类型 | 指标 |
|---------|------|
| 均线 | MA5/10/20/60/120/250、多头排列/空头排列 |
| 摆动 | RSI(6/14/24)、KDJ(K/D/J) | KDJ因需要历史平滑值，短期数据可能有误差 |
| MACD | DIF/DEA/MACD柱(DIF线/DEA线/Histogram) | MACD柱=DIF-DEA×2 |
| 趋势 | ADX趋向指数 | ADX>25表示趋势强 |
| 布林 | 布林带(20日±2标准差)、布林带位置 | 位置>80超买，<20超卖 |
| Hurst | Hurst指数(趋势/均值回归/随机) |

### 1.4 投资大师分析范式

| 大师 | 分析重点 | 核心指标 |
|------|---------|---------|
| 巴菲特 | 价值投资 | ROE>15%、护城河、DCF内在价值、安全边际 |
| 格雷厄姆 | 价值安全 | Graham Number、NCAV、盈利稳定性 |
| 彼得林奇 | 成长投资 | PEG、营收CAGR、负债率、机构持仓 |
| 技术派 | 趋势跟踪 | EMA排列、ADX、Hurst指数 |
| 情绪派 | 市场情绪 | 新闻情感、资金流向、内幕交易 |

---

## 2. 股票跟踪

```bash
# 添加跟踪股票
python scripts/stock_researcher.py --track 600519 --add

# 检查所有跟踪股票
python scripts/stock_researcher.py --track --check

# 查看跟踪列表
python scripts/stock_researcher.py --track --list
```

**跟踪功能**：
- 价格监控（现价、涨跌幅）
- 止损/止盈提醒
- 技术信号恶化提醒（RSI超买/超卖）
- 资金大幅流出预警
- 持仓盈亏统计

---

## 3. 指数分析

```bash
# 分析所有指数
python scripts/stock_researcher.py --index

# 分析指定指数
python scripts/stock_researcher.py --index sh000001    # 上证指数
python scripts/stock_researcher.py --index sh000300    # 沪深300
python scripts/stock_researcher.py --index sz399006    # 创业板指
python scripts/stock_researcher.py --index sh000688    # 科创50
```

**分析内容**：
- 实时价格与涨跌幅
- 均线系统（MA5/10/20/60）
- RSI、MACD、ADX指标
- 均线多空状态判断
- 市场情绪（积极/中性/谨慎）

---

## 4. 板块分析

```bash
# 分析所有板块
python scripts/stock_researcher.py --sector

# 分析指定板块
python scripts/stock_researcher.py --sector 银行
python scripts/stock_researcher.py --sector 食品饮料
```

**申万一级行业板块**（15个）：
银行、非银金融、房地产、医药生物、食品饮料、汽车、电子、计算机、通信、传媒、军工、新能源、化工、有色金属、机械设备

**板块分析内容**：
- 平均涨跌幅
- 上涨/下跌家数
- 主力资金净流入/出
- 强弱排名
- 轮动信号

---

## 4.1 产业链分析（新功能）

### 概述

六层递进产业链分析框架，支持**通用模式**和**A股专版模式**。从产业链地图到投资判断，完整覆盖上中下游价值分布、竞争格局、国产替代进度。

### 快速使用

```bash
# 列出所有预设产业链
python scripts/stock_researcher.py --chain

# 通用产业链分析（6层框架）
python scripts/stock_researcher.py --chain 半导体

# A股专版产业链分析（含国产替代进度）
python scripts/stock_researcher.py --chain 半导体 --chain-mode ashare
```

### 预设产业链

| 产业链 | 上游 | 中游 | 下游 |
|--------|------|------|------|
| 半导体 | 设备/EDA/材料/IP核 | 芯片设计/晶圆制造/封测 | 消费电子/汽车/AI算力 |
| 新能源汽车 | 锂矿/正负极/电解液/隔膜 | 动力电池/电机电控/热管理 | 整车/充电桩/储能 |
| 光伏 | 多晶硅/硅片/银浆/玻璃 | 电池片/组件/逆变器 | 电站/分布式/BIPV |
| AI芯片 | GPU芯片/封装/HBM/光模块 | 服务器/AI框架/云计算 | 大模型/AI应用/智驾 |
| 医药 | 原料药/CRO/辅料/包装 | 创新药/仿制药/器械 | 医院/药店/医保 |
| 消费电子 | 芯片/面板/摄像头/元件 | ODM/结构件/连接器 | 手机/PC/穿戴/ARVR |
| 军工 | 特料/军用电子/军用芯片 | 发动机/导弹/飞机/舰船 | 军队采购/军贸 |
| 机器人 | 减速器/伺服/控制器/传感器 | 工业机器人/协作/人形 | 汽车/3C/物流/医疗 |

### 通用模式 — 六层递进框架

| 层级 | 名称 | 核心问题 |
|------|------|---------|
| 第一层 | 产业链地图绘制 | 产业链全貌是什么？各节点功能和代表企业 |
| 第二层 | 价值分布分析 | 利润在哪里？微笑曲线位置判断 |
| 第三层 | 竞争格局分析 | 谁在赢？集中度+竞争矩阵+护城河类型 |
| 第四层 | 战略控制点识别 | 卡脖子在哪里？谁控制、为什么能控制 |
| 第五层 | 动态演化分析 | 格局怎么变？技术替代/整合/地缘/成本 |
| 第六层 | 投资/战略判断 | 最值得关注vs需警惕的节点，明确立场 |

### A股专版 — 六层递进框架

| 层级 | 名称 | 核心问题 |
|------|------|---------|
| 第一层 | 产业链地图(🟢🟡🔴) | 哪些节点有A股参与？参与度如何？ |
| 第二层 | 价值分布(A股视角) | A股企业能拿到哪部分利润？ |
| 第三层 | A股竞争矩阵 | 谁在赢？技术/成本/规模/客户横向对比 |
| 第四层 | 国产替代进度 | 国产化率多少？空间多大？节奏如何？ |
| 第五层 | 动态演化(A股节奏) | 需求催化/供给变化/政策/竞争演变时间表 |
| 第六层 | A股投资判断 | 具体标的推荐+警惕标的+信号检查 |

### 国产替代进度评估（A股专版核心）

替代阶段划分：
- 🚀 突破期：国内已有产品，正在客户验证，1-2年内放量
- 📈 加速期：已进入供应链，份额快速提升
- ✅ 成熟期：国产化率已超50%，份额稳定
- ⏳ 攻坚期：技术差距仍大，3年以上才能突破

### A股信号检查清单

**积极信号**（加分项）：
- 国家大基金/社保/北向资金增持
- 机构调研密度上升
- 大客户首次进入或扩大采购
- 产能利用率 > 90%
- 研发费用率持续提升

**风险信号**（减分项）：
- 大股东近期减持
- 前五大客户集中度 > 70%
- 同行密集上市/定增
- 毛利率连续2个季度下滑
- 应收账款增速 > 营收增速

### API使用

```python
from stock_researcher.industry_chain import (
    IndustryChainAnalyzer, AShareChainAnalyzer,
    get_preset_chain, list_presets
)

# 通用模式
analyzer = IndustryChainAnalyzer()
nodes = analyzer.build_chain_map("半导体",
    upstream=["半导体设备", "EDA工具", "半导体材料"],
    midstream=["芯片设计", "晶圆制造", "封装测试"],
    downstream=["消费电子", "汽车电子", "AI算力"]
)
result = analyzer.analyze("半导体")
print(analyzer.format_report(result))

# A股模式
ashare = AShareChainAnalyzer()
nodes = ashare.build_chain_map("半导体",
    upstream=[{"name": "半导体设备", "participation": "🟡"}],
    midstream=[{"name": "芯片设计", "participation": "🟢"}],
    downstream=[{"name": "AI算力", "participation": "🟢"}]
)
# 补充竞争矩阵数据
matrix = ashare.build_competition_matrix("芯片设计", [
    {"name": "海光信息", "code": "688041", "tech": 3, "cost": 2, "scale": 2, "customer": 3},
    {"name": "寒武纪", "code": "688256", "tech": 3, "cost": 1, "scale": 2, "customer": 2},
])
# 评估国产替代
sub = ashare.assess_substitution(
    node=nodes[0], current_rate=15, target_rate=60,
    total_market_billion=500, barriers=["工艺代差", "认证周期长"]
)
print(f"可替代空间: {sub.replaceable_size}亿, 阶段: {sub.stage}")
```

---

## 5. 投资报告

### 5.1 短期报告（技术面为主）
- 行情概览
- 技术分析（均线、RSI、MACD）
- 资金流向
- 新闻舆情
- 1-5日预测与操作建议

### 5.2 中期报告（估值+趋势）
- 行情概览
- 均线趋势分析
- 估值分析（PE/PB历史分位）
- 基本面（ROE、EPS）
- 20-60日预测与操作建议

### 5.3 长期报告（价值投资）
- 巴菲特价值分析（ROE、护城河、内在价值）
- 格雷厄姆分析（Graham Number、NCAV）
- 彼得林奇成长分析（CAGR、PEG）
- 120+日预测与操作建议
- 风险提示

---

## 6. 全市场股票爬取

```bash
# 获取全市场股票列表
python scripts/stock_researcher.py --market-all

# 获取涨幅榜/跌幅榜Top 10
python scripts/stock_researcher.py --market-all --top 10

# 股票筛选（低估值价值股）
python scripts/stock_researcher.py --screener --top 10
```

**功能说明**：
- 从东方财富API获取全市场A股列表（上交所/深交所/创业板/科创板）
- 支持市值、PE、PB、换手率、涨跌幅多维度筛选
- 实时行情增量更新
- 数据缓存5分钟，避免频繁请求

**筛选维度**：
| 维度 | 说明 |
|------|------|
| 市值 | 大盘股(>500亿)、中盘股(100-500亿)、小盘股(<50亿) |
| PE | 市盈率范围筛选 |
| PB | 市净率范围筛选 |
| 涨跌幅 | 涨幅/跌幅范围筛选 |
| 换手率 | 活跃度筛选 |

---

## 7. 股吧/雪球情绪分析

```bash
# 分析指定股票情绪
python scripts/stock_researcher.py --sentiment 600519

# 爬取股吧帖子
python scripts/stock_researcher.py --forum-crawl --codes 600519
```

**数据来源**：
- 东方财富股吧：https://guba.eastmoney.com
- 雪球股票讨论：https://xueqiu.com

**情绪分析维度**：
| 维度 | 说明 |
|------|------|
| 多头比例 | 正面帖子/总帖子 |
| 情绪评分 | -100(极度悲观) ~ +100(极度乐观) |
| 情绪标签 | 极度乐观/乐观/中性/悲观/极度悲观 |
| 热门话题 | 高频关键词统计 |

**告警类型**：
| 类型 | 触发条件 | 建议 |
|------|---------|------|
| EXTREME_BULLISH | 多头比例>85% | 注意分批减仓 |
| EXTREME_BEARISH | 多头比例<15% | 关注超跌机会 |
| SENTIMENT_SPIKE | 情绪突变>+20% | 可适当关注 |
| SENTIMENT_DROP | 情绪突变<-20% | 建议观望 |

---

## 8. 研究报告导出

```bash
# 导出PPT/PDF报告
python scripts/stock_researcher.py --report 600519 --export-format ppt pdf

# 导出纯文本报告
python scripts/stock_researcher.py --report 600519 --export-format txt
```

**报告内容**：
1. 基本信息（代码、名称、行业、市值）
2. 技术分析（均线、RSI、MACD、布林带）
3. 情绪分析（东方财富股吧+雪球）
4. 历史案例分析
5. 短中期预测与操作建议

**导出格式**：
| 格式 | 说明 | 依赖库 |
|------|------|--------|
| PPT | 可视化演示文稿 | python-pptx |
| PDF | 详细研究报告 | reportlab |
| TXT | 纯文本格式 | 无 |

---

## 9. 持仓导入引擎（新功能）

> 支持多种方式导入客户提供的股票/基金持仓信息，自动识别并维护到客户持仓仓库进行量化跟踪。

### 9.1 导入方式总览

| 导入方式 | 命令示例 | 适用场景 |
|---------|---------|---------|
| 📸 截图OCR识别 | `--import-screenshot D:\截图\持仓.png` | 客户发送持仓页面截图 |
| 📊 PPT导入 | `--import-ppt D:\客户\持仓分析.pptx` | 客户提供PPT版持仓信息 |
| 📄 Word导入 | `--import-docx D:\客户\持仓表.docx` | 客户提供Word版持仓清单 |
| 📑 PDF导入 | `--import-pdf D:\客户\对账单.pdf` | 客户提供PDF对账单/报告 |
| 🌐 链接爬取 | `--import-url https://...` | 客户提供登录后的基金平台链接 |
| 📋 Excel导出 | `--export-excel --client 张先生` | 导出持仓为Excel表格 |
| 📋 CSV导出 | `--export-csv --client 张先生` | 导出CSV格式供其他系统使用 |

### 9.2 命令行使用

```bash
# 截图OCR识别
python scripts/stock_researcher/import_engine.py --import-screenshot "D:\截图\我的持仓.png" --client 张先生

# PPT导入
python scripts/stock_researcher/import_engine.py --import-ppt "D:\客户\持仓分析.pptx" --client 张先生

# Word文档导入
python scripts/stock_researcher/import_engine.py --import-docx "D:\客户\持仓表.docx" --client 张先生

# PDF导入
python scripts/stock_researcher/import_engine.py --import-pdf "D:\客户\对账单.pdf" --client 张先生

# 链接爬取
python scripts/stock_researcher/import_engine.py --import-url "https://fund.eastmoney.com/..." --client 张先生

# 导出Excel
python scripts/stock_researcher/import_engine.py --export-excel --client 张先生

# 查看客户列表
python scripts/stock_researcher/import_engine.py --list-clients

# 查看客户持仓
python scripts/stock_researcher/import_engine.py --summary --client 张先生
```

### 9.3 API调用示例

```python
from import_engine import StockImportEngine

engine = StockImportEngine()

# 截图OCR识别
result = engine.import_from_screenshot("D:\\截图\\持仓.png", client_id="张先生")
print(f"识别到 {len(result['items'])} 条持仓")

# PPT导入
result = engine.import_from_ppt("D:\\客户\\持仓分析.pptx", client_id="张先生")

# Word导入
result = engine.import_from_docx("D:\\客户\\持仓表.docx", client_id="张先生")

# PDF导入
result = engine.import_from_pdf("D:\\客户\\对账单.pdf", client_id="张先生")

# 链接爬取（无需登录）
result = engine.import_from_url("https://fund.eastmoney.com/001924.html", client_id="张先生")

# 链接爬取（需登录）
result = engine.import_from_url(
    "https://...", client_id="张先生",
    credentials={"username": "13800138000", "password": "xxx"}
)

# 导出Excel
items = engine.load_client_items("张先生")
excel_path = engine.export_to_excel(items, client_id="张先生")

# 查看客户列表
clients = engine.list_clients()
```

### 9.4 客户持仓仓库结构

```
data/clients/
├── _index.json                    # 仓库索引
├── {客户ID}/
│   ├── holdings.json              # 当前持仓（按代码合并去重）
│   ├── history/
│   │   └── holdings_{时间戳}.json  # 历史快照
│   ├── imports/
│   │   └── import_{时间戳}.json   # 导入记录
│   └── reports/
│       └── holdings_{时间戳}.xlsx  # 导出报告
```

导入后自动同步到两个跟踪器：
- **SQLite** `pkg/portfolio_tracker.py` → `data/portfolio.db`
- **JSON** `tracker/portfolio.py` → `data/stock_tracking.json`

### 9.5 MCP Server 集成（新）

> 将 ai-stock-researcher 包装为 MCP Server，可直接调用股票研究、持仓导入、技术分析等功能。

**MCP 配置**：

```json
{
  "mcpServers": {
    "ai-stock-researcher": {
      "command": "python",
      "args": ["D:/claude 开发/skill of me/ai-stock-researcher/mcp_server.py"],
      "env": {
        "PYTHONDONTWRITEBYTECODE": "1"
      }
    }
  }
}
```

**依赖安装**：
```bash
pip install mcp
```

**可用工具总览**：

| 分类 | 工具名 | 功能 |
|------|-------|------|
| 持仓导入 | `import_holdings_screenshot` | 截图OCR识别 |
| 持仓导入 | `import_holdings_ppt` | PPT幻灯片导入 |
| 持仓导入 | `import_holdings_docx` | Word文档导入 |
| 持仓导入 | `import_holdings_pdf` | PDF文档导入 |
| 持仓导入 | `import_holdings_url` | 浏览器链接爬取 |
| 持仓导入 | `auto_import_file` | 智能导入（自动识别格式） |
| 持仓导出 | `export_holdings_excel` | 导出Excel表格 |
| 持仓导出 | `export_holdings_csv` | 导出CSV文件 |
| 客户管理 | `list_clients` | 列出所有客户 |
| 客户管理 | `get_client_holdings` | 查看客户持仓详情 |
| 客户管理 | `get_import_history` | 查看导入历史 |
| 股票研究 | `analyze_stock` | 股票综合分析（短期/中期/长期） |
| 股票研究 | `get_stock_technical_indicators` | 技术指标详情（均线/RSI/MACD/布林） |
| 股票研究 | `get_stock_sentiment` | 市场情绪分析（股吧/雪球） |
| 大盘指数 | `analyze_index` | 指数分析（上证/沪深300/创业板/科创50） |
| 板块分析 | `get_sector_analysis` | 行业板块强弱与轮动 |
| 跟踪管理 | `track_stock` | 添加/移除/查看股票跟踪 |
| 产业链 | `list_industry_presets` | 列出预设产业链 |
| 产业链 | `analyze_industry_chain` | 产业链分析（通用/A股模式） |
| 产业链 | `get_chain_preset_detail` | 查看产业链节点详情 |

**使用示例**：
```
用户: 帮我分析一下贵州茅台的技术面
→ 调用 get_stock_technical_indicators(code="600519")

用户: 导入张先生的持仓PPT
→ 调用 import_holdings_ppt(file_path="D:\客户\张先生.pptx", client_id="张先生")

用户: 查看沪深300指数走势
→ 调用 analyze_index(index_code="sh000300")

用户: 分析一下医药生物板块
→ 调用 get_sector_analysis(sector_name="医药生物")

用户: 把600519加入跟踪
→ 调用 track_stock(code="600519", action="add")

用户: 列出所有预设产业链
→ 调用 list_industry_presets()

用户: 分析半导体产业链（A股视角）
→ 调用 analyze_industry_chain(industry="半导体", mode="ashare")
```

### 9.6 依赖安装

```bash
# OCR截图识别
pip install pytesseract pillow
# 还需安装 Tesseract OCR 系统包:
# https://github.com/UB-Mannheim/tesseract/wiki

# 文档解析
pip install python-docx python-pptx pdfplumber

# 浏览器爬取
pip install selenium

# Excel导出
pip install openpyxl
```

---

## 10. 量化模型

基于 QuantConnect Lean 架构的A股量化交易模型。

### 10.1 Alpha模型 - 信号生成

```python
from stock_researcher.quantitative import (
    DualThrustAlpha, RateOfChangeAlpha, MeanReversionAlpha,
    MomentumAlpha, ValueInvestingAlpha, QuantitativeEngine
)

# 创建引擎
engine = QuantitativeEngine()

# 添加Alpha模型
engine.add_alpha_model('dual_thrust', k1=0.63, k2=0.63, period=20)
engine.add_alpha_model('momentum', fast_period=5, slow_period=20)
engine.add_alpha_model('mean_reversion', period=20, std_threshold=2.0)

# 添加风控模型
engine.add_risk_model('stop_loss', stop_loss_pct=0.05)
engine.add_risk_model('max_drawdown', max_drawdown=0.15)

# 设置组合模型
engine.set_portfolio_model('equal_weight', max_positions=10)

# 生成信号
signals = engine.generate_signals(['600519'], price_data, fundamentals)
```

### 10.2 Alpha模型类型

| 模型 | 类型 | 适用场景 | 参数 |
|------|------|---------|------|
| DualThrustAlpha | 突破策略 | 日内/短线 | k1, k2, period |
| RateOfChangeAlpha | 动量策略 | 趋势跟踪 | period, threshold |
| MeanReversionAlpha | 均值回归 | 震荡市 | period, std_threshold |
| MomentumAlpha | 趋势策略 | 趋势确认 | fast_period, slow_period |
| ValueInvestingAlpha | 价值投资 | 长线持有 | pe_max, roa_min |

### 10.3 风险模型

| 模型 | 功能 | 参数 |
|------|------|------|
| StopLossRiskModel | 固定/跟踪止损 | stop_loss_pct, trailing_pct |
| MaximumDrawdownRiskModel | 最大回撤控制 | max_drawdown, reduce_percent |
| TargetProfitRiskModel | 移动止盈 | target_profit_pct, trailing_pct |
| CompositeRiskModel | 组合风控 | 组合多个风控模型 |

### 10.4 组合模型

| 模型 | 原理 | 适用场景 |
|------|------|---------|
| EqualWeightPortfolio | 等权分配 | 分散化投资 |
| RiskParityPortfolio | 风险平价 | 稳健组合 |
| ValueWeightedPortfolio | 置信度加权 | alpha增强 |
| MomentumPortfolio | 动量加权 | 趋势跟踪 |

### 10.5 技术指标

```python
from stock_researcher.quantitative.indicators import QuantIndicators

indicators = QuantIndicators()

# 更新数据
results = indicators.update({
    'open': 100,
    'high': 105,
    'low': 98,
    'close': 103,
    'volume': 1000000
})

# 获取分析摘要
summary = indicators.get_summary()
# {'macd': {...}, 'rsi': {...}, 'bollinger': {...}, 'adx': {...}, ...}
```

### 10.6 A股专用引擎

```python
from stock_researcher.quantitative.engine import AShareQuantEngine

engine = AShareQuantEngine()

# 分析单只股票
result = engine.analyze_stock(
    symbol='600519',
    price_history=price_list,
    fundamentals={'pe': 30, 'pb': 10, 'roe': 25}
)

print(result['recommendation'])  # '强烈买入'/'适量买入'/'观望'
```

---

## 核心脚本

| 脚本 | 功能 |
|------|------|
| `stock_researcher/` | 专业研究员核心模块 |
| `stock_researcher/core/` | 技术分析、估值、三维预测引擎 |
| `stock_researcher/quantitative/` | **量化模型（Alpha/Risk/Portfolio/Indicators）** |
| `stock_researcher/agents/` | 巴菲特/格雷厄姆/林奇/技术/情绪Agent |
| `stock_researcher/data/` | 市场、基本面、资金、新闻、宏观数据 |
| `stock_researcher/data/market_all_stocks_crawler.py` | **全市场A股股票爬虫** |
| `stock_researcher/data/sentiment_forum_crawler.py` | **东方财富/雪球情绪爬虫** |
| `stock_researcher/report/` | PDF/PPT报告生成器 |
| `stock_researcher/report/stock_report_generator.py` | **综合研究报告生成器(PPT/PDF)** |
| `stock_researcher/tracker/` | 持仓跟踪、警报、监控 |
| `stock_researcher/index_analysis/` | 上证/沪深300/创业板/科创50分析 |
| `stock_researcher/sector_analysis/` | 板块轮动分析 |
| `stock_researcher/industry_chain/` | **产业链分析（通用+A股专版/国产替代）** |
| `stock_researcher/import_engine.py` | **持仓导入引擎（截图OCR/PPT/Word/PDF/URL/Excel）** |
| `mcp_server.py` | **MCP Server 入口** |
| `pkg/portfolio_tracker.py` | 持仓追踪（SQLite）+ 调仓建议 |
| `pkg/recommendation_engine.py` | 股票三维评分 |
| `scripts/daily_scheduler.py` | 每日自动化调度 |

---

## 模块架构

```
mcp_server.py              # MCP Server 入口
stock_researcher/
├── import_engine.py         # 持仓导入引擎（截图OCR/PPT/Word/PDF/URL/导出）
├── core/
│   ├── analyzer.py          # 统一分析调度器
│   ├── technical.py         # 技术指标（MA/EMA/MACD/RSI/KDJ/布林带/ADX/Hurst）
│   ├── valuation.py         # 估值指标（PE/PB历史分位/Graham Number/DCF）
│   └── prediction_engine.py # 三维预测引擎
├── quantitative/            # 量化模型（基于QuantConnect Lean）
│   ├── alpha_models.py      # Alpha信号模型（DualThrust/ROC/MeanReversion等）
│   ├── risk_models.py       # 风险模型（止损/回撤/止盈）
│   ├── portfolio_models.py  # 组合模型（等权/风险平价/价值加权）
│   ├── indicators.py        # 技术指标（MACD/RSI/布林/ADX/Hurst/KDJ/CCI）
│   └── engine.py            # 量化引擎整合
├── agents/
│   ├── buffett.py           # 巴菲特：ROE/护城河/DCF/安全边际
│   ├── graham.py            # 格雷厄姆：Graham Number/NCAV/盈利稳定性
│   ├── lynch.py             # 林奇：PEG/营收增长/CAGR/负债率
│   ├── technical.py         # 技术分析师：均线系统/ADX/Hurst
│   └── sentiment.py         # 情绪分析师：新闻+资金流向
├── data/
│   ├── market.py            # 腾讯财经行情API
│   ├── fundamental.py       # 东方财富财务API
│   ├── money_flow.py        # 资金流向
│   ├── news.py              # 新闻获取与分析
│   └── macro.py             # 宏观数据（GDP/CPI/PMI）
├── report/
│   └── generator.py         # PDF报告生成器
├── tracker/
│   ├── portfolio.py         # 持仓跟踪
│   ├── alerts.py            # 警报触发
│   └── monitor.py           # 每日监控
├── index_analysis/
│   └── indices.py           # 上证/沪深300/创业板/科创50
├── sector_analysis/
│   ├── sectors.py           # 申万行业板块
│   └── rotation.py          # 板块轮动
└── industry_chain/          # 产业链分析（通用+A股专版）
    └── chain_analyzer.py    # 六层框架/国产替代/竞争矩阵/预设产业
```

---

## 数据源

| 数据类型 | 来源 |
|---------|------|
| A股实时行情 | 腾讯财经 `qt.gtimg.cn` |
| A股历史K线 | 腾讯财经 `web.ifzq.gtimg.cn` |
| 全市场股票列表 | 东方财富 `push2.eastmoney.com` |
| 财务数据 | 东方财富 `emweb.securities.eastmoney.com` |
| 估值数据 | 东方财富数据中心 |
| 新闻资讯 | 东方财富、同花顺 |
| 股吧帖子 | 东方财富股吧 `guba.eastmoney.com` |
| 雪球讨论 | 雪球 `xueqiu.com` |
| 宏观数据 | 东方财富宏观指标 |

---

## FAQ — 常见问题与故障排查

### 分析相关

**Q: 提示"数据不足"？**
A: 股票历史数据少于20个数据点。排查：
1. 检查股票代码是否正确（6位数字，沪市60开头，深市00/30开头）
2. 新股或停牌股数据不足，换只老股票试试
3. 使用 long 周期：`--period long`

**Q: 分析结果输出空白/没有任何内容？**
A: 通常是网络问题导致数据获取失败，但错误被吞掉了。排查：
1. 检查网络是否通畅
2. 换只股票代码重试
3. 如果所有股票都空白，可能是腾讯财经API临时不可用，稍后再试

**Q: 三维预测评分感觉像"掷骰子"？**
A: 评分基于"当前条件与历史相似案例的统计对比"，不是确定性预测。73分意味着"历史上73个类似条件中有上涨"，但市场随时可能打破历史规律。**请结合自己的判断使用**。

**Q: KDJ指标数值很奇怪？**
A: KDJ需要历史平滑值，如果数据点太少（<30天）结果会失真。建议用 `--period medium` 或 `--period long` 获取更多数据。

**Q: 雪球数据获取失败？**
A: 雪球需要登录cookie。如果不需要雪球数据，东方财富股吧的情绪分析可正常匿名使用。

### 网络/数据相关

**Q: 网络获取失败/超时？**
A: 这是最常见的问题。腾讯财经和东方财富API在国内通常可用，但偶有波动：
1. 稍后重试（等待1-2分钟）
2. 检查是否开了VPN/代理（可能干扰国内API访问）
3. 本工具**不会自动重试**，需要你手动重新执行命令
4. 如果频繁失败，检查 DNS 设置

**Q: 实时行情和实际价格不一致？**
A: 腾讯财经行情有几秒到几分钟的延迟，属于正常现象。如需精确实时价格请查看券商软件。

**Q: 财务数据是上季度的？**
A: 财务数据在季报/年报披露后更新，存在4-8周延迟。这是所有公开数据源的共性。

### 导出/导入相关

**Q: PPT报告导出失败？**
A: 常见原因：
1. `ModuleNotFoundError: No module named 'pptx'` → `pip install python-pptx`
2. 文件写入权限问题 → 检查输出目录是否有写权限

**Q: PDF报告导出失败？**
A: 需要 reportlab 库：`pip install reportlab`

**Q: 截图OCR识别不准？**
A: OCR准确率取决于截图质量。技巧：高清截图、字体清晰、包含股票代码列、背景干净。如果还是不行，手动输入更快。

**Q: Excel导出打不开？**
A: 需要 openpyxl：`pip install openpyxl`

### 报错速查表

| 报错信息 | 原因 | 解决 |
|---------|------|------|
| `ModuleNotFoundError: No module named 'requests'` | 核心依赖未装 | `pip install requests beautifulsoup4 lxml` |
| `ModuleNotFoundError: No module named 'pptx'` | PPT依赖未装 | `pip install python-pptx` |
| `ModuleNotFoundError: No module named 'reportlab'` | PDF依赖未装 | `pip install reportlab` |
| `ModuleNotFoundError: No module named 'pytesseract'` | OCR依赖未装 | `pip install pytesseract pillow` + Tesseract系统包 |
| `ModuleNotFoundError: No module named 'akshare'` | 数据依赖未装 | `pip install akshare` |
| `数据不足` / `Insufficient data` | 历史数据点<20 | 换 `--period long` 或换只股票 |
| `ConnectionError` / `Timeout` | 网络不通 | 检查网络，稍后重试，关VPN |
| `JSONDecodeError` | API返回异常 | 接口临时故障，稍后重试 |
| `PermissionError` | 文件写入权限 | 检查输出目录权限 |
| 输出空白无报错 | 数据获取被吞 | 网络问题，换股票/换时间重试 |

### 容错机制说明

了解工具在网络出问题时的行为，避免困惑：

| 场景 | 工具行为 | 你需要做的 |
|------|---------|-----------|
| 单只股票网络失败 | 跳过该只，继续分析其他 | 重新执行命令 |
| 所有股票都失败 | 输出空白或简短错误 | 检查网络后重试 |
| 雪球需要登录 | 跳过雪球，只用东方财富 | 不影响核心功能 |
| API返回格式变了 | 可能解析出错 | 等待工具更新 |

> 注意：当前版本**不会自动重试**网络请求。如果遇到网络波动，需要手动重新执行命令。

---

## 核心限制与免责

1. **预测基于历史数据**，仅供参考，不构成投资建议
2. **投资有风险**，入市需谨慎
3. **技术指标滞后**：KDJ、ADX等指标存在固有的滞后性
4. **评分标准差异**：不同模块的评分方法可能不一致，分析结果仅供参考
5. **网络依赖**：实时行情和财务数据依赖外部API，网络不好时可能获取失败，工具不会自动重试

### 评分标准说明

不同模块使用不同的评分体系，注意不要直接比较：

| 模块 | 评分范围 | 说明 |
|------|---------|------|
| 技术分析 | -100 ~ +100 | 综合均线/RSI/MACD/布林带 |
| 三维预测 | 0-100分 | 情绪25%+估值25%+历史30%+技术20% |
| 大师分析 | 定性 | 巴菲特/格雷厄姆/林奇各有标准 |
| 量化Alpha | 信号型 | 买入/观望/卖出 |
