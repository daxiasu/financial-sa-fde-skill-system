#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量化知识库 v1.0 — 因子/策略/研报摘要/基金经理风格"""
from __future__ import annotations
import sys, json, re, time, sqlite3
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = SKILL_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "quant_wiki.db"

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS factors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, category TEXT, description TEXT,
        formula TEXT, usage TEXT, source TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, type TEXT, description TEXT,
        implementation TEXT, backtest_result TEXT, source TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS research_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, title TEXT, source TEXT, summary TEXT,
        sentiment TEXT, tags TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS fund_styles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manager_name TEXT UNIQUE, style TEXT, tags TEXT,
        strength TEXT, weakness TEXT, updated_at TEXT
    );
    """)
    conn.commit()
    conn.close()

def _get_conn():
    _init_db()
    return sqlite3.connect(DB_PATH)

# ── 因子 ──────────────────────────────────────────────
FACTORS_SEED = [
    ("PE", "估值", "市盈率，最常用的价值因子", "PE = 股价 / 每股收益(EPS)", "价值投资，低PE买入高PE卖出", "经典财务因子"),
    ("PB", "估值", "市净率，适合金融/周期股", "PB = 股价 / 每股净资产", "破净买入，适合银行/地产", "经典财务因子"),
    ("PS", "估值", "市销率，适合成长股", "PS = 股价 / 每股营收", "收入稳定成长股估值", "经典财务因子"),
    ("ROE", "盈利", "净资产收益率，核心盈利指标", "ROE = 净利润 / 净资产", "ROE>15%为优质公司", "杜邦分析"),
    ("ROA", "盈利", "资产收益率", "ROA = 净利润 / 总资产", "资产利用效率", "杜邦分析"),
    ("毛利率", "盈利", "毛利率，护城河指标", "毛利率 = (营收-成本)/营收", "毛利率稳定且高=强护城河", "财务因子"),
    ("净利润增速", "成长", "净利润同比增速", "增速 = (本期-上期)/上期*100%", "增速>20%为高成长", "成长因子"),
    ("营收增速", "成长", "营收同比增速", "营收增长率计算", "增速>15%为成长股", "成长因子"),
    ("经营性现金流", "财务质量", "经营现金流净额", "OCF = 净利润 + 非现金支出", "OCF>净利润=高质量", "现金流因子"),
    ("北向资金持仓", "资金面", "北向资金持股占总股本比例", "北向持仓% = 外资持股 / 总股本", "持续增持=外资看好", "资金因子"),
    ("换手率", "交易", "日均换手率，反映流动性", "换手率 = 成交股数/总股本", "换手率异常放大需警惕", "技术因子"),
    ("波动率", "风险", "收益率标准差，年化", "σ = std(日收益率)*sqrt(252)", "低波动=低风险高持股体验", "风险因子"),
    ("布林带", "技术", "中轨20日均线+上下轨2倍标准差", "上轨=MA20+2σ, 下轨=MA20-2σ", "触及下轨买入，触碰上轨卖出", "技术因子"),
    ("RSI", "技术", "相对强弱指数，0-100", "RSI = 100 - 100/(1+RS), RS=涨幅均值/跌幅均值", "RSI<30超卖买入, RSI>70超买卖出", "技术因子"),
    ("MACD", "技术", "指数平滑异同移动平均线", "DIF=EMA12-EMA26, DEA=DIF的EMA9", "金叉买入，死叉卖出", "技术因子"),
    ("量比", "交易", "当日成交量/过去5日均量", "量比 = 当日量 / 5日均量", "量比>2为放量异常", "量价因子"),
    ("PEG", "成长", "PE除以净利润增速，G>0时<1为低估", "PEG = PE / (净利润增速*100)", "PEG<1成长股低估", "成长-价值混合"),
    ("阿尔法", "基金", "基金超额收益相对基准", "α = 组合收益 - β*基准收益", "α>0跑赢基准", "基金评价"),
    ("夏普比率", "风险收益", "每承担一单位风险获得的超额收益", "SR = (Rp-Rf)/σp", "SR>0.5为优秀", "基金评价"),
    ("最大回撤", "风险", "历史最大亏损幅度", "MDD = max(Peak-Trough)/Peak", "MDD<15%为低风险", "基金评价"),
]

def init_factors():
    conn = _get_conn()
    for name, cat, desc, formula, usage, source in FACTORS_SEED:
        conn.execute("""
            INSERT OR IGNORE INTO factors(name,category,description,formula,usage,source,created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (name, cat, desc, formula, usage, source, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def get_factors(category: str = "") -> list[dict]:
    conn = _get_conn()
    if category:
        rows = conn.execute("SELECT * FROM factors WHERE category=? ORDER BY name", (category,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM factors ORDER BY category, name").fetchall()
    conn.close()
    cols = ["id","name","category","description","formula","usage","source","created_at"]
    return [dict(zip(cols, r)) for r in rows]

# ── 策略 ──────────────────────────────────────────────
STRATEGIES_SEED = [
    ("均线交叉", "趋势", "短期均线上穿/下穿长期均线", "MA5>MA20金叉买入, MA5<MA20死叉卖出", "趋势行情有效，横盘失效", "技术分析"),
    ("布林带策略", "均值回归", "价格触及布林下轨买入，上轨卖出", "买入信号: price<lower_band, 卖出: price>upper_band", "适合震荡市，单边市失效", "统计套利"),
    ("北向资金流向", "资金", "北向资金大幅净流入次日跟买", "北向净流入>5亿且持续3天", "外资择时能力强", "资金流"),
    ("PE分位择时", "估值", "指数PE历史分位低于20%买入，高于80%卖出", "当PE_PCT<20%买入, >80%卖出", "长期有效，持有周期长", "估值择时"),
    ("ST动量", "事件", "涨停后次日有惯性上涨动力", "涨停次日开盘买入，盘中卖出", "高风险，需要快进快出", "事件驱动"),
    ("定投指数", "配置", "每月固定日期买入指数ETF", "固定金额买入，不择时", "长期年化8-12%，适合养老", "长期配置"),
    ("打新策略", "套利", "持有沪深市值打新，沪深各1万", "市值>1万即可参与，沪深各配", "年化增强5-10%", "制度套利"),
    ("分级A轮动", "套利", "分级A价格<0.85时买入，>1.00时卖出", "类固收，隐含收益率>5%", "机构玩法，流动性差", "固定收益"),
    ("REITs配置", "配置", "配置优质REITs获取稳定分红", "分散于不同类型REITs", "年化4-8%，抗通胀", "资产配置"),
    ("可转债策略", "条款博弈", "价格<105且溢价率<20%的双低转债", "双低策略: 价格低+溢价低", "下有保底上不封顶", "条款博弈"),
]

def init_strategies():
    conn = _get_conn()
    for name, stype, desc, impl, result, source in STRATEGIES_SEED:
        conn.execute("""
            INSERT OR IGNORE INTO strategies(name,type,description,implementation,backtest_result,source,created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (name, stype, desc, impl, result, source, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def get_strategies(stype: str = "") -> list[dict]:
    conn = _get_conn()
    if stype:
        rows = conn.execute("SELECT * FROM strategies WHERE type=? ORDER BY name", (stype,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM strategies ORDER BY type, name").fetchall()
    conn.close()
    cols = ["id","name","type","description","implementation","backtest_result","source","created_at"]
    return [dict(zip(cols, r)) for r in rows]

# ── 研报摘要 ──────────────────────────────────────────
def save_research_note(code: str, title: str, source: str, summary: str,
                       sentiment: str = "中性", tags: str = "") -> int:
    conn = _get_conn()
    cur = conn.execute("""
        INSERT INTO research_notes(code,title,source,summary,sentiment,tags,created_at)
        VALUES (?,?,?,?,?,?,?)""",
        (code, title, source, summary, sentiment, tags, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    nid = cur.lastrowid
    conn.close()
    return nid

def get_research_notes(code: str = "", limit: int = 50) -> list[dict]:
    conn = _get_conn()
    if code:
        rows = conn.execute("""
            SELECT * FROM research_notes WHERE code=? ORDER BY created_at DESC LIMIT ?""",
            (code, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM research_notes ORDER BY created_at DESC LIMIT ?""",
            (limit,)).fetchall()
    conn.close()
    cols = ["id","code","title","source","summary","sentiment","tags","created_at"]
    return [dict(zip(cols, r)) for r in rows]

# ── 基金经理风格 ──────────────────────────────────────
def save_fund_style(manager_name: str, style: str, tags: str,
                    strength: str, weakness: str) -> int:
    conn = _get_conn()
    cur = conn.execute("""
        INSERT OR REPLACE INTO fund_styles(manager_name,style,tags,strength,weakness,updated_at)
        VALUES (?,?,?,?,?,?)""",
        (manager_name, style, tags, strength, weakness, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return mid

def get_fund_styles() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM fund_styles ORDER BY manager_name").fetchall()
    conn.close()
    cols = ["id","manager_name","style","tags","strength","weakness","updated_at"]
    return [dict(zip(cols, r)) for r in rows]

def match_fund_style(target_traits: str) -> list[dict]:
    """根据特征词匹配风格相似的基金经理
    target_traits: 如 "价值 低波动 高夏普"
    """
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM fund_styles").fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(zip(["id","manager_name","style","tags","strength","weakness","updated_at"], row))
        # 简单匹配：标签重叠多优先
        score = sum(1 for kw in target_traits.split() if kw in d.get("tags",""))
        results.append((score, d))
    results.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in results if _ > 0]

# ── 量化研报问答 ─────────────────────────────────────
QUANT_QA = [
    ("PE为负能买吗？", "PE为负表示公司亏损，看PB和现金流更可靠。若扭亏预期明确，PE参考价值不大。"),
    ("北向资金怎么看？", "北向资金（外资）持有市值变化可在东财/同花顺查。持续净买入=外资看好，但需结合估值。"),
    ("布林带怎么用？", "20日布林带：中轨=20日均线，上轨=中轨+2倍标准差，下轨=中轨-2倍标准差。价格触及下轨考虑买入。"),
    ("什么是量化交易？", "用数学模型选股，纪律性强，避免人为情绪干扰。包括多因子、统计套利、机器学习等方法。"),
    ("打新需要多少市值？", "沪市和深市各需至少1万元股票市值才能参与打新。沪深各配号，提高中奖率。"),
    ("什么是融资融券？", "融资=借钱买股票（做多），融券=借股卖出（做空）。杠杆放大收益也放大亏损。"),
    ("RSI指标怎么用？", "RSI>70表示超买（可能下跌），RSI<30表示超卖（可能反弹）。震荡市有效，单边市失效。"),
    ("什么是阿尔法收益？", "阿尔法=基金实际收益 - 基准收益。正阿尔法表示跑赢大盘，是基金经理能力的体现。"),
    ("什么是夏普比率？", "每承受一单位风险获得的超额收益。夏普比率>0.5算优秀，越高越好。"),
    ("ROE和ROA什么区别？", "ROE=净利润/净资产（股东视角），ROA=净利润/总资产（整体资产利用效率）。ROE更受关注。"),
    ("什么是PEG指标？", "PEG=PE/净利润增速。PEG<1表示成长股被低估（假设增速持续），PEG>1.5表示偏贵。"),
    ("基金限购意味着什么？", "基金限制申购通常为保护持有人利益（防止规模过大难以管理，或仓位快速上升）。有时也是基金经理对后市谨慎。"),
    ("什么是风格漂移？", "风格漂移指基金实际持仓风格与招募说明书不符。比如名字叫大盘价值但实际重仓小盘成长。需用持仓穿透检验。"),
    ("基金经理离职怎么办？", "关注：1)是否有共同管理其他基金经理接任；2）新基金经理历史业绩；3）持仓风格是否可能大变。一般可观察一两个季度再决定是否赎回。"),
    ("ETF和LOF什么区别？", "ETF是交易所交易基金，盘中实时报价，跟踪指数。LOF是上市型开放基金，场外可申购，两者都可以在二级市场买卖。"),
    ("什么是对冲？", "对冲=同时做多和做空相关资产，降低风险。常见做法是买入股票同时做空股指期货，或买入个股同时买入看跌期权。"),
]

def ask_quant_question(q: str) -> str:
    """回答常见量化问题"""
    q_lower = q.lower()
    for keywords, answer in QUANT_QA:
        if any(kw in q_lower for kw in keywords.lower().split()):
            return answer
    return "这个问题较专业，建议查阅基金招募说明书或咨询专业投资顾问。"

# ── 初始化并打印状态 ─────────────────────────────────
def init_all():
    init_factors()
    init_strategies()

def print_status():
    conn = _get_conn()
    fc = conn.execute("SELECT COUNT(*) FROM factors").fetchone()[0]
    sc = conn.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
    nc = conn.execute("SELECT COUNT(*) FROM research_notes").fetchone()[0]
    mc = conn.execute("SELECT COUNT(*) FROM fund_styles").fetchone()[0]
    conn.close()
    print(f"因子:{fc} | 策略:{sc} | 研报笔记:{nc} | 经理风格:{mc}")

if __name__ == "__main__":
    init_all()
    print("=== 量化知识库状态 ===")
    print_status()
    print("\n=== 因子列表(估值类) ===")
    for f in get_factors("估值"):
        print(f"  [{f['name']}] {f['description']}")
    print("\n=== 策略列表(趋势类) ===")
    for s in get_strategies("趋势"):
        print(f"  [{s['name']}] {s['description']}")
    print("\n=== 回答测试 ===")
    print(ask_quant_question("PE为负能买吗？"))
