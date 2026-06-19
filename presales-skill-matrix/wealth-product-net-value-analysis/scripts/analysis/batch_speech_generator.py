#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import random
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUT_FILE = os.path.join(DATA_DIR, 'fund_managers_speech.json')
INPUT_FILE = os.path.join(DATA_DIR, 'fund_managers_distilled.json')

random.seed(42)

STYLE_OPENINGS = {
    "成长型": ["说实话，", "我觉得吧，", "这些年下来我的体会是，", "我对这块还是比较有信心的，"],
    "价值型": ["我觉得，", "估值角度看，", "我的想法是，", "长期来看，"],
    "均衡型": ["说实话，", "我觉得吧，", "我的想法比较简单，", "说实话我挺看好"],
}
STYLE_OPENINGS[""] = STYLE_OPENINGS["均衡型"]

SECTOR_KEYWORDS = {
    "科技": ["半导体", "国产替代", "AI", "科技", "技术", "龙头", "竞争壁垒"],
    "新能源": ["新能源", "渗透率", "储能", "光伏", "电动车", "清洁能源", "成本优势"],
    "消费": ["消费", "品牌", "复苏", "白酒", "龙头", "估值", "韧性"],
    "医药": ["医药", "创新药", "器械", "估值", "分化", "中药", "品牌中药"],
    "金融": ["银行", "保险", "券商", "估值", "弹性", "压舱石", "基本面"],
    "制造": ["制造", "国产替代", "技术壁垒", "军工", "化工", "差异化", "龙头"],
    "综合": ["均衡配置", "好公司", "质地", "估值", "长期持有", "稳健"],
}

SECTOR_VIEWS = {
    "科技": [
        "半导体这块，我还是比较有信心的。国产替代这条逻辑没变，估值也回调了不少。",
        "AI这波行情还没走完，但接下来会更挑股票，不是眉毛胡子一把抓的时候了。",
        "科技股研究起来挺累的，但机会也确实多。我更偏好龙头的确定性。",
        "科技这块机会是有的，但波动也不小。我更多会关注那些真正能落地的东西，不是概念。",
        "半导体国产替代的逻辑很清晰，这个方向值得长期关注。",
        "消费电子需求还没完全起来，但我更看重有创新能力的公司。",
        "软件估值贵的先等等，竞争格局还没定。",
        "科技创新是长期方向，但短期波动大，我会控制节奏。",
        "找有真正技术壁垒的公司，而不是纯概念。",
    ],
    "新能源": [
        "新能源车渗透率还在往上走，但竞争也激烈了。我会更关注格局稳定的环节。",
        "光伏最近压力不小，产能过剩的问题还没消化完。但长期看，清洁能源的方向没问题。",
        "储能这块我比较看好，逻辑很简单，新能源要大规模用，储能必须跟上。",
        "电动车渗透率起来了，但竞争也到了白热化阶段。我更看重有成本优势的公司。",
        "新能源这波调整还没结束，产能去化需要时间，但我会保持跟踪。",
        "风电和光伏都在降本，这个趋势没变。长期逻辑通顺。",
        "新能源阶段性过热之后会有分化，要精选环节。",
        "氢能源长期有空间，但短期还不成熟。",
    ],
    "消费": [
        "消费复苏比我想象的慢，但龙头公司的韧性还是可以的。",
        "白酒我还在观察，商务消费可以，但大众消费还没完全起来。",
        "找到那些有品牌溢价能力的公司，长期拿着问题不大。",
        "消费这块现在估值不算贵了，但需要耐心等待。逆向布局的感觉。",
        "大众消费还没完全起来，但边际在改善。",
        "餐饮、出行恢复得比较快，但家电还有点压力。",
        "消费品牌要有定价权才能长期跑出来，不然就是周期股。",
        "消费板块估值合理偏低，但需要等催化剂。",
    ],
    "医药": [
        "医药跌了这么久，估值确实有吸引力了。但创新药的不确定性还是要注意。",
        "医疗器械国产替代的逻辑很清晰，我看的时间比较长。",
        "中药最近有动静，但我更关注有真正疗效和产品力的公司。",
        "医药需要精选，不是整个板块都能买。分化会很明显。",
        "创新药风险大，但我愿意赌有真正研发能力的公司。",
        "CXO最近压力不小，海外融资环境还没好转。",
        "医药长期逻辑很通顺，人口老龄化是确定的。",
        "仿制药集采影响在递减，但估值也杀得差不多了。",
    ],
    "金融": [
        "银行板块估值确实低，但弹性也一般。我更多是当作压舱石配置。",
        "券商这两年比较难，但熊市的时候反而应该多看看。",
        "保险我觉得是被低估了，人均收入在提高，对保险的需求也会上来。",
        "地产链还在调整，但我比较关注有独特性的物业公司。",
        "银行让利实体经济的背景下，盈利能力有压力。",
        "配置金融更多是防御思路，不是进攻首选。",
        "资本市场改革对券商长期利好，但短期弹性一般。",
        "金融股便宜是硬道理，但要看有没有催化剂。",
    ],
    "制造": [
        "制造业是中国经济的老本行了，我比较看重有技术壁垒的公司。",
        "军工有点特殊性，我的配置思路是聚焦核心零部件。",
        "化工行业周期性强，我更关注有差异化产品的公司。",
        "机械装备国产替代的空间还挺大的。",
        "高端制造的龙头公司在全球都有竞争力。",
        "喜欢有定价权的制造型企业，而不是纯加工代工。",
        "军工订单确定性高，但信息不透明，要找能跟踪的公司。",
        "新能源带动了相关设备需求，但这波之后要看消化情况。",
    ],
    "综合": [
        "市场短期波动很难预测，但长期看，中国经济的韧性还是很强的。",
        "更看重公司的质地，而不是择时。选好公司，长期持有，这话说起来容易，做起来难。",
        "A股波动大，我的做法是不去猜，专心找好公司。",
        "均衡配置，不赌单一方向。长期下来这样可能更稳一些。",
        "买基金这事，心态很重要。",
        "更愿意慢慢赚钱，不追求一夜暴富。",
        "好公司最终会跑出来。耐心是美德。",
        "不要太贪也不要太慌，这是我这些年最大的体会。",
    ],
}
SECTOR_VIEWS[""] = SECTOR_VIEWS["综合"]

