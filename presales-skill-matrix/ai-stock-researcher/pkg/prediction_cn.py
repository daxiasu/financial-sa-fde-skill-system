#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A股三维预测模型 v1.0 — 技术面 × 资金面 × 情绪面"""
from __future__ import annotations
import sys, re, json, time, math
from pathlib import Path
from datetime import datetime, timedelta

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "pkg"))
from crawl_utils import safe_request

# ─────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────
def safe_float(v, default=0.0):
    try:
        return float(v) if v not in ("", "-", "N/A", None) else default
    except:
        return default

def calc_returns(prices: list[float]) -> list[float]:
    """计算收益率序列"""
    returns = []
    for i in range(1, len(prices)):
        if prices[i-1] != 0:
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
    return returns

def calc_volatility(returns: list[float]) -> float:
    if not returns:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    return math.sqrt(variance * 252)  # 年化

def calc_sharpe(returns: list[float], risk_free: float = 0.03) -> float:
    if not returns:
        return 0.0
    annual_ret = sum(returns) / len(returns) * 252
    vol = calc_volatility(returns)
    return (annual_ret - risk_free) / vol if vol > 0 else 0.0

# ─────────────────────────────────────────────────────
# 技术面：腾讯行情历史（简化版，使用日K）
# ─────────────────────────────────────────────────────
def _fetch_kline_sina(code: str, days: int = 60) -> list[dict]:
    """新浪财经K线备源 (https://money.finance.sina.com.cn)"""
    # 转换代码格式: sh600519 -> sh600519, sz000858 -> sz000858
    sym = code if code.startswith(("sh", "sz")) else (("sh" if code.startswith("6") else "sz") + code)
    url = (f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php"
           f"/CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=5&datalen={days}")
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
    try:
        raw = safe_request(url, headers=headers, timeout=8)
        if isinstance(raw, tuple):
            raw = raw[0]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        items = json.loads(raw) if raw else []
        results = []
        for it in items:
            results.append({
                "date": it.get("day", "")[:10],
                "open": safe_float(it.get("open")),
                "close": safe_float(it.get("close")),
                "high": safe_float(it.get("high")),
                "low": safe_float(it.get("low")),
                "volume": safe_float(it.get("volume")),
            })
        return results[-days:]
    except Exception:
        return []

def fetch_kline_tx(code: str, days: int = 60) -> list[dict]:
    """获取股票历史K线 (优先腾讯，备用新浪)
    code: 如 'sh600519' 或 'sz000858' 或纯数字 '600519'
    返回: [{date, open, high, low, close, volume}, ...]
    """
    # 标准化 prefix
    if not code.startswith(("sh", "sz")):
        code = ("sh" if code.startswith("6") else "sz") + code

    # 腾讯主源
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={code},day,,,{days},qfq"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://gu.qq.com",
    }
    try:
        raw = safe_request(url, headers=headers, timeout=8)
        if isinstance(raw, tuple):
            raw = raw[0]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        raw = re.sub(r"^[^=]+=", "", raw.strip())
        data = json.loads(raw)
        day_data = data.get("data", {}).get(code, {}).get("qfqday", [])
        results = []
        for item in day_data[-days:]:
            if len(item) >= 6:
                results.append({
                    "date": item[0],
                    "open": safe_float(item[1]),
                    "close": safe_float(item[2]),
                    "high": safe_float(item[3]),
                    "low": safe_float(item[4]),
                    "volume": safe_float(item[5]),
                })
        if results:
            return results
    except Exception:
        pass

    # 新浪备源
    return _fetch_kline_sina(code, days)

