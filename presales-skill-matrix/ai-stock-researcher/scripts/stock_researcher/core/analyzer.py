#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一分析调度器
Stock Researcher - Unified Analysis Engine
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass

from .technical import TechnicalAnalyzer, TechnicalIndicators
from .valuation import ValuationAnalyzer, ValuationMetrics
from .prediction_engine import ThreeDimensionPredictionEngine, ThreeDimensionPrediction

from ..agents.buffett import BuffettAnalyzer, BuffettAnalysis
from ..agents.graham import GrahamAnalyzer, GrahamAnalysis
from ..agents.lynch import LynchAnalyzer, LynchAnalysis
from ..agents.technical import TechnicalAgent, TechnicalAgentResult
from ..agents.sentiment import SentimentAnalyzer, SentimentResult

from ..data.market import MarketData
from ..data.fundamental import FundamentalData
from ..data.money_flow import MoneyFlowData
from ..data.news import NewsData
from ..data.macro import MacroData

from ..report.generator import ReportGenerator
from ..tracker.portfolio import PortfolioTracker
from ..tracker.alerts import AlertSystem
from ..tracker.monitor import StockMonitor

from ..index_analysis.indices import IndexAnalyzer, IndexResult
from ..sector_analysis.sectors import SectorAnalyzer, SectorResult
from ..industry_chain import IndustryChainAnalyzer, AShareChainAnalyzer, ChainAnalysisResult


@dataclass
class StockAnalysisResult:
    """股票分析完整结果"""
    code: str
    name: str
    date: str

    # 行情数据
    price: float = 0
    change_pct: float = 0

    # 技术分析
    technical: Optional[TechnicalIndicators] = None

    # 估值分析
    valuation: Optional[ValuationMetrics] = None

    # 基本面
    fundamentals: Dict = None

    # 资金流向
    money_flow: Dict = None

    # 新闻舆情
    sentiment: Optional[SentimentResult] = None

    # 投资大师分析
    buffett: Optional[BuffettAnalysis] = None
    graham: Optional[GrahamAnalysis] = None
    lynch: Optional[LynchAnalysis] = None

    # 三维预测
    prediction: Optional[ThreeDimensionPrediction] = None


