#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多股/多基追踪器 v2.0 - SQLite持久化+成本盈亏+追踪记录"""
import json, sqlite3, time, urllib.request, re
from pathlib import Path
from datetime import datetime

def _safe_float(v, default=0.0):
    try:
        return float(v) if v not in ("", "-", None, "N/A") else default
    except:
        return default

class BaseTracker:
    DB_SCHEMA = ""

    def __init__(self, db_path=None, data_dir=None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self.data_dir / self.DB_NAME
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(self.DB_SCHEMA)
            conn.commit()

    def _dict_row(self, conn, query, params=()):
        cur = conn.execute(query, params)
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            yield dict(zip(cols, row))

    def add(self, code, name=None, cost=None, shares=None, note=""):
        """添加追踪项"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # 检查是否已存在
            existing = conn.execute(
                "SELECT id FROM tracked_items WHERE code=?", (str(code).zfill(6),)
            ).fetchone()
            if existing:
                return existing[0], False  # 已存在
            conn.execute(
                "INSERT INTO tracked_items (code,name,cost,shares,note,added_date) VALUES (?,?,?,?,?,?)",
                (str(code).zfill(6), name, cost, shares, note, datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            return rowid, True

    def remove(self, code):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM tracked_items WHERE code=?", (str(code).zfill(6),))
            conn.commit()
            return conn.total_changes > 0

    def list_items(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            return list(self._dict_row(conn, "SELECT * FROM tracked_items ORDER BY added_date DESC"))

    def update_price(self, code, current_price, change_pct=0):
        with sqlite3.connect(str(self.db_path)) as conn:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT INTO price_history (code, price, change_pct, update_time)
                VALUES (?, ?, ?, ?)
            """, (str(code).zfill(6), current_price, change_pct, now))
            conn.execute("""
                UPDATE tracked_items SET current_price=?, change_pct=?, last_update=? WHERE code=?
            """, (current_price, change_pct, now, str(code).zfill(6)))
            conn.commit()

    def get_history(self, code, days=30):
        code_str = str(code).zfill(6)
        with sqlite3.connect(str(self.db_path)) as conn:
            rows = list(self._dict_row(conn, """
                SELECT * FROM price_history WHERE code=? AND update_time > datetime('now', '-{} days')
                ORDER BY update_time ASC
            """.format(days), (code_str,)))
            return rows

    def get_performance(self, code):
        code_str = str(code).zfill(6)
        with sqlite3.connect(str(self.db_path)) as conn:
            item = conn.execute("SELECT * FROM tracked_items WHERE code=?", (code_str,)).fetchone()
            if not item:
                return None
            cols = [d[0] for d in conn.execute("SELECT * FROM tracked_items WHERE code=?", (code_str,)).description]
            item_dict = dict(zip(cols, item))
            history = list(self._dict_row(conn, """
                SELECT price, update_time FROM price_history WHERE code=? ORDER BY update_time ASC
            """, (code_str,)))
            if not history:
                return item_dict
            first_price = _safe_float(history[0]["price"])
            last_price = _safe_float(history[-1]["price"])
            if first_price > 0:
                item_dict["total_return"] = round((last_price - first_price) / first_price * 100, 2)
            else:
                item_dict["total_return"] = 0
            item_dict["price_history"] = history
            return item_dict


