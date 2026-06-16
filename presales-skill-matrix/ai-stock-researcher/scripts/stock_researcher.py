#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专业股票研究员 - CLI入口
Professional Stock Researcher CLI

功能：
- 股票研究分析（短/中/长期报告）
- 指数分析
- 板块分析
- 股票跟踪
- 全市场股票爬取
- 股吧/雪球情绪分析
- PPT/PDF报告导出
"""

import sys
sys.dont_write_bytecode = True
import time
from pathlib import Path

# 添加项目路径
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR))

from stock_researcher import StockResearcher
from stock_researcher.index_analysis.indices import IndexAnalyzer
from stock_researcher.sector_analysis.sectors import SectorAnalyzer
from stock_researcher.sector_analysis.rotation import SectorRotation
from stock_researcher.data.market_all_stocks_crawler import MarketAllStocksCrawler, StockScreener
from stock_researcher.data.sentiment_forum_crawler import SentimentForumCrawler, SentimentAlert
from stock_researcher.report.stock_report_generator import StockResearchReportGenerator
from stock_researcher.industry_chain import (
    IndustryChainAnalyzer, AShareChainAnalyzer,
    get_preset_chain, list_presets
)


def print_header():
    print(f"\n{'='*70}")
    print(f"  专业股票研究员  {time.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")


def analyze_stock_cli(codes, period, researcher):
    """股票分析"""
    for code in codes:
        code = str(code).zfill(6)
        print(f"\n分析股票: {code}")
        try:
            result = researcher.analyze_stock(code, period)

            # 打印结果
            print(f"  名称: {result.name}")
            print(f"  价格: {result.price:.2f} ({result.change_pct:+.2f}%)")

            if result.technical:
                print(f"  技术: MA({result.technical.ma_arrangement}) RSI({result.technical.rsi14:.0f}) MACD({'金叉' if result.technical.macd_hist > 0 else '死叉'})")

            if result.sentiment:
                print(f"  情绪: {result.sentiment.sentiment_label} (评分: {result.sentiment.sentiment_score:.0f})")

            if result.prediction:
                print(f"  预测:")
                print(f"    短期({result.prediction.short_term.period}): {result.prediction.short_term.signal} {result.prediction.short_term.predicted_return:+.2f}%")
                print(f"    中期({result.prediction.medium_term.period}): {result.prediction.medium_term.signal} {result.prediction.medium_term.predicted_return:+.2f}%")
                print(f"    长期({result.prediction.long_term.period}): {result.prediction.long_term.signal} {result.prediction.long_term.predicted_return:+.2f}%")

            # 生成报告
            pdf_path = researcher.generate_report(code, period)
            print(f"  报告: {pdf_path}")

        except Exception as e:
            print(f"  错误: {e}")


def index_cli(index_code, researcher):
    """指数分析"""
    analyzer = IndexAnalyzer()
    if index_code:
        result = analyzer.analyze_index(index_code)
        print(f"\n指数: {result.name}")
        print(f"  价格: {result.price:.2f} ({result.change_pct:+.2f}%)")
        print(f"  均线: MA5={result.ma5:.2f} MA10={result.ma10:.2f} MA20={result.ma20:.2f}")
        print(f"  状态: {result.ma_status} RSI={result.rsi:.0f}")
        print(f"  信号: {result.signal} 情绪: {result.market_sentiment}")
    else:
        analyzer.print_analysis()


def sector_cli(sector_name, researcher):
    """板块分析"""
    if sector_name:
        result = researcher.analyze_sector(sector_name)
        if result:
            print(f"\n板块: {result[0].name if result else sector_name}")
            print(f"  平均涨跌: {result[0].avg_change_pct:+.2f}%")
            print(f"  上涨家数: {result[0].up_count} 下跌家数: {result[0].down_count}")
            print(f"  主力净流入: {result[0].total_net_flow:+.0f}万")
            print(f"  信号: {result[0].signal} 轮动: {result[0].rotation_signal}")
    else:
        analyzer = SectorAnalyzer()
        results = analyzer.get_sector_ranking()
        analyzer.print_analysis(results)


def tracking_cli(code, action, researcher):
    """股票跟踪"""
    if action == "add":
        if code:
            researcher.track_stock(code, stop_loss=None, take_profit=None)
        else:
            print("请指定股票代码: --track 600519 --add")
    elif action == "check":
        result = researcher.check_tracking()
        print(f"\n检查时间: {result.get('date', '')}")
        print(f"检查股票数: {result.get('checked', 0)}")
        alerts = result.get("alerts", [])
        if alerts:
            print(f"\n触发警报: {len(alerts)}条")
            for a in alerts:
                print(f"  [{a.get('type')}] {a.get('message')}")
        else:
            print("无警报触发")
    elif action == "list":
        summary = researcher.get_tracked_summary()
        print(f"\n跟踪汇总:")
        print(f"  股票数: {summary.get('total', 0)}")
        stocks = summary.get("stocks", [])
        for s in stocks:
            print(f"  {s.get('code')} {s.get('name')}: 现价{s.get('price',0):.2f} 成本{s.get('cost',0):.2f}")


def market_cli(top_n):
    """全市场股票爬取"""
    crawler = MarketAllStocksCrawler()
    stocks = crawler.fetch_all_stocks()
    print(f"\n全市场股票数量: {len(stocks)}")

    # 市场摘要
    summary = crawler.get_market_summary()
    print(f"  上涨: {summary['rising_count']} ({summary['rising_ratio']})")
    print(f"  下跌: {summary['falling_count']}")
    print(f"  平盘: {summary['unchanged_count']}")
    print(f"  市场情绪: {summary['market_sentiment']}")

    # 涨幅榜
    print(f"\n涨幅榜 Top {top_n}:")
    top_rising = crawler.get_top_stocks(by="change_pct", limit=top_n)
    for i, s in enumerate(top_rising, 1):
        print(f"  {i}. {s['name']}({s['code']}): {s['change_pct']:+.2f}%")

    # 跌幅榜
    print(f"\n跌幅榜 Top {top_n}:")
    top_falling = crawler.get_top_stocks(by="change_pct", limit=top_n, ascending=True)
    for i, s in enumerate(top_falling, 1):
        print(f"  {i}. {s['name']}({s['code']}): {s['change_pct']:+.2f}%")


def screener_cli(top_n):
    """股票筛选"""
    crawler = MarketAllStocksCrawler()
    screener = StockScreener(crawler)

    print("\n筛选条件: PE<15, PB<2 (价值股)")
    value_stocks = screener.get_value_stocks(max_pe=15, max_pb=2)
    print(f"筛选结果: {len(value_stocks)}只")
    for s in value_stocks[:top_n]:
        print(f"  {s['name']}({s['code']}): PE={s.get('pe_ratio', 0):.1f}, PB={s.get('pb_ratio', 0):.2f}, 市值={s.get('market_cap', 0)/1e8:.1f}亿")


def sentiment_cli(code):
    """情绪分析"""
    crawler = SentimentForumCrawler()

    if code and code != "all":
        # 单只股票情绪
        result = crawler.analyze_stock_sentiment(code)
        print(f"\n{code} 情绪分析:")
        print(f"  东方财富股吧帖子: {result['guba']['post_count']}条")
        print(f"    多头比例: {result['guba']['sentiment']['bullish_ratio']:.1f}%")
        print(f"    情绪标签: {result['guba']['sentiment']['sentiment_label']}")
        print(f"  综合情绪: {result['combined']['sentiment_label']} ({result['combined']['bullish_ratio']:.1f}%)")
    else:
        print("\n请指定股票代码: --sentiment 600519")


def forum_crawl_cli():
    """股吧爬取"""
    print("\n股吧爬取功能需要指定股票代码")
    print("用法: python stock_researcher.py --sentiment 600519")


def report_cli(code, formats):
    """研究报告导出"""
    generator = StockResearchReportGenerator()

    if code and code != "all":
        print(f"\n生成 {code} 研究报告...")
        outputs = generator.export_report(code, period="medium", formats=formats)
        print("生成结果:")
        for fmt, path in outputs.items():
            print(f"  {fmt}: {path}")
    else:
        print("\n请指定股票代码: --report 600519")


def industry_chain_cli(industry, mode):
    """产业链分析"""
    preset = get_preset_chain(industry)
    if not preset:
        # 列出预设
        print(f"\n未找到「{industry}」的预设产业链。")
        print(f"可用预设: {', '.join(list_presets())}")
        print(f"或通过 API 手动构建产业链节点。")
        return

    print(f"\n{'='*60}")
    print(f"  {industry} — {'A股' if mode == 'ashare' else ''}产业链分析")
    print(f"{'='*60}")

    # 构建产业链地图骨架
    if mode == "ashare":
        analyzer = AShareChainAnalyzer()
        nodes = analyzer.build_chain_map(
            industry,
            [{"name": n, "participation": "🟡"} for n in preset["upstream"]],
            [{"name": n, "participation": "🟡"} for n in preset["midstream"]],
            [{"name": n, "participation": "🟡"} for n in preset["downstream"]]
        )
    else:
        analyzer = IndustryChainAnalyzer()
        nodes = analyzer.build_chain_map(
            industry, preset["upstream"], preset["midstream"], preset["downstream"]
        )

    # 打印骨架
    level_labels = {"upstream": "上游", "midstream": "中游", "downstream": "下游"}
    for node in nodes:
        label = level_labels.get(node.level, node.level)
        participation = f" (参与度:{node.ashare_participation})" if mode == "ashare" else ""
        print(f"  [{label}] {node.name}{participation}")

    print(f"\n  骨架已生成，共{len(nodes)}个节点。")
    print(f"  使用 API 补充各节点数据后可生成完整分析报告。")
    print(f"  API: analyzer.analyze('{industry}') → ChainAnalysisResult")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="专业股票研究员")

    # 股票分析
    parser.add_argument("--codes", nargs="*", help="股票代码列表")
    parser.add_argument("--period", choices=["short", "medium", "long"], default="short",
                       help="报告周期: short(1-5日)/medium(20-60日)/long(120+日)")

    # 指数分析
    parser.add_argument("--index", nargs="?", const="all", help="指数代码(如sh000001)，不指定则分析所有")

    # 板块分析
    parser.add_argument("--sector", nargs="?", const="all", help="板块名称(如银行)，不指定则分析所有")

    # 股票跟踪
    parser.add_argument("--track", nargs="?", help="股票代码")
    parser.add_argument("--add", action="store_true", help="添加跟踪")
    parser.add_argument("--check", action="store_true", help="检查跟踪")
    parser.add_argument("--list", action="store_true", help="列出跟踪")

    # 全市场股票爬取
    parser.add_argument("--market-all", action="store_true", help="获取全市场股票列表")
    parser.add_argument("--screener", action="store_true", help="筛选股票")
    parser.add_argument("--top", type=int, default=10, help="排行数量")

    # 情绪分析
    parser.add_argument("--sentiment", nargs="?", const="all", help="股票代码(不指定则全市场)")
    parser.add_argument("--forum-crawl", action="store_true", help="爬取股吧/雪球帖子")

    # 报告导出
    parser.add_argument("--report", nargs="?", const="all", help="股票代码(不指定则全市场)")
    parser.add_argument("--export-format", nargs="*", default=["ppt", "pdf"],
                       help="导出格式: ppt pdf txt")

    # 产业链分析
    parser.add_argument("--chain", nargs="?", const="list", help="产业链名称(如半导体/新能源汽车)，不指定则列出预设")
    parser.add_argument("--chain-mode", choices=["general", "ashare"], default="general",
                       help="分析模式: general(通用) / ashare(A股专版)")

    args = parser.parse_args()

    print_header()

    # 初始化研究员
    researcher = StockResearcher()

    if args.codes:
        analyze_stock_cli(args.codes, args.period, researcher)

    elif args.index is not None:
        idx = args.index if args.index != "all" else None
        index_cli(idx, researcher)

    elif args.sector is not None:
        sec = args.sector if args.sector != "all" else None
        sector_cli(sec, researcher)

    elif args.track:
        if args.add:
            tracking_cli(args.track, "add", researcher)
        elif args.check:
            tracking_cli(args.track, "check", researcher)
        else:
            tracking_cli(args.track, "list", researcher)

    elif args.list:
        tracking_cli(None, "list", researcher)

    elif args.market_all:
        market_cli(args.top)

    elif args.screener:
        screener_cli(args.top)

    elif args.sentiment is not None:
        sentiment_cli(args.sentiment)

    elif args.forum_crawl:
        forum_crawl_cli()

    elif args.report is not None:
        report_cli(args.report, args.export_format)

    elif args.chain is not None:
        if args.chain == "list":
            print(f"\n预设产业链: {', '.join(list_presets())}")
        else:
            industry_chain_cli(args.chain, args.chain_mode)

    else:
        # 默认：指数+板块分析
        print("\n【指数分析】")
        index_cli(None, researcher)

        print("\n【板块分析】")
        sector_cli(None, researcher)

    print()


if __name__ == "__main__":
    main()