class StockResearcher:
    """
    专业股票研究员

    功能：
    1. 完整股票分析（技术/估值/基本面/资金/情绪）
    2. 三维预测（情绪/估值/历史案例/技术）
    3. 投资大师分析（巴菲特/格雷厄姆/林奇）
    4. 短/中/长期报告生成
    5. 股票跟踪与提醒
    6. 指数分析
    7. 板块分析
    """

    def __init__(self, data_dir: str = None):
        # 数据层
        self.market = MarketData()
        self.fundamental = FundamentalData()
        self.money_flow_data = MoneyFlowData()
        self.news_data = NewsData()
        self.macro_data = MacroData()

        # 分析引擎
        self.tech_analyzer = TechnicalAnalyzer()
        self.val_analyzer = ValuationAnalyzer()
        self.prediction_engine = ThreeDimensionPredictionEngine()

        # 投资大师Agent
        self.buffett_analyzer = BuffettAnalyzer()
        self.graham_analyzer = GrahamAnalyzer()
        self.lynch_analyzer = LynchAnalyzer()
        self.technical_agent = TechnicalAgent()
        self.sentiment_analyzer = SentimentAnalyzer()

        # 报告生成器
        self.report_gen = ReportGenerator(data_dir)

        # 跟踪器
        self.tracker = PortfolioTracker(data_dir)
        self.alert_system = AlertSystem(data_dir)
        self.monitor = StockMonitor(data_dir)

        # 指数分析器
        self.index_analyzer = IndexAnalyzer()

        # 板块分析器
        self.sector_analyzer = SectorAnalyzer()

        # 产业链分析器
        self.chain_analyzer = IndustryChainAnalyzer()
        self.ashare_chain_analyzer = AShareChainAnalyzer()

    def analyze_stock(self, code: str, period: str = "short") -> StockAnalysisResult:
        """
        综合分析股票

        Args:
            code: 股票代码
            period: 报告周期 short/medium/long

        Returns:
            StockAnalysisResult
        """
        code = str(code).zfill(6)

        # 1. 获取行情数据
        rt_data = self.market.fetch_realtime([code])
        if code not in rt_data:
            raise ValueError(f"无法获取股票行情: {code}")

        stock_rt = rt_data[code]
        name = stock_rt.get("name", code)
        price = stock_rt.get("price", 0)
        change_pct = stock_rt.get("change_pct", 0)

        # 2. 获取历史数据用于技术分析
        kline = self.market.fetch_history(code, days=250)
        closes = kline.get("closes", []) if kline else []
        highs = kline.get("highs", []) if kline else []
        lows = kline.get("lows", []) if kline else []

        # 3. 技术分析
        tech = None
        if len(closes) >= 20:
            tech = self.tech_analyzer.analyze(code, closes, highs, lows)

        # 4. 资金流向
        money_flow = self.money_flow_data.get_money_flow([code]).get(code, {})

        # 5. 新闻舆情
        news_list = self.news_data.fetch_stock_news(code, limit=20)
        sentiment_data = self.news_data.analyze_news_sentiment(news_list)

        # 6. 估值数据（简化）
        val = ValuationMetrics(
            pe=20,  # 简化，实际应从API获取
            pb=2,
            pe_percentile=50,
            pb_percentile=50
        )

        # 7. 三维预测
        prediction = self.prediction_engine.predict_with_factors(
            news_sentiment=sentiment_data.get("score", 0) / 100,
            money_flow=money_flow.get("score", 0),
            change_pct=change_pct,
            pe_percentile=val.pe_percentile,
            pb_percentile=val.pb_percentile,
            similar_returns=closes[-60:] if len(closes) >= 60 else [],
            tech_score=tech.tech_score if tech else 0,
            ma_status=tech.ma_arrangement if tech else "混乱",
            rsi=tech.rsi14 if tech else 50,
            macd_hist=tech.macd_hist if tech else 0
        )

        return StockAnalysisResult(
            code=code,
            name=name,
            date=time.strftime("%Y-%m-%d"),
            price=price,
            change_pct=change_pct,
            technical=tech,
            valuation=val,
            fundamentals={},
            money_flow=money_flow,
            sentiment=SentimentResult(
                news_score=sentiment_data.get("score", 0),
                news_positive=sentiment_data.get("positive", 0),
                news_negative=sentiment_data.get("negative", 0),
                news_neutral=sentiment_data.get("neutral", 0),
                sentiment_score=sentiment_data.get("score", 0),
                sentiment_label=sentiment_data.get("overall", "中性")
            ),
            prediction=prediction
        )

    def generate_report(self, code: str, period: str = "short") -> str:
        """
        生成研究报告

        Args:
            code: 股票代码
            period: short/medium/long

        Returns:
            str: 报告文件路径
        """
        result = self.analyze_stock(code, period)

        stock_data = {
            "code": result.code,
            "name": result.name,
            "price": result.price,
            "change_pct": result.change_pct
        }

        tech_data = {}
        if result.technical:
            tech_data = {
                "ma5": result.technical.ma5,
                "ma10": result.technical.ma10,
                "ma20": result.technical.ma20,
                "ma60": result.technical.ma60,
                "rsi14": result.technical.rsi14,
                "macd_hist": result.technical.macd_hist,
                "ma_arrangement": result.technical.ma_arrangement,
                "tech_score": result.technical.tech_score,
                "tech_signal": result.technical.tech_signal
            }

        if period == "short":
            return self.report_gen.generate_short_report(
                stock_data=stock_data,
                tech_data=tech_data,
                money_data=result.money_flow or {},
                sentiment_data={
                    "sentiment_label": result.sentiment.sentiment_label if result.sentiment else "中性",
                    "sentiment_score": result.sentiment.sentiment_score if result.sentiment else 0,
                    "news_positive": result.sentiment.news_positive if result.sentiment else 0,
                    "news_negative": result.sentiment.news_negative if result.sentiment else 0,
                },
                prediction={
                    "short_term": result.prediction.short_term if result.prediction else None,
                    "medium_term": result.prediction.medium_term if result.prediction else None,
                    "long_term": result.prediction.long_term if result.prediction else None,
                }
            )
        elif period == "medium":
            val_data = {}
            if result.valuation:
                val_data = {
                    "pe": result.valuation.pe,
                    "pb": result.valuation.pb,
                    "pe_percentile": result.valuation.pe_percentile,
                    "pb_percentile": result.valuation.pb_percentile,
                    "val_signal": result.valuation.val_signal,
                    "valuation_state": result.valuation.valuation_state,
                    "graham_number": result.valuation.graham_number
                }

            return self.report_gen.generate_medium_report(
                stock_data=stock_data,
                tech_data=tech_data,
                val_data=val_data,
                fundamental_data=result.fundamentals or {},
                prediction={
                    "short_term": result.prediction.short_term if result.prediction else None,
                    "medium_term": result.prediction.medium_term if result.prediction else None,
                    "long_term": result.prediction.long_term if result.prediction else None,
                }
            )
        else:  # long
            return self.report_gen.generate_long_report(
                stock_data=stock_data,
                fundamental_data=result.fundamentals or {},
                buffett_analysis={
                    "roe": 15,
                    "operating_margin": 20,
                    "moat_score": 60,
                    "intrinsic_value": 0,
                    "margin_of_safety": 0,
                    "buffett_score": 0,
                    "signal": "中性"
                },
                graham_analysis={
                    "graham_number": 0,
                    "ncav": 0,
                    "current_ratio": 2,
                    "debt_ratio": 50,
                    "margin_of_safety": 0,
                    "graham_score": 0
                },
                lynch_analysis={
                    "revenue_growth": 10,
                    "eps_growth": 10,
                    "cagr": 10,
                    "peg": 1.5,
                    "debt_ratio": 50,
                    "lynch_score": 0
                },
                prediction={
                    "short_term": result.prediction.short_term if result.prediction else None,
                    "medium_term": result.prediction.medium_term if result.prediction else None,
                    "long_term": result.prediction.long_term if result.prediction else None,
                }
            )

    def analyze_index(self, index_code: str = None) -> List[IndexResult]:
        """
        分析指数

        Args:
            index_code: 指数代码，如不指定则分析所有

        Returns:
            List[IndexResult]
        """
        if index_code:
            return [self.index_analyzer.analyze_index(index_code)]
        return self.index_analyzer.analyze_all()

    def analyze_sector(self, sector_name: str = None) -> List[SectorResult]:
        """
        分析板块

        Args:
            sector_name: 板块名称，如不指定则分析所有

        Returns:
            List[SectorResult]
        """
        if sector_name:
            return [self.sector_analyzer.analyze_sector(sector_name)]
        return self.sector_analyzer.get_sector_ranking()

    def track_stock(self, code: str, name: str = None, cost: float = None,
                    shares: float = None, stop_loss: float = None,
                    take_profit: float = None) -> bool:
        """
        添加跟踪股票

        Args:
            code: 股票代码
            name: 股票名称
            cost: 持仓成本
            shares: 持仓数量
            stop_loss: 止损价
            take_profit: 止盈价

        Returns:
            bool
        """
        return self.tracker.add_stock(code, name, cost, shares, stop_loss, take_profit)

    def check_tracking(self) -> Dict:
        """
        检查跟踪股票

        Returns:
            Dict: 检查结果
        """
        return self.monitor.run_and_report()

    def get_tracked_summary(self) -> Dict:
        """获取跟踪汇总"""
        return self.tracker.get_tracking_summary()

    def analyze_industry_chain(self, industry: str, mode: str = "general") -> ChainAnalysisResult:
        """
        产业链分析

        Args:
            industry: 产业链名称
            mode: general(通用) / ashare(A股专版)

        Returns:
            ChainAnalysisResult
        """
        from ..industry_chain import get_preset_chain

        preset = get_preset_chain(industry)
        if not preset:
            raise ValueError(f"未找到预设产业链: {industry}")

        if mode == "ashare":
            nodes = self.ashare_chain_analyzer.build_chain_map(
                industry,
                [{"name": n, "participation": "🟡"} for n in preset["upstream"]],
                [{"name": n, "participation": "🟡"} for n in preset["midstream"]],
                [{"name": n, "participation": "🟡"} for n in preset["downstream"]]
            )
            return self.ashare_chain_analyzer.analyze(industry, nodes)
        else:
            nodes = self.chain_analyzer.build_chain_map(
                industry, preset["upstream"], preset["midstream"], preset["downstream"]
            )
            return self.chain_analyzer.analyze(industry, nodes)