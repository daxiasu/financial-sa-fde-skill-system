#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-stock-researcher Flask Web Server — A股智能投研仪表盘
集成 TradingAgents 多智能体分析、技术分析、板块轮动、产业链分析。
启动: python scripts/web_server.py → http://localhost:5003
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime, date
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from flask import Flask, jsonify, request, render_template, Response, stream_with_context
from flask_cors import CORS

# ==================== 缓存 ====================

_cache = {}
_cache_lock = threading.Lock()

def _cache_get(key, loader, ttl=300):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry["ts"]) < ttl:
            return entry["data"]
    try:
        data = loader()
    except Exception:
        data = entry["data"] if entry else None
    with _cache_lock:
        _cache[key] = {"data": data, "ts": time.time()}
    return data

# ==================== 数据获取 ====================

def _fetch_realtime_quote(code):
    """腾讯财经实时行情"""
    import requests
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    url = f"http://qt.gtimg.cn/q={prefix}{code}"
    try:
        r = requests.get(url, timeout=5)
        r.encoding = "gbk"
        fields = r.text.split("~")
        if len(fields) < 45:
            return None
        return {
            "code": code,
            "name": fields[1],
            "price": float(fields[3]) if fields[3] else 0,
            "prev_close": float(fields[4]) if fields[4] else 0,
            "open": float(fields[5]) if fields[5] else 0,
            "volume": float(fields[6]) if fields[6] else 0,
            "amount": float(fields[37]) if fields[37] else 0,
            "high": float(fields[33]) if fields[33] else 0,
            "low": float(fields[34]) if fields[34] else 0,
            "pe": float(fields[39]) if fields[39] else 0,
            "pb": float(fields[46]) if len(fields) > 46 and fields[46] else 0,
            "market_cap": float(fields[45]) if len(fields) > 45 and fields[45] else 0,
            "change_pct": round((float(fields[3]) - float(fields[4])) / float(fields[4]) * 100, 2) if fields[3] and fields[4] and float(fields[4]) > 0 else 0,
        }
    except Exception:
        return None

def _fetch_kline(code, count=120):
    """腾讯财经K线数据"""
    import requests
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,{count},qfq"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        key = f"{prefix}{code}"
        stock_data = data.get("data", {}).get(key, {})
        klines = stock_data.get("qfqday") or stock_data.get("day") or []
        result = []
        for k in klines:
            if len(k) >= 5:
                result.append({
                    "date": k[0],
                    "open": float(k[1]),
                    "close": float(k[2]),
                    "high": float(k[3]),
                    "low": float(k[4]),
                    "volume": float(k[5]) if len(k) > 5 else 0,
                })
        return result
    except Exception:
        return []

def _fetch_index_data(index_code):
    """获取指数行情"""
    return _fetch_realtime_quote(index_code)

