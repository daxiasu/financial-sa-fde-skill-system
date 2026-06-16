#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预测模型自动优化引擎 v1.0
分析历史准确率 → 自动调整MA/MC权重/信号阈值/板块系数 → 验证优化效果
用法:
  python scripts/model_optimizer.py              # 运行优化
  python scripts/model_optimizer.py --dry-run    # 仅分析不应用
  python scripts/model_optimizer.py --show-config # 显示当前模型配置
"""
from __future__ import annotations
import sys, json, math, copy
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "pkg"))
from prediction_tracker import (
    load_db, calc_all_metrics, direction_accuracy,
    suggest_ma_weight_tuning, analyze_by_horizon
)

# ─────────────────────────────────────────
# 模型配置存储
# ─────────────────────────────────────────
CONFIG_FILE = SKILL_DIR / "data" / "model_config.json"

DEFAULT_CONFIG = {
    "ma_mc_weights": {
        "1": {"ma": 0.30, "mc": 0.70},   # 1日：MC为主
        "3": {"ma": 0.35, "mc": 0.65},   # 3日：MC略重
        "5": {"ma": 0.40, "mc": 0.60},   # 5日：MC仍略重
    },
    "signal_thresholds": {
        "up": 0.5,     # >0.5% → 看涨
        "down": -0.5,  # <-0.5% → 看跌
        "strong_up": 2.0,   # >2% → 强看涨
        "strong_down": -2.0,
    },
    "confidence_floor": 0.20,   # 最低置信度
    "min_sample_for_optimize": 10,  # 最少样本量才进行优化
    "version": "1.0",
    "last_updated": None,
    "changelog": [],
}

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        # 合并默认配置（防新字段）
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    return copy.deepcopy(DEFAULT_CONFIG)

def save_config(cfg):
    cfg["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def get_weight(horizon):
    cfg = load_config()
    w = cfg["ma_mc_weights"].get(str(horizon), {"ma": 0.30, "mc": 0.70})
    return w["ma"], w["mc"]

def get_signal_thresholds():
    cfg = load_config()
    return cfg["signal_thresholds"]

def signal_from_avg(avg_pct, horizon=None):
    """根据avg_pct和当前配置判断信号"""
    cfg = load_config()
    th = cfg["signal_thresholds"]
    if avg_pct >= th["strong_up"]:
        return "强上涨"
    elif avg_pct >= th["up"]:
        return "上涨"
    elif avg_pct <= th["strong_down"]:
        return "强下跌"
    elif avg_pct <= th["down"]:
        return "下跌"
    else:
        return "震荡"

# ─────────────────────────────────────────
# 核心优化逻辑
# ─────────────────────────────────────────
def analyze_ma_vs_mc_accuracy(preds):
    """
    分析MA模型 vs MC模型在各horizon的准确率
    返回: {(horizon, model): {"direction_acc": 0.xx, "mae": xx, "count": n}}
    """
    results = {}
    for h in [1, 3, 5]:
        h_preds = [p for p in preds if p.get("horizon") == h]
        ma_preds = [p for p in h_preds if "ma_pct" in p]
        mc_preds = [p for p in h_preds if "mc_pct" in p]
        for model, model_preds in [("ma", ma_preds), ("mc", mc_preds)]:
            if len(model_preds) < 3:
                continue
            key = (h, model)
            # 用单模型预测方向
            th = get_signal_thresholds()
            def single_signal(pct):
                if pct >= th["up"]: return "上涨"
                elif pct <= th["down"]: return "下跌"
                else: return "震荡"
            evals = []
            for p in model_preds:
                actual_pct = p["actual_pct"]
                pred_pct = p.get("ma_pct" if model=="ma" else "mc_pct", 0)
                evals.append({
                    "pred_dir": single_signal(pred_pct),
                    "actual_dir": p["actual_dir"],
                    "pred_pct": pred_pct,
                    "actual_pct": actual_pct,
                })
            da = direction_accuracy(evals)
            mae = sum(abs(e["pred_pct"]-e["actual_pct"]) for e in evals)/len(evals)
            results[key] = {"direction_acc": da, "mae": mae, "count": len(evals)}
    return results

def find_optimal_weights_for_horizon(preds, horizon, ma_range=(0.1, 0.9), step=0.1):
    """
    暴力搜索：找到某horizon下MA/MC最优权重组合
    """
    h_preds = [p for p in preds if p.get("horizon") == horizon and "ma_pct" in p and "mc_pct" in p]
    if len(h_preds) < 5:
        return None

    th = get_signal_thresholds()
    def signal(pct):
        if pct >= th["up"]: return "上涨"
        elif pct <= th["down"]: return "下跌"
        else: return "震荡"

    best = None
    best_score = -1
    ma_weights = []
    w = round(ma_range[0], 1)
    while w <= ma_range[1] + 1e-9:
        ma_weights.append(round(w, 2))
        w += step
    ma_weights = sorted(set(ma_weights))

    for ma_w in ma_weights:
        mc_w = 1 - ma_w
        evals = []
        for p in h_preds:
            combined = ma_w * p.get("ma_pct", 0) + mc_w * p.get("mc_pct", 0)
            evals.append({
                "pred_dir": signal(combined),
                "actual_dir": p["actual_dir"],
                "pred_pct": combined,
                "actual_pct": p["actual_pct"],
            })
        da = direction_accuracy(evals)
        mae = sum(abs(e["pred_pct"]-e["actual_pct"]) for e in evals)/len(evals)
        # 综合评分：方向准确率*0.7 + (1-归一化MAE)*0.3
        norm_mae = min(mae / 5.0, 1.0)  # 假设5%以上MAE为差
        score = da * 0.7 + (1 - norm_mae) * 0.3
        if da is not None and score > best_score:
            best_score = score
            best = {"ma": ma_w, "mc": mc_w, "direction_acc": da, "mae": mae, "score": score}
    return best

def optimize_by_confidence_bins(preds):
    """
    分析不同置信度区间下MA vs MC的准确率
    → 建议高/低置信度下分别用什么权重
    """
    cfg = load_config()
    bins = [
        ("low", 0, 0.4),
        ("mid", 0.4, 0.7),
        ("high", 0.7, 1.0),
    ]
    result = {}
    for label, lo, hi in bins:
        bin_preds = [p for p in preds if lo <= p.get("confidence", 0.5) < hi]
        ma_preds = [p for p in bin_preds if "ma_pct" in p]
        mc_preds = [p for p in bin_preds if "mc_pct" in p]
        th = get_signal_thresholds()
        def signal(pct):
            if pct >= th["up"]: return "上涨"
            elif pct <= th["down"]: return "下跌"
            else: return "震荡"
        def eval_model(model_preds):
            if len(model_preds) < 3: return None
            evals = []
            for p in model_preds:
                pp = p.get("ma_pct" if model_preds==ma_preds else "mc_pct", 0)
                evals.append({"pred_dir": signal(pp), "actual_dir": p["actual_dir"]})
            return direction_accuracy(evals)
        result[label] = {
            "ma_direction_acc": eval_model(ma_preds),
            "mc_direction_acc": eval_model(mc_preds),
            "count": len(bin_preds),
        }
    return result

def analyze_market_regime(preds):
    """
    分析不同市场状态下的准确率（用于判断市场是趋势市还是震荡市）
    通过预测分布判断：如果实际涨跌分布接近50/50，说明市场偏震荡
    """
    up_preds = [p for p in preds if p["pred_dir"] == "上涨"]
    down_preds = [p for p in preds if p["pred_dir"] == "下跌"]
    flat_preds = [p for p in preds if p["pred_dir"] == "震荡"]
    up_acc = direction_accuracy(up_preds) if up_preds else None
    down_acc = direction_accuracy(down_preds) if down_preds else None
    # 判断市场状态
    if up_acc and down_acc:
        if abs(up_acc - down_acc) > 0.2:
            regime = "趋势市" if up_acc > down_acc else "空头趋势"
        else:
            regime = "震荡市"
    else:
        regime = "未知"
    return {"regime": regime, "up_acc": up_acc, "down_acc": down_acc}

def run_optimization(dry_run=False):
    """
    完整优化流程
    """
    db = load_db()
    cfg = load_config()

    # 收集所有有actual的评估
    all_evals = []
    for code, pred_dict in db["predictions"].items():
        for d, rec in pred_dict.items():
            if "actual" not in rec:
                continue
            for h in [1, 3, 5]:
                # 手动构造评估（复用prediction_tracker的逻辑，但直接计算）
                p_rec = rec.get("predictions", {}).get(h, {})
                if not p_rec:
                    continue
                actual = rec["actual"]
                ma_pct = p_rec.get("ma_pct", 0)
                mc_pct = p_rec.get("mc_pct", 0)
                w = cfg["ma_mc_weights"].get(str(h), {"ma":0.3,"mc":0.7})
                avg_pct = w["ma"] * ma_pct + w["mc"] * mc_pct
                th = cfg["signal_thresholds"]
                def sig(p):
                    if p >= th["strong_up"]: return "强上涨"
                    elif p >= th["up"]: return "上涨"
                    elif p <= th["strong_down"]: return "强下跌"
                    elif p <= th["down"]: return "下跌"
                    else: return "震荡"
                pred_dir = sig(avg_pct)
                actual_dir = sig(actual.get("change_pct", 0))
                all_evals.append({
                    "code": code, "horizon": h,
                    "ma_pct": ma_pct, "mc_pct": mc_pct, "avg_pct": avg_pct,
                    "pred_dir": pred_dir, "actual_dir": actual_dir,
                    "actual_pct": actual.get("change_pct", 0),
                    "confidence": p_rec.get("confidence", 0.5),
                    "sector": rec.get("sector", "其他"),
                })

    if len(all_evals) < cfg["min_sample_for_optimize"]:
        print(f"样本量不足 ({len(all_evals)})，需要 {cfg['min_sample_for_optimize']} 才能优化")
        return None

    HR = "=" * 90
    SEP = "-" * 90
    print(f"\n{HR}")
    print(f"  预测模型自动优化  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  样本量: {len(all_evals)} 条有效预测")
    print(HR)

    changelog = []

    # 1. MA vs MC 各窗口准确率
    print(f"\n{HR}")
    print("  【1】MA vs MC 各窗口准确率分析")
    print(HR)
    model_acc = analyze_ma_vs_mc_accuracy(all_evals)
    print(f"  {'窗口':>5} {'模型':>6} {'方向准确率':>10} {'MAE':>8} {'样本':>5}")
    print(SEP)
    for h in [1, 3, 5]:
        for model in ["ma", "mc"]:
            key = (h, model)
            if key in model_acc:
                v = model_acc[key]
                da = f"{v['direction_acc']:.1%}" if v['direction_acc'] else "N/A"
                print(f"  {h}日   {model:>6} {da:>10} {v['mae']:.3f}% {v['count']:>5}")

    # 2. 最优权重搜索
    print(f"\n{HR}")
    print("  【2】最优MA/MC权重搜索")
    print(HR)
    optimal_weights = {}
    for h in [1, 3, 5]:
        opt = find_optimal_weights_for_horizon(all_evals, h)
        if opt:
            old = cfg["ma_mc_weights"].get(str(h), {"ma": 0.3, "mc": 0.7})
            improved = abs(opt["direction_acc"] - (direction_accuracy([p for p in all_evals if p["horizon"]==h and "ma_pct" in p]) or 0))
            opt_horizon = direction_accuracy([p for p in all_evals if p["horizon"]==h])
            improved = opt_horizon - (direction_accuracy([p for p in all_evals if p["horizon"]==h]) or 0) if opt_horizon else 0
            # 计算当前权重准确率
            th = cfg["signal_thresholds"]
            def sig(p):
                if p >= th["up"]: return "上涨"
                elif p <= th["down"]: return "下跌"
                else: return "震荡"
            h_preds = [p for p in all_evals if p.get("horizon")==h]
            curr_evals = [{"pred_dir": sig(p["avg_pct"]), "actual_dir": p["actual_dir"]} for p in h_preds]
            curr_acc = direction_accuracy(curr_evals)
            new_acc = opt["direction_acc"]
            improvement = (new_acc - (curr_acc or 0)) * 100
            optimal_weights[h] = opt
            change = "→" if abs(opt["ma"] - old["ma"]) < 0.01 else "★ CHANGE"
            print(f"  H{h}: MA={old['ma']:.0%}→{opt['ma']:.0%} MC={old['mc']:.0%}→{opt['mc']:.0%} {change}")
            print(f"       方向准确率: {(curr_acc or 0):.1%} → {new_acc:.1%} ({improvement:+.1f}%)")
            print(f"       MAE: {opt['mae']:.3f}%")
            if not dry_run and abs(opt["ma"] - old["ma"]) >= 0.05 and improvement > 0:
                changelog.append(f"H{h}权重: MA{old['ma']:.0%}→{opt['ma']:.0%}, MC{old['mc']:.0%}→{opt['mc']:.0%}, 方向准确率{improvement:+.1f}%")
                cfg["ma_mc_weights"][str(h)] = {"ma": opt["ma"], "mc": opt["mc"]}
        else:
            print(f"  H{h}: 样本不足，跳过")

    # 3. 置信度分组分析
    print(f"\n{HR}")
    print("  【3】置信度分组优化建议")
    print(HR)
    conf_result = optimize_by_confidence_bins(all_evals)
    for label, vals in conf_result.items():
        if vals["count"] < 3:
            continue
        label_cn = {"low": "低置信(<40%)", "mid": "中置信(40-70%)", "high": "高置信(≥70%)"}.get(label, label)
        ma_acc = f"{vals['ma_direction_acc']:.1%}" if vals['ma_direction_acc'] else "N/A"
        mc_acc = f"{vals['mc_direction_acc']:.1%}" if vals['mc_direction_acc'] else "N/A"
        print(f"  {label_cn} ({vals['count']}样本): MA准确率{ma_acc}, MC准确率{mc_acc}")
        if vals['ma_direction_acc'] and vals['mc_direction_acc']:
            if vals['ma_direction_acc'] > vals['mc_direction_acc'] + 0.1:
                print(f"    → 建议该置信区间提高MA权重")
                if not dry_run:
                    changelog.append(f"置信区间{label}建议提高MA权重")
            elif vals['mc_direction_acc'] > vals['ma_direction_acc'] + 0.1:
                print(f"    → 建议该置信区间提高MC权重")

    # 4. 市场状态判断
    print(f"\n{HR}")
    print("  【4】市场状态判断")
    print(HR)
    regime_info = analyze_market_regime(all_evals)
    print(f"  市场状态: {regime_info['regime']}")
    print(f"  看涨信号准确率: {regime_info['up_acc']:.1%}" if regime_info['up_acc'] else "  看涨准确率: N/A")
    print(f"  看跌信号准确率: {regime_info['down_acc']:.1%}" if regime_info['down_acc'] else "  看跌准确率: N/A")
    if regime_info['regime'] == "震荡市":
        regime_tip = "震荡市特征明显，建议降低信号阈值灵敏度，避免频繁交易"
    elif regime_info['regime'] == "趋势市":
        regime_tip = "趋势市特征，建议MA权重适度提高"
    else:
        regime_tip = ""
    if regime_tip:
        print(f"  建议: {regime_tip}")

    # 5. 偏差分析
    print(f"\n{HR}")
    print("  【5】系统性偏差检测")
    print(HR)
    errors = [p["avg_pct"] - p["actual_pct"] for p in all_evals]
    avg_err = sum(errors)/len(errors)
    bias_cn = "预测偏高" if avg_err > 0.5 else ("预测偏低" if avg_err < -0.5 else "基本无偏")
    print(f"  平均预测误差: {avg_err:+.3f}%  ({bias_cn})")
    if abs(avg_err) > 1.0 and not dry_run:
        # 建议调整阈值
        changelog.append(f"检测到系统性偏差{avg_err:+.2f}%，建议调整信号阈值")
        print(f"  → 建议调整信号阈值以消除偏差")

    # 6. 综合建议
    ma_suggestions = suggest_ma_weight_tuning(all_evals)
    if ma_suggestions:
        print(f"\n{HR}")
        print("  【6】综合优化建议")
        print(HR)
        for s in ma_suggestions:
            print(f"  {s}")

    # 7. 保存/应用
    print(f"\n{HR}")
    if dry_run:
        print("  [DRY RUN] 未应用任何变更")
    else:
        if changelog:
            cfg["changelog"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "changes": changelog,
            })
        save_config(cfg)
        print(f"  [已应用] {len(changelog)} 项优化变更已保存")
        print(f"  变更记录: {changelog}")
    print(HR)

    return cfg

def show_config():
    cfg = load_config()
    print(f"\n{'='*90}")
    print(f"  当前模型配置")
    print(f"{'='*90}")
    print(f"  版本: {cfg['version']}  |  上次更新: {cfg['last_updated'] or '从未'}")
    print(f"\n  MA/MC权重:")
    for h, w in cfg["ma_mc_weights"].items():
        print(f"    H{h}: MA={w['ma']:.0%}  MC={w['mc']:.0%}")
    print(f"\n  信号阈值:")
    th = cfg["signal_thresholds"]
    print(f"    看涨: >{th['up']}% | 强看涨: >{th['strong_up']}%")
    print(f"    看跌: <{th['down']}% | 强看跌: <{th['strong_down']}%")
    print(f"\n  置信度下限: {cfg['confidence_floor']:.0%}")
    print(f"  优化最小样本: {cfg['min_sample_for_optimize']}")
    if cfg["changelog"]:
        print(f"\n  优化历史 (最近5条):")
        for ch in cfg["changelog"][-5:]:
            print(f"    {ch['date']}: {ch['changes']}")
    print(f"{'='*90}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="仅分析不应用")
    parser.add_argument("--show-config", action="store_true", help="显示当前配置")
    args = parser.parse_args()
    if args.show_config:
        show_config()
    else:
        run_optimization(dry_run=args.dry_run)
