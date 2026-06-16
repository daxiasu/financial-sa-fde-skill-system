"""
recommendation_engine.py - Smart Stock/Fund Recommendation Engine v1.0

Multi-dimensional scoring:
  - Research Score (30%): Broker target price, ratings, earnings forecasts
  - News Sentiment (20%): News analysis + event-driven
  - Technical (20%): Moving averages / MACD / RSI / Volume
  - Holder Feedback (15%): Xueqiu / Eastmoney holder sentiment
  - Risk (15%): Volatility / drawdown / valuation percentile

Recommendation Index: 0-100 (Buy/Accumulate/Hold/Reduce/Sell)
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import re
import math
import time
import socket

SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "pkg"))

try:
    import research_cn as rc
    import news_analyzer as na
    import prediction_cn as pc
    import quant_wiki as qw
    import fund_analyzer as fa
    _HAS_DEPS = True
except ImportError:
    _HAS_DEPS = False

TIMEOUT = 10
socket.setdefaulttimeout(TIMEOUT)

WEIGHTS = {
    "research": 0.30,
    "news": 0.20,
    "technical": 0.20,
    "holder": 0.15,
    "risk": 0.15,
}

RECO_LEVELS = [
    (85, "5", "Strong Buy", "recommend"),
    (70, "4", "Buy", "buy"),
    (55, "3", "Hold", "hold"),
    (40, "2", "Cautious", "cautious"),
    (0, "1", "Sell", "sell"),
]

def safe_float(val, default=0.0):
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default

def safe_request(url, headers=None, timeout=10):
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

def calc_research_score(code):
    if not _HAS_DEPS:
        return {"score": 50, "signal": "Unavailable", "details": {}, "research_count": 0, "avg_target_premium": 0.0, "bullish_ratio": 0.5}
    result = {"score": 50, "signal": "Neutral", "details": {}, "research_count": 0, "avg_target_premium": 0.0, "bullish_ratio": 0.5}
    try:
        overview = rc.fetch_research_overview(code)
        if not overview or not isinstance(overview, dict):
            return result
        items = overview.get("items", [])
        if not items:
            return result
        result["research_count"] = len(items)
        ratings = {"Buy": 0, "Outperform": 0, "Neutral": 0, "Reduce": 0, "Sell": 0, "Other": 0}
        target_prices = []
        current_price = None
        for item in items:
            title = item.get("title", "")
            for rating in ratings.keys():
                if rating in title:
                    ratings[rating] += 1
                    break
            tp_match = re.search(r"(\d+\.?\d*)\s*元", title)
            if tp_match:
                target_prices.append(float(tp_match.group(1)))
            if current_price is None:
                price_match = re.search(r"现价[：:]\s*(\d+\.?\d*)", title)
                if price_match:
                    current_price = float(price_match.group(1))
        bullish = ratings.get("Buy", 0) + ratings.get("Outperform", 0)
        total = sum(ratings.values())
        if total > 0:
            result["bullish_ratio"] = bullish / total
        if target_prices and current_price:
            avg_target = sum(target_prices) / len(target_prices)
            premium = (avg_target - current_price) / current_price * 100
            result["avg_target_premium"] = premium
        score = 50 + (result["bullish_ratio"] - 0.5) * 30
        if result["avg_target_premium"] > 0:
            score += min(result["avg_target_premium"] * 0.4, 20)
        else:
            score += max(result["avg_target_premium"] * 0.4, -10)
        score += min(len(items) * 0.5, 5)
        result["score"] = max(0, min(100, round(score)))
        if result["bullish_ratio"] >= 0.8:
            result["signal"] = "Strong Bullish"
        elif result["bullish_ratio"] >= 0.6:
            result["signal"] = "Bullish"
        elif result["bullish_ratio"] >= 0.4:
            result["signal"] = "Neutral"
        else:
            result["signal"] = "Bearish"
        result["details"] = {"ratings": ratings, "target_prices": target_prices, "current_price": current_price}
    except Exception:
        pass
    return result

def calc_news_score(code, limit=20):
    if not _HAS_DEPS:
        return {"score": 50, "signal": "Unavailable", "details": {}, "news_count": 0, "sentiment_avg": 0.0, "positive_ratio": 0.5}
    result = {"score": 50, "signal": "Neutral", "details": {}, "news_count": 0, "sentiment_avg": 0.0, "positive_ratio": 0.5}
    try:
        news_list = rc.fetch_eastmoney_stock_news(code, limit=limit) if hasattr(rc, "fetch_eastmoney_stock_news") else []
        if not news_list and hasattr(rc, "fetch_ths_stock_news"):
            news_list = rc.fetch_ths_stock_news(code, limit=limit)
        if not news_list:
            return result
        result["news_count"] = len(news_list)
        analyzed = na.analyze_news_batch(news_list)
        if isinstance(analyzed, dict):
            sentiment_avg = analyzed.get("sentiment_avg", 0.0)
            impact_counts = analyzed.get("impact_counts", {})
            result["sentiment_avg"] = sentiment_avg
            result["positive_ratio"] = impact_counts.get("利好", 0) / max(sum(impact_counts.values()), 1)
            score = 50 + sentiment_avg * 50
            result["score"] = max(0, min(100, round(score)))
            if sentiment_avg >= 0.3:
                result["signal"] = "Bullish Dominant"
            elif sentiment_avg >= 0.1:
                result["signal"] = "Slightly Bullish"
            elif sentiment_avg >= -0.1:
                result["signal"] = "Neutral"
            elif sentiment_avg >= -0.3:
                result["signal"] = "Slightly Bearish"
            else:
                result["signal"] = "Bearish Dominant"
            result["details"] = {"sentiment_avg": sentiment_avg, "impact_counts": impact_counts, "tag_counts": analyzed.get("tag_counts", {})}
        else:
            sentiments = []
            for news in news_list[:10]:
                analyzed_item = na.analyze_news_item(news)
                sentiments.append(analyzed_item.get("sentiment", 0))
            if sentiments:
                avg = sum(sentiments) / len(sentiments)
                result["sentiment_avg"] = avg
                result["score"] = max(0, min(100, round(50 + avg * 50)))
    except Exception:
        pass
    return result

def calc_technical_score(code):
    if not _HAS_DEPS:
        return {"score": 50, "signal": "Neutral", "details": {}, "ma_status": "Unknown", "macd_status": "Unknown", "rsi": 50}
    result = {"score": 50, "signal": "Neutral", "details": {}, "ma_status": "Unknown", "macd_status": "Unknown", "rsi": 50}
    try:
        kline = pc.fetch_kline_tx(code, days=60) if hasattr(pc, "fetch_kline_tx") else []
        if not kline or len(kline) < 20:
            return result
        prices = [float(k.get("close", 0)) for k in kline if k.get("close")]
        if len(prices) < 20:
            return result
        ma5 = sum(prices[-5:]) / 5
        ma10 = sum(prices[-10:]) / 10
        ma20 = sum(prices[-20:]) / 20
        current = prices[-1]
        if ma5 > ma10 > ma20:
            ma_status = "Bullish"
            ma_score = 20
        elif ma5 < ma10 < ma20:
            ma_status = "Bearish"
            ma_score = -10
        else:
            ma_status = "Sideways"
            ma_score = 5
        result["ma_status"] = ma_status
        result["ma5"] = round(ma5, 2)
        result["ma10"] = round(ma10, 2)
        result["ma20"] = round(ma20, 2)
        result["current"] = round(current, 2)
        ema12 = sum(prices[-12:]) / 12
        ema26 = sum(prices[-26:]) / 26
        dif = ema12 - ema26
        macd_signal = 0
        if len(prices) >= 9:
            dea = sum([prices[-i] for i in range(1, 10)]) / 9
            macd_signal = (dif - dea) * 2
        macd_status = "Gold Cross" if macd_signal > 0 else "Death Cross" if macd_signal < 0 else "Neutral"
        macd_score = 10 if macd_signal > 0 else -5 if macd_signal < 0 else 0
        result["macd_status"] = macd_status
        result["macd_signal"] = round(macd_signal, 4)
        if len(prices) >= 14:
            gains = []
            losses = []
            for i in range(-14, 0):
                diff = prices[i + 1] - prices[i]
                gains.append(max(diff, 0))
                losses.append(max(-diff, 0))
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        result["rsi"] = round(rsi, 1)
        if rsi > 80:
            rsi_score = -15
        elif rsi > 70:
            rsi_score = -5
        elif rsi < 20:
            rsi_score = 15
        elif rsi < 30:
            rsi_score = 5
        else:
            rsi_score = 0
        vol_ma5 = sum([float(k.get("volume", 0)) for k in kline[-6:-1]]) / 5
        vol_current = float(kline[-1].get("volume", 0)) if kline else 0
        vol_ratio = vol_current / vol_ma5 if vol_ma5 > 0 else 1
        vol_score = 5 if vol_ratio > 1.5 else (-5 if vol_ratio < 0.7 else 0)
        result["vol_ratio"] = round(vol_ratio, 2)
        score = 50 + ma_score + macd_score + rsi_score + vol_score
        result["score"] = max(0, min(100, round(score)))
        if score >= 70:
            result["signal"] = "Strong"
        elif score >= 55:
            result["signal"] = "Slightly Strong"
        elif score >= 45:
            result["signal"] = "Neutral"
        elif score >= 30:
            result["signal"] = "Slightly Weak"
        else:
            result["signal"] = "Weak"
        result["details"] = {"ma5": result["ma5"], "ma10": result["ma10"], "ma20": result["ma20"], "rsi": result["rsi"], "macd": macd_status, "vol_ratio": result["vol_ratio"]}
    except Exception:
        pass
    return result

def calc_holder_score(code, is_fund=False):
    if not _HAS_DEPS:
        return {"score": 50, "signal": "Neutral", "details": {}, "discussion_count": 0, "sentiment": 0.0}
    result = {"score": 50, "signal": "Neutral", "details": {}, "discussion_count": 0, "sentiment": 0.0}
    try:
        if is_fund:
            info = fa.fetch_fund_info(code) if hasattr(fa, "fetch_fund_info") else {}
            if info:
                result["details"]["fund_info"] = {"name": info.get("name", ""), "manager": info.get("manager", ""), "scale": info.get("scale", "")}
                scale = info.get("scale", "")
                if scale:
                    try:
                        scale_val = float(re.sub(r"[^\d.]", "", str(scale)))
                        if 5 < scale_val < 100:
                            result["score"] += 5
                    except:
                        pass
        else:
            xueqiu_news = rc.fetch_xueqiu_stock_news(code, limit=20) if hasattr(rc, "fetch_xueqiu_stock_news") else []
            if xueqiu_news:
                result["discussion_count"] = len(xueqiu_news)
                sentiments = []
                for news in xueqiu_news[:10]:
                    analyzed_item = na.analyze_news_item(news)
                    sentiments.append(analyzed_item.get("sentiment", 0))
                if sentiments:
                    avg_sentiment = sum(sentiments) / len(sentiments)
                    result["sentiment"] = avg_sentiment
                    result["score"] = max(0, min(100, round(50 + avg_sentiment * 50)))
        if result["score"] >= 70:
            result["signal"] = "Holders Bullish"
        elif result["score"] >= 55:
            result["signal"] = "Slightly Positive"
        elif result["score"] >= 45:
            result["signal"] = "Neutral"
        elif result["score"] >= 30:
            result["signal"] = "Slightly Negative"
        else:
            result["signal"] = "Holders Bearish"
    except Exception:
        pass
    return result

def calc_risk_score(code, is_fund=False):
    result = {"score": 50, "level": "Medium", "signal": "Normal", "details": {}}
    try:
        if is_fund and _HAS_DEPS:
            history = fa.fetch_fund_history(code, days=180) if hasattr(fa, "fetch_fund_history") else []
            if history:
                navs = [float(h.get("nav", 0)) for h in history if h.get("nav")]
                if len(navs) >= 30:
                    returns = [(navs[i] - navs[i-1]) / navs[i-1] for i in range(1, len(navs))]
                    if returns:
                        mean_ret = sum(returns) / len(returns)
                        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
                        volatility = math.sqrt(variance * 252) * 100
                        peak = navs[0]
                        max_drawdown = 0
                        for nav in navs:
                            if nav > peak:
                                peak = nav
                            dd = (peak - nav) / peak * 100
                            if dd > max_drawdown:
                                max_drawdown = dd
                        result["details"]["volatility"] = round(volatility, 2)
                        result["details"]["max_drawdown"] = round(max_drawdown, 2)
                        score = 80
                        if volatility > 40:
                            score -= (volatility - 40) * 1.5
                        elif volatility < 15:
                            score += 5
                        if max_drawdown > 30:
                            score -= (max_drawdown - 30) * 1.2
                        result["score"] = max(0, min(100, round(score)))
                        if result["score"] >= 70:
                            result["level"] = "Low Risk"
                            result["signal"] = "Stable"
                        elif result["score"] >= 50:
                            result["level"] = "Medium Risk"
                            result["signal"] = "Normal"
                        else:
                            result["level"] = "High Risk"
                            result["signal"] = "Volatile"
        else:
            result["score"] = 55
            result["signal"] = "Normal"
    except Exception:
        pass
    return result

def get_recommendation(code, is_fund=False):
    scores = {}
    composite = 0.0
    scores["research"] = calc_research_score(code)
    composite += scores["research"]["score"] * WEIGHTS["research"]
    scores["news"] = calc_news_score(code)
    composite += scores["news"]["score"] * WEIGHTS["news"]
    scores["technical"] = calc_technical_score(code)
    composite += scores["technical"]["score"] * WEIGHTS["technical"]
    scores["holder"] = calc_holder_score(code, is_fund)
    composite += scores["holder"]["score"] * WEIGHTS["holder"]
    scores["risk"] = calc_risk_score(code, is_fund)
    composite += scores["risk"]["score"] * WEIGHTS["risk"]
    data_points = 5
    available = sum(1 for s in scores.values() if s.get("score", 0) > 0)
    confidence = available / data_points
    composite = round(composite)
    for threshold, stars, level, action in RECO_LEVELS:
        if composite >= threshold:
            reco_stars = stars
            reco_level = level
            reco_action = action
            break
    else:
        reco_stars = "1"
        reco_level = "Sell"
        reco_action = "sell"
    pros = []
    cons = []
    if scores["research"]["bullish_ratio"] > 0.7:
        pros.append(f"Research bullish {scores['research']['bullish_ratio']*100:.0f}%")
    elif scores["research"]["bullish_ratio"] < 0.3:
        cons.append(f"Research bullish only {scores['research']['bullish_ratio']*100:.0f}%")
    if scores["news"]["sentiment_avg"] > 0.2:
        pros.append(f"News sentiment positive ({scores['news']['sentiment_avg']:.2f})")
    elif scores["news"]["sentiment_avg"] < -0.2:
        cons.append(f"News sentiment negative ({scores['news']['sentiment_avg']:.2f})")
    if scores["technical"]["ma_status"] == "Bullish":
        pros.append("MA Bullish Alignment")
    elif scores["technical"]["ma_status"] == "Bearish":
        cons.append("MA Bearish Alignment")
    if scores["risk"]["level"] == "Low Risk":
        pros.append("Low Risk Profile")
    elif scores["risk"]["level"] == "High Risk":
        cons.append("High Risk Profile")
    summary = f"Composite score {composite}, {reco_level}."
    name = code
    if is_fund and _HAS_DEPS and hasattr(fa, "fetch_fund_info"):
        info = fa.fetch_fund_info(code)
        if info:
            name = info.get("name", code)
    return {
        "code": code,
        "name": name,
        "is_fund": is_fund,
        "recommendation_index": composite,
        "recommendation_level": reco_level,
        "recommendation_stars": reco_stars,
        "action": reco_action,
        "scores": scores,
        "composite_score": composite,
        "confidence": round(confidence, 2),
        "summary": summary,
        "pros": pros,
        "cons": cons,
        "timestamp": time.strftime("%Y-%m-%d"),
    }

def scan_recommendations(codes, is_fund=False):
    results = []
    for code in codes:
        rec = get_recommendation(code.strip(), is_fund)
        results.append(rec)
        time.sleep(0.5)
    results.sort(key=lambda x: x["recommendation_index"], reverse=True)
    return results

def print_recommendation(rec):
    lines = [
        "",
        "=" * 60,
        f"{'Stock' if not rec['is_fund'] else 'Fund'}: {rec['name']} ({rec['code']})",
        "=" * 60,
        "",
        f"Recommendation Index: {rec['recommendation_index']} stars={rec['recommendation_stars']}",
        f"Level: {rec['recommendation_level']}",
        f"Action: {rec['action']}",
        f"Confidence: {rec['confidence']*100:.0f}%",
        "",
        "-" * 40,
        "5-Dimension Scores:",
        "",
        f"  Research (30%): {rec['scores']['research']['score']:.0f} | {rec['scores']['research']['signal']}",
        f"  News (20%): {rec['scores']['news']['score']:.0f} | {rec['scores']['news']['signal']}",
        f"  Technical (20%): {rec['scores']['technical']['score']:.0f} | {rec['scores']['technical']['signal']}",
        f"  Holder (15%): {rec['scores']['holder']['score']:.0f} | {rec['scores']['holder']['signal']}",
        f"  Risk (15%): {rec['scores']['risk']['score']:.0f} | {rec['scores']['risk']['signal']}",
        "",
    ]
    if rec["pros"]:
        lines.append("Pros:")
        for pro in rec["pros"]:
            lines.append(f"  + {pro}")
    if rec["cons"]:
        lines.append("Cons:")
        for con in rec["cons"]:
            lines.append(f"  - {con}")
    lines.extend(["", f"Summary: {rec['summary']}", f"Time: {rec['timestamp']}", "=" * 60])
    return "\n".join(lines)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Smart Stock/Fund Recommendation")
    parser.add_argument("--code", "-c", help="Single code")
    parser.add_argument("--codes", nargs="+", help="Batch codes")
    parser.add_argument("--fund", "-f", action="store_true", help="Fund mode")
    parser.add_argument("--scan", nargs="+", help="Scan batch")
    args = parser.parse_args()
    if args.scan:
        print(f"\nScanning {len(args.scan)} {'funds' if args.fund else 'stocks'}...")
        results = scan_recommendations(args.scan, args.fund)
        print(f"\n{'Fund' if args.fund else 'Stock'} Ranking:\n")
        print(f"{'Code':<10} {'Name':<15} {'Index':<8} {'Level':<12} {'Action'}")
        print("-" * 60)
        for r in results:
            print(f"{r['code']:<10} {r['name'][:12]:<15} {r['recommendation_index']:<8} {r['recommendation_level']:<12} {r['action']}")
    elif args.code:
        rec = get_recommendation(args.code, args.fund)
        print(print_recommendation(rec))
    else:
        print("Usage:")
        print("  python recommendation_engine.py --code 600519")
        print("  python recommendation_engine.py --code 110022 --fund")
        print("  python recommendation_engine.py --scan 600519 000858 110022")
