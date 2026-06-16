#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A股新闻情感分析器 v1.0 — 中文金融语境专用"""
from __future__ import annotations
import re, json, time
from pathlib import Path
from typing import Literal

SentimentScore = Literal[-2, -1, 0, 1, 2]
MarketImpact = Literal["利好", "利空", "中性", "不确定"]

# ── 情感词典（A股专用，10年经验总结）──────────────────
POSITIVE_PHRASES = [
    "涨停", "大涨", "暴涨", "飙升", "大幅上涨", "强势涨停", "集体涨停",
    "净流入", "主力净流入", "大单净流入", "北向资金净买入", "外资大幅买入",
    "业绩预增", "业绩超预期", "净利润增长", "营收增长", "利润增长",
    "订单超预期", "订单大增", "签约大单", "合同金额",
    "政策支持", "政策利好", "政策加码", "政策松绑", "政策红利",
    "获批", "上市获批", "注册获批", "通过审批", "批准上市",
    "回购", "增持", "大手笔回购", "股东增持",
    "分红", "高分红", "派息", "现金分红",
    "上调评级", "强烈推荐", "买入评级", "优于大市", "跑赢行业",
    "突破", "创新高", "历史新高", "创历史新高", "再创新高",
    "超跌反弹", "估值修复", "估值重构",
    "国产替代", "自主可控", "打破垄断", "技术突破",
    "产能扩张", "满产满销", "销量大增",
    "行业景气", "行业拐点", "景气度提升", "需求旺盛",
    "降本增效", "毛利率提升", "净利率提升", "盈利能力增强",
    "牵手", "合作", "战略合作", "联合中标",
    "新品发布", "新产品", "重磅新品", "新品上市",
    "ai赋能", "智能化", "数字化转型",
]

NEGATIVE_PHRASES = [
    "跌停", "大跌", "暴跌", "闪崩", "跌跌不休", "持续下跌",
    "净流出", "主力净流出", "大单净流出", "北向资金净卖出", "外资大幅卖出",
    "业绩下滑", "业绩不及预期", "净利润下降", "营收下降", "亏损",
    "被调查", "立案调查", "监管调查", "证监会调查",
    "被处罚", "顶格处罚", "行政处罚", "罚款", "警示函",
    "商誉爆雷", "资产减值", "大幅计提", "计提减值",
    "债务违约", "违约", "逾期", "资金紧张",
    "减持", "大幅减持", "清仓式减持", "股东减持",
    "下调评级", "降级", "卖出评级", "跑输行业",
    "产能过剩", "库存积压", "销量下滑", "订单减少",
    "行业景气下行", "行业衰退", "景气度下降", "需求萎缩",
    "政策收紧", "政策利空", "监管加强", "整顿",
    "竞争加剧", "价格战", "毛利率下降", "净利率下降",
    "技术替代", "被取代", "替代风险", "技术路线风险",
    "创始人出事", "高管出事", "实际控制人变更",
    "黑天鹅", "突发事件", "不可抗力",
    "破发", "破净", "跌破发行价",
    "终止", "终止上市", "退市", "暂停上市",
]

NEUTRAL_PHRASES = [
    "震荡", "横盘", "整理", "调整", "区间震荡",
    "观望", "等待", "谨慎", "审慎",
    "披露", "公告", "发布", "表示", "指出",
    "符合预期", "在预期内", "符合要求",
]

# ── 情感评分 ─────────────────────────────────────────
def score_sentiment(text: str) -> tuple[SentimentScore, float, list[str]]:
    """对新闻文本评分，返回 (score, confidence, matched_phrases)"""
    text_lower = text.lower()
    matched_pos = [p for p in POSITIVE_PHRASES if p in text]
    matched_neg = [p for p in NEGATIVE_PHRASES if p in text]
    matched_neu = [p for p in NEUTRAL_PHRASES if p in text]

    score = len(matched_pos) - len(matched_neg)

    # 极强信号词权重放大
    strong_signals = ["涨停", "跌停", "净流入", "净流出", "业绩预增", "业绩下滑",
                      "被调查", "被处罚", "回购", "减持", "政策利好", "政策利空",
                      "大幅上涨", "大跌", "突破", "创新高"]
    for sig in strong_signals:
        if sig in text:
            if sig in matched_pos:
                score += 1
            elif sig in matched_neg:
                score -= 1

    if score > 0:
        sentiment: SentimentScore = 1
    elif score < 0:
        sentiment = -1
    else:
        sentiment = 0

    confidence = min(1.0, (len(matched_pos) + len(matched_neg)) * 0.2)
    all_matched = matched_pos + matched_neg
    return sentiment, confidence, all_matched

# ── 市场影响评估 ─────────────────────────────────────
MARKET_IMPACT_KEYWORDS = {
    "利好": [
        "降准", "降息", "放水", "宽松", "qe", "量化宽松",
        "减税", "免税", "补贴", "扶持", "政策支持",
        "外资开放", "放开准入", "注册制", "科创板", "创业板",
        "并购重组", "资产重组", "混改",
    ],
    "利空": [
        "加息", "缩表", "收紧", "去杠杆", "严监管",
        "制裁", "出口管制", "实体清单", "断供",
        "发行上市", "扩容", "ipo加速", "再融资",
        "限售股解禁", "解禁",
    ],
}

def assess_market_impact(text: str, sentiment: SentimentScore) -> MarketImpact:
    """评估对大盘影响"""
    for m in re.finditer(r"[沪深]([涨跌])", text):
        direction = m.group(1)
        if direction == "涨":
            return "利好"
        elif direction == "跌":
            return "利空"

    for kw in MARKET_IMPACT_KEYWORDS["利好"]:
        if kw in text:
            return "利好"
    for kw in MARKET_IMPACT_KEYWORDS["利空"]:
        if kw in text:
            return "利空"

    if sentiment == 1:
        return "利好"
    elif sentiment == -1:
        return "利空"
    return "中性"

