#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fund-advisor Web Server — 基金投资智能顾问 Web UI
Flask + Jinja2 单页仪表盘，提供市场行情、持仓分析、基金查询、量化预估、新闻资讯、智能对话。

数据源: akshare / 东财 / 新浪基金 / 腾讯财经 / 和讯 / 本地JSON数据库
启动方式:
  python scripts/web_server.py          # 独立启动
  或通过 MCP tool: launch_web_ui        # 集成启动
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import re
import math
from datetime import datetime, timedelta
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DATA_DIR = BASE_DIR / "data"
sys.path.insert(0, str(SCRIPT_DIR))

# ── 延迟导入 ─────────────────────────────────────────────────────────
_HoldingsImporter = None

def _get_importer():
    global _HoldingsImporter
    if _HoldingsImporter is None:
        from client_manager.holdings_importer import HoldingsImporter
        _HoldingsImporter = HoldingsImporter
    return _HoldingsImporter()

# ── 缓存层 ──────────────────────────────────────────────────────────
_cache = {}
_cache_lock = threading.Lock()


def _cache_get(key, loader, ttl=300):
    """带TTL的缓存读取"""
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry['ts']) < ttl:
            return entry['data']
    try:
        data = loader()
        with _cache_lock:
            _cache[key] = {'data': data, 'ts': time.time()}
        return data
    except Exception as e:
        print(f"[cache] loader error for {key}: {e}")
        return None


# ── 本地数据懒加载 ───────────────────────────────────────────────────
_managers_data = None
_companies_data = None
_holdings_db = None


def _load_managers():
    global _managers_data
    if _managers_data is None:
        path = DATA_DIR / 'fund_managers_distilled.json'
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                _managers_data = json.load(f).get('managers', [])
    return _managers_data or []


def _load_companies():
    global _companies_data
    if _companies_data is None:
        path = DATA_DIR / 'fund_companies_distilled.json'
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                _companies_data = json.load(f).get('companies', [])
    return _companies_data or []


def _load_holdings_db():
    global _holdings_db
    if _holdings_db is None:
        path = DATA_DIR / 'holdings_database.json'
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                _holdings_db = json.load(f).get('holdings', [])
    return _holdings_db or []


# ── akshare 数据获取 ─────────────────────────────────────────────────
def _get_akshare():
    try:
        import akshare as ak
        return ak
    except ImportError:
        return None


def _fetch_index_data(code, name, market='cn'):
    """获取单个指数数据"""
    ak = _get_akshare()
    if ak is None:
        return None
    try:
        if market == 'cn':
            df = ak.stock_zh_index_daily_em(symbol=code)
        elif market == 'hk':
            df = ak.stock_hk_index_daily_em(symbol=code)
        elif market == 'us':
            df = ak.index_us_stock_sina(symbol=code)
        else:
            return None
        if df is None or df.empty:
            return None
        df = df.tail(30)
        dates = df.iloc[:, 0].astype(str).tolist()
        closes = df['close'].astype(float).tolist() if 'close' in df.columns else df.iloc[:, 4].astype(float).tolist()
        current = closes[-1] if closes else 0
        prev = closes[-2] if len(closes) > 1 else current
        change_pct = ((current - prev) / prev * 100) if prev else 0
        return {
            'name': name, 'code': code,
            'price': round(current, 2),
            'change_pct': round(change_pct, 2),
            'dates': dates, 'closes': [round(c, 2) for c in closes]
        }
    except Exception as e:
        print(f"[akshare] fetch {code} error: {e}")
        return None


def _fetch_fund_nav(code):
    """获取基金历史净值"""
    ak = _get_akshare()
    if ak is None:
        return None
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
        if df is None or df.empty:
            return None
        df.columns = ['date', 'nav', 'acc_nav']
        df['date'] = df['date'].astype(str)
        return df.tail(365)
    except Exception as e:
        print(f"[akshare] fund nav {code} error: {e}")
        return None


def _fetch_fund_info(code):
    """获取基金基本信息"""
    ak = _get_akshare()
    if ak is None:
        return None
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="基金概况")
        if df is not None and not df.empty:
            return dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
    except Exception:
        pass
    return None