def _calc_technical(klines):
    """计算技术指标"""
    if len(klines) < 20:
        return {}
    closes = [k["close"] for k in klines]

    def ma(data, n):
        if len(data) < n:
            return None
        return round(sum(data[-n:]) / n, 2)

    def rsi(data, n=14):
        if len(data) < n + 1:
            return None
        gains, losses = [], []
        for i in range(-n, 0):
            diff = data[i] - data[i-1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / n
        avg_loss = sum(losses) / n
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return round(100 - 100 / (1 + rs), 2)

    def macd(data):
        if len(data) < 26:
            return None, None, None
        ema12 = data[-26]
        ema26 = data[-26]
        for v in data[-25:]:
            ema12 = v * 2/13 + ema12 * 11/13
            ema26 = v * 2/27 + ema26 * 25/27
        dif = ema12 - ema26
        dea = dif  # simplified
        for v in data[-8:]:
            ema12 = v * 2/13 + ema12 * 11/13
            ema26 = v * 2/27 + ema26 * 25/27
            dif = ema12 - ema26
            dea = dif * 2/10 + dea * 8/10
        return round(dif, 4), round(dea, 4), round((dif - dea) * 2, 4)

    dif, dea, hist = macd(closes)

    return {
        "ma5": ma(closes, 5),
        "ma10": ma(closes, 10),
        "ma20": ma(closes, 20),
        "ma60": ma(closes, 60),
        "rsi6": rsi(closes, 6),
        "rsi14": rsi(closes, 14),
        "dif": dif,
        "dea": dea,
        "macd_hist": hist,
        "close": closes[-1],
    }

# ==================== Multi-Agent 分析 ====================

_analysis_status = {}
_analysis_lock = threading.Lock()

def _run_multi_agent_analysis(ticker, trade_date, llm_provider, quick_model, deep_model, analysis_id):
    """在后台线程运行多智能体分析"""
    try:
        with _analysis_lock:
            _analysis_status[analysis_id] = {
                "status": "running",
                "stage": "初始化",
                "progress": 0,
                "reports": {},
                "error": None,
                "start_time": time.time(),
            }

        sys.path.insert(0, str(SCRIPT_DIR))
        try:
            from multi_agent.default_config import DEFAULT_CONFIG
            from multi_agent.graph.trading_graph import TradingAgentsGraph
        except ImportError as ie:
            with _analysis_lock:
                _analysis_status[analysis_id].update({
                    "status": "error",
                    "error": f"缺少多智能体依赖: {ie}。请安装: pip install langchain-core langchain-openai langgraph",
                    "stage": "失败",
                })
            return

        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = llm_provider
        config["quick_think_llm"] = quick_model
        config["deep_think_llm"] = deep_model
        config["output_language"] = "Chinese"
        config["max_debate_rounds"] = 1
        config["max_risk_discuss_rounds"] = 1

        def _update(stage, progress, reports=None):
            with _analysis_lock:
                s = _analysis_status[analysis_id]
                s["stage"] = stage
                s["progress"] = progress
                if reports:
                    s["reports"].update(reports)

        _update("创建分析图", 5)
        graph = TradingAgentsGraph(
            selected_analysts=["market", "social", "news", "fundamentals", "policy", "hot_money", "lockup"],
            config=config,
        )

        stages = [
            ("市场分析师", 10), ("社交情绪分析师", 20), ("新闻分析师", 30),
            ("基本面分析师", 40), ("政策分析师", 50), ("资金流向追踪", 60),
            ("限售解禁监控", 65), ("质量门控", 70),
            ("多空辩论", 75), ("研究员决策", 80),
            ("交易员计划", 85), ("风险辩论", 90), ("最终决策", 95),
        ]

        # We can't easily get per-stage progress from the graph,
        # so we update progress as we go
        _update("运行7位分析师", 10)
        final_state, signal = graph.propagate(ticker, trade_date)

        reports = {}
        for key in ["market_report", "sentiment_report", "news_report",
                     "fundamentals_report", "policy_report", "hot_money_report", "lockup_report"]:
            if final_state.get(key):
                reports[key] = final_state[key]

        _update("分析完成", 100, reports)
        with _analysis_lock:
            _analysis_status[analysis_id].update({
                "status": "complete",
                "signal": signal,
                "final_decision": final_state.get("final_trade_decision", ""),
                "investment_plan": final_state.get("investment_plan", ""),
                "trader_plan": final_state.get("trader_investment_plan", ""),
                "bull_history": final_state.get("investment_debate_state", {}).get("bull_history", ""),
                "bear_history": final_state.get("investment_debate_state", {}).get("bear_history", ""),
                "judge_decision": final_state.get("investment_debate_state", {}).get("judge_decision", ""),
                "risk_aggressive": final_state.get("risk_debate_state", {}).get("aggressive_history", ""),
                "risk_conservative": final_state.get("risk_debate_state", {}).get("conservative_history", ""),
                "risk_neutral": final_state.get("risk_debate_state", {}).get("neutral_history", ""),
                "risk_decision": final_state.get("risk_debate_state", {}).get("judge_decision", ""),
                "data_quality": final_state.get("data_quality_summary", ""),
                "elapsed": round(time.time() - _analysis_status[analysis_id]["start_time"], 1),
            })
    except Exception as e:
        with _analysis_lock:
            _analysis_status[analysis_id].update({
                "status": "error",
                "error": f"{type(e).__name__}: {e}",
                "stage": "失败",
            })
        traceback.print_exc()

# ==================== Flask App ====================

def create_app():
    template_dir = str(SKILL_DIR / "templates")
    app = Flask(__name__, template_folder=template_dir)
    CORS(app)
    app.config["JSON_AS_ASCII"] = False

    @app.route("/")
    def index():
        return render_template("index.html")

    # ---------- 市场概览 ----------
    @app.route("/api/market/overview")
    def market_overview():
        indices = {
            "sh000001": "上证指数",
            "sh000300": "沪深300",
            "sz399006": "创业板指",
            "sh000688": "科创50",
            "sh000016": "上证50",
            "sz399005": "中小板指",
        }
        result = []
        for code, name in indices.items():
            data = _cache_get(f"idx_{code}", lambda c=code: _fetch_index_data(c), ttl=120)
            if data:
                data["display_name"] = name
                result.append(data)
            else:
                result.append({"code": code, "display_name": name, "name": name,
                              "price": 0, "change_pct": 0, "error": True})
        return jsonify(result)

    @app.route("/api/market/kline")
    def market_kline():
        code = request.args.get("code", "sh000001")
        count = int(request.args.get("count", 60))
        data = _cache_get(f"kline_{code}_{count}", lambda: _fetch_kline(code, count), ttl=600)
        return jsonify(data or [])

    # ---------- 股票分析 ----------
    @app.route("/api/stock/quote")
    def stock_quote():
        code = request.args.get("code", "")
        if not code or len(code) != 6:
            return jsonify({"error": "请提供6位股票代码"}), 400
        data = _cache_get(f"quote_{code}", lambda: _fetch_realtime_quote(code), ttl=60)
        return jsonify(data or {"error": "获取行情失败"})

    @app.route("/api/stock/kline")
    def stock_kline():
        code = request.args.get("code", "")
        count = int(request.args.get("count", 120))
        if not code:
            return jsonify({"error": "请提供股票代码"}), 400
        data = _cache_get(f"stk_{code}_{count}", lambda: _fetch_kline(code, count), ttl=600)
        return jsonify(data or [])

    @app.route("/api/stock/technical")
    def stock_technical():
        code = request.args.get("code", "")
        if not code:
            return jsonify({"error": "请提供股票代码"}), 400
        klines = _cache_get(f"stk_{code}_120", lambda: _fetch_kline(code, 120), ttl=600)
        if not klines:
            return jsonify({"error": "获取K线数据失败"})
        tech = _calc_technical(klines)
        return jsonify(tech)

    # ---------- 多智能体分析 ----------
    @app.route("/api/agent/analyze", methods=["POST"])
    def agent_analyze():
        data = request.json or {}
        ticker = data.get("ticker", "").strip()
        trade_date = data.get("trade_date", date.today().strftime("%Y-%m-%d"))
        llm_provider = data.get("llm_provider", "deepseek")
        quick_model = data.get("quick_model", "deepseek-chat")
        deep_model = data.get("deep_model", "deepseek-chat")

        if not ticker:
            return jsonify({"error": "请提供股票代码或名称"}), 400

        import uuid
        analysis_id = str(uuid.uuid4())[:8]
        thread = threading.Thread(
            target=_run_multi_agent_analysis,
            args=(ticker, trade_date, llm_provider, quick_model, deep_model, analysis_id),
            daemon=True,
        )
        thread.start()
        return jsonify({"analysis_id": analysis_id, "status": "started"})

    @app.route("/api/agent/status")
    def agent_status():
        aid = request.args.get("id", "")
        with _analysis_lock:
            status = _analysis_status.get(aid)
        if not status:
            return jsonify({"error": "未找到分析任务"}), 404
        return jsonify(status)

    @app.route("/api/agent/stream/<analysis_id>")
    def agent_stream(analysis_id):
        """SSE 流式推送分析进度"""
        def generate():
            last_progress = -1
            while True:
                with _analysis_lock:
                    status = _analysis_status.get(analysis_id)
                if not status:
                    yield f"data: {json.dumps({'error': 'not found'})}\n\n"
                    break
                if status["progress"] != last_progress:
                    last_progress = status["progress"]
                    yield f"data: {json.dumps(status, ensure_ascii=False)}\n\n"
                if status["status"] in ("complete", "error"):
                    break
                time.sleep(1)
        return Response(stream_with_context(generate()), mimetype="text/event-stream")

    # ---------- 搜索 ----------
    @app.route("/api/search")
    def search():
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify([])
        # Try as stock code
        if q.isdigit() and len(q) == 6:
            quote = _fetch_realtime_quote(q)
            if quote:
                return jsonify([{"type": "stock", "code": q, "name": quote["name"]}])
        return jsonify([])

    # ---------- 板块分析 ----------
    @app.route("/api/sector/ranking")
    def sector_ranking():
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from stock_researcher.sector_analysis.sectors import SectorAnalyzer
            analyzer = SectorAnalyzer()
            results = analyzer.get_sector_ranking()
            data = [{"name": r.name, "avg_change_pct": r.avg_change_pct,
                     "up_count": r.up_count, "down_count": r.down_count,
                     "total_net_flow": r.total_net_flow, "signal": r.signal}
                    for r in results[:15]]
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ---------- 健康检查 ----------
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "time": datetime.now().isoformat()})

    return app


# ==================== 独立启动 ====================

_web_server_thread = None

def launch_web_ui(port=5003):
    global _web_server_thread
    if _web_server_thread and _web_server_thread.is_alive():
        return f"http://localhost:{port}"
    app = create_app()
    def run():
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
    _web_server_thread = threading.Thread(target=run, daemon=True)
    _web_server_thread.start()
    return f"http://localhost:{port}"


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5003
    url = launch_web_ui(port)
    print(f"Web UI 启动: {url}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("Web UI 已停止")
