#!/usr/bin/env python3
"""
nuwa DNA 基金经理话术生成器 v2
数据源: distill 34,437条 (经理x基金) + 天天基金4,204人基础字段
输出: fund_managers_speech_by_company.json (按公司分组)
      fund_managers_speech_v2_index.json (扁平索引)
生成: 2026-05-21
"""
import json, os, random
from datetime import datetime
from collections import defaultdict

# 使用相对于脚本位置的路径，增强跨平台兼容性
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DATA = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "data")
MANAGER_DATA = os.path.join(SKILL_DATA, "fund_managers_distilled.json")
TTJJ_DATA = os.path.join(SKILL_DATA, "全市场基金经理名录_天天基金.json")
OUTPUT_DIR = SKILL_DATA

# ═══════════════════════════════════════════════════════════
# nuwa DNA 语料库
# ═══════════════════════════════════════════════════════════
VIEW_BALANCED = [
    "我的想法比较简单，均衡配置，不赌单一方向。长期下来这样可能更稳一些。",
    "我不追求买在最低、卖在最高。配置均衡一些，持有体验会好很多。",
    "市场短期波动很难预测，但长期看，中国经济的韧性还是很强的。",
    "我更看重公司的质地，而不是择时。选好公司，长期持有，这话说起来容易，做起来难。",
    "说实话，波动大的时候我也会担心，但只要方向没变，我会保持仓位。",
    "这些年下来我的体会是：不要太贪，也不要太慌。",
    "均衡的好处是，当某个板块调整的时候，其他仓位可以形成对冲。",
    "我不太喜欢择时，更愿意把精力放在选股上。",
    "好公司的股价波动大，但长期持有回报是可观的。",
    "我的组合里既有成长类资产，也有防御类资产，这样心态会稳一些。",
    "配置均衡的好处是，市场大幅波动的时候，组合不会伤筋动骨。",
    "只要管理的产品还在，我的投资逻辑就不会变。",
]
VIEW_GROWTH = [
    "我比较喜欢挖掘成长股的机会，像科技、新能源这些赛道我研究得比较多。",
    "风格上偏进攻，波动可能会大一些，但我觉得长期回报会更好。",
    "成长股波动大，但只要看准了方向，赔率是很高的。",
    "我不太喜欢择时，更愿意把精力放在选股上。好的成长股，持有时间越长，回报越可观。",
    "科技和新能源是我长期看好的方向，渗透率还在低位，成长空间很大。",
    "投资成长股最重要是看产业趋势，只要趋势没变，短期的调整是机会。",
    "我更关注公司的长期竞争力，而不是短期估值波动。",
    "成长股投资要有耐心，短期内股价可能偏离基本面，但长期一定会回归。",
    "我不怕买得贵，就怕买错公司。",
    "制造业升级和能源革命是我最看好的两条主线。",
    "选成长股最重要的是看管理层和竞争格局，行业beta只是辅助。",
]
SECTOR_VIEWS = {
    "医药":   "医药行业长期逻辑清晰，人口老龄化是确定性很高的趋势。创新药械是核心方向。",
    "新能源": "新能源渗透率还在提升阶段，储能、海风、电网改造都是我看好的细分领域。",
    "科技":   "科技投资核心看产品力和生态壁垒，中国科技公司全球竞争力在提升。",
    "消费":   "消费升级和消费分化是两条主线，高性价比品牌和高端龙头都有机会。",
    "半导体": "半导体国产替代是长期主题，但要注意库存周期的影响。",
    "军工":   "军工订单刚性，受宏观经济影响小，是防御性较强的成长方向。",
    "港股":   "港股估值有吸引力，但受海外流动性影响大，需关注汇率和美股走势。",
    "QDII":   "海外市场提供差异化配置价值，但要注意汇率风险和海外宏观波动。",
    "制造":   "制造业升级是长期主线，中国制造正在向全球价值链高端延伸。",
    "金融":   "金融板块估值低，但需关注资产质量和利率环境的变化。",
    "农业":   "农业板块波动大，价格周期明显，适合逆向布局。",
    "ETF":    "指数投资透明、高效，是资产配置的良好工具。",
    "量化":   "量化策略能在波动市中提供稳定的超额收益来源。",
    "债券":   "债券是资产组合的稳定器，在市场不确定时提供保护。",
    "REITs":  "REITs提供稳定的现金流收益，是分散投资的好选择。",
    "医疗":   "医疗行业长期逻辑清晰，人口老龄化是确定性很高的趋势。",
    "新能源车": "新能源车渗透率快速提升，智能化是下半场竞争的核心。",
    "有色金属": "有色金属受益于全球能源转型，铜和锂是核心品种。",
    "房地产": "房地产行业还在调整期，但政策底已经出现。",
    "煤炭":   "煤炭供需格局改善，估值有支撑，但长期趋势向下。",
    "石油":   "石油价格受地缘政治影响大，中期供给约束仍在。",
    "银行":   "银行板块估值低位，资产质量边际改善，股息率有吸引力。",
    "计算机": "计算机行业受益于AI产业化，软件和算力是两条主线。",
}
INTRO_TEMPLATES = [
    "{name}，{years:.1f}年经验，现任{company}{fund}基金经理。",
    "{name}，{years:.1f}年投研经验，现任{company}{fund}基金经理，风格{style}。",
    "{name}，资本市场沉浮{years:.1f}年，现任{company}基金经理，管理{fund}。",
    "{name}，{years:.1f}年投资老将，现任{company}基金经理，长期坚守{style}风格。",
]
SUITABLE_TEMPLATES = [
    "适合{total_years:.0f}年以上投资周期、能承受一定波动的{suitable}类型投资者。",
    "如果您认可{style}投资理念，并愿意中长期持有，{fund}比较适合您。",
    "建议持有周期{total_years:.0f}年以上，追求中长期稳健增长的家庭理财配置。",
]
GAIN_SPEECH = {
    "1y":  "持有1年左右，收益可能还不稳定，我更看重组合的配置逻辑有没有变化。",
    "3y":  "持有3年左右，一般能经历一个完整周期，这时候看绝对收益更有意义。",
    "5y+": "持有5年以上，才能真正体现专业投资和长期持有相结合的价值。",
}
LOSS_TEMPLATES = [
    "短期波动是市场的常态，我的组合配置相对均衡，下跌幅度应该有限。",
    "市场的周期性调整是正常的，这时候最重要的是不要在低位卖出。",
    "这种级别的下跌确实很煎熬。但从历史经验看，优秀管理人在危机时刻反而是超额收益的来源。",
]

