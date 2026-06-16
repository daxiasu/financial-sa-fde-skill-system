# AI股票研究员

> 专业股票分析 | 三维预测 | 投资大师范式 | 短中长报告 | 股票跟踪 | 指数板块

## 功能特性

- **技术分析** - MA/EMA/MACD/RSI/KDJ/布林带/ADX/Hurst指数
- **三维预测** - 情绪面25%+估值面25%+历史案例30%+技术面20%
- **短中长报告** - 1-5日/20-60日/120+日投资价值分析
- **投资大师范式** - 巴菲特/格雷厄姆/彼得林奇分析方法
- **股票跟踪** - 持仓监控/止损止盈/RSI预警
- **指数分析** - 上证/沪深300/创业板/科创50
- **板块轮动** - 申万15个一级行业资金流向

## 安装依赖

```bash
pip install requests reportlab
```

## 使用方法

### 股票研究分析

```bash
# 短期报告（1-5日）
python scripts/stock_researcher.py --codes 600519 --period short

# 中期报告（20-60日）
python scripts/stock_researcher.py --codes 600519 --period medium

# 长期报告（120+日）
python scripts/stock_researcher.py --codes 600519 --period long
```

### 股票跟踪

```bash
# 添加跟踪
python scripts/stock_researcher.py --track 600519 --add

# 检查跟踪
python scripts/stock_researcher.py --track --check

# 跟踪列表
python scripts/stock_researcher.py --track --list
```

### 指数分析

```bash
# 所有指数
python scripts/stock_researcher.py --index

# 指定指数
python scripts/stock_researcher.py --index sh000001  # 上证
python scripts/stock_researcher.py --index sh000300  # 沪深300
```

### 板块分析

```bash
# 所有板块
python scripts/stock_researcher.py --sector

# 指定板块
python scripts/stock_researcher.py --sector 银行
```

## Skill触发词

- 股票研究、个股报告、技术分析
- 投资价值、短期预测、中期预测、长期预测
- 股票跟踪、指数分析、板块轮动

## 目录结构

```
ai-stock-researcher/
├── scripts/
│   ├── stock_researcher/     # 股票研究员核心模块
│   │   ├── core/            # 技术/估值/预测引擎
│   │   ├── agents/          # 投资大师Agent
│   │   ├── data/           # 市场数据
│   │   ├── report/         # PDF报告生成
│   │   ├── tracker/         # 持仓跟踪
│   │   ├── index_analysis/  # 指数分析
│   │   └── sector_analysis/ # 板块分析
│   ├── stock_researcher.py  # CLI入口
│   ├── quant_estimate.py    # 三维评分
│   ├── sector_forecast.py    # 板块轮动
│   └── daily_scheduler.py   # 每日调度
├── pkg/                      # 工具包
└── _meta.json              # Skill元数据
```

## 免责声明

本工具仅供投资参考，不构成投资建议。股票投资有风险，入市需谨慎。