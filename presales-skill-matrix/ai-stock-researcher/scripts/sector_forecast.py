#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""板块投资时机分析 v1.0
基于申万行业涨跌+板块内代表性个股预测，判断板块短期投资价值和时间窗口
用法: python scripts/sector_forecast.py
"""
from __future__ import annotations
import sys, json, time, math, re
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "pkg"))
from crawl_utils import safe_request

def sf(v, default=0.0):
    try:
        return float(v) if v not in ("", "-", None, "N/A", "null") else default
    except:
        return default

def fp(v):
    return f"{v:+.2f}%" if v is not None else "N/A"

def calc_returns(prices):
    return [prices[i]/prices[i-1]-1 for i in range(1, len(prices))]

def forecast_ma(closes, periods=[1,3,5]):
    if len(closes) < 5:
        return {}
    ma5=sum(closes[-5:])/5; ma10=sum(closes[-10:])/10; ma20=sum(closes[-20:])/20
    last=closes[-1]; r={}
    for n in periods:
        ma = ma5 if n==1 else (ma10 if n==3 else ma20)
        mean_ret = (ma/last - 1) * 0.5
        drift = (ma10/ma20 - 1) * 0.3 if ma20 > 0 else 0
        pct = (mean_ret + drift) * 100
        r[n] = {"pct": round(pct, 2), "confidence": round(min(0.7, 0.3+0.05*min(n,5)), 2)}
    return r

def forecast_mc(closes, periods=[1,3,5], sims=500):
    import random; random.seed(42)
    if len(closes) < 20:
        return {}
    rets = calc_returns(closes[-120:]) if len(closes)>=120 else calc_returns(closes)
    if len(rets) < 10:
        return {}
    mu=sum(rets)/len(rets); sigma=math.sqrt(sum((r-mu)**2 for r in rets)/len(rets))
    last=closes[-1]; r={}
    for n in periods:
        finals=[]
        for _ in range(sims):
            p=last
            for _ in range(n): p *= (1 + random.gauss(mu, sigma))
            finals.append(p)
        finals.sort()
        pct = (sum(finals)/len(finals) - last)/last*100
        prob_up = sum(1 for p in finals if p>last)/sims
        dc = min(len(rets)/120, 1.0)
        vc = max(0.2, 1.0-min(sigma*4, 0.8))
        r[n] = {"pct": round(pct,2), "prob_up": round(prob_up*100,1),
                "p50": round(finals[sims//2],2), "confidence": round(dc*vc,2)}
    return r

def get_tx_price(codes):
    """批量获取股票价格"""
    if not codes:
        return {}
    ts = ",".join(f"sh{c}" if c.startswith(("6","5")) else f"sz{c}" for c in codes)
    url = f"https://qt.gtimg.cn/q={ts}&_={int(time.time()*1000)}"
    raw = safe_request(url, timeout=8)
    if not raw:
        return {}
    text = raw.decode("gbk", errors="replace")
    result = {}
    for line in text.strip().split("\n"):
        m = re.search(r"v_(\w+)=\"(.+?)\"", line)
        if not m:
            continue
        code_full = m.group(1)
        fields = m.group(2).split("~")
        if len(fields) < 10:
            continue
        raw_code = code_full[2:] if code_full.startswith(("sh","sz")) else code_full
        result[raw_code] = {
            "name": fields[1], "price": sf(fields[3]),
            "change_pct": sf(fields[31]),
        }
    return result

def get_klines(code, days=120):
    prefix = "sh" if code.startswith(("6","5")) else "sz"
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={prefix}{code},day,,,{days},qfq"
    raw = safe_request(url, timeout=8)
    if not raw:
        return []
    text = raw.decode("utf-8", errors="replace").strip()
    text = re.sub(r"^[^=]+=", "", text)
    try:
        obj = json.loads(text)
        stock = obj.get("data", {}).get(f"{prefix}{code}", {})
        for key in ["qfqday", "day", "hfqday"]:
            if key in stock:
                day = stock[key]
                return [{"date":item[0], "close":sf(item[2])} for item in day[-days:] if len(item)>=6]
        return []
    except:
        return []

def predict(code):
    klines = get_klines(code, 120)
    if not klines or len(klines) < 20:
        return {}
    closes = [k["close"] for k in klines]
    last = closes[-1]
    ma_fc = forecast_ma(closes)
    mc_fc = forecast_mc(closes)
    result = {"last_price": last, "forecasts": {}}
    for n in [1, 3, 5]:
        ma_p = ma_fc.get(n, {}).get("pct", 0)
        mc_p = mc_fc.get(n, {}).get("pct", 0)
        avg = ma_p*0.3 + mc_p*0.7
        sig = "上涨" if avg>2 else ("微涨" if avg>0.5 else ("下跌" if avg<-2 else ("微跌" if avg<-0.5 else "震荡")))
        result["forecasts"][n] = {
            "avg_pct": round(avg, 2), "confidence": mc_fc.get(n, {}).get("confidence", 0.5),
            "signal": sig, "prob_up": mc_fc.get(n, {}).get("prob_up", 50),
        }
    return result

# 申万一级行业分布 + 各板块代表股
SECTOR_MAP = {
    "银行":     {"codes": ["600036","601318","600016","601166","600000"], "desc": "估值低、防御性强，跟随宏观利率"},
    "非银金融": {"codes": ["601601","600837","601628","601688","000166"], "desc": "券商/保险，资本市场情绪放大器"},
    "食品饮料": {"codes": ["600519","000858","600887","603288","002304"], "desc": "白酒龙头，防御+消费复苏"},
    "医药生物": {"codes": ["000538","600276","603259","301050","000661"], "desc": "政策免疫+创新驱动，长期价值"},
    "电子":     {"codes": ["002475","603986","000725","600183","688981"], "desc": "AI硬件+半导体周期，波动大"},
    "计算机":   {"codes": ["000977","002410","300033","600570","002230"], "desc": "AI应用+信创，主题催化强"},
    "通信":     {"codes": ["000063","600050","601728","002281","600487"], "desc": "运营商+光通信，AI算力需求"},
    "传媒":     {"codes": ["300059","002027","603444","300413","000503"], "desc": "AI内容+AIGC，主题投资"},
    "军工":     {"codes": ["600893","002013","000733","601985","600760"], "desc": "地缘政治+国防现代化，事件驱动"},
    "新能源":   {"codes": ["300750","002594","600900","601012","002459"], "desc": "光伏/锂电/储能，产能周期压力"},
    "汽车":     {"codes": ["002594","000625","601127","600741","601238"], "desc": "政策补贴+以旧换新，竞争加剧"},
    "房地产":   {"codes": ["000002","600048","600383","001979","600606"], "desc": "政策博弈，销售数据是关键"},
    "有色金属": {"codes": ["601899","600111","000630","002460","601600"], "desc": "大宗商品定价，跟随美元和全球经济"},
    "基础化工": {"codes": ["600309","002601","600486","000301","002064"], "desc": "化工周期，跟随PPI波动"},
    "电力设备": {"codes": ["600900","601012","002459","601615","603806"], "desc": "新能源设备，产能过剩困扰"},
}

def estimate_investment_period(sector, avg5pct, avg1pct, sector_conf):
    """根据板块预测估算投资周期"""
    if avg5pct > 3:
        base = "5-10个交易日"
    elif avg5pct > 1.5:
        base = "3-5个交易日"
    elif avg5pct > 0.5:
        base = "1-3个交易日"
    elif avg5pct > -0.5:
        base = "观望，等待催化"
    elif avg5pct > -2:
        base = "短线1-3日，注意止损"
    else:
        base = "回避，等待底部确认"

    # 置信度调整
    conf_factor = sector_conf / 0.5 if sector_conf > 0 else 1.0
    if conf_factor > 1.5 and avg5pct > 1:
        extended = "（信号较强，可延长1-2天）"
    elif conf_factor < 0.8 and avg5pct > 1:
        extended = "（信号偏弱，缩短周期）"
    else:
        extended = ""

    # 方向调整
    if avg1pct > avg5pct * 2 and avg1pct > 1:
        direction = " | 短期爆发力强，首日优先"
    elif avg1pct < -1 and avg5pct > 0:
        direction = " | 短期震荡，中期看好"
    else:
        direction = ""

    return base + extended + direction

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    HR = "=" * 100
    SEP = "-" * 100

    print("\n" + HR)
    print("  板块投资时机分析  |  " + today)
    print(HR)

    all_codes = []
    for codes in SECTOR_MAP.values():
        all_codes.extend(codes["codes"])
    all_codes = list(dict.fromkeys(all_codes))  # 去重保持顺序

    print(f"\n正在抓取 {len(all_codes)} 只行业代表股行情和K线...")
    prices = get_tx_price(all_codes)
    print(f"  行情获取完成: {len(prices)} 只")

    sector_results = []
    for sector, info in SECTOR_MAP.items():
        codes = info["codes"]
        sector_pred = {}
        reps = []
        for code in codes:
            price_info = prices.get(code, {})
            p = predict(code)
            if p.get("forecasts"):
                reps.append({"code": code, "name": price_info.get("name",""),
                             "price": price_info.get("price",0),
                             "change_pct": price_info.get("change_pct",0),
                             "prediction": p})
            time.sleep(0.05)

        if not reps:
            continue

        # 板块综合预测 = 代表股均值
        def avg_pred(n):
            vals = [r["prediction"]["forecasts"].get(n,{}).get("avg_pct",0) for r in reps if r["prediction"].get("forecasts",{}).get(n)]
            return sum(vals)/len(vals) if vals else 0

        avg1 = avg_pred(1); avg3 = avg_pred(3); avg5 = avg_pred(5)
        conf_vals = [r["prediction"]["forecasts"].get(5,{}).get("confidence",0) for r in reps]
        sector_conf = sum(conf_vals)/len(conf_vals) if conf_vals else 0.3

        sig5 = "上涨" if avg5>2 else ("微涨" if avg5>0.5 else ("下跌" if avg5<-2 else ("微跌" if avg5<-0.5 else "震荡")))

        # 板块涨跌情绪
        pos_count = sum(1 for r in reps if r.get("change_pct",0) > 0)
        neg_count = sum(1 for r in reps if r.get("change_pct",0) < 0)
        neu_count = len(reps) - pos_count - neg_count

        # 投资周期估算
        invest_period = estimate_investment_period(sector, avg5, avg1, sector_conf)

        sector_results.append({
            "sector": sector, "desc": info["desc"],
            "representatives": reps,
            "avg1": round(avg1,2), "avg3": round(avg3,2), "avg5": round(avg5,2),
            "sector_conf": round(sector_conf,2),
            "signal_5d": sig5,
            "pos_neg_neu": f"涨{pos_count}/跌{neg_count}/平{neu_count}",
            "invest_period": invest_period,
        })

    # 按5日平均预测排序
    sector_results.sort(key=lambda x: x["avg5"], reverse=True)

    print("\n" + HR)
    print("  申万一级行业投资信号（按5日预测排序）")
    print(HR)
    print(f"  {'板块':<10} {'今日涨跌分布':>12} {'1日预测':>8s} {'3日预测':>8s} {'5日预测':>8s} {'置信':>5} {'信号':<6} {'投资周期'}")
    print(SEP)
    for s in sector_results:
        sig_map = {"上涨": "看多", "微涨": "偏多", "震荡": "中性", "微跌": "偏空", "下跌": "看空"}
        sig_label = sig_map.get(s["signal_5d"], s["signal_5d"])
        print(f"  {s['sector']:<10} {s['pos_neg_neu']:>12} {fp(s['avg1']):>8s} {fp(s['avg3']):>8s} {fp(s['avg5']):>8s} {s['sector_conf']:.0%} {sig_label:<6} {s['invest_period']}")

    print("\n" + HR)
    print("  各板块代表股预测详情")
    print(HR)
    for s in sector_results:
        sig5 = s["signal_5d"]
        sig_map = {"上涨": "\u8d62", "微涨": "\u504f\u8d62", "震荡": "\u4e2d\u6027", "微跌": "\u504f\u7a7a", "下跌": "\u770b\u7a7a"}
        sig_icon = sig_map.get(sig5, "-")
        print(f"\n  【{s['sector']}】{sig_icon}{sig5} | 5日预测{fp(s['avg5'])} | {s['desc']}")
        print(f"  {'代表股':<12} {'现价':>8} {'今日涨跌':>7s} {'1日预测':>7s} {'3日预测':>7s} {'5日预测':>7s}")
        print(f"  " + "-" * 60)
        for r in s["representatives"]:
            p = r.get("prediction",{}).get("forecasts",{})
            p1=p.get(1,{}); p3=p.get(3,{}); p5=p.get(5,{})
            name = r.get("name","") or r["code"]
            chg = r.get("change_pct", 0)
            chg_str = fp(chg) if chg != 0 else "N/A"
            print(f"  {name[:12]:<12} {r.get('price',0):>8.2f} {chg_str:>7s} {fp(p1.get('avg_pct')):>7s} {fp(p3.get('avg_pct')):>7s} {fp(p5.get('avg_pct')):>7s}")

    print("\n" + HR)
    print("  综合投资建议")
    print(HR)

    buy_sectors = [s for s in sector_results if s["signal_5d"] in ("上涨","微涨") and s["avg5"] > 0.5]
    avoid_sectors = [s for s in sector_results if s["signal_5d"] in ("下跌","微跌") and s["avg5"] < -0.5]

    print("  【值得关注的板块】（5日预测>0.5%，信号偏多）")
    if buy_sectors:
        for s in buy_sectors:
            sig5 = s["signal_5d"]
            sig_map = {"上涨": "强看多", "微涨": "谨慎看多"}
            sig_label = sig_map.get(sig5, sig5)
            print(f"  {s['sector']}: {sig_label} {fp(s['avg5'])} {s['invest_period']}")
            print(f"       {s['desc']}")
    else:
        print("  暂无明确看多板块，建议观望")

    print()
    print("  【需谨慎的板块】（5日预测<-0.5%，信号偏空）")
    if avoid_sectors:
        for s in avoid_sectors:
            print(f"  {s['sector']}: 看空 {fp(s['avg5'])} - {s['invest_period']}")
            print(f"       {s['desc']}")
    else:
        print("  暂无明确看空板块")

    print()
    print("  【市场整体判断】")
    top3 = sector_results[:3]
    bottom3 = sector_results[-3:]
    if top3:
        top_sectors = "、".join([f"{s['sector']}({fp(s['avg5'])})" for s in top3])
        print(f"  资金活跃板块: {top_sectors}")
    if bottom3:
        bot_sectors = "、".join([f"{s['sector']}({fp(s['avg5'])})" for s in bottom3])
        print(f"  资金流出板块: {bot_sectors}")
    print(f"  综合市场信号: 共{len(sector_results)}个板块，{sum(1 for s in sector_results if s['signal_5d'] in ('上涨','微涨'))}个看多，{sum(1 for s in sector_results if s['signal_5d'] in ('下跌','微跌'))}个看空")

    print()
    print(HR)
    print("  注：板块预测基于代表个股的MA+MC模型，历史统计仅供参考，不构成投资建议")
    print(HR)

    # 保存
    out_file = SKILL_DIR / "data" / f"sector_forecast_{today}.json"
    out_file.parent.mkdir(exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"date": today, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "sectors": sector_results}, f, ensure_ascii=False, indent=2)
    print("  [完成] 已保存至 data/sector_forecast_" + today + ".json")

if __name__ == "__main__":
    main()