# ═══════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════
def style_disp(s):
    return "均衡配置" if s == "均衡型" else "成长进取"

def loss_idx(y):
    return 0 if y < 3 else (1 if y < 8 else 2)

def intro_idx(y):
    return 0 if y < 3 else (1 if y < 8 else (2 if y < 13 else 3))

def build_intro(name, company, fund, years, s):
    sd = style_disp(s)
    i = intro_idx(years)
    return INTRO_TEMPLATES[i].format(name=name, years=years, company=company, fund=fund, style=sd)

def build_suitable(years, s, fund, suitable_inv):
    sd = style_disp(s)
    sm = {"":"平衡型","平衡型":"平衡型","积极型":"积极型","保守型":"保守型"}
    sd2 = sm.get(suitable_inv, "平衡型")
    return random.choice(SUITABLE_TEMPLATES).format(
        total_years=max(int(years),2), style=sd, suitable=sd2, fund=fund)

def build_views(s, fund, company, sector_desc):
    pool = VIEW_GROWTH if s == "成长型" else VIEW_BALANCED
    stmts = random.sample(pool, min(2, len(pool)))
    all_txt = (fund or "") + (company or "") + (sector_desc or "")
    for kw, view in SECTOR_VIEWS.items():
        if kw in all_txt and view not in stmts:
            stmts.insert(0, view)
            break
    return stmts

def get_stock_names(top_stocks):
    if not top_stocks:
        return []
    names = []
    for s in top_stocks[:5]:
        if isinstance(s, dict):
            names.append(s.get("stock_name",""))
        elif isinstance(s, str):
            names.append(s)
    return [n for n in names if n]

