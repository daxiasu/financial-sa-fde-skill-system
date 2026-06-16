#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""政策分析模块 v3.0（自包含，零第三方依赖）"""
from __future__ import annotations
import sys, re, time, json, html
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from crawl_utils import safe_request

# ===== 关键词库 =====
MACRO_KWS = [
    "央行", "降准", "加息", "货币政策", "财政", "经济", "CPI", "PPI", "GDP", "M2",
    "美联储", "国务院", "发改委", "财政部", "商务部", "银保监", "统计局"
]
INDUSTRY_KWS = {
    "新能源": ["新能源", "光伏", "风电", "储能", "电动车", "锂电", "电池", "新能源汽车"],
    "医药": ["医药", "中药", "医疗器械", "创新药", "疫苗", "医保"],
    "科技": ["半导体", "芯片", "AI", "人工智能", "软件", "5G", "华为"],
    "消费": ["白酒", "食品", "饮料", "家电", "汽车", "零售"],
    "金融": ["银行", "保险", "券商", "基金", "信托", "降息"],
    "地产": ["房地产", "楼市", "房贷", "万科", "保利"],
}
MARKET_KWS = [
    "证监会", "IPO", "注册制", "退市", "量化", "做空", "涨停", "北向", "外资",
    "公募", "私募", "ETF", "融资", "融券"
]
POSITIVE = ["利好", "上涨", "创新高", "突破", "增长", "积极", "支持", "促进", "扩大", "开放", "宽松", "超预期", "首推", "增持", "买入"]
NEGATIVE = ["利空", "下跌", "风险", "加强监管", "严格", "收紧", "控制", "抑制", "整顿", "违规", "减持", "警告", "调查", "暴跌", "亏损"]

def _sentiment(text):
    pos = sum(1 for w in POSITIVE if w in text)
    neg = sum(1 for w in NEGATIVE if w in text)
    t = pos + neg
    return int((pos - neg) / max(t, 1) * 100)

def _classify(text):
    cats = []
    if any(k in text for k in MACRO_KWS):
        cats.append("宏观")
    for cat, kws in INDUSTRY_KWS.items():
        if any(k in text for k in kws):
            cats.append(cat)
    if any(k in text for k in MARKET_KWS):
        cats.append("股市")
    return cats if cats else ["其他"]

def _filter_policy(title):
    all_kws = MACRO_KWS + sum(INDUSTRY_KWS.values(), []) + MARKET_KWS
    return any(k in title for k in all_kws)

