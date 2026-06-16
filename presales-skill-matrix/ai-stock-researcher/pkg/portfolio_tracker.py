#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""持仓追踪引擎 v1.0 - 支持股票和基金，成本盈亏，调仓建议"""
from __future__ import annotations
import sys, json, sqlite3, time, re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "pkg"))
from crawl_utils import safe_request

def _sf(v, default=0.0):
    """safe float"""
    try:
        return float(v) if v not in ("", "-", None, "N/A", "null") else default
    except (TypeError, ValueError):
        return default

def _fetch_tx_price(codes: list[str]) -> dict[str, dict]:
    """通过腾讯API批量获取股票现价，返回 {code: {price, change_pct, name}}"""
    if not codes:
        return {}
    ts = ",".join(f"sh{c}" if c.startswith(("6", "5")) else f"sz{c}" for c in codes if c.strip())
    if not ts:
        return {}
    url = f"https://qt.gtimg.cn/q={ts}&_={int(time.time()*1000)}"
    raw = safe_request(url, timeout=8)
    result = {}
    if not raw:
        return result
    text = raw.decode("gbk", errors="replace")
    for line in text.strip().split("\n"):
        m = re.search(r"v_(\w+)=\"(.+?)\"", line)
        if not m:
            continue
        code_full = m.group(1)  # e.g. sh600519
        fields = m.group(2).split("~")
        if len(fields) < 5:
            continue
        raw_code = code_full[2:] if code_full.startswith(("sh", "sz")) else code_full
        result[raw_code] = {
            "name": fields[1],
            "price": _sf(fields[3]),
            "change_pct": _sf(fields[31]) if len(fields) > 31 else 0,
            "open": _sf(fields[4]),
            "high": _sf(fields[5]),
            "low": _sf(fields[6]),
            "volume": _sf(fields[7]),
            "turnover": _sf(fields[8]),
            "amplitude": _sf(fields[32]) if len(fields) > 32 else 0,
        }
    return result

def _fetch_fund_nav(codes: list[str]) -> dict[str, dict]:
    """通过天天基金API获取基金净值"""
    result = {}
    for code in codes:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time()*1000)}"
        raw = safe_request(url, timeout=8)
        if not raw:
            continue
        text = raw.decode("utf-8", errors="replace")
        m = re.search(r"\((.+)\)", text)
        if not m:
            continue
        try:
            d = json.loads(m.group(1))
            result[code] = {
                "name": d.get("name", ""),
                "nav": _sf(d.get("dwjz", 0)),
                "acc_nav": _sf(d.get("gsz", 0)),
                "change_pct": _sf(d.get("gszzl", 0)),
                "date": d.get("gztime", "")[:10] if d.get("gztime") else "",
            }
        except Exception:
            continue
    return result

# ─────────────────────────────────────────────────────────────
# 数据库 Schema
# ─────────────────────────────────────────────────────────────
DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS holdings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type       TEXT    NOT NULL CHECK(item_type IN ('stock','fund')),
    code            TEXT    NOT NULL,
    name            TEXT,
    cost            REAL    NOT NULL DEFAULT 0,
    shares          REAL    NOT NULL DEFAULT 0,
    target_return   REAL    DEFAULT 0,
    stop_loss       REAL    DEFAULT -10.0,
    stop_profit     REAL    DEFAULT 30.0,
    alert_threshold REAL    DEFAULT 0,
    alert_type      TEXT    DEFAULT 'both',
    hold_days       INTEGER DEFAULT 0,
    note            TEXT,
    added_at        TEXT    NOT NULL,
    UNIQUE(item_type, code)
);

CREATE TABLE IF NOT EXISTS price_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type  TEXT    NOT NULL,
    code       TEXT    NOT NULL,
    price      REAL    NOT NULL,
    change_pct REAL    DEFAULT 0,
    logged_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS adjustment_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type   TEXT    NOT NULL,
    code        TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    price       REAL,
    shares      REAL,
    reason      TEXT,
    advised_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pl_type_code ON price_log(item_type, code);