# ── 多渠道数据源（新浪、腾讯、和讯）─────────────────────────────────
def _fetch_sina_fund_nav(code):
    """新浪基金净值数据"""
    import urllib.request
    try:
        url = f"https://stock.finance.sina.com.cn/fundInfo/api/openapi.php/CaihuiFundInfoService.getNav?symbol={code}&pageindex=1&num=180"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'https://finance.sina.com.cn/'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        data = json.loads(text)
        items = data.get('result', {}).get('data', {}).get('data', [])
        if not items:
            return None
        dates, navs, acc_navs = [], [], []
        for item in reversed(items):
            dates.append(item.get('fbrq', '')[:10])
            navs.append(float(item.get('jjjz', 0)))
            acc_navs.append(float(item.get('ljjz', 0)))
        return {'dates': dates, 'navs': navs, 'acc_navs': acc_navs}
    except Exception as e:
        print(f"[sina] fund nav {code} error: {e}")
        return None


def _fetch_tencent_index(code):
    """腾讯财经指数数据"""
    import urllib.request
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,30,qfq"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'https://finance.qq.com/'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        data = json.loads(text)
        code_key = list(data.get('data', {}).keys())[0] if data.get('data') else None
        if not code_key:
            return None
        klines = data['data'][code_key].get('qfqday', []) or data['data'][code_key].get('day', [])
        if not klines:
            return None
        dates = [k[0] for k in klines]
        closes = [float(k[2]) for k in klines]
        return {'dates': dates, 'closes': closes}
    except Exception as e:
        print(f"[tencent] index {code} error: {e}")
        return None


def _fetch_hexun_news():
    """和讯网财经新闻"""
    import urllib.request
    from html.parser import HTMLParser
    try:
        url = "https://news.hexun.com/financial/index.html"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        # 简单正则提取新闻标题和链接
        pattern = r'<a[^>]+href="(https?://[^"]*)"[^>]*>([^<]{8,80})</a>'
        matches = re.findall(pattern, text)
        news = []
        seen_titles = set()
        for url, title in matches[:30]:
            title = title.strip()
            if title and title not in seen_titles and len(title) > 8:
                seen_titles.add(title)
                news.append({
                    'title': title, 'source': '和讯网',
                    'url': url, 'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'sentiment': 'neutral'
                })
        return news
    except Exception as e:
        print(f"[hexun] news error: {e}")
        return []


def _fetch_sina_news():
    """新浪财经新闻"""
    import urllib.request
    try:
        url = "https://finance.sina.com.cn/roll/index.d.html?cid=56588&page=1"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        pattern = r'<a[^>]+href="(https?://finance\.sina\.com\.cn/[^"]*)"[^>]*>([^<]{8,80})</a>'
        matches = re.findall(pattern, text)
        news = []
        seen_titles = set()
        for url, title in matches[:30]:
            title = title.strip()
            if title and title not in seen_titles and len(title) > 8:
                seen_titles.add(title)
                news.append({
                    'title': title, 'source': '新浪财经',
                    'url': url, 'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'sentiment': 'neutral'
                })
        return news
    except Exception as e:
        print(f"[sina] news error: {e}")
        return []


def _fetch_tencent_news():
    """腾讯财经新闻"""
    import urllib.request
    try:
        url = "https://news.qq.com/rain/a/FinancialNewsIndex.html"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        pattern = r'<a[^>]+href="(https?://new\.qq\.com/[^"]*)"[^>]*>([^<]{8,80})</a>'
        matches = re.findall(pattern, text)
        news = []
        seen_titles = set()
        for url, title in matches[:30]:
            title = title.strip()
            if title and title not in seen_titles and len(title) > 8:
                seen_titles.add(title)
                news.append({
                    'title': title, 'source': '腾讯财经',
                    'url': url, 'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'sentiment': 'neutral'
                })
        return news
    except Exception as e:
        print(f"[tencent] news error: {e}")
        return []