def generate_speech(r, ttjj_by_key):
    name    = r["name"]
    company = r["company_name"]
    fund    = r["current_fund_name"] or "在管基金"
    fund_cd = r["current_fund_code"] or ""
    s       = r.get("investment_style") or "均衡型"
    years   = r.get("tenure_years") or 0
    ttjj    = ttjj_by_key.get((name, company), {})
    aum     = ttjj.get("aum", "")
    inv_goal   = str(r.get("investment_goal") or "")
    inv_scope  = str(r.get("investment_scope") or "")
    inv_period = str(r.get("investment_period") or "")
    top_stocks = get_stock_names(r.get("top_stocks") or [])
    suitable_inv = r.get("suitable_investors") or ""

    gain_key = "1y" if years < 2 else ("3y" if years < 5 else "5y+")
    li = loss_idx(years)
    sd = style_disp(s)

    if top_stocks:
        stocks_str = "、".join(top_stocks[:5])
        holding_q = (f"{fund}是我目前管理的产品之一。"
                     f"前十大持仓包括{stocks_str}，"
                     f"整体配置兼顾成长与防御，注重个股基本面质量。")
    else:
        holding_q = (f"{fund}是我目前管理的产品。"
                     f"组合以{sd}策略为核心，注重精选个股和动态再平衡。")

    return {
        "manager_id_ttjj": ttjj.get("manager_id_ttjj",""),
        "name": name,
        "company": company,
        "fund_code": fund_cd,
        "fund_name": fund,
        "style": s,
        "tenure_years": years,
        "aum": aum,
        "scenarios": {
            "intro":         build_intro(name, company, fund, years, s),
            "suitable":     build_suitable(years, s, fund, suitable_inv),
            "views":        build_views(s, fund, company, str(r.get("sector_description") or "")),
            "opinion":      (f"关于{company}，我们有系统的研究框架。"
                           f"管理目标是在控制回撤的前提下争取超额收益。"
                           + (f" {inv_goal[:60]}。" if inv_goal else "")),
            "strategy":     (f"{fund}以{sd}策略为核心，"
                           f"投资范围{inv_scope[:50] if inv_scope else '聚焦A股优质标的'}。"
                           + (f"建议持有周期：{inv_period}。" if inv_period else "")),
            "loss_comfort": LOSS_TEMPLATES[li],
            "gain_speech":  GAIN_SPEECH[gain_key],
            "holding_query": holding_q,
        },
    }

# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading distill data...")
    with open(MANAGER_DATA, "r", encoding="utf-8") as f:
        managers_raw = json.load(f)["managers"]
    print(f"  distill records: {len(managers_raw)}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading 天天基金 data...")
    with open(TTJJ_DATA, "r", encoding="utf-8") as f:
        ttjj_data = json.load(f)
    ttjj_by_key = {}
    for rec in ttjj_data["raw"]:
        key = (rec[1], rec[3])
        if key not in ttjj_by_key:
            ttjj_by_key[key] = {
                "manager_id_ttjj": rec[0],
                "tenure_days_ttjj": int(rec[6]) if rec[6].isdigit() else 0,
                "aum": rec[10],
            }
    print(f"  ttjj lookup keys: {len(ttjj_by_key)}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating speeches ({len(managers_raw)} records)...")
    random.seed(42)
    all_speeches = []
    by_company = defaultdict(list)
    index = {}

    for i, r in enumerate(managers_raw):
        if i % 5000 == 0:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {i}/{len(managers_raw)}")
        speech = generate_speech(r, ttjj_by_key)
        all_speeches.append(speech)
        by_company[r["company_name"]].append(speech)
        key = "{name}|{company}|{fund_code}".format(
            name=r["name"], company=r["company_name"], fund_code=r["current_fund_code"])
        index[key] = i

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Done: {len(all_speeches)} records, {len(by_company)} companies")

    SPEECH_DB = os.path.join(OUTPUT_DIR, "fund_managers_speech_by_company.json")
    INDEX_FILE = os.path.join(OUTPUT_DIR, "fund_managers_speech_v2_index.json")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Writing speech DB...")
    with open(SPEECH_DB, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {
                "total_records": len(all_speeches),
                "total_companies": len(by_company),
                "generated_at": datetime.now().isoformat(),
                "source": "distill 34,437 + 天天基金 4,204",
                "engine": "nuwa-dna-v2",
                "description": "每条记录 = 经理 x 基金，按公司分组",
            },
            "by_company": dict(by_company),
        }, f, ensure_ascii=False, indent=2)
    print(f"  -> {SPEECH_DB} ({os.path.getsize(SPEECH_DB)/1024/1024:.1f} MB)")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Writing index...")
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    print(f"  -> {INDEX_FILE} ({len(index)} entries)")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ALL DONE")
