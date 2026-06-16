#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键全量抓取 + 筛选 + 跟踪产品 + Windows对话框展示
用法:
  python run_full_daily_dialog.py --all        # 股票+基金+弹框
  python run_full_daily_dialog.py --stocks     # 仅股票
  python run_full_daily_dialog.py --funds      # 仅基金
  python run_full_daily_dialog.py --forecast 600519   # 单独预测
  python run_full_daily_dialog.py --text-only  # 仅文本，不弹框
"""
import sys, os, json, time, re, datetime, ctypes
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, str(SKILL_DIR / "pkg"))

from crawl_utils import safe_request, today_str, write_json, read_json
from prediction_cn import forecast_stock

DATA_DIR = SKILL_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

def show_dialog(title, message, kind="info"):
    style_map = {"info": 0x40, "warn": 0x30, "error": 0x10}
    style = style_map.get(kind, 0x40)
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, style)
    except Exception:
        print(f"[{title}] {message}")

def fmt_price(p):
    if p is None: return "N/A"
    try: return f"\u00a5{float(p):.2f}"
    except: return str(p)

def fmt_pct(p):
    if p is None: return "N/A"
    try:
        v = float(p)
        return f"{v:+.2f}%" if v != 0 else "0.00%"
    except: return str(p)

def load_today_stocks():
    date_str = today_str()
    for src in [DATA_DIR / f"all_stocks_{date_str}.json",
                DATA_DIR / f"stocks_filtered_{date_str}.json",
                DATA_DIR / f"stocks_raw_{date_str}.json"]:
        if src.exists():
            data = read_json(src, [])
            if isinstance(data, list) and data:
                print(f"  [数据源] {src.name} ({len(data)}只)")
                return data, date_str
    return [], date_str

def load_today_funds():
    date_str = today_str()
    for src in [DATA_DIR / f"all_funds_{date_str}.json",
                DATA_DIR / f"fund_raw_{date_str}.json",
                DATA_DIR / f"fund_filtered_{date_str}.json"]:
        if src.exists():
            data = read_json(src, [])
            if isinstance(data, list) and data:
                print(f"  [数据源] {src.name} ({len(data)}只)")
                return data, date_str
    return [], date_str

def filter_rank_stocks(stocks):
    filtered = []
    for s in stocks:
        code = str(s.get("code", "")).strip()
        name = str(s.get("name", "")).strip()
        if not code or not name: continue
        if "ST" in name or "*ST" in name: continue
        pe = s.get("pe")
        try: pe_val = float(pe) if pe not in (None, "", "N/A", "nan") else None
        except: pe_val = None
        if pe_val is not None and (pe_val < 0 or pe_val > 200): continue
        turnover = s.get("turnover")
        try: turnover_val = float(turnover) if turnover not in (None, "") else 0
        except: turnover_val = 0
        if turnover_val < 2: continue
        mkt = s.get("market_cap") or s.get("float_cap") or 0
        try: mkt_val = float(mkt)
        except: mkt_val = 0
        if mkt_val > 0 and mkt_val < 5e8: continue
        filtered.append(s)

    scored = []
    for s in filtered:
        code = str(s.get("code", "")).strip()
        name = str(s.get("name", "")).strip()
        price = s.get("price")
        try: pe_val = float(s.get("pe")) if s.get("pe") not in (None, "", "N/A") else 30
        except: pe_val = 30
        try: turnover_val = float(s.get("turnover")) if s.get("turnover") else 0
        except: turnover_val = 0
        try: change_val = float(s.get("change_pct") or 0)
        except: change_val = 0

        score = 0; reasons = []
        if 10 <= pe_val <= 25: score += 25; reasons.append(f"PE={pe_val:.0f} ok")
        elif pe_val < 10: score += 15; reasons.append(f"PE={pe_val:.0f}低")
        elif pe_val <= 50: score += 10
        if 2 <= turnover_val <= 5: score += 20; reasons.append(f"换手{turnover_val:.1f}%")
        elif turnover_val > 5: score += 15; reasons.append(f"换手{turnover_val:.1f}%活")
        flow_net = s.get("main_net_inflow") or 0
        try: flow_val = float(flow_net)
        except: flow_val = 0
        if flow_val > 1e8: score += 25; reasons.append(f"净入{flow_val/1e8:.1f}亿")
        elif flow_val > 0: score += 15
        if 0 <= change_val <= 3: score += 20; reasons.append(f"涨幅{change_val:.1f}%")
        elif change_val > 3: score += 10
        elif change_val >= -2: score += 15
        try:
            fore = forecast_stock(code)
            if "error" not in fore:
                prob_up = fore.get("mc_forecast", {}).get(1, {}).get("prob_up", 0.5)
                if prob_up >= 0.55: score += 10; reasons.append(f"看涨{prob_up:.0%}")
                elif prob_up <= 0.40: score += 0; reasons.append(f"看跌{prob_up:.0%}")
        except: pass

        scored.append({
            "code": code, "name": name, "price": price,
            "change_pct": change_val, "score": score,
            "reasons": " | ".join(reasons) if reasons else "综合普通"
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored

def filter_rank_funds(funds):
    filtered = []
    for f in funds:
        code = str(f.get("fund_code", f.get("code", ""))).strip()
        name = str(f.get("name", "")).strip()
        if not code or not name: continue
        nav = f.get("nav") or f.get("dwjz")
        try: nav_val = float(nav) if nav not in (None, "", "N/A") else None
        except: nav_val = None
        if nav_val is None: continue
        scale = str(f.get("asset_scale") or f.get("scale") or "0")
        try:
            if "亿" in scale: scale_val = float(re.sub(r"[^0-9.]", "", scale)) * 1e8
            else: scale_val = float(re.sub(r"[^0-9.]", "", scale))
        except: scale_val = 0
        if scale_val > 0 and scale_val < 1e7: continue
        filtered.append(f)

    scored = []
    for f in filtered:
        code = str(f.get("fund_code", f.get("code", ""))).strip()
        name = str(f.get("name", "")).strip()
        nav = f.get("nav"); gsz = f.get("gsz"); change_pct = f.get("change_pct")
        try: change_val = float(change_pct) if change_pct not in (None, "") else 0
        except: change_val = 0
        try: annual_val = float(f.get("annual_yield_1y") or 0)
        except: annual_val = 0
        try: rating_val = int(f.get("morningstar_rating") or 0)
        except: rating_val = 0

        score = 0; reasons = []
        if rating_val >= 4: score += 35; reasons.append(f"晨星{rating_val}星")
        elif rating_val >= 3: score += 20
        if annual_val > 15: score += 30; reasons.append(f"年化{annual_val:.1f}%优")
        elif annual_val > 8: score += 20; reasons.append(f"年化{annual_val:.1f}%良")
        if abs(change_val) < 1: score += 15; reasons.append("今日平稳")
        elif change_val > 0: score += 10
        try:
            scale_str = str(f.get("asset_scale") or f.get("scale") or "0")
            if "亿" in scale_str:
                sv = float(re.sub(r"[^0-9.]", "", scale_str))
                if 5 <= sv <= 100: score += 20; reasons.append(f"规模{sv:.0f}亿适")
                elif sv > 100: score += 10
        except: pass

        scored.append({
            "code": code, "name": name, "nav": nav, "gsz": gsz,
            "change_pct": change_val, "annual_yield": annual_val,
            "rating": rating_val, "score": score,
            "reasons": " | ".join(reasons) if reasons else "综合普通"
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored

TRACKED_STOCKS = [
    {"code": "600519", "name": "贵州茅台", "cost": 1350, "target": 0.20},
    {"code": "000858", "name": "五粮液", "cost": 95, "target": 0.15},
    {"code": "300750", "name": "宁德时代", "cost": 450, "target": 0.25},
]
TRACKED_FUNDS = [
    {"code": "110022", "name": "易方达消费", "cost": 2.8, "target": 0.15},
    {"code": "001667", "name": "天弘沪深300", "cost": 1.8, "target": 0.12},
    {"code": "260108", "name": "景顺新兴成长", "cost": 1.6, "target": 0.20},
]

def tracked_stock_report(items):
    lines = []
    for item in items:
        code = item["code"]; name = item["name"]; cost = item["cost"]; target = item["target"]
        try:
            fore = forecast_stock(code)
            if "error" in fore: lines.append(f"  {name}({code}): 数据获取失败"); continue
            pd = fore.get("price", {})
            cur_price = pd.get("price") or pd.get("current") if isinstance(pd, dict) else pd
            pct_change = (cur_price - cost) / cost * 100 if cur_price else 0
            mc1 = fore.get("mc_forecast", {}).get(1, {})
            ma1 = fore.get("ma_forecast", {}).get(1, {})
            ma3 = fore.get("ma_forecast", {}).get(3, {})
            ma5 = fore.get("ma_forecast", {}).get(5, {})
            prob_up = mc1.get("prob_up", 0.5)
            signal = fore.get("combined_signal", {})
            status = "o"
            if pct_change >= target * 100: status = "* 达标"
            elif pct_change < -10: status = "^ 亏损大"
            lines.append(
                f"{status} {name}({code})
"
                f"  当前:{fmt_price(cur_price)} 成本:{fmt_price(cost)} 收益:{pct_change:+.1f}% 目标:+{target*100:.0f}%
"
                f"  预测: 1d:{signal.get('1d','N/A')}({ma1.get('pct_change',0):+.2f}%) "
                f"3d:{signal.get('3d','N/A')}({ma3.get('pct_change',0):+.2f}%) "
                f"5d:{signal.get('5d','N/A')}({ma5.get('pct_change',0):+.2f}%) 涨概率:{prob_up:.0%}"
            )
        except Exception as e:
            lines.append(f"  {name}({code}): {e}")
    return "
".join(lines)

def tracked_fund_report(items):
    lines = []
    for item in items:
        code = item["code"]; name = item["name"]; cost = item["cost"]; target = item["target"]
        try:
            from pkg.fund_analyzer import fetch_fund_nav
            info = fetch_fund_nav(code)
            nav = info.get("nav") or info.get("dwjz")
            gsz = info.get("gsz")
            change_pct = info.get("change_pct") or 0
            cur_nav = nav if nav else gsz
            pct_change = (cur_nav - cost) / cost * 100 if cur_nav else 0
            try: change_val = float(change_pct) if change_pct else 0
            except: change_val = 0
            pred_1d = change_val * 0.8; pred_3d = change_val * 2.0; pred_5d = change_val * 3.5
            direction = "震荡" if abs(pred_1d) < 0.3 else ("上涨" if pred_1d > 0 else "下跌")
            status = "o"
            if pct_change >= target * 100: status = "* 达标"
            elif pct_change < -10: status = "^ 亏损大"
            lines.append(
                f"{status} {name}({code})
"
                f"  净值:{fmt_price(nav)} 估算:{fmt_price(gsz)} 今日:{fmt_pct(change_pct)}
"
                f"  持仓收益:{pct_change:+.1f}% 目标:+{target*100:.0f}%
"
                f"  预测: 1d:{direction}({pred_1d:+.2f}%) 3d:{direction}({pred_3d:+.2f}%) 5d:{direction}({pred_5d:+.2f}%)"
            )
        except Exception as e:
            lines.append(f"  {name}({code}): {e}")
    return "
".join(lines)

def build_report(stocks, funds, date_str):
    sb = []
    sb.append("=" * 50)
    sb.append(f"  A股全量量化日报 {date_str}")
    sb.append(f"  生成时间: {datetime.datetime.now().strftime('%H:%M:%S')}")
    sb.append("=" * 50)

    sb.append(f"
[全量数据概况]")
    sb.append(f"  股票总数: {len(stocks)} 只")
    sb.append(f"  基金总数: {len(funds)} 只")

    if stocks:
        ranked = filter_rank_stocks(stocks)
        sb.append(f"
[精选股票TOP10] 五维评分")
        sb.append(f"  筛选: PE 0-200 + 换手率>2% + 非ST + 市值>5亿 (符合{len(ranked)}只)")
        sb.append(f"  序  名称        代码      评分  现价       涨跌")
        sb.append(f"  {'-'*50}")
        for i, s in enumerate(ranked[:10], 1):
            sb.append(f"  {i:2}. {s['name'][:8]:<10} {s['code']:<10} {s['score']:<5} "
                     f"{fmt_price(s.get('price')):<10} {fmt_pct(s.get('change_pct')):<8}")
    else:
        sb.append(f"
[精选股票] (今日无全量数据)")

    sb.append(f"
[我的股票持仓]")
    sb.append(tracked_stock_report(TRACKED_STOCKS))

    if funds:
        ranked_f = filter_rank_funds(funds)
        sb.append(f"
[精选基金TOP10]")
        sb.append(f"  序  名称          代码      评分  净值       今日     年化")
        sb.append(f"  {'-'*58}")
        for i, f in enumerate(ranked_f[:10], 1):
            annual = f.get('annual_yield', 0)
            try: annual_str = f"{float(annual):+.1f}%" if annual else "N/A"
            except: annual_str = "N/A"
            sb.append(f"  {i:2}. {f['name'][:10]:<12} {f['code']:<10} {f['score']:<5} "
                     f"{fmt_price(f.get('nav')):<10} {fmt_pct(f.get('change_pct')):<10} {annual_str:<8}")
    else:
        sb.append(f"
[精选基金] (今日无基金数据)")

    sb.append(f"
[我的基金持仓]")
    sb.append(tracked_fund_report(TRACKED_FUNDS))

    desktop = Path.home() / "Desktop"
    sb.append(f"
[Excel输出路径]")
    sb.append(f"  股票: {desktop / f'股票全量表_{date_str}.xlsx'}")
    sb.append(f"  基金: {desktop / f'基金全量表_{date_str}.xlsx'}")

    return "
".join(sb)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="一键全量量化日报")
    parser.add_argument("--stocks", action="store_true", help="股票")
    parser.add_argument("--funds", action="store_true", help="基金")
    parser.add_argument("--all", action="store_true", help="股票+基金")
    parser.add_argument("--forecast", default="", help="单独预测股票")
    parser.add_argument("--text-only", action="store_true", help="仅文本，不弹框")
    args = parser.parse_args()

    if args.forecast:
        code = args.forecast.strip()
        print(f"正在获取 {code} 的预测...")
        try:
            fore = forecast_stock(code)
            if "error" in fore: print(f"[ERROR] {fore.get('error')}")
            else:
                from prediction_cn import print_forecast
                print_forecast(fore)
        except Exception as e:
            print(f"[ERROR] {e}")
        return

    do_stocks = args.stocks or args.all
    do_funds = args.funds or args.all

    print("=" * 55)
    print("  一键全量量化日报")
    print("=" * 55)

    stocks = []; funds = []; date_str = today_str()

    if do_stocks:
        print("
[Step1] 抓取股票...")
        try:
            from crawl_all_sources import fetch_all_stocks
            stocks = fetch_all_stocks(test=False)
        except Exception as e:
            print(f"  [WARN] {e}，读本地...")
            stocks, date_str = load_today_stocks()
        print(f"  -> {len(stocks)} 只")

    if do_funds:
        print("
[Step1] 抓取基金...")
        try:
            from crawl_all_sources import fetch_all_funds
            funds = fetch_all_funds(test=False)
        except Exception as e:
            print(f"  [WARN] {e}，读本地...")
            funds, date_str = load_today_funds()
        print(f"  -> {len(funds)} 只")

    if not stocks and not funds:
        print("
[INFO] 无新数据，读今日本地...")
        s, ds = load_today_stocks()
        f, df = load_today_funds()
        if s or f:
            stocks = s if s else stocks
            funds = f if f else funds
            date_str = ds if s else (df if f else date_str)

    print("
[Step2] 生成Excel...")
    desktop = Path.home() / "Desktop"
    stock_out = None; fund_out = None

    if do_stocks and stocks:
        try:
            sys.path.insert(0, str(SKILL_DIR / "scripts"))
            from generate_full_excel import generate_full_stock_excel
            stock_out = generate_full_stock_excel(date_str)
        except Exception as e:
            print(f"  [WARN] 股票Excel: {e}")

    if do_funds and funds:
        try:
            sys.path.insert(0, str(SKILL_DIR / "scripts"))
            from generate_full_excel import generate_full_fund_excel
            fund_out = generate_full_fund_excel(date_str)
        except Exception as e:
            print(f"  [WARN] 基金Excel: {e}")

    print("
[Step3] 生成报告...")
    report = build_report(stocks, funds, date_str)
    print("
" + report)

    if not args.text_only:
        print("
[INFO] 弹对话框...")
        show_dialog(f"A股全量量化日报 {date_str}", report, "info")

    print("
" + "=" * 55)
    print("  Excel路径:")
    if stock_out: print(f"  股票: {stock_out}")
    if fund_out: print(f"  基金: {fund_out}")
    print("=" * 55)

if __name__ == "__main__":
    main()