def _extract_links(data, domain, source, min_len=6, max_count=20):
    """从HTML中提取链接标题（字符串查找方式）"""
    if not data:
        return []
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")
    news = []
    seen = set()
    data_lower = data.lower()
    pos = 0
    chinese_re = re.compile(r"[\u4e00-\u9fff]")
    while len(news) < max_count * 3 and pos < len(data) - 50:
        idx_a = data_lower.find("<a href=", pos)
        if idx_a < 0:
            break
        q1 = data[idx_a + 9]
        end_q = data.find(q1, idx_a + 10)
        if end_q < 0:
            pos = idx_a + 1
            continue
        url = data[idx_a + 10:end_q]
        if not url or url.startswith(("javascript:", "#", "/")):
            pos = idx_a + 1
            continue
        if url.startswith("ttps://"):
            url = "h" + url
        elif url.startswith("tps://"):
            url = "ht" + url
        if domain not in url.lower():
            pos = idx_a + 1
            continue
        end_a = data.find("</a>", end_q)
        if end_a < 0:
            pos = idx_a + 1
            continue
        inner_start = data.find(">", end_q)
        if inner_start < 0 or inner_start >= end_a:
            pos = idx_a + 1
            continue
        raw = data[inner_start + 1:end_a]
        title = re.sub(r"<[^>]*>", "", raw)
        title = re.sub(r"[\s\n\r\t]+", " ", title).strip()
        title = html.unescape(title)
        pos = end_a + 4
        if len(title) < min_len or not chinese_re.search(title):
            continue
        if any(b in title for b in ["登录", "注册", "客户端", "下载", "app", "广告", "javascript"]):
            pos = idx_a + 1
            continue
        if title in seen:
            continue
        if _filter_policy(title):
            seen.add(title)
            cats = _classify(title)
            score = _sentiment(title)
            news.append({
                "title": title,
                "url": url,
                "source": source,
                "category": cats,
                "sentiment": score,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
    return news[:max_count]

class PolicyAnalyzer:
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True, parents=True)

    def fetch_sina_policy(self):
        data = safe_request("https://finance.sina.com.cn/", timeout=8)
        if not data:
            return []
        return _extract_links(data, "finance.sina.com.cn", "新浪财经")

    def fetch_phoenix_policy(self):
        data = safe_request("https://finance.ifeng.com/", timeout=8)
        if not data:
            return []
        return _extract_links(data, "finance.ifeng.com", "凤凰财经")

    def fetch_eastmoney_policy(self):
        news = []
        for url in ["https://money.eastmoney.com/", "https://www.eastmoney.com/"]:
            data = safe_request(url, timeout=6)
            if not data:
                continue
            items = _extract_links(data, "eastmoney.com", "东方财富")
            news.extend(items)
            if news:
                break
        return news[:15]

    def fetch_policy_news(self, days=3):
        all_news = []
        all_news.extend(self.fetch_sina_policy())
        time.sleep(0.2)
        all_news.extend(self.fetch_phoenix_policy())
        time.sleep(0.2)
        all_news.extend(self.fetch_eastmoney_policy())
        seen, unique = set(), []
        for n in all_news:
            if n["title"] not in seen:
                seen.add(n["title"])
                unique.append(n)
        return unique

    def analyze_policy_impact(self, news_list, stock_codes=None, fund_codes=None):
        industry_map = {
            "新能源": ["宁德时代", "比亚迪", "隆基绿能"],
            "医药": ["恒瑞医药", "药明康德", "迈瑞医疗"],
            "科技": ["中芯国际", "华为", "韦尔股份"],
            "消费": ["贵州茅台", "五粮液", "美的集团"],
            "金融": ["中国平安", "招商银行", "东方财富"],
            "地产": ["万科A", "保利发展"],
        }
        stock_impact = {code: {"score": 0, "news": []} for code in (stock_codes or [])}
        for n in news_list:
            title = n["title"]
            score = n["sentiment"]
            for cat in n.get("category", []):
                if cat in industry_map:
                    for kw in industry_map[cat]:
                        if kw in title and stock_codes:
                            for code in stock_codes:
                                if code in stock_impact:
                                    stock_impact[code]["score"] += score * 0.3
                                    if len(stock_impact[code]["news"]) < 3:
                                        stock_impact[code]["news"].append(title[:40])
        return {"stocks": stock_impact, "funds": {}}

    def generate_policy_report(self, stock_codes=None, fund_codes=None, days=3):
        news = self.fetch_policy_news(days)
        cat_count, cat_sent = {}, {}
        for n in news:
            for cat in n.get("category", []):
                cat_count[cat] = cat_count.get(cat, 0) + 1
                cat_sent[cat] = cat_sent.get(cat, 0) + n["sentiment"]
        for cat in cat_sent:
            if cat_count[cat] > 0:
                cat_sent[cat] = int(cat_sent[cat] / cat_count[cat])
        scores = [n["sentiment"] for n in news]
        avg = int(sum(scores) / max(len(scores), 1))
        tone = "偏多" if avg > 10 else "偏空" if avg < -10 else "中性"
        impact = self.analyze_policy_impact(news, stock_codes, fund_codes)
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_news": len(news),
            "category_counts": cat_count,
            "category_sentiment": cat_sent,
            "avg_sentiment": avg,
            "market_tone": tone,
            "news": news[:30],
            "impact": impact,
        }

if __name__ == "__main__":
    print("政策分析测试...")
    analyzer = PolicyAnalyzer()
    report = analyzer.generate_policy_report()
    print(f"获取 {report['total_news']} 条政策新闻 | 市场: {report['market_tone']}({report['avg_sentiment']:+.0f})")
    print(f"分类: {report['category_counts']}")
    for n in report["news"][:5]:
        print(f"  [{'/'.join(n['category'])}][{n['sentiment']:+.0f}] {n['title'][:45]}")