def make_intro(m):
    style = m.get("investment_style", "均衡型")
    yrs = int(m.get("tenure_years", 0))
    name = m.get("name", "")
    co = m.get("company_name", "")
    sector = m.get("sector_description", "")
    intros = {
        "成长型": f"你好，我是{name}。在这个市场里摸爬滚打有{yrs}年了，现在在{co}。我比较喜欢挖掘成长股的机会，{sector}。风格上偏进攻，波动可能会大一些，但我觉得长期回报会更好。",
        "价值型": f"你好，我是{name}。在这个市场里折腾了{yrs}年了，现在在{co}。我的风格偏价值，不追热点，更在意买的便宜。{sector}。目标是找到好公司，在估值合理的时候买进去。",
        "均衡型": f"你好，我是{name}。在这个市场里摸爬滚打有{yrs}年了，现在在{co}。我的风格比较均衡，不会押注单一方向。目标是让净值走势稳一点，不要大起大落。",
    }
    return intros.get(style, intros["均衡型"])

def make_comfort(m, pct):
    style = m.get("investment_style", "均衡型")
    stocks = m.get("top_stocks", [])
    reasons = {
        "成长型": "最近市场对高估值成长股比较谨慎，你的基金重仓科技、新能源，跌幅大一些有这个背景。",
        "价值型": "这波价值风格相对抗跌，但整体市场偏弱，也受到了一些影响。",
        "均衡型": "市场整体不好的时候，偏股型基金都会受影响，这是正常的。",
    }
    reason = reasons.get(style, reasons["均衡型"])
    stock_names = [s["stock_name"] for s in stocks[:3] if s.get("stock_name")]
    stock_part = f"前几大重仓像{'、'.join(stock_names)}，基本面其实没有太大变化。" if stock_names else ""
    endings = [
        "投资这事，心态很重要。有什么问题随时聊。",
        "你的心情我理解，咱们保持沟通。",
        "希望我的想法对你有帮助。市场震荡的时候，更要看清楚手里的牌。",
    ]
    return [
        f"亏钱了肯定不好受，我理解你的心情。说实话，跌了有{pct:.1f}%，我看着也着急。",
        reason,
        stock_part,
        random.choice(endings),
    ]

def make_gain(m, pct):
    style = m.get("investment_style", "均衡型")
    stocks = m.get("top_stocks", [])
    reasons = {
        "成长型": "这波科技、新能源表现不错，赶上了这波行情。",
        "价值型": "价值风格这阵子相对稳，你的基金也受益了。",
        "均衡型": "整体市场氛围不错，加上基金配置的方向对路了。",
    }
    reason = reasons.get(style, reasons["均衡型"])
    stock_names = [s["stock_name"] for s in stocks[:3] if s.get("stock_name")]
    stock_part = f"前几大重仓股{'、'.join(stock_names)}也跟着受益。" if stock_names else ""
    endings = [
        "涨得快的时候人容易冲动，我想提醒一句，别追太猛。落袋为安嘛。",
        "说实话，如果仓位比较重，可以考虑分批减一点。",
        "账户飘红的时候风险管理同样重要，别让盈利变成亏损。",
    ]
    return [
        f"涨了{pct:.1f}%，恭喜你！这种时候心情好是正常的。",
        reason,
        stock_part,
        random.choice(endings),
    ]

def detect_sector(stocks, sector_desc, sectors):
    if sectors:
        return sectors[0]
    if sector_desc:
        for kw in SECTOR_KEYWORDS:
            for word in SECTOR_KEYWORDS[kw]:
                if word in sector_desc:
                    return kw
    for s in (stocks or [])[:3]:
        name = s.get("stock_name", "")
        for kw in SECTOR_KEYWORDS:
            if kw != "综合":
                for word in SECTOR_KEYWORDS[kw]:
                    if word in name:
                        return kw
    return "综合"