class StockTracker(BaseTracker):
    DB_NAME = "tracked_stocks_v2.db"
    DB_SCHEMA = """
    CREATE TABLE IF NOT EXISTS tracked_items (
        id INTEGER PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        name TEXT,
        cost REAL,
        shares INTEGER,
        current_price REAL,
        change_pct REAL,
        note TEXT,
        added_date TEXT,
        last_update TEXT
    );
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        price REAL NOT NULL,
        change_pct REAL,
        update_time TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_code ON price_history(code);
    CREATE INDEX IF NOT EXISTS idx_time ON price_history(update_time);
    """

    def get_portfolio_summary(self):
        """计算组合汇总"""
        items = self.list_items()
        total_cost = 0
        total_market = 0
        holdings = []
        for item in items:
            cost = _safe_float(item.get("cost")) * _safe_float(item.get("shares", 0))
            price = _safe_float(item.get("current_price"))
            shares = _safe_float(item.get("shares", 0))
            market = price * shares
            pnl = market - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0
            total_cost += cost
            total_market += market
            holdings.append({
                "code": item["code"],
                "name": item.get("name", ""),
                "shares": shares,
                "cost": cost,
                "market": market,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "current_price": price,
                "change_pct": _safe_float(item.get("change_pct")),
            })
        total_pnl = total_market - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        return {
            "total_cost": round(total_cost, 2),
            "total_market": round(total_market, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "holdings": holdings,
        }

    def print_portfolio(self):
        summary = self.get_portfolio_summary()
        print("\n" + "=" * 70)
        print("  股票持仓追踪汇总")
        print("=" * 70)
        print(f"  {'代码':<8} {'名称':<12} {'持仓':>6} {'成本':>10} {'现价':>8} {'市值':>10} {'盈亏':>10} {'收益率':>8}")
        print("-" * 70)
        for h in summary["holdings"]:
            print(f"  {h['code']:<8} {h['name']:<12} {h['shares']:>6.0f} {h['cost']:>10.2f} {h['current_price']:>8.2f} {h['market']:>10.2f} {h['pnl']:>+10.2f} {h['pnl_pct']:>+7.2f}%")
        print("-" * 70)
        print(f"  合计: 成本 {summary['total_cost']:.2f}  市值 {summary['total_market']:.2f}  盈亏 {summary['total_pnl']:+.2f} ({summary['total_pnl_pct']:+.2f}%)")
        print("=" * 70)
        return summary


class FundTracker(BaseTracker):
    DB_NAME = "tracked_funds_v2.db"
    DB_SCHEMA = """
    CREATE TABLE IF NOT EXISTS tracked_items (
        id INTEGER PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        name TEXT,
        cost REAL,
        shares REAL,
        current_nav REAL,
        change_pct REAL,
        note TEXT,
        added_date TEXT,
        last_update TEXT
    );
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        nav REAL NOT NULL,
        change_pct REAL,
        update_time TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_code ON price_history(code);
    CREATE INDEX IF NOT EXISTS idx_time ON price_history(update_time);
    """

    def get_portfolio_summary(self):
        items = self.list_items()
        total_cost = 0
        total_market = 0
        holdings = []
        for item in items:
            cost = _safe_float(item.get("cost")) * _safe_float(item.get("shares", 0))
            nav = _safe_float(item.get("current_nav"))
            shares = _safe_float(item.get("shares", 0))
            market = nav * shares
            pnl = market - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0
            total_cost += cost
            total_market += market
            holdings.append({
                "code": item["code"],
                "name": item.get("name", ""),
                "shares": shares,
                "cost": cost,
                "current_nav": nav,
                "market": market,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "change_pct": _safe_float(item.get("change_pct")),
            })
        total_pnl = total_market - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        return {
            "total_cost": round(total_cost, 2),
            "total_market": round(total_market, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "holdings": holdings,
        }

    def print_portfolio(self):
        summary = self.get_portfolio_summary()
        print("\n" + "=" * 70)
        print("  基金持仓追踪汇总")
        print("=" * 70)
        print(f"  {'代码':<8} {'名称':<16} {'持有份额':>8} {'成本':>10} {'净值':>8} {'市值':>10} {'盈亏':>10} {'收益率':>8}")
        print("-" * 70)
        for h in summary["holdings"]:
            print(f"  {h['code']:<8} {h['name']:<16} {h['shares']:>8.2f} {h['cost']:>10.2f} {h['current_nav']:>8.4f} {h['market']:>10.2f} {h['pnl']:>+10.2f} {h['pnl_pct']:>+7.2f}%")
        print("-" * 70)
        print(f"  合计: 成本 {summary['total_cost']:.2f}  市值 {summary['total_market']:.2f}  盈亏 {summary['total_pnl']:+.2f} ({summary['total_pnl_pct']:+.2f}%)")
        print("=" * 70)
        return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: tracker.py stock|fund add <code> [name] [cost] [shares]")
        print("      tracker.py stock|fund list")
        print("      tracker.py stock|fund remove <code>")
        sys.exit(1)

    kind = sys.argv[1]
    cmd = sys.argv[2] if len(sys.argv) > 2 else "list"
    tracker = StockTracker() if kind == "stock" else FundTracker()

    if cmd == "add":
        code = sys.argv[3] if len(sys.argv) > 3 else ""
        name = sys.argv[4] if len(sys.argv) > 4 else ""
        cost = float(sys.argv[5]) if len(sys.argv) > 5 else None
        shares = float(sys.argv[6]) if len(sys.argv) > 6 else None
        rid, added = tracker.add(code, name, cost, shares)
        print(f"  {'添加成功' if added else '已存在'}: {code} {name}")
    elif cmd == "list":
        if kind == "stock":
            tracker.print_portfolio()
        else:
            tracker.print_portfolio()
    elif cmd == "remove":
        code = sys.argv[3] if len(sys.argv) > 3 else ""
        ok = tracker.remove(code)
        print(f"  {'删除成功' if ok else '未找到'}: {code}")