# ── 事件标签分类 ─────────────────────────────────────
EVENT_TAGS = {
    "宏观政策": ["降准", "降息", "加息", "缩表", "qe", "量化宽松", "减税", "补贴",
                "宽松", "收紧", "去杠杆", "严监管", "政策", "政治局", "国常会"],
    "公司经营": ["业绩", "订单", "签约", "合作", "新品", "技术突破", "产能",
                "营收", "利润", "增长", "下滑", "亏损"],
    "并购重组": ["并购", "重组", "收购", "混改", "资产注入", "定增"],
    "股东动向": ["增持", "减持", "回购", "分红", "大宗交易", "股权激励"],
    "监管动态": ["调查", "处罚", "警示函", "立案", "监管", "整改", "核查"],
    "行业景气": ["景气", "需求", "产能过剩", "供需", "行业", "赛道", "板块"],
    "资金动向": ["北向", "外资", "净流入", "净流出", "主力", "大单", "融资融券"],
    "海外市场": ["美联储", "美股", "港股", "纳斯达克", "标普", "道琼斯",
                "欧股", "日经", "原油", "黄金", "比特币"],
    "市场情绪": ["涨停", "跌停", "闪崩", "护盘", "抄底", "割肉", "恐慌"],
}

def tag_event(text: str) -> list[str]:
    """给新闻打事件标签（可多个）"""
    tags = []
    text_emoji_stripped = re.sub(r"\[.*?\]", "", text)
    for tag, keywords in EVENT_TAGS.items():
        if any(kw in text_emoji_stripped for kw in keywords):
            tags.append(tag)
    return tags if tags else ["其他"]

# ── 个股/行业关联 ────────────────────────────────────
def extract_mentioned_codes(text: str) -> list[str]:
    """从文本中提取股票代码（6位数字）"""
    codes = re.findall(r"\b(\d{6})\b", text)
    return list(dict.fromkeys(codes))  # 去重保持顺序

# ── 完整新闻分析 ─────────────────────────────────────
def analyze_news_item(item: dict) -> dict:
    """分析单条新闻，返回增强版"""
    text = item.get("title", "") + " " + item.get("content", "") + " " + item.get("summary", "")

    sentiment, confidence, phrases = score_sentiment(text)
    impact = assess_market_impact(text, sentiment)
    tags = tag_event(text)
    codes = extract_mentioned_codes(text)

    sentiment_map: dict = {-2: "极利空", -1: "利空", 0: "中性", 1: "利好", 2: "极利好"}
    sentiment_label = sentiment_map.get(sentiment, "中性")

    return {
        **item,
        "sentiment": sentiment,
        "sentiment_label": sentiment_label,
        "confidence": round(confidence, 2),
        "market_impact": impact,
        "tags": tags,
        "mentioned_codes": codes,
        "key_phrases": phrases[:5],
        "summary": item.get("summary", item.get("content", ""))[:200],
    }

def analyze_news_batch(news: list[dict]) -> dict:
    """批量分析新闻列表，返回汇总报告"""
    if not news:
        return {"total": 0, "sentiment_counts": {}, "tag_counts": {}, "impact_counts": {}}

    analyzed = [analyze_news_item(item) for item in news]

    sentiment_counts = {"极利好": 0, "利好": 0, "中性": 0, "利空": 0, "极利空": 0}
    impact_counts = {"利好": 0, "中性": 0, "利空": 0, "不确定": 0}
    tag_counts: dict = {}

    for item in analyzed:
        sentiment_counts[item["sentiment_label"]] = sentiment_counts.get(item["sentiment_label"], 0) + 1
        impact_counts[item["market_impact"]] = impact_counts.get(item["market_impact"], 0) + 1
        for tag in item["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # 综合情绪：加权平均
    weights = {"极利好": 2, "利好": 1, "中性": 0, "利空": -1, "极利空": -2}
    total_sentiment = sum(weights.get(item["sentiment_label"], 0) for item in analyzed)
    avg_sentiment = total_sentiment / len(analyzed) if analyzed else 0

    if avg_sentiment > 0.5:
        overall = "偏利好"
    elif avg_sentiment < -0.5:
        overall = "偏利空"
    else:
        overall = "中性"

    return {
        "total": len(analyzed),
        "overall_sentiment": overall,
        "sentiment_avg": round(avg_sentiment, 2),
        "sentiment_counts": sentiment_counts,
        "impact_counts": impact_counts,
        "tag_counts": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)),
        "top_positive": [i["title"] for i in analyzed if i["sentiment"] > 0][:3],
        "top_negative": [i["title"] for i in analyzed if i["sentiment"] < 0][:3],
        "items": analyzed,
    }

if __name__ == "__main__":
    # 快速测试
    test_news = [
        {"title": "贵州茅台业绩超预期！净利润大增20%，股价创历史新高", "content": ""},
        {"title": "某上市公司被证监会立案调查，涉嫌信披违规", "content": ""},
        {"title": "央行宣布降准0.5个百分点，释放长期资金约1万亿元", "content": ""},
    ]
    result = analyze_news_batch(test_news)
    print(f"总: {result['total']} | 综合: {result['overall_sentiment']} | "
          f"利好:{result['impact_counts'].get('利好',0)} "
          f"利空:{result['impact_counts'].get('利空',0)} "
          f"中性:{result['impact_counts'].get('中性',0)}")
    print(f"标签: {list(result['tag_counts'].items())[:5]}")