def make_view(m):
    sector = detect_sector(m.get("top_stocks", []), m.get("sector_description", ""), m.get("sectors", []))
    style = m.get("investment_style", "均衡型")
    openings = STYLE_OPENINGS.get(style, STYLE_OPENINGS["均衡型"])
    views = SECTOR_VIEWS.get(sector, SECTOR_VIEWS["综合"])
    parts = []
    parts.append(random.choice(openings) + random.choice(views))
    parts.append(random.choice(views))
    if style == "成长型":
        parts.append("我不太喜欢择时，更愿意把精力放在选股上。好的成长股，持有时间越长，回报越可观。")
    elif style == "价值型":
        parts.append("估值便宜是硬道理。耐心等，好公司总会给机会的。")
    else:
        parts.append("我的想法比较简单，均衡配置，不赌单一方向。长期下来这样可能更稳一些。")
    return parts

def make_holdings(m):
    stocks = m.get("top_stocks", [])
    if not stocks:
        return ["目前没有持仓明细数据"]
    lines = []
    for i, s in enumerate(stocks[:5], 1):
        ch = f"{s.get('change', 0):+.1f}%" if s.get('change') else ""
        lines.append(f"  {i}. {s.get('stock_name','')}（占比 {s.get('weight',0)}%）{ch}")
    lines_str = "\n".join(lines)
    return [f"你问我持仓，我直接跟你说。\n{lines_str}\n老实说，基本面没什么大问题。长期来看，这些公司还是有空间的。"]

def make_suitable(m):
    style = m.get("investment_style", "均衡型")
    map_ = {
        "成长型": "适合积极型投资者，能承受较大波动，追求长期高收益。投资周期建议3-5年以上。",
        "价值型": "适合稳健型投资者，不追求暴富，希望稳稳当当跑赢通胀就行。投资周期建议2-3年以上。",
        "均衡型": "适合平衡型投资者，希望收益与风险平衡。适合定投，也适合一次性配置，投资周期2-5年。",
    }
    return map_.get(style, map_["均衡型"])

QDII_KWS = ["QDII", "全球", "海外", "纳斯达克", "标普", "恒生", "美元", "日元", "欧元", "伦敦金", "大宗商品", "原油", "REITs"]

def is_qdii(fund_name, scope):
    for kw in QDII_KWS:
        if kw in (fund_name or "") or kw in (scope or ""):
            return True
    return False

def make_nav(m, nav_info):
    gsz = float(nav_info.get("gszzl", 0))
    fund_name = m.get("current_fund_name", "")
    scope = m.get("investment_scope", "")
    qdii_note = " QDII基金，估值可能存在延迟，请以净值披露为准。" if is_qdii(fund_name, scope) else ""
    parts = []
    parts.append(f"今天（{nav_info.get('gztime','')}）{fund_name}的估算净值是 {nav_info.get('gsz','')}，预计涨跌 {gsz:+.2f}%。{qdii_note}")
    if gsz >= 0:
        parts.append("说实话，今天表现还行，享受上涨的同时保持清醒。")
    else:
        parts.append("老实说，今天有点压力。但非理性的下跌，往往孕育着机会。")
    return parts

def process_managers():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading database...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
    managers = db["managers"]
    total = len(managers)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Total {total:,} managers. Starting...")

    results = []
    errors = 0

    for idx, m in enumerate(managers):
        try:
            sector = detect_sector(
                m.get("top_stocks", []),
                m.get("sector_description", ""),
                m.get("sectors", [])
            )
            record = {
                "manager_id": m.get("manager_id", str(idx)),
                "name": m.get("name", ""),
                "company_name": m.get("company_name", ""),
                "current_fund_code": m.get("current_fund_code", ""),
                "current_fund_name": m.get("current_fund_name", ""),
                "investment_style": m.get("investment_style", "均衡型"),
                "sector": sector,
                "is_qdii": is_qdii(m.get("current_fund_name", ""), m.get("investment_scope", "")),
                "speech": {
                    "intro": make_intro(m),
                    "views": make_view(m),
                    "suitable": make_suitable(m),
                    "holdings": make_holdings(m),
                    "advice": m.get("investment_advice", ""),
                    "warning": m.get("risk_warning", ""),
                    "loss_comfort_pct_10": make_comfort(m, 10.0),
                    "loss_comfort_pct_20": make_comfort(m, 20.0),
                    "gain_speech_pct_10": make_gain(m, 10.0),
                    "personality_intro_raw": m.get("personality_intro", ""),
                }
            }
            results.append(record)
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  ERR [{idx}] {m.get('name','?')}: {e}")

        if (idx + 1) % 5000 == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {idx+1:,}/{total:,} ({(idx+1)/total*100:.1f}%)  errors={errors}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Done! {len(results):,} records, errors={errors}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"managers_speech": results, "meta": {
            "total": len(results),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "fund_managers_distilled.json",
            "version": "2.0-nuwa"
        }}, f, ensure_ascii=False, indent=2)

    sz = os.path.getsize(OUT_FILE)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Written: {OUT_FILE} ({sz/1024/1024:.1f} MB)")
    return results

if __name__ == "__main__":
    process_managers()