# ── Flask 应用工厂 ───────────────────────────────────────────────────
def create_app():
    from flask import Flask, request, jsonify, render_template
    from flask_cors import CORS

    app = Flask(__name__, template_folder=str(BASE_DIR / 'templates'))
    CORS(app)

    # ─── 页面路由 ─────────────────────────────────────────────────
    @app.route('/')
    def index():
        return render_template('index.html')

    # ─── 1. 基金/经理/公司搜索 ───────────────────────────────────
    @app.route('/api/search')
    def api_search():
        q = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'fund')
        if not q:
            return jsonify({'error': '请输入搜索关键词'}), 400

        results = []
        q_lower = q.lower()

        if search_type == 'manager':
            managers = _load_managers()
            for m in managers:
                name = m.get('name', '')
                company = m.get('company_name', '')
                fund = m.get('current_fund_name', '')
                if q_lower in name.lower() or q in name or q_lower in company.lower() or q in fund:
                    results.append({
                        'type': 'manager',
                        'manager_id': m.get('manager_id', ''),
                        'name': name,
                        'company': company,
                        'fund_name': fund,
                        'fund_code': m.get('current_fund_code', ''),
                        'style': m.get('investment_style', ''),
                        'tenure_years': m.get('tenure_years', 0),
                        'sector': m.get('sector_description', ''),
                    })
                    if len(results) >= 20:
                        break

        elif search_type == 'company':
            companies = _load_companies()
            for c in companies:
                name = c.get('name', '')
                short = c.get('short_name', '')
                if q_lower in name.lower() or q in name or q_lower in short.lower() or q in short:
                    results.append({
                        'type': 'company',
                        'company_id': c.get('company_id', ''),
                        'name': name,
                        'short_name': short,
                        'total_funds': c.get('total_funds', 0),
                        'manager_count': c.get('manager_count', 0),
                        'style': c.get('dominant_style', ''),
                    })
                    if len(results) >= 20:
                        break

        else:  # fund
            # 从 holdings_database 和 managers 中搜基金
            seen = set()
            managers = _load_managers()
            for m in managers:
                code = m.get('current_fund_code', '')
                name = m.get('current_fund_name', '')
                if code in seen:
                    continue
                if q in code or q_lower in name.lower() or q in name:
                    seen.add(code)
                    results.append({
                        'type': 'fund',
                        'code': code,
                        'name': name,
                        'manager': m.get('name', ''),
                        'company': m.get('company_name', ''),
                        'style': m.get('investment_style', ''),
                    })
                    if len(results) >= 20:
                        break

            # 也从 holdings_database 搜索
            if len(results) < 20:
                holdings = _load_holdings_db()
                for h in holdings:
                    code = h.get('fund_code', '')
                    name = h.get('fund_name', h.get('stock_name', ''))
                    if code in seen:
                        continue
                    if q in code or q_lower in str(name).lower() or q in str(name):
                        seen.add(code)
                        results.append({
                            'type': 'fund',
                            'code': code,
                            'name': str(name),
                            'manager': h.get('manager_name', ''),
                            'company': h.get('company_name', ''),
                        })
                        if len(results) >= 20:
                            break

        return jsonify({'type': search_type, 'query': q, 'results': results})

    # ─── 2. 市场行情总览 ─────────────────────────────────────────
    @app.route('/api/market/overview')
    def api_market_overview():
        def load_overview():
            indices = [
                ('sh000300', '沪深300', 'cn'),
                ('sz399006', '创业板指', 'cn'),
                ('sh000016', '上证50', 'cn'),
                ('sz399001', '深证成指', 'cn'),
                ('sh000015', '红利指数', 'cn'),
                ('sh000905', '中证500', 'cn'),
            ]
            markets = []
            for code, name, mkt in indices:
                # 先尝试 akshare
                data = _fetch_index_data(code, name, mkt)
                if data is None:
                    # fallback 腾讯
                    tcode = code[:2].replace('sh', 'sh').replace('sz', 'sz') + code[2:]
                    tdata = _fetch_tencent_index(tcode)
                    if tdata:
                        closes = tdata['closes']
                        current = closes[-1] if closes else 0
                        prev = closes[-2] if len(closes) > 1 else current
                        chg = ((current - prev) / prev * 100) if prev else 0
                        data = {
                            'name': name, 'code': code,
                            'price': round(current, 2),
                            'change_pct': round(chg, 2),
                            'dates': tdata['dates'][-30:],
                            'closes': [round(c, 2) for c in closes[-30:]]
                        }
                if data:
                    markets.append(data)
            return {'markets': markets, 'timestamp': datetime.now().isoformat()}

        data = _cache_get('market_overview', load_overview, ttl=300)
        return jsonify(data or {'markets': [], 'timestamp': datetime.now().isoformat()})

    # ─── 3. 基金净值走势 ─────────────────────────────────────────
    @app.route('/api/nav/chart')
    def api_nav_chart():
        code = request.args.get('code', '').strip()
        period = request.args.get('period', '1y')
        if not code:
            return jsonify({'error': '请输入基金代码'}), 400

        period_days = {'1m': 30, '3m': 90, '6m': 180, '1y': 365}
        days = period_days.get(period, 365)

        cache_key = f'nav_{code}_{period}'

        def load_nav():
            # 优先 akshare
            df = _fetch_fund_nav(code)
            if df is not None and not df.empty:
                df = df.tail(days)
                dates = df['date'].tolist()
                navs = df['nav'].astype(float).tolist()
                acc_navs = df['acc_nav'].astype(float).tolist()
            else:
                # fallback 新浪
                sina = _fetch_sina_fund_nav(code)
                if sina:
                    dates = sina['dates'][-days:]
                    navs = [round(n, 4) for n in sina['navs'][-days:]]
                    acc_navs = [round(n, 4) for n in sina['acc_navs'][-days:]]
                else:
                    return None

            # 计算统计指标
            if len(navs) >= 20:
                returns = [(navs[i] - navs[i-1]) / navs[i-1] for i in range(1, len(navs)) if navs[i-1] > 0]
                total_return = (navs[-1] - navs[0]) / navs[0] * 100 if navs[0] > 0 else 0
                max_nav = navs[0]
                max_dd = 0
                for n in navs:
                    if n > max_nav:
                        max_nav = n
                    dd = (max_nav - n) / max_nav
                    if dd > max_dd:
                        max_dd = dd
                daily_std = (sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns)) ** 0.5 if returns else 0
                vol = daily_std * math.sqrt(252) * 100
                sharpe = (sum(returns)/len(returns) * 252 - 0.03) / (daily_std * math.sqrt(252)) if daily_std > 0 else 0
                stats = {
                    'return_pct': round(total_return, 2),
                    'max_drawdown': round(max_dd * 100, 2),
                    'volatility': round(vol, 2),
                    'sharpe': round(sharpe, 2),
                }
            else:
                stats = {'return_pct': 0, 'max_drawdown': 0, 'volatility': 0, 'sharpe': 0}

            # 查基金名称
            fund_name = ''
            for m in _load_managers():
                if m.get('current_fund_code') == code:
                    fund_name = m.get('current_fund_name', '')
                    break

            return {
                'code': code, 'name': fund_name,
                'dates': dates, 'navs': navs, 'acc_navs': acc_navs,
                'stats': stats
            }

        data = _cache_get(cache_key, load_nav, ttl=3600)
        if data is None:
            return jsonify({'error': f'未找到基金 {code} 的净值数据'}), 404
        return jsonify(data)

    # ─── 4. 客户持仓 ─────────────────────────────────────────────
    @app.route('/api/holdings')
    def api_holdings():
        client_id = request.args.get('client_id', '').strip()
        if not client_id:
            # 尝试列出可用客户
            clients_dir = DATA_DIR / 'clients'
            clients = []
            if clients_dir.exists():
                for d in clients_dir.iterdir():
                    if d.is_dir():
                        clients.append(d.name)
            return jsonify({'clients': clients, 'message': '请指定客户ID'})

        # 读取客户持仓
        client_dir = DATA_DIR / 'clients' / client_id
        holdings_file = client_dir / 'holdings.json'
        if not holdings_file.exists():
            # fallback 到 user_holdings.json
            holdings_file = DATA_DIR / 'user_holdings.json'

        if not holdings_file.exists():
            return jsonify({'client_id': client_id, 'holdings': [], 'summary': {}})

        try:
            with open(holdings_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except Exception:
            return jsonify({'client_id': client_id, 'holdings': [], 'summary': {}})

        # 处理不同格式
        holdings_list = []
        if isinstance(raw, dict):
            items = raw.get('holdings', [raw])
            if isinstance(items, dict):
                items = [{'code': k, **v} if isinstance(v, dict) else {'code': k} for k, v in items.items()]
            elif not isinstance(items, list):
                items = []
        elif isinstance(raw, list):
            items = raw
        else:
            items = []

        total_value = 0
        total_cost = 0
        for item in items:
            code = item.get('code', item.get('fund_code', ''))
            name = item.get('name', item.get('fund_name', ''))
            shares = float(item.get('shares', item.get('amount', 0)))
            cost_nav = float(item.get('cost', item.get('cost_nav', 0)))

            # 获取当前净值
            current_nav = cost_nav
            try:
                ak = _get_akshare()
                if ak:
                    est = ak.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
                    if est is not None and not est.empty:
                        current_nav = float(est.iloc[-1, 1])
            except Exception:
                pass

            pnl_pct = ((current_nav - cost_nav) / cost_nav * 100) if cost_nav > 0 else 0
            value = current_nav * shares
            cost_total = cost_nav * shares
            total_value += value
            total_cost += cost_total

            # 查基金名称
            if not name:
                for m in _load_managers():
                    if m.get('current_fund_code') == code:
                        name = m.get('current_fund_name', '')
                        break

            holdings_list.append({
                'code': code, 'name': name,
                'shares': shares, 'cost_nav': round(cost_nav, 4),
                'current_nav': round(current_nav, 4),
                'pnl_pct': round(pnl_pct, 2),
                'value': round(value, 2), 'cost_total': round(cost_total, 2)
            })

        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        return jsonify({
            'client_id': client_id,
            'holdings': holdings_list,
            'summary': {
                'total_value': round(total_value, 2),
                'total_cost': round(total_cost, 2),
                'total_pnl': round(total_pnl, 2),
                'total_pnl_pct': round(total_pnl_pct, 2)
            }
        })

    # ─── 5. 新闻资讯 ─────────────────────────────────────────────
    @app.route('/api/news')
    def api_news():
        limit = int(request.args.get('limit', 20))

        def load_news():
            all_news = []

            # 1. 本地 news_advisor
            try:
                from analysis.news_advisor import NewsAdvisor
                advisor = NewsAdvisor()
                summary = advisor.get_news_summary(limit=limit)
                items = summary.get('items', summary.get('news', []))
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            all_news.append({
                                'title': item.get('title', ''),
                                'source': item.get('source', '本地'),
                                'time': item.get('time', item.get('pub_time', '')),
                                'url': item.get('url', ''),
                                'sentiment': item.get('sentiment', 'neutral'),
                                'summary': item.get('summary', item.get('content', ''))[:200],
                            })
            except Exception as e:
                print(f"[news] NewsAdvisor error: {e}")

            # 2. 新浪财经
            sina_news = _fetch_sina_news()
            all_news.extend(sina_news)

            # 3. 腾讯财经
            tencent_news = _fetch_tencent_news()
            all_news.extend(tencent_news)

            # 4. 和讯网
            hexun_news = _fetch_hexun_news()
            all_news.extend(hexun_news)

            # 去重
            seen = set()
            unique = []
            for n in all_news:
                title = n.get('title', '')
                if title and title not in seen:
                    seen.add(title)
                    unique.append(n)

            return {'news': unique[:limit], 'total': len(unique), 'timestamp': datetime.now().isoformat()}

        data = _cache_get('news_feed', load_news, ttl=1800)
        return jsonify(data or {'news': [], 'total': 0})

    # ─── 6. 量化预估 ─────────────────────────────────────────────
    @app.route('/api/quant/forecast', methods=['POST'])
    def api_quant_forecast():
        body = request.json or {}
        code = body.get('code', '').strip()
        forecast_days = int(body.get('forecast_days', 30))
        if not code:
            return jsonify({'error': '请输入基金代码'}), 400

        try:
            from analysis.fund_quant_analyzer import FundQuantAnalyzer
            analyzer = FundQuantAnalyzer()
            analysis = analyzer.analyze_fund(code)
        except Exception as e:
            return jsonify({'error': f'量化分析失败: {e}'}), 500

        # 获取净值数据用于预测
        nav_data = _fetch_fund_nav(code)
        forecast_list = []
        if nav_data is not None and not nav_data.empty:
            navs = nav_data['acc_nav'].astype(float).tolist()
            dates_raw = nav_data['date'].tolist()
            if len(navs) >= 20:
                # 简单线性回归预测
                n = len(navs)
                x_mean = (n - 1) / 2
                y_mean = sum(navs) / n
                num = sum((i - x_mean) * (navs[i] - y_mean) for i in range(n))
                den = sum((i - x_mean) ** 2 for i in range(n))
                slope = num / den if den else 0
                intercept = y_mean - slope * x_mean

                # 均线趋势
                ma5 = sum(navs[-5:]) / 5
                ma20 = sum(navs[-20:]) / 20
                trend_dir = 'up' if ma5 > ma20 else ('down' if ma5 < ma20 else 'sideways')

                # 波动率
                returns = [(navs[i] - navs[i-1]) / navs[i-1] for i in range(1, n) if navs[i-1] > 0]
                daily_std = (sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns)) ** 0.5 if returns else 0

                # 生成预测
                last_date_str = dates_raw[-1]
                try:
                    last_date = datetime.strptime(last_date_str[:10], '%Y-%m-%d')
                except Exception:
                    last_date = datetime.now()

                for i in range(1, forecast_days + 1):
                    pred_date = last_date + timedelta(days=i)
                    pred_nav = intercept + slope * (n - 1 + i)
                    confidence = daily_std * math.sqrt(i) * navs[-1]
                    forecast_list.append({
                        'date': pred_date.strftime('%Y-%m-%d'),
                        'predicted_nav': round(pred_nav, 4),
                        'confidence_low': round(pred_nav - 1.96 * confidence, 4),
                        'confidence_high': round(pred_nav + 1.96 * confidence, 4)
                    })

                # 信号
                combined = analysis.get('combined_signal', 0)
                if combined > 0.3:
                    signal = 'buy'
                elif combined < -0.3:
                    signal = 'sell'
                else:
                    signal = 'hold'

                metrics = {
                    'trend': trend_dir,
                    'volatility': round(daily_std * math.sqrt(252) * 100, 2),
                    'signal': signal,
                    'combined_signal': combined,
                    'action': analysis.get('action', '持有'),
                    'action_reason': analysis.get('action_reason', ''),
                }
            else:
                metrics = {'trend': 'sideways', 'volatility': 0, 'signal': 'hold'}
        else:
            metrics = {'trend': 'sideways', 'volatility': 0, 'signal': 'hold'}

        # 查基金名称
        fund_name = ''
        for m in _load_managers():
            if m.get('current_fund_code') == code:
                fund_name = m.get('current_fund_name', '')
                break

        return jsonify({
            'code': code, 'name': fund_name,
            'current_nav': navs[-1] if nav_data is not None and not nav_data.empty else 0,
            'forecast': forecast_list,
            'metrics': metrics,
            'signals': analysis.get('signals', {}),
            'method': 'moving_average + linear_regression',
            'analyzed_at': analysis.get('analyzed_at', datetime.now().strftime('%Y-%m-%d %H:%M'))
        })

    # ─── 7. 基金对比 ─────────────────────────────────────────────
    @app.route('/api/compare', methods=['POST'])
    def api_compare():
        body = request.json or {}
        codes = body.get('codes', [])
        if len(codes) < 2:
            return jsonify({'error': '请至少输入两个基金代码'}), 400

        funds = []
        all_dates = []
        all_series = {}

        for code in codes[:5]:
            fund_info = {'code': code, 'name': '', 'nav': 0, 'return_1y': 0,
                         'max_drawdown': 0, 'sharpe': 0, 'manager': ''}

            # 查名称和经理
            for m in _load_managers():
                if m.get('current_fund_code') == code:
                    fund_info['name'] = m.get('current_fund_name', '')
                    fund_info['manager'] = m.get('name', '')
                    break

            # 获取净值
            nav_data = _fetch_fund_nav(code)
            if nav_data is not None and not nav_data.empty:
                navs = nav_data['acc_nav'].astype(float).tolist()
                dates = nav_data['date'].tolist()
                fund_info['nav'] = round(navs[-1], 4)
                if len(navs) >= 252:
                    fund_info['return_1y'] = round((navs[-1] - navs[-252]) / navs[-252] * 100, 2)

                # 计算最大回撤
                max_nav = navs[0]
                max_dd = 0
                for n in navs:
                    if n > max_nav:
                        max_nav = n
                    dd = (max_nav - n) / max_nav
                    if dd > max_dd:
                        max_dd = dd
                fund_info['max_drawdown'] = round(max_dd * 100, 2)

                # 夏普比率
                returns = [(navs[i] - navs[i-1]) / navs[i-1] for i in range(1, len(navs)) if navs[i-1] > 0]
                if returns:
                    avg_r = sum(returns) / len(returns)
                    std_r = (sum((r - avg_r)**2 for r in returns) / len(returns)) ** 0.5
                    if std_r > 0:
                        fund_info['sharpe'] = round((avg_r * 252 - 0.03) / (std_r * math.sqrt(252)), 2)

                # 归一化走势用于对比图
                if navs[0] > 0:
                    normalized = [round(n / navs[0] * 100, 2) for n in navs]
                    all_series[code] = normalized
                    if len(dates) > len(all_dates):
                        all_dates = dates

            funds.append(fund_info)

        return jsonify({
            'funds': funds,
            'chart_data': {'dates': all_dates[-365:], 'series': {k: v[-365:] for k, v in all_series.items()}}
        })

    # ─── 8. 智能对话 ─────────────────────────────────────────────
    _cm_instance = None
    _cm_lock = threading.Lock()

    def _get_client_manager():
        nonlocal _cm_instance
        if _cm_instance is None:
            with _cm_lock:
                if _cm_instance is None:
                    try:
                        from client_manager.conversation_engine import ClientManager
                        _cm_instance = ClientManager()
                    except Exception as e:
                        print(f"[chat] ClientManager init error: {e}")
        return _cm_instance

    @app.route('/api/chat', methods=['POST'])
    def api_chat():
        body = request.json or {}
        query = body.get('query', '').strip()
        if not query:
            return jsonify({'error': '请输入问题'}), 400

        # 优先使用 ClientManager
        cm = _get_client_manager()
        if cm:
            try:
                reply = cm.chat('web_user', query)
                return jsonify({
                    'reply': reply,
                    'source': 'local_engine',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                print(f"[chat] ClientManager error: {e}")

        # fallback: 简单回复 + 引导
        return jsonify({
            'reply': f'收到您的问题："{query}"。对话引擎正在加载中，请稍后重试。您也可以使用上方的基金查询功能直接搜索。',
            'source': 'fallback',
            'timestamp': datetime.now().isoformat()
        })

    # ─── 9. 文件上传 ─────────────────────────────────────────────
    @app.route('/api/upload', methods=['POST'])
    def api_upload():
        """上传持仓文件（截图/Word/PDF/Excel/CSV），自动识别并返回持仓数据"""
        from werkzeug.utils import secure_filename

        if 'file' not in request.files:
            return jsonify({'error': '请上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400

        client_id = request.form.get('client_id', '').strip() or 'web_default'
        filename = secure_filename(file.filename)
        ext = Path(filename).suffix.lower()

        allowed_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.gif',
                        '.docx', '.pdf', '.xlsx', '.xls', '.csv'}
        if ext not in allowed_exts:
            return jsonify({'error': f'不支持的文件格式: {ext}，支持: 图片/Word/PDF/Excel/CSV'}), 400

        # 保存到临时目录
        upload_dir = DATA_DIR / 'uploads' / client_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_name = f"{timestamp}_{filename}"
        saved_path = upload_dir / saved_name
        file.save(str(saved_path))

        # 根据文件类型调用不同导入方法
        try:
            importer = _get_importer()
            if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif'):
                result = importer.import_from_screenshot(str(saved_path), client_id=client_id)
                method = '截图OCR识别'
            elif ext == '.docx':
                result = importer.import_from_docx(str(saved_path), client_id=client_id)
                method = 'Word文档解析'
            elif ext == '.pdf':
                result = importer.import_from_pdf(str(saved_path), client_id=client_id)
                method = 'PDF文档解析'
            elif ext in ('.xlsx', '.xls', '.csv'):
                result = _import_excel_csv(saved_path, client_id, ext)
                method = 'Excel/CSV解析'
            else:
                return jsonify({'error': '不支持的文件类型'}), 400
        except Exception as e:
            return jsonify({'error': f'文件处理失败: {e}', 'method': method if 'method' in dir() else ext}), 500

        holdings = result.get('holdings', [])
        success = result.get('success', len(holdings) > 0)

        # 保存到客户仓库
        if success and holdings and client_id:
            try:
                importer.save_to_repository(client_id, holdings,
                                            source=method, source_path=str(saved_path))
            except Exception as e:
                print(f"[upload] save to repository error: {e}")

        # 格式化回复
        reply_lines = [f"已通过{method}识别到 {len(holdings)} 条持仓信息:"]
        for h in holdings[:10]:
            code = h.get('fund_code', h.get('code', ''))
            name = h.get('fund_name', h.get('name', '未知'))
            shares = h.get('shares', h.get('amount', '?'))
            cost = h.get('cost', h.get('cost_nav', '?'))
            reply_lines.append(f"  {code} {name} 份额:{shares} 成本:{cost}")
        if len(holdings) > 10:
            reply_lines.append(f"  ...及其他 {len(holdings) - 10} 条")
        if client_id and client_id != 'web_default':
            reply_lines.append(f"已保存到客户「{client_id}」的持仓仓库。")

        return jsonify({
            'success': success,
            'method': method,
            'filename': filename,
            'holdings': holdings,
            'reply': '\n'.join(reply_lines),
            'raw_text': result.get('raw_text', ''),
            'errors': result.get('errors', [])
        })

    def _import_excel_csv(file_path, client_id, ext):
        """Excel/CSV 持仓导入"""
        result = {'success': False, 'holdings': [], 'errors': []}
        try:
            import pandas as pd
            if ext == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)

            # 尝试自动识别列名
            col_map = {}
            df_cols = {str(c).strip(): str(c) for c in df.columns}
            # 基金代码
            for key in ['基金代码', '代码', 'fund_code', 'code', '产品代码']:
                if key in df_cols:
                    col_map['fund_code'] = df_cols[key]
                    break
            # 基金名称
            for key in ['基金名称', '名称', 'fund_name', 'name', '产品名称']:
                if key in df_cols:
                    col_map['fund_name'] = df_cols[key]
                    break
            # 份额
            for key in ['份额', '持有份额', 'shares', 'amount', '持有份数', '持仓份额',
                         '持有金额', '市值', '投资金额', '申购金额']:
                if key in df_cols:
                    col_map['shares'] = df_cols[key]
                    break
            # 成本
            for key in ['成本', '成本净值', 'cost', 'cost_nav', '买入净值', '买入成本',
                         '单位成本', '平均成本']:
                if key in df_cols:
                    col_map['cost'] = df_cols[key]
                    break

            if 'fund_code' not in col_map:
                # 尝试按第一列是代码、第二列是名称猜测
                cols = list(df.columns)
                if len(cols) >= 2:
                    # 检查第一列是否有6位数字
                    sample = str(df.iloc[0, 0]) if len(df) > 0 else ''
                    if any(c.isdigit() for c in sample):
                        col_map['fund_code'] = cols[0]
                        col_map['fund_name'] = cols[1] if len(cols) > 1 else cols[0]
                        if len(cols) >= 3:
                            col_map['shares'] = cols[2]
                        if len(cols) >= 4:
                            col_map['cost'] = cols[3]

            holdings = []
            for _, row in df.iterrows():
                h = {}
                code_raw = str(row.get(col_map.get('fund_code', ''), ''))
                code = re.sub(r'\D', '', code_raw)[:6]
                if not code or len(code) < 5:
                    continue
                h['fund_code'] = code.zfill(6)
                h['fund_name'] = str(row.get(col_map.get('fund_name', ''), ''))
                shares_raw = str(row.get(col_map.get('shares', ''), '0'))
                h['shares'] = float(re.sub(r'[^\d.]', '', shares_raw) or 0)
                cost_raw = str(row.get(col_map.get('cost', ''), '0'))
                h['cost'] = float(re.sub(r'[^\d.]', '', cost_raw) or 0)
                holdings.append(h)

            result['success'] = len(holdings) > 0
            result['holdings'] = holdings
        except Exception as e:
            result['errors'].append(str(e))
        return result

    # ─── 10. 健康检查 ────────────────────────────────────────────
    @app.route('/api/health')
    def api_health():
        return jsonify({
            'status': 'ok',
            'service': 'fund-advisor-web',
            'managers_loaded': len(_load_managers()),
            'companies_loaded': len(_load_companies()),
            'timestamp': datetime.now().isoformat()
        })

    return app


# ─── 独立启动入口 ────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("  基金投资智能顾问 Web UI")
    print("  http://localhost:5002")
    print("=" * 50)
    app = create_app()
    app.run(host='0.0.0.0', port=5002, debug=False, use_reloader=False, threaded=True)