CREATE INDEX IF NOT EXISTS idx_pl_time     ON price_log(logged_at);
"""

class PortfolioTracker:
    def __init__(self, db_path: str | Path | None = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = SKILL_DIR / "data" / "portfolio.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(DB_SCHEMA)
            # Migrate existing holdings to add stop_loss/stop_profit columns
            try:
                conn.execute("ALTER TABLE holdings ADD COLUMN stop_loss REAL DEFAULT -10.0")
                conn.execute("ALTER TABLE holdings ADD COLUMN stop_profit REAL DEFAULT 30.0")
                conn.execute("ALTER TABLE holdings ADD COLUMN alert_threshold REAL DEFAULT 0")
                conn.execute("ALTER TABLE holdings ADD COLUMN alert_type TEXT DEFAULT 'both'")
                conn.commit()
            except Exception:
                pass  # columns already exist

    def update_settings(self, item_type: str, code: str,
                         stop_loss: float = None, stop_profit: float = None,
                         alert_threshold: float = None, alert_type: str = None,
                         target_return: float = None, note: str = None):
        code = str(code).zfill(6)
        updates = []
        params = []
        for k, v in [('stop_loss', stop_loss), ('stop_profit', stop_profit),
                     ('alert_threshold', alert_threshold), ('alert_type', alert_type),
                     ('target_return', target_return), ('note', note)]:
            if v is not None:
                updates.append(f"{k}=?")
                params.append(v)
        if not updates:
            return False
        params.extend([item_type, code])
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(f"UPDATE holdings SET {','.join(updates)} WHERE item_type=? AND code=?", params)
            conn.commit()
            return cur.rowcount > 0

    def get_tracked_items(self, item_type: str = None) -> list[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM holdings WHERE (? IS NULL OR item_type=?) ORDER BY item_type, code",
                (item_type, item_type))
            return [dict(row) for row in cur.fetchall()]

    def check_alerts(self, prices: dict = None) -> list[dict]:
        if prices is None:
            holdings = self.get_tracked_items()
            stock_codes = [h['code'] for h in holdings if h['item_type'] == 'stock']
            fund_codes = [h['code'] for h in holdings if h['item_type'] == 'fund']
            sp = _fetch_tx_price(stock_codes)
            fp = _fetch_fund_nav(fund_codes)
            sp.update(fp)
            prices = sp
        alerts = []
        holdings = self.get_tracked_items()
        for h in holdings:
            code = h['code']
            if code not in prices:
                continue
            p = prices[code]
            cost = h['cost']
            stop_loss = h['stop_loss']
            stop_profit = h['stop_profit']
            alert_th = h['alert_threshold']
            alert_type = h['alert_type']
            price = p.get('price', 0) or p.get('nav', 0)
            if not price or not cost:
                continue
            pct = (price / cost - 1) * 100
            if pct <= stop_loss:
                alerts.append({'type': 'STOP_LOSS', 'item_type': h['item_type'],
                    'code': code, 'name': h['name'], 'pct': round(pct,2),
                    'threshold': stop_loss, 'price': price,
                    'msg': f"触及止损线！浮亏{pct:+.1f}%，超过止损线{stop_loss}%"})
            elif pct >= stop_profit:
                alerts.append({'type': 'STOP_PROFIT', 'item_type': h['item_type'],
                    'code': code, 'name': h['name'], 'pct': round(pct,2),
                    'threshold': stop_profit, 'price': price,
                    'msg': f"触及止盈线！浮盈{pct:+.1f}%，达到止盈线{stop_profit}%"})
            if alert_th > 0:
                today_chg = p.get('change_pct', 0)
                if alert_type in ('down', 'both') and today_chg <= -alert_th:
                    alerts.append({'type': 'ALERT_DOWN', 'item_type': h['item_type'],
                        'code': code, 'name': h['name'], 'pct': round(pct,2),
                        'threshold': -alert_th, 'price': price, 'today_chg': today_chg,
                        'msg': f"价格警报！今日下跌{today_chg:+.1f}%，超过跌幅阈值{alert_th}%"})
                if alert_type in ('up', 'both') and today_chg >= alert_th:
                    alerts.append({'type': 'ALERT_UP', 'item_type': h['item_type'],
                        'code': code, 'name': h['name'], 'pct': round(pct,2),
                        'threshold': alert_th, 'price': price, 'today_chg': today_chg,
                        'msg': f"价格警报！今日上涨{today_chg:+.1f}%，超过涨幅阈值{alert_th}%"})
        return alerts

    def _row2dict(self, cur) -> list[dict]:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    # ── 持仓管理 ───────────────────────────────────────────────

    def add_holding(self, item_type: str, code: str, name: str = "",
                    cost: float = 0, shares: float = 0,
                    target_return: float = 0, note: str = ""):
        """添加或更新持仓"""
        code = str(code).zfill(6)
        name = name or code
        added_at = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO holdings (item_type,code,name,cost,shares,target_return,note,added_at)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(item_type,code) DO UPDATE SET
                    name=excluded.name, cost=excluded.cost, shares=excluded.shares,
                    target_return=excluded.target_return, note=excluded.note
            """, (item_type, code, name, cost, shares, target_return, note, added_at))
            conn.commit()

    def remove_holding(self, item_type: str, code: str):
        code = str(code).zfill(6)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM holdings WHERE item_type=? AND code=?", (item_type, code))
            conn.commit()

    def list_holdings(self, item_type: str = "") -> list[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            if item_type:
                rows = conn.execute(
                    "SELECT * FROM holdings WHERE item_type=? ORDER BY added_at DESC",
                    (item_type,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM holdings ORDER BY added_at DESC").fetchall()
            return self._row2dict(conn.execute(
                "SELECT * FROM holdings WHERE item_type=? ORDER BY added_at DESC" if item_type
                else "SELECT * FROM holdings ORDER BY added_at DESC",
                (item_type,) if item_type else ()
            ))

    def update_prices(self, item_type: str) -> dict[str, str]:
        """批量更新价格，返回 {code: status}"""
        holdings = self.list_holdings(item_type)
        if not holdings:
            return {}
        codes = [h["code"] for h in holdings]
        if item_type == "stock":
            prices = _fetch_tx_price(codes)
            status = {}
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(str(self.db_path)) as conn:
                for h in holdings:
                    p = prices.get(h["code"], {})
                    price = p.get("price", 0)
                    chg = p.get("change_pct", 0)
                    if price > 0:
                        conn.execute("""
                            INSERT INTO price_log (item_type,code,price,change_pct,logged_at)
                            VALUES (?,?,?,?,?)
                        """, (item_type, h["code"], price, chg, now_str))
                    status[h["code"]] = f"{price} ({chg:+.2f}%)" if price else "N/A"
                conn.commit()
            return status
        else:  # fund
            navs = _fetch_fund_nav(codes)
            status = {}
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(str(self.db_path)) as conn:
                for h in holdings:
                    d = navs.get(h["code"], {})
                    nav = d.get("nav", 0)
                    chg = d.get("change_pct", 0)
                    if nav > 0:
                        conn.execute("""
                            INSERT INTO price_log (item_type,code,price,change_pct,logged_at)
                            VALUES (?,?,?,?,?)
                        """, (item_type, h["code"], nav, chg, now_str))
                    status[h["code"]] = f"{nav} ({chg:+.2f}%)" if nav else "N/A"
                conn.commit()
            return status

    def get_holding_detail(self, item_type: str, code: str) -> dict:
        code = str(code).zfill(6)
        with sqlite3.connect(str(self.db_path)) as conn:
            h = conn.execute(
                "SELECT * FROM holdings WHERE item_type=? AND code=?", (item_type, code)
            ).fetchone()
            if not h:
                return {}
            cols = [d[0] for d in conn.execute(
                "SELECT * FROM holdings WHERE item_type=? AND code=?", (item_type, code)
            ).description]
            result = dict(zip(cols, h))
            # 查找最新价格
            latest = conn.execute("""
                SELECT price, change_pct, logged_at FROM price_log
                WHERE item_type=? AND code=? ORDER BY logged_at DESC LIMIT 1
            """, (item_type, code)).fetchone()
            if latest:
                result["current_price"] = latest[0]
                result["change_pct"] = latest[1]
                result["last_update"] = latest[2]
            # 价格历史
            history = conn.execute("""
                SELECT price, change_pct, logged_at FROM price_log
                WHERE item_type=? AND code=? ORDER BY logged_at DESC LIMIT 60
            """, (item_type, code)).fetchall()
            result["history"] = [
                {"price": r[0], "change_pct": r[1], "logged_at": r[2]}
                for r in history
            ]
            # 计算成本盈亏
            result = self._calc_pnl(result)
            return result

    def _calc_pnl(self, h: dict) -> dict:
        cost = _sf(h.get("cost"))
        shares = _sf(h.get("shares"))
        current = _sf(h.get("current_price"))
        if cost > 0 and shares > 0 and current > 0:
            total_cost = cost * shares
            total_market = current * shares
            pnl = total_market - total_cost
            pnl_pct = pnl / total_cost * 100
            h["total_cost"] = round(total_cost, 2)
            h["total_market"] = round(total_market, 2)
            h["pnl"] = round(pnl, 2)
            h["pnl_pct"] = round(pnl_pct, 2)
            # 持仓天数
            added = h.get("added_at", "")
            if added:
                try:
                    days = (datetime.now() - datetime.strptime(added, "%Y-%m-%d")).days
                    h["hold_days"] = days
                except Exception:
                    h["hold_days"] = 0
            # 距离目标收益率
            target = _sf(h.get("target_return"))
            h["distance_to_target"] = round(target - h.get("pnl_pct", 0), 2)
        return h

    def get_portfolio_summary(self, item_type: str = "") -> dict:
        holdings = self.list_holdings(item_type)
        total_cost = 0
        total_market = 0
        items = []
        for h in holdings:
            detail = self.get_holding_detail(h["item_type"], h["code"])
            items.append(detail)
            total_cost += _sf(detail.get("total_cost"))
            total_market += _sf(detail.get("total_market"))
        pnl = total_market - total_cost
        pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0
        return {
            "total_cost": round(total_cost, 2),
            "total_market": round(total_market, 2),
            "total_pnl": round(pnl, 2),
            "total_pnl_pct": round(pnl_pct, 2),
            "items": items,
        }

    def log_adjustment(self, item_type: str, code: str, action: str,
                       price: float = 0, shares: float = 0, reason: str = ""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO adjustment_log (item_type,code,action,price,shares,reason,advised_at)
                VALUES (?,?,?,?,?,?,?)
            """, (item_type, code, action, price, shares, reason, now))
            conn.commit()

    def get_adjustments(self, item_type: str = "", limit: int = 20) -> list[dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            q = "SELECT * FROM adjustment_log"
            params = []
            if item_type:
                q += " WHERE item_type=?"
                params = [item_type]
            q += " ORDER BY advised_at DESC LIMIT ?"
            params.append(limit)
            return self._row2dict(conn.execute(q, params))

    # ── 调仓建议引擎 ───────────────────────────────────────────

    def generate_advice(self, item_type: str = "") -> list[dict]:
        """生成调仓建议"""
        summary = self.get_portfolio_summary(item_type)
        advice_list = []
        for item in summary.get("items", []):
            if not item:
                continue
            pnl_pct = _sf(item.get("pnl_pct"))
            target = _sf(item.get("target_return"))
            hold_days = item.get("hold_days", 0)
            chg_pct = _sf(item.get("change_pct"))
            current = _sf(item.get("current_price"))
            cost = _sf(item.get("cost"))
            code = item.get("code", "")
            name = item.get("name", code)
            reasons = []

            # 逻辑1：达到目标收益率，止盈建议
            if target > 0 and pnl_pct >= target:
                advice_list.append({
                    "code": code, "name": name, "item_type": item_type,
                    "action": "SELL",
                    "priority": "🔴 高",
                    "reason": f"已达目标收益率 {target}%（当前 {pnl_pct:+.2f}%）",
                    "detail": f"持仓 {hold_days} 天，浮盈 {pnl_pct:+.2f}%，建议分批止盈",
                })
                reasons.append("止盈")

            # 逻辑2：亏损超过-15%，补仓建议（每跌8%补1倍）
            elif pnl_pct < -15 and current > 0 and cost > 0:
                drop_pct = (cost - current) / cost * 100
                if drop_pct >= 8:
                    advice_list.append({
                        "code": code, "name": name, "item_type": item_type,
                        "action": "BUY",
                        "priority": "🟡 中",
                        "reason": f"下跌 {drop_pct:.1f}%，浮亏 {pnl_pct:+.2f}%，建议补仓",
                        "detail": f"成本 {cost:.2f}，现价 {current:.2f}，建议加仓摊薄成本",
                    })
                    reasons.append("补仓")

            # 逻辑3：持续下跌超过5个交易日
            elif len(item.get("history", [])) >= 5:
                recent_5 = item["history"][:5]
                all_down = all(_sf(h.get("change_pct")) < 0 for h in recent_5)
                if all_down and chg_pct < -3:
                    advice_list.append({
                        "code": code, "name": name, "item_type": item_type,
                        "action": "WATCH",
                        "priority": "🟡 中",
                        "reason": f"连续下跌，当前跌幅 {chg_pct:+.2f}%",
                        "detail": "建议观察，不急于操作，等待趋势明朗",
                    })
                    reasons.append("观察")

            # 逻辑4：超过持有期限（默认365天），提醒检视
            elif hold_days > 365 and pnl_pct < 5:
                advice_list.append({
                    "code": code, "name": name, "item_type": item_type,
                    "action": "REVIEW",
                    "priority": "🟢 低",
                    "reason": f"持仓超 {hold_days} 天，收益率仅 {pnl_pct:+.2f}%，建议重新评估",
                    "detail": "长期持有但收益不佳，建议考虑换仓或止损",
                })
                reasons.append("检视")

            # 逻辑5：涨幅超过20%但未达目标
            elif pnl_pct > 20 and target > 0 and pnl_pct < target:
                advice_list.append({
                    "code": code, "name": name, "item_type": item_type,
                    "action": "HOLD",
                    "priority": "🟢 低",
                    "reason": f"浮盈 {pnl_pct:+.2f}%，距离目标 {target}% 还差 {target - pnl_pct:.1f}%",
                    "detail": "继续持有，耐心等待目标收益率",
                })
                reasons.append("持有")

            # 记录到调整日志（如果有建议）
            for a in advice_list[-len([r for r in reasons if r]) if advice_list else 0:]:
                self.log_adjustment(
                    item_type, code, a["action"],
                    current, _sf(item.get("shares")), a["reason"]
                )

        # 按优先级排序
        order = {"🔴 高": 0, "🟡 中": 1, "🟢 低": 2}
        advice_list.sort(key=lambda x: order.get(x["priority"], 3))
        return advice_list

    # ── 文字报告 ───────────────────────────────────────────────

    def print_summary(self, item_type: str = ""):
        summary = self.get_portfolio_summary(item_type)
        type_label = {"stock": "股票", "fund": "基金"}.get(item_type, "全部")
        print("\n" + "=" * 70)
        print(f"  {type_label}持仓汇总")
        print("=" * 70)
        print(f"  {'代码':<8} {'名称':<12} {'现价':>8} {'涨跌':>7} {'市值':>10} {'盈亏':>10} {'收益率':>8} {'建议'}")
        print("-" * 70)
        for item in summary.get("items", []):
            chg = _sf(item.get("change_pct"))
            chg_str = f"{chg:+.2f}%" if chg else "N/A"
            pnl = _sf(item.get("pnl"))
            pnl_pct = _sf(item.get("pnl_pct"))
            # 生成单项目建议标签
            label = ""
            if pnl_pct < -15:
                label = "补仓"
            elif pnl_pct > _sf(item.get("target_return", 0)) > 0:
                label = "止盈"
            name = (item.get("name") or item.get("code", ""))[:10]
            code = item.get("code", "")
            price = _sf(item.get("current_price"))
            market = _sf(item.get("total_market"))
            print(f"  {code:<8} {name:<12} {price:>8.2f} {chg_str:>7} {market:>10.2f} {pnl:>+10.2f} {pnl_pct:>+7.2f}%  {label}")
        print("-" * 70)
        total_pnl = _sf(summary.get("total_pnl"))
        total_pnl_pct = _sf(summary.get("total_pnl_pct"))
        print(f"  合计: 成本 {summary['total_cost']:.2f}  市值 {summary['total_market']:.2f}  盈亏 {total_pnl:+.2f} ({total_pnl_pct:+.2f}%)")
        print("=" * 70)
        return summary

    def print_advice(self, item_type: str = ""):
        advices = self.generate_advice(item_type)
        type_label = {"stock": "股票", "fund": "基金"}.get(item_type, "全部")
        print("\n" + "=" * 70)
        print(f"  {type_label}调仓建议")
        print("=" * 70)
        if not advices:
            print("  暂无调仓建议（所有持仓运行正常）")
        else:
            for a in advices:
                print(f"  [{a['priority']}] {a['code']} {a['name']}")
                print(f"       操作: {a['action']} | {a['reason']}")
                print(f"       {a['detail']}")
                print()
        print("=" * 70)
        return advices
