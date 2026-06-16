#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预测准确率追踪与自我优化 v1.0
记录每日预测 → 下一交易日验证 → 计算准确率 → 优化算法/权重/数据源
用法:
  python scripts/prediction_accuracy_tracker.py          # 全量追踪（昨日预测 vs 今日实际）
  python scripts/prediction_accuracy_tracker.py --date   # 指定日期预测的追踪
  python scripts/prediction_accuracy_tracker.py --report # 输出准确率报告+优化建议
"""
from __future__ import annotations
import sys, json, time, math, re, copy
from pathlib import Path
from datetime import datetime, timedelta

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "pkg"))
from crawl_utils import safe_request

# ─────────────────────────────────────────
# 基础工具
# ─────────────────────────────────────────
def sf(v, default=0.0):
    try:
        return float(v) if v not in ("", "-", None, "N/A", "null") else default
    except:
        return default

def fp(v):
    return f"{v:+.2f}%" if v is not None else "N/A"

def get_tx_price(codes):
    """腾讯行情批量获取现价"""
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
        fields = m.group(2).split("~")
        if len(fields) < 10:
            continue
        raw_code = m.group(1)[2:] if m.group(1).startswith(("sh","sz")) else m.group(1)
        result[raw_code] = {
            "name": fields[1], "price": sf(fields[3]),
            "change_pct": sf(fields[31]),
            "prev_close": sf(fields[4]),  # 昨日收盘
        }
    return result

def get_fund_nav(codes):
    """天天基金获取净值"""
    result = {}
    for code in codes:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time()*1000)}"
        raw = safe_request(url, timeout=8)
        if not raw:
            continue
        text = raw.decode("utf-8", errors="replace")
        mr = re.search(r"\((.+)\)", text)
        if not mr:
            continue
        try:
            d = json.loads(mr.group(1))
            result[code] = {
                "name": d.get("name",""), "nav": sf(d.get("dwjz",0)),
                "change_pct": sf(d.get("gszzl",0)),
            }
        except:
            pass
        time.sleep(0.1)
    return result

def get_klines(code, days=130):
    """获取K线（含前后足够数据）"""
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
                return [{"date":item[0], "close":sf(item[2])} for item in day if len(item)>=6]
        return []
    except:
        return []

# ─────────────────────────────────────────
# 预测记录数据库
# ─────────────────────────────────────────
DB_FILE = SKILL_DIR / "data" / "prediction_history.json"

def load_db():
    if DB_FILE.exists():
        with open(DB_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"predictions": {}, "accuracy": {}, "optimizations": [], "model_configs": {}}

def save_db(db):
    DB_FILE.parent.mkdir(exist_ok=True)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def save_prediction(code, pred_date, item_type, pred_data):
    """
    保存某日对某标的的预测
    pred_data = {
        "name": "...", "type": "stock/fund",
        "source": "ma_mc_model",          # 预测方法
        "predictions": {1: {"avg_pct": +1.5, "signal": "微涨", "confidence": 0.83}, 3: {...}, 5: {...}},
        "metadata": {...}
    }
    """
    db = load_db()
    key = f"{code}"
    if key not in db["predictions"]:
        db["predictions"][key] = {}
    db["predictions"][key][pred_date] = pred_data
    save_db(db)

def get_prediction(code, pred_date):
    db = load_db()
    return db["predictions"].get(code, {}).get(pred_date)

def get_predictions_for_code(code, limit=10):
    """获取某标的所有历史预测（最新优先）"""
    db = load_db()
    preds = db["predictions"].get(code, {})
    dates = sorted(preds.keys(), reverse=True)
    return [(d, preds[d]) for d in dates[:limit]]

def record_actual(code, actual_date, actual_data):
    """
    记录某标的在某日期的实际涨跌
    actual_data = {"type": "stock/fund", "close": 100.5, "change_pct": +2.3, "volume": ...}
    """
    db = load_db()
    key = f"{code}"
    if key not in db["predictions"]:
        db["predictions"][key] = {}
    if actual_date not in db["predictions"][key]:
        db["predictions"][key][actual_date] = {}
    db["predictions"][key][actual_date]["actual"] = actual_data
    # 清理超过90天的旧数据
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    for d in list(db["predictions"][key].keys()):
        if d < cutoff:
            del db["predictions"][key][d]
    save_db(db)

# ─────────────────────────────────────────
# 准确率计算
# ─────────────────────────────────────────
def direction_accuracy(preds):
    """方向准确率：预测涨跌方向正确的比例"""
    correct = sum(1 for p in preds if p["pred_dir"] == p["actual_dir"])
    return correct / len(preds) if preds else None

def mae(preds):
    """平均绝对误差"""
    vals = [abs(p["pred_pct"] - p["actual_pct"]) for p in preds]
    return sum(vals)/len(vals) if vals else None

def mape(preds):
    """平均绝对百分比误差（排除actual≈0的情况）"""
    vals = [abs(p["pred_pct"] - p["actual_pct"])/max(abs(p["actual_pct"]), 0.01) for p in preds]
    return sum(vals)/len(vals)*100 if vals else None

def within_tolerance(preds, tol=1.0):
    """预测误差在容忍范围内的比例"""
    ok = sum(1 for p in preds if abs(p["pred_pct"] - p["actual_pct"]) <= tol)
    return ok/len(preds) if preds else None

def calc_all_metrics(preds):
    d = direction_accuracy(preds)
    m = mae(preds)
    mp = mape(preds)
    w1 = within_tolerance(preds, 1.0)
    w2 = within_tolerance(preds, 2.0)
    return {"direction_accuracy": d, "mae": m, "mape": mp,
            "within_1pct": w1, "within_2pct": w2, "sample_size": len(preds)}

def eval_forecast(code, horizon, pred_date):
    """评估某日对某标的某时间窗口的预测"""
    pred_rec = get_prediction(code, pred_date)
    if not pred_rec or "predictions" not in pred_rec:
        return None
    pred_info = pred_rec["predictions"].get(horizon)
    if not pred_info:
        return None

    # 获取实际收盘价（预测日期之后第horizon个交易日）
    item_type = pred_rec.get("type", "stock")
    klines = get_klines(code, days=150) if item_type == "stock" else []
    if item_type == "fund":
        # 基金用净值
        fund_history_url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=30&startDate=&endDate="
        raw = safe_request(fund_history_url, timeout=8)
        klines = []
        if raw:
            try:
                obj = json.loads(raw.decode("utf-8", errors="replace"))
                lsjz = obj.get("Data", {}).get("LSJZList", [])
                for item in lsjz:
                    klines.append({"date": item.get("FSRQ",""), "close": sf(item.get("DWJZ", 0))})
            except:
                pass

    if not klines:
        return None

    date_map = {item["date"]: i for i, item in enumerate(klines)}
    if pred_date not in date_map:
        return None

    start_idx = date_map[pred_date]
    end_idx = start_idx + horizon
    if end_idx >= len(klines):
        return None

    start_price = klines[start_idx]["close"]
    end_price = klines[end_idx]["close"]
    actual_pct = (end_price / start_price - 1) * 100

    pred_pct = pred_info.get("avg_pct", 0)
    pred_dir = "上涨" if pred_pct > 0.5 else ("下跌" if pred_pct < -0.5 else "震荡")
    actual_dir = "上涨" if actual_pct > 0.5 else ("下跌" if actual_pct < -0.5 else "震荡")

    return {
        "code": code, "name": pred_rec.get("name",""),
        "pred_date": pred_date, "horizon": horizon,
        "pred_pct": pred_pct, "pred_dir": pred_dir,
        "actual_pct": round(actual_pct, 3), "actual_dir": actual_dir,
        "error": round(pred_pct - actual_pct, 3),
    }

# ─────────────────────────────────────────
# 优化分析
# ─────────────────────────────────────────
def analyze_by_horizon(preds):
    """按时间窗口分组统计"""
    by_h = {}
    for p in preds:
        h = p["horizon"]
        if h not in by_h:
            by_h[h] = []
        by_h[h].append(p)
    result = {}
    for h, ps in by_h.items():
        result[f"horizon_{h}d"] = calc_all_metrics(ps)
    return result

def analyze_by_confidence(preds):
    """按置信度分组：高/中/低"""
    high = [p for p in preds if p.get("confidence", 0) >= 0.7]
    mid  = [p for p in preds if 0.4 <= p.get("confidence", 0) < 0.7]
    low  = [p for p in preds if p.get("confidence", 0) < 0.4]
    return {
        "high_conf": calc_all_metrics(high) if high else None,
        "mid_conf":  calc_all_metrics(mid) if mid else None,
        "low_conf":  calc_all_metrics(low) if low else None,
    }

def analyze_by_signal(preds):
    """按信号方向分组"""
    up   = [p for p in preds if p["pred_dir"] == "上涨"]
    flat = [p for p in preds if p["pred_dir"] == "震荡"]
    down = [p for p in preds if p["pred_dir"] == "下跌"]
    return {
        "signal_up":   calc_all_metrics(up) if up else None,
        "signal_flat": calc_all_metrics(flat) if flat else None,
        "signal_down": calc_all_metrics(down) if down else None,
    }

def analyze_by_sector(preds):
    """按板块分组"""
    by_sec = {}
    for p in preds:
        sec = p.get("sector", "其他")
        if sec not in by_sec:
            by_sec[sec] = []
        by_sec[sec].append(p)
    result = {}
    for sec, ps in by_sec.items():
        result[sec] = calc_all_metrics(ps)
    return result

def analyze_error_bias(preds):
    """分析系统性偏差：预测是否系统性偏高/偏低"""
    if not preds:
        return {}
    errors = [p["error"] for p in preds]
    avg_err = sum(errors) / len(errors)
    # 正=预测偏高，负=预测偏低
    bias = "偏高" if avg_err > 0.5 else ("偏低" if avg_err < -0.5 else "中性")
    # 哪些标的系统性偏差大
    by_code = {}
    for p in preds:
        c = p["code"]
        if c not in by_code:
            by_code[c] = []
        by_code[c].append(p["error"])
    code_bias = {c: sum(es)/len(es) for c, es in by_code.items() if len(es) >= 2}
    worst = sorted(code_bias.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
    return {"avg_error": round(avg_err, 3), "bias": bias,
            "worst_bias_codes": [{"code": c, "avg_error": round(e,3)} for c, e in worst]}

def suggest_ma_weight_tuning(preds):
    """建议调整MA权重（MA vs MC）"""
    # 分析不同horizon下MA和MC各自的准确率
    suggestions = []
    for h in [1, 3, 5]:
        h_preds = [p for p in preds if p["horizon"] == h and "ma_pct" in p and "mc_pct" in p]
        if len(h_preds) < 3:
            continue
        ma_errs = [abs(p.get("ma_pct",0) - p["actual_pct"]) for p in h_preds]
        mc_errs = [abs(p.get("mc_pct",0) - p["actual_pct"]) for p in h_preds]
        ma_mae = sum(ma_errs)/len(ma_errs)
        mc_mae = sum(mc_errs)/len(mc_errs)
        if mc_mae < ma_mae * 0.8:
            suggestions.append(f"H{h}d: MC误差{ma_mae:.2f} vs MA误差{mc_mae:.2f}，建议提高MC权重至0.8")
        elif ma_mae < mc_mae * 0.8:
            suggestions.append(f"H{h}d: MA误差{ma_mae:.2f} vs MC误差{mc_mae:.2f}，建议提高MA权重至0.8")
        else:
            suggestions.append(f"H{h}d: MA/MC误差相近({ma_mae:.2f}/{mc_mae:.2f})，维持当前0.3/0.7配置")
    return suggestions

def find_similar_cases(code, horizon, top_n=3):
    """寻找同类股票/基金的参考案例"""
    db = load_db()
    candidates = []
    for c, pred_dict in db["predictions"].items():
        if c == code:
            continue
        for d, rec in pred_dict.items():
            if "actual" in rec and horizon in rec.get("predictions", {}):
                p = rec["predictions"][horizon]
                candidates.append({
                    "code": c, "name": rec.get("name",""),
                    "pred_pct": p.get("avg_pct", 0), "pred_dir": p.get("signal",""),
                    "actual_pct": rec["actual"].get("change_pct", 0),
                    "pred_date": d,
                })
    if not candidates:
        return []
    # 找预测方向相同且有实际数据的
    our_pred = get_prediction(code, (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))
    our_pct = our_pred.get("predictions",{}).get(horizon,{}).get("avg_pct",0) if our_pred else 0
    our_dir = "上涨" if our_pct > 0.5 else ("下跌" if our_pct < -0.5 else "震荡")
    similar = [c for c in candidates if c["pred_dir"] == our_dir]
    similar.sort(key=lambda x: abs(x["actual_pct"]), reverse=True)
    return similar[:top_n]

def compute_rolling_accuracy(code, window=10):
    """计算某标的滚动准确率"""
    db = load_db()
    preds = db["predictions"].get(code, {})
    dated_preds = [(d, p) for d, p in preds.items() if "actual" in p]
    dated_preds.sort(key=lambda x: x[0], reverse=True)
    recent = dated_preds[:window]
    all_evals = []
    for d, p in recent:
        for h in [1, 3, 5]:
            ev = eval_forecast(code, h, d)
            if ev:
                all_evals.append(ev)
    return calc_all_metrics(all_evals) if all_evals else None

# ─────────────────────────────────────────
# 每日追踪主流程
# ─────────────────────────────────────────
def track_yesterday_predictions():
    """
    主追踪流程：读取昨日预测数据 → 获取今日实际数据 → 计算准确率 → 更新DB
    """
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 读取昨日各数据源的预测
    db = load_db()
    all_codes = list(db["predictions"].keys())

    # 读取昨日 stock_picks
    picks_file = SKILL_DIR / "data" / f"stock_picks_{yesterday.replace('-','')}.json"
    fund_uni_file = SKILL_DIR / "data" / f"fund_universe_{yesterday}.json"
    tracker_file = SKILL_DIR / "data" / f"tracker_daily_{yesterday}.json"

    updated = 0
    all_evals = []

    # 1. 追踪选股预测
    if picks_file.exists():
        with open(picks_file, encoding="utf-8") as f:
            picks_data = json.load(f)
        for group_key in ["break_high", "break_low"]:
            for item in picks_data.get(group_key, []):
                code = item["code"]
                pred_rec = get_prediction(code, yesterday)
                if not pred_rec or "actual" in pred_rec:
                    continue
                # 获取今日实际
                actuals = get_tx_price([code])
                if code in actuals:
                    act = actuals[code]
                    chg = act["change_pct"]
                    record_actual(code, yesterday, {"type": "stock", "change_pct": chg,
                                                     "close": act["price"], "name": item.get("name","")})
                    updated += 1
                    # 评估
                    for h in [1, 3, 5]:
                        ev = eval_forecast(code, h, yesterday)
                        if ev:
                            ev["sector"] = item.get("industry","其他")
                            ev["group"] = group_key
                            ev["source"] = "analyze_breakthrough"
                            all_evals.append(ev)
                time.sleep(0.1)

    # 2. 追踪基金预测
    if fund_uni_file.exists():
        with open(fund_uni_file, encoding="utf-8") as f:
            fund_data = json.load(f)
        for item in fund_data.get("results", []):
            code = item["code"]
            pred_rec = get_prediction(code, yesterday)
            if not pred_rec or "actual" in pred_rec:
                continue
            navs = get_fund_nav([code])
            if code in navs:
                act = navs[code]
                chg = act["change_pct"]
                record_actual(code, yesterday, {"type": "fund", "change_pct": chg,
                                                  "nav": act["nav"], "name": item.get("name","")})
                updated += 1
                for h in [1, 3, 5]:
                    ev = eval_forecast(code, h, yesterday)
                    if ev:
                        ev["sector"] = item.get("industry","其他")
                        ev["source"] = "fund_universe"
                        all_evals.append(ev)
                time.sleep(0.1)

    # 3. 追踪tracker定向预测
    if tracker_file.exists():
        with open(tracker_file, encoding="utf-8") as f:
            td_data = json.load(f)
        for item in td_data.get("stocks", []) + td_data.get("funds", []):
            code = item["code"]
            pred_rec = get_prediction(code, yesterday)
            if not pred_rec or "actual" in pred_rec:
                continue
            itype = item["type"]
            if itype == "stock":
                prices = get_tx_price([code])
                if code in prices:
                    act = prices[code]
                    chg = act["change_pct"]
                    record_actual(code, yesterday, {"type": "stock", "change_pct": chg,
                                                     "close": act["price"], "name": item.get("name","")})
                    updated += 1
                    for h in [1, 3, 5]:
                        ev = eval_forecast(code, h, yesterday)
                        if ev:
                            ev["source"] = "tracker"
                            all_evals.append(ev)
                    time.sleep(0.1)
            else:
                navs = get_fund_nav([code])
                if code in navs:
                    act = navs[code]
                    chg = act["change_pct"]
                    record_actual(code, yesterday, {"type": "fund", "change_pct": chg,
                                                      "nav": act["nav"], "name": item.get("name","")})
                    updated += 1
                    for h in [1, 3, 5]:
                        ev = eval_forecast(code, h, yesterday)
                        if ev:
                            ev["source"] = "tracker"
                            all_evals.append(ev)
                    time.sleep(0.1)

    return {"date": yesterday, "updated": updated, "evals": all_evals}

# ─────────────────────────────────────────
# 准确率报告生成
# ─────────────────────────────────────────
def generate_accuracy_report():
    """生成完整准确率报告"""
    db = load_db()
    HR = "=" * 100
    SEP = "-" * 100

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{HR}")
    print(f"  预测准确率追踪报告  |  {today}")
    print(HR)

    # 收集所有有actual的评估
    all_evals = []
    for code, pred_dict in db["predictions"].items():
        for d, rec in pred_dict.items():
            if "actual" not in rec:
                continue
            for h in [1, 3, 5]:
                ev = eval_forecast(code, h, d)
                if ev:
                    all_evals.append(ev)

    if not all_evals:
        print("  暂无足够数据（需要至少1个预测周期完成后才有数据）")
        print(HR)
        return

    # 总体统计
    overall = calc_all_metrics(all_evals)
    print(f"\n{HR}")
    print("  【总体准确率】")
    print(HR)
    print(f"  总样本: {overall['sample_size']} 条预测")
    print(f"  方向准确率: {overall['direction_accuracy']:.1%}  (预测涨跌方向正确的比例)")
    print(f"  MAE(平均绝对误差): {overall['mae']:.3f}%")
    print(f"  MAPE: {overall['mape']:.1f}%")
    print(f"  误差≤1%的比例: {overall['within_1pct']:.1%}")
    print(f"  误差≤2%的比例: {overall['within_2pct']:.1%}")

    # 按时间窗口
    by_horizon = analyze_by_horizon(all_evals)
    print(f"\n{HR}")
    print("  【按时间窗口】")
    print(HR)
    print(f"  {'窗口':<10} {'样本':>5} {'方向准确':>8} {'MAE':>8} {'≤1%比例':>8} {'≤2%比例':>8}")
    print(SEP)
    for k, v in sorted(by_horizon.items()):
        n = k.split("_")[1]
        if v:
            da = f"{v['direction_accuracy']:.1%}" if v['direction_accuracy'] else "N/A"
            mae_v = f"{v['mae']:.3f}%" if v['mae'] else "N/A"
            w1 = f"{v['within_1pct']:.1%}" if v['within_1pct'] else "N/A"
            w2 = f"{v['within_2pct']:.1%}" if v['within_2pct'] else "N/A"
            print(f"  {n:<10} {v['sample_size']:>5} {da:>8} {mae_v:>8} {w1:>8} {w2:>8}")

    # 按置信度
    by_conf = analyze_by_confidence(all_evals)
    print(f"\n{HR}")
    print("  【按置信度分组】")
    print(HR)
    print(f"  {'置信分组':<10} {'样本':>5} {'方向准确':>8} {'MAE':>8}")
    print(SEP)
    conf_labels = {"high_conf": "高置信(≥70%)", "mid_conf": "中置信(40-70%)", "low_conf": "低置信(<40%)"}
    for k, v in by_conf.items():
        label = conf_labels.get(k, k)
        if v:
            da = f"{v['direction_accuracy']:.1%}" if v['direction_accuracy'] else "N/A"
            mae_v = f"{v['mae']:.3f}%" if v['mae'] else "N/A"
            print(f"  {label:<10} {v['sample_size']:>5} {da:>8} {mae_v:>8}")

    # 按信号
    by_sig = analyze_by_signal(all_evals)
    print(f"\n{HR}")
    print("  【按信号方向】")
    print(HR)
    print(f"  {'信号':<10} {'样本':>5} {'方向准确':>8} {'MAE':>8}")
    print(SEP)
    sig_labels = {"signal_up": "看涨信号", "signal_flat": "震荡信号", "signal_down": "看跌信号"}
    for k, v in by_sig.items():
        label = sig_labels.get(k, k)
        if v:
            da = f"{v['direction_accuracy']:.1%}" if v['direction_accuracy'] else "N/A"
            mae_v = f"{v['mae']:.3f}%" if v['mae'] else "N/A"
            print(f"  {label:<10} {v['sample_size']:>5} {da:>8} {mae_v:>8}")

    # 偏差分析
    bias = analyze_error_bias(all_evals)
    if bias:
        print(f"\n{HR}")
        print("  【系统性偏差分析】")
        print(HR)
        print(f"  平均误差: {fp(bias.get('avg_error',0))}  ({bias.get('bias','?')})")
        if bias.get("worst_bias_codes"):
            print("  偏差最大的标的:")
            for item in bias["worst_bias_codes"]:
                print(f"    {item['code']}: 平均误差 {fp(item['avg_error'])}")

    # 优化建议
    suggestions = suggest_ma_weight_tuning(all_evals)
    if suggestions:
        print(f"\n{HR}")
        print("  【算法优化建议】")
        print(HR)
        for s in suggestions:
            print(f"  {s}")

    # 预测可信度评级
    if overall["direction_accuracy"] is not None:
        da = overall["direction_accuracy"]
        print(f"\n{HR}")
        print("  【综合评级】")
        print(HR)
        if da >= 0.75:
            print("  A级 — 预测模型较为可靠，方向准确率≥75%")
        elif da >= 0.60:
            print("  B级 — 预测模型基本可用，方向准确率60-75%")
        elif da >= 0.50:
            print("  C级 — 预测模型有待改进，方向准确率50-60%")
        else:
            print("  D级 — 预测模型需重大改进，方向准确率<50%")
        print(f"  建议: {'继续使用当前模型，建议增加样本量' if overall['sample_size'] < 30 else '样本量充足，可进行参数调优'}")

    print(f"\n{HR}")
    print(f"  共追踪 {len(db['predictions'])} 个标的的预测记录")
    print(HR)

    # 保存报告
    report = {
        "date": today, "overall": overall,
        "by_horizon": by_horizon, "by_confidence": by_conf,
        "by_signal": by_sig, "bias_analysis": bias,
        "suggestions": suggestions,
        "total_codes": len(db["predictions"]),
    }
    out_file = SKILL_DIR / "data" / f"accuracy_report_{today.replace('-','')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  [完成] 报告已保存至 data/accuracy_report_{today.replace('-','')}.json")
    return report

# ─────────────────────────────────────────
# 将当前预测自动写入DB（对接analyze_breakthrough等脚本）
# ─────────────────────────────────────────
def register_todays_predictions():
    """
    在每日分析结束后调用，将当日所有预测注册到追踪DB
    对接 stock_picks / fund_universe / tracker_daily 的输出
    """
    today = datetime.now().strftime("%Y-%m-%d")
    db = load_db()
    count = 0

    # 1. 注册 stock_picks
    picks_file = SKILL_DIR / "data" / f"stock_picks_{today.replace('-','')}.json"
    if picks_file.exists():
        with open(picks_file, encoding="utf-8") as f:
            data = json.load(f)
        for group_key in ["break_high", "break_low"]:
            for item in data.get(group_key, []):
                code = item["code"]
                pred = {
                    "name": item.get("name",""), "type": "stock",
                    "sector": item.get("industry","其他"),
                    "source": "analyze_breakthrough", "group": group_key,
                    "predictions": item.get("predictions", {}),
                    "metadata": {k: v for k, v in item.items()
                                 if k not in ("code","name","industry","predictions")},
                }
                if item.get("predictions"):
                    save_prediction(code, today, "stock", pred)
                    count += 1

    # 2. 注册 fund_universe
    fund_file = SKILL_DIR / "data" / f"fund_universe_{today}.json"
    if fund_file.exists():
        with open(fund_file, encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("results", []):
            code = item["code"]
            pred = {
                "name": item.get("name",""), "type": "fund",
                "sector": item.get("industry","综合"),
                "source": "fund_universe_analyzer",
                "predictions": item.get("prediction",{}).get("forecasts",{}),
                "metadata": {k: v for k, v in item.items()
                             if k not in ("code","name","industry","prediction")},
            }
            if item.get("prediction",{}).get("forecasts"):
                save_prediction(code, today, "fund", pred)
                count += 1

    # 3. 注册 tracker_daily
    td_file = SKILL_DIR / "data" / f"tracker_daily_{today}.json"
    if td_file.exists():
        with open(td_file, encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("stocks", []) + data.get("funds", []):
            code = item["code"]
            itype = item["type"]
            pred = {
                "name": item.get("name",""), "type": itype,
                "source": "tracker_daily_report",
                "predictions": item.get("prediction",{}).get("forecasts",{}),
                "metadata": {k: v for k, v in item.items()
                             if k not in ("code","name","type","prediction")},
            }
            if item.get("prediction",{}).get("forecasts"):
                save_prediction(code, today, itype, pred)
                count += 1

    print(f"[注册完成] 今日{today}共注册{count}条预测到追踪系统")
    return count

# ─────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="预测准确率追踪与优化")
    parser.add_argument("--track", action="store_true", help="追踪昨日预测的准确率")
    parser.add_argument("--register", action="store_true", help="注册当日预测到追踪系统")
    parser.add_argument("--report", action="store_true", help="生成准确率报告+优化建议")
    args = parser.parse_args()

    if args.track:
        result = track_yesterday_predictions()
        print(f"追踪完成: 更新{result['updated']}条, 评估{len(result['evals'])}条")
    elif args.register:
        register_todays_predictions()
    elif args.report:
        generate_accuracy_report()
    else:
        # 默认：先注册今日，再追踪昨日，再报告
        register_todays_predictions()
        print()
        result = track_yesterday_predictions()
        print(f"追踪完成: 更新{result['updated']}条, 评估{len(result['evals'])}条")
        print()
        generate_accuracy_report()