def technical_signals(klines: list[dict]) -> dict:
    """基于K线计算技术面信号"""
    if len(klines) < 20:
        return {"signal": "数据不足", "score": 0}

    closes = [k["close"] for k in klines]
    volumes = [k["volume"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]

    # 均线系统
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else sum(closes) / len(closes)

    current = closes[-1]

    # 均线多头/空头排列
    bullish_ma = ma5 > ma10 > ma20
    bearish_ma = ma5 < ma10 < ma20

    # MACD
    def ema(data, n):
        k = 2.0 / (n + 1)
        ema_val = data[0]
        for v in data[1:]:
            ema_val = v * k + ema_val * (1 - k)
        return ema_val

    if len(closes) >= 26:
        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        dif = ema12 - ema26
        # DEA简化
        dea = dif * 0.8  # 近似
        macd = (dif - dea) * 2
    else:
        dif = dea = macd = 0

    # RSI(14)
    if len(closes) >= 15:
        gains, losses = [], []
        for i in range(1, 15):
            diff = closes[-i] - closes[-i-1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - 100 / (1 + rs)
    else:
        rsi = 50

    # 布林带
    recent = closes[-20:]
    b_mean = sum(recent) / 20
    b_std = math.sqrt(sum((c - b_mean) ** 2 for c in recent) / 20)
    upper_band = b_mean + 2 * b_std
    lower_band = b_mean - 2 * b_std
    b_position = (current - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0.5

    # KDJ简化
    if len(klines) >= 9:
        low9 = min(lows[-9:])
        high9 = max(highs[-9:])
        rsv = 100 * (current - low9) / (high9 - low9) if high9 != low9 else 50
        k_val = 2/3 * 50 + 1/3 * rsv
        d_val = 2/3 * 50 + 1/3 * k_val
        j_val = 3 * k_val - 2 * d_val
    else:
        k_val = d_val = j_val = 50

    # 成交量异常（量比）
    avg_vol5 = sum(volumes[-5:]) / 5
    vol_ratio = volumes[-1] / avg_vol5 if avg_vol5 > 0 else 1

    # 综合技术评分（-100 ~ +100）
    score = 0
    details = []

    if current > ma5:
        score += 15
        details.append("价格>MA5(+15)")
    else:
        score -= 15
        details.append("价格<MA5(-15)")

    if ma5 > ma10:
        score += 10
        details.append("MA5>MA10(+10)")
    else:
        score -= 10
        details.append("MA5<MA10(-10)")

    if macd > 0:
        score += 15
        details.append("MACD>0(+15)")
    else:
        score -= 15
        details.append("MACD<0(-15)")

    if rsi < 30:
        score += 15
        details.append(f"RSI超卖({rsi:.0f})(+15)")
    elif rsi > 70:
        score -= 15
        details.append(f"RSI超买({rsi:.0f})(-15)")

    if b_position < 0.2:
        score += 10
        details.append("布林下轨(+10)")
    elif b_position > 0.8:
        score -= 10
        details.append("布林上轨(-10)")

    if vol_ratio > 2:
        score += 10
        details.append(f"放量({vol_ratio:.1f}x)(+10)")
    elif vol_ratio < 0.5:
        score -= 5
        details.append(f"缩量({vol_ratio:.1f}x)(-5)")

    if k_val < 20:
        score += 10
        details.append("KDJ超卖(+10)")
    elif k_val > 80:
        score -= 10
        details.append("KDJ超买(-10)")

    # 归一化到 -100~100
    signal_score = max(-100, min(100, score))

    if signal_score > 30:
        signal = "强势"
    elif signal_score > 10:
        signal = "偏强"
    elif signal_score < -30:
        signal = "弱势"
    elif signal_score < -10:
        signal = "偏弱"
    else:
        signal = "中性"

    return {
        "signal": signal,
        "score": signal_score,
        "price": current,
        "ma5": round(ma5, 2),
        "ma20": round(ma20, 2),
        "ma60": round(ma60, 2),
        "rsi": round(rsi, 1),
        "macd": round(macd, 3),
        "kdj_k": round(k_val, 1),
        "kdj_j": round(j_val, 1),
        "bollinger_lower": round(lower_band, 2),
        "bollinger_upper": round(upper_band, 2),
        "bollinger_position": round(b_position, 2),
        "volume_ratio": round(vol_ratio, 2),
        "details": details,
    }

# ─────────────────────────────────────────────────────
# 资金面：资金流向（从腾讯API）
# ─────────────────────────────────────────────────────
def fetch_money_flow(code: str) -> dict:
    """获取个股资金流向
    code: 如 'sh600519'
    """
    url = f"https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?lmt=0&klt=1&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56&secid=1.{code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }
    try:
        raw = safe_request(url, headers=headers, timeout=8)
        if isinstance(raw, tuple):
            raw = raw[0]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        data = json.loads(raw)
        items = data.get("data", {}).get("klines", [])
        results = []
        for item in items[-5:]:
            parts = item.split(",")
            if len(parts) >= 6:
                results.append({
                    "date": parts[0],
                    "main_net": safe_float(parts[1]),      # 主力净流入
                    "super_net": safe_float(parts[2]),      # 超大单净流入
                    "big_net": safe_float(parts[3]),        # 大单净流入
                    "mid_net": safe_float(parts[4]),        # 中单净流入
                    "small_net": safe_float(parts[5]),      # 小单净流入
                })
        if results:
            latest = results[-1]
            # 5日平均主力净流入
            avg_main = sum(r["main_net"] for r in results) / len(results)
            return {
                "date": latest["date"],
                "main_net": latest["main_net"],
                "super_net": latest["super_net"],
                "big_net": latest["big_net"],
                "avg_main_net_5d": round(avg_main, 0),
                "unit": "万元",
            }
    except Exception:
        pass
    return {}

def money_flow_score(flow: dict) -> dict:
    """评估资金面信号"""
    main_net = flow.get("main_net", 0)
    avg_main = flow.get("avg_main_net_5d", 0)

    score = 0
    details = []

    if main_net > 0:
        score += 20
        details.append("今日主力净流入(+20)")
    else:
        score -= 20
        details.append(f"今日主力净流出({main_net:.0f}万)(-20)")

    if avg_main > 0:
        score += 15
        details.append("5日主力持续净买入(+15)")
    else:
        score -= 15
        details.append("5日主力持续净卖出(-15)")

    # 归一化
    signal_score = max(-100, min(100, score))

    return {
        "signal": "资金流入" if score > 0 else "资金流出",
        "score": signal_score,
        "details": details,
    }

# ─────────────────────────────────────────────────────
# 情绪面：市场整体情绪（通过沪深300波动）
# ─────────────────────────────────────────────────────
def fetch_market_sentiment() -> dict:
    """获取市场情绪（通过沪深300近期表现）
    优先使用新浪财经，备用腾讯
    """
    # 先用腾讯沪深300，不行换新浪
    klines = fetch_kline_tx("sh000300", days=20)
    if not klines:
        klines = _fetch_kline_sina("sh000300", 20)
    if not klines:
        return {"signal": "数据获取失败", "score": 0, "volatility": 0, "ret_5d": 0, "details": ["K线数据不可用"]}

    closes = [k["close"] for k in klines]
    returns = calc_returns(closes)
    vol = calc_volatility(returns)

    # 近5日收益率
    ret5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0

    score = 0
    if vol < 0.15:
        score += 15
        signal = "市场平稳"
    elif vol > 0.30:
        score -= 15
        signal = "市场恐慌"
    else:
        signal = "市场中性"

    if ret5d > 2:
        score += 15
        signal = "偏热"
    elif ret5d < -2:
        score -= 15
        signal = "偏冷"

    signal_score = max(-100, min(100, score))

    return {
        "signal": signal,
        "score": signal_score,
        "volatility": round(vol * 100, 2),  # 年化波动率%
        "ret_5d": round(ret5d, 2),
        "details": [f"5日涨跌{ret5d:+.2f}%", f"年化波动率{vol*100:.1f}%"],
    }


# ─────────────────────────────────────────────────────
# 价格预测：蒙特卡洛模拟 × 移动平均外推
# ─────────────────────────────────────────────────────

def calc_daily_returns(prices: list[float]) -> list[float]:
    """计算日收益率序列"""
    returns = []
    for i in range(1, len(prices)):
        if prices[i-1] > 0:
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
    return returns

def forecast_ma(prices: list[float], periods: list[int] = [1, 3, 5]) -> dict:
    """移动平均外推预测（简单趋势延续）

    基于最近N日平均收益率，对未来1/3/5日进行外推。
    仅适用于短期参考，误差随天数增加而增大。

    Args:
        prices: 历史收盘价序列
        periods: 预测天数列表 [1, 3, 5]

    Returns:
        {1: {mean, std, min, max, confidence},
         3: {...},
         5: {...}}
    """
    if len(prices) < 10:
        return {}

    returns = calc_daily_returns(prices[-60:])  # 用近60日收益
    if len(returns) < 5:
        return {}

    mean_ret = sum(returns) / len(returns)
    std_ret = math.sqrt(sum((r - mean_ret)**2 for r in returns) / len(returns))
    last_price = prices[-1]

    # 日历天数到交易日映射（粗略按1:1）
    results = {}
    for n in periods:
        # 简单外推：均值 ± 1标准差
        predicted = last_price * (1 + mean_ret * n)
        min_pred = last_price * (1 + (mean_ret - std_ret) * n)
        max_pred = last_price * (1 + (mean_ret + std_ret) * n)

        # 置信度：数据越多越置信，历史波动越大置信度越低
        data_conf = min(len(returns) / 60, 1.0)
        vol_conf = max(0.3, 1.0 - min(std_ret * 5, 0.7))  # 波动率超过20%则置信度降至30%+
        confidence = round(data_conf * vol_conf, 2)

        pct_change = (predicted - last_price) / last_price * 100
        results[n] = {
            "predicted_price": round(predicted, 2),
            "pct_change": round(pct_change, 2),
            "min_price": round(min_pred, 2),
            "max_price": round(max_pred, 2),
            "confidence": confidence,
            "mean_daily_ret": round(mean_ret * 100, 3),
            "std_daily_ret": round(std_ret * 100, 3),
        }
    return results

def forecast_monte_carlo(prices: list[float], periods: list[int] = [1, 3, 5],
                         simulations: int = 1000) -> dict:
    """蒙特卡洛模拟预测

    基于历史收益率分布，随机抽样生成多条价格路径，
    统计未来1/3/5日价格分布（均值/标准差/分位数）。

    Args:
        prices: 历史收盘价序列
        periods: 预测天数列表
        simulations: 模拟次数（默认1000）

    Returns:
        {1: {mean, std, p5, p25, p50, p75, p95, prob_up, confidence},
         3: {...},
         5: {...}}
    """
    import random
    random.seed(42)  # 可重复

    if len(prices) < 20:
        return {}

    returns = calc_daily_returns(prices[-120:])  # 近120日
    if len(returns) < 10:
        return {}

    mean_ret = sum(returns) / len(returns)
    std_ret = math.sqrt(sum((r - mean_ret)**2 for r in returns) / len(returns))
    last_price = prices[-1]

    results = {}
    for n in periods:
        # 模拟N日后的价格路径
        final_prices = []
        for _ in range(simulations):
            price = last_price
            for _ in range(n):
                # 随机收益率：均值 ± 标准差的正态近似
                ret = random.gauss(mean_ret, std_ret)
                price *= (1 + ret)
            final_prices.append(price)

        final_prices.sort()
        p5 = final_prices[int(simulations * 0.05)]
        p25 = final_prices[int(simulations * 0.25)]
        p50 = final_prices[int(simulations * 0.50)]
        p75 = final_prices[int(simulations * 0.75)]
        p95 = final_prices[int(simulations * 0.95)]
        mean_pred = sum(final_prices) / len(final_prices)

        prob_up = sum(1 for p in final_prices if p > last_price) / simulations

        # 置信度：数据量和波动率共同决定
        data_conf = min(len(returns) / 120, 1.0)
        vol_conf = max(0.2, 1.0 - min(std_ret * 4, 0.8))
        confidence = round(data_conf * vol_conf, 2)

        pct_change = (mean_pred - last_price) / last_price * 100
        results[n] = {
            "mean_price": round(mean_pred, 2),
            "pct_change": round(pct_change, 2),
            "std": round(math.sqrt(sum((p - mean_pred)**2 for p in final_prices) / simulations), 2),
            "p5": round(p5, 2),
            "p25": round(p25, 2),
            "p50": round(p50, 2),   # 中位数预测
            "p75": round(p75, 2),
            "p95": round(p95, 2),
            "prob_up": round(prob_up * 100, 1),
            "confidence": confidence,
            "mean_daily_ret": round(mean_ret * 100, 3),
            "std_daily_ret": round(std_ret * 100, 3),
        }
    return results

def forecast_stock(code: str, periods: list[int] = [1, 3, 5]) -> dict:
    """综合价格预测（MA外推 + 蒙特卡洛模拟）

    结合技术面/资金面信号权重，对未来1/3/5日价格进行预测。
    输出两套预测结果（MA外推 / 蒙特卡洛）以及综合信号。

    Args:
        code: 股票代码（6位数字）
        periods: 预测天数列表

    Returns:
        {
            "code": "600519",
            "name": "贵州茅台",
            "timestamp": "2026-05-18",
            "last_price": 1332.95,
            "ma_forecast": {1: {...}, 3: {...}, 5: {...}},
            "mc_forecast": {1: {...}, 3: {...}, 5: {...}},
            "combined_signal": {"1d": "上涨", "3d": "上涨", "5d": "震荡"},
            "confidence": 0.65,
            "raw_data": {...}
        }
    """
    # 格式化code
    if not code.startswith("sh") and not code.startswith("sz"):
        code = "sh" + code if code.startswith("6") else "sz" + code

    klines = fetch_kline_tx(code, days=120)
    if not klines or len(klines) < 20:
        return {"error": "K线数据不足，无法预测"}

    closes = [k["close"] for k in klines]
    last_price = closes[-1]

    # MA外推
    ma_forecast = forecast_ma(closes, periods)

    # 蒙特卡洛模拟
    mc_forecast = forecast_monte_carlo(closes, periods)

    # 技术面信号（用于调整置信度）
    tech = technical_signals(klines)
    tech_score = tech.get("score", 0)  # -100 ~ +100

    # 置信度综合：MA和MC的置信度取平均，再受技术面调整
    confidences = []
    for n in periods:
        ma_conf = ma_forecast.get(n, {}).get("confidence", 0)
        mc_conf = mc_forecast.get(n, {}).get("confidence", 0)
        confidences.append((ma_conf + mc_conf) / 2)

    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    # 技术面强势(+30以上)可提升置信度5%，弱势(-30以下)降低5%
    tech_adj = 0.05 if tech_score > 30 else (-0.05 if tech_score < -30 else 0)
    final_conf = max(0.1, min(0.95, avg_conf + tech_adj))

    # 综合信号：结合MA和MC的预测方向
    combined = {}
    for n in periods:
        ma_pct = ma_forecast.get(n, {}).get("pct_change", 0)
        mc_pct = mc_forecast.get(n, {}).get("pct_change", 0)
        # 加权平均（MC更可靠，权重更高）
        avg_pct = ma_pct * 0.3 + mc_pct * 0.7

        if avg_pct > 2:
            direction = "上涨"
        elif avg_pct > 0.5:
            direction = "微涨"
        elif avg_pct >= -0.5:
            direction = "震荡"
        elif avg_pct >= -2:
            direction = "微跌"
        else:
            direction = "下跌"

        combined[f"{n}d"] = direction

    return {
        "code": code,
        "name": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last_price": last_price,
        "ma_forecast": ma_forecast,
        "mc_forecast": mc_forecast,
        "combined_signal": combined,
        "confidence": round(final_conf, 2),
        "tech_score": tech_score,
        "tech_signal": tech.get("signal", "N/A"),
        "raw_data": {
            "klines_used": len(klines),
            "periods": periods,
        }
    }

def print_forecast(fore: dict):
    """打印价格预测报告"""
    if "error" in fore:
        print(f"  [预测失败] {fore['error']}")
        return

    print(f"\n  代码: {fore['code']} | 最新价: {fore['last_price']} | 时间: {fore['timestamp']}")
    print(f"  技术信号: {fore['tech_signal']}({fore['tech_score']:+d}分) | 置信度: {fore['confidence']:.0%}")
    print(f"  综合信号: {' / '.join([f'{k}={v}' for k,v in fore['combined_signal'].items()])}")

    print(f"\n  ── MA外推预测 ──")
    for n, v in fore.get("ma_forecast", {}).items():
        print(f"    {n}日: 预测价={v['predicted_price']} | 涨跌={v['pct_change']:+.2f}% "
              f"| 区间=[{v['min_price']}, {v['max_price']}] | 置信={v['confidence']:.0%}")

    print(f"\n  ── 蒙特卡洛模拟 (1000次) ──")
    for n, v in fore.get("mc_forecast", {}).items():
        print(f"    {n}日: 均值={v['mean_price']} | 涨跌={v['pct_change']:+.2f}% "
              f"| 中位数={v['p50']} | 区间[p5={v['p5']}, p95={v['p95']}] "
              f"| 上涨概率={v['prob_up']:.1f}%")

# ─────────────────────────────────────────────────────
# 三维综合预测
# ─────────────────────────────────────────────────────
def predict_stock(code: str) -> dict:
    """三维预测：技术面 × 资金面 × 情绪面"""
    # 格式化code
    if not code.startswith("sh") and not code.startswith("sz"):
        code = "sh" + code if code.startswith("6") else "sz" + code

    tech_klines = fetch_kline_tx(code, days=60)
    tech = technical_signals(tech_klines)

    clean_code = code[2:] if len(code) == 8 else code
    flow = fetch_money_flow(clean_code)
    money = money_flow_score(flow) if flow else {"signal": "数据不可用", "score": 0}

    sentiment = fetch_market_sentiment()

    # 加权综合
    w_tech, w_money, w_sent = 0.5, 0.3, 0.2
    composite = (tech["score"] * w_tech +
                 money.get("score", 0) * w_money +
                 sentiment.get("score", 0) * w_sent)

    if composite > 30:
        recommendation = "建议关注"
        action = "适量买入"
    elif composite > 10:
        recommendation = "谨慎看好"
        action = "持有观察"
    elif composite < -30:
        recommendation = "风险较大"
        action = "建议减仓"
    elif composite < -10:
        recommendation = "谨慎观望"
        action = "持有不动"
    else:
        recommendation = "中性"
        action = "观望"

    return {
        "code": code,
        "name": "",  # 可由调用方填充
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "composite_score": round(composite, 1),
        "composite_signal": recommendation,
        "action": action,
        "technical": tech,
        "money_flow": {**money, **flow},
        "market_sentiment": sentiment,
        "summary": (
            f"技术面{tech['signal']}({tech['score']:+d}分) | "
            f"资金面{money.get('signal','N/A')}({money.get('score',0):+d}分) | "
            f"情绪面{sentiment.get('signal','N/A')}({sentiment.get('score',0):+d}分)"
        ),
    }

# ─────────────────────────────────────────────────────
# 输出格式化
# ─────────────────────────────────────────────────────
def print_prediction(pred: dict):
    print(f"\n{'='*60}")
    print(f"  {pred['code']} 三维预测报告 ({pred['timestamp']})")
    print(f"{'='*60}")
    print(f"  综合评分: {pred['composite_score']:+6.1f}  [{pred['composite_signal']}]")
    print(f"  操作建议: {pred['action']}")
    print()
    print(f"  ── 技术面 ({pred['technical']['score']:+3d}分) ──")
    t = pred["technical"]
    print(f"    信号: {t['signal']} | 现价: {t['price']} | MA5:{t['ma5']} MA20:{t['ma20']}")
    print(f"    RSI:{t['rsi']} MACD:{t['macd']:+.3f} KDJ_K:{t['kdj_k']}")
    print(f"    布林位:{t['bollinger_position']} 量比:{t['volume_ratio']}")
    for d in t.get("details", [])[:4]:
        print(f"    · {d}")
    print()
    print(f"  ── 资金面 ({pred['money_flow'].get('score',0):+3d}分) ──")
    m = pred["money_flow"]
    print(f"    信号: {m.get('signal','N/A')} | "
          f"主力净流入: {m.get('main_net',0):+.0f}万 | "
          f"5日均: {m.get('avg_main_net_5d',0):+.0f}万")
    for d in m.get("details", []):
        print(f"    · {d}")
    print()
    print(f"  ── 情绪面 ({pred['market_sentiment'].get('score',0):+3d}分) ──")
    s = pred["market_sentiment"]
    print(f"    信号: {s.get('signal','N/A')} | 5日涨跌: {s.get('ret_5d',0):+.2f}% | 波动率: {s.get('volatility',0):.1f}%")
    for d in s.get("details", []):
        print(f"    · {d}")
    print()
    print(f"  总结: {pred['summary']}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    print("=== 三维预测测试：贵州茅台 ===")
    pred = predict_stock("600519")
    print_prediction(pred)
