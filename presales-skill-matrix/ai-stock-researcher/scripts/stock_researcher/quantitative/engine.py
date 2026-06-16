# -*- coding: utf-8 -*-
"""
量化引擎
Quantitative Engine

整合 Alpha模型 + Risk模型 + Portfolio模型
提供完整的量化交易信号生成和风险管理

使用示例：
```python
from quantitative.engine import QuantitativeEngine

# 初始化引擎
engine = QuantitativeEngine()

# 添加Alpha模型
engine.add_alpha_model('dual_thrust', period=20)

# 添加风控模型
engine.add_risk_model('stop_loss', stop_loss_pct=0.05)

# 设置组合模型
engine.set_portfolio_model('equal_weight', max_positions=10)

# 生成信号
signals = engine.generate_signals(stock_data)

# 获取风控报告
risk_reports = engine.assess_risks(positions, market_data)
```
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .alpha_models import (
    AlphaModel, Insight, InsightDirection,
    DualThrustAlpha, RateOfChangeAlpha, MeanReversionAlpha,
    MomentumAlpha, ValueInvestingAlpha, create_alpha_model
)
from .risk_models import (
    RiskModel, RiskReport, RiskDecision,
    MaximumDrawdownRiskModel, StopLossRiskModel, TargetProfitRiskModel,
    CompositeRiskModel, create_risk_model
)
from .portfolio_models import (
    PortfolioConstructionModel, PortfolioTarget, PortfolioResult,
    EqualWeightPortfolio, RiskParityPortfolio, ValueWeightedPortfolio,
    MomentumPortfolio, create_portfolio_model
)
from .indicators import QuantIndicators


@dataclass
class QuantSignal:
    """量化信号"""
    symbol: str
    direction: InsightDirection
    confidence: float
    magnitude: float
    period: int
    model_name: str
    indicators: Dict = field(default_factory=dict)
    risk_report: RiskReport = None
    target_weight: float = 0


@dataclass
class QuantResult:
    """量化分析结果"""
    signals: List[QuantSignal]
    portfolio: PortfolioResult
    risk_reports: List[RiskReport]
    summary: Dict


class QuantitativeEngine:
    """
    量化引擎

    整合信号生成、风险评估、组合构建
    """

    def __init__(self, name: str = ""):
        self.name = name or "QuantitativeEngine"
        self._alpha_models: Dict[str, AlphaModel] = {}
        self._risk_models: Dict[str, RiskModel] = {}
        self._portfolio_model: PortfolioConstructionModel = None
        self._indicators: Dict[str, QuantIndicators] = {}
        self._price_history: Dict[str, List[Dict]] = {}

    def add_alpha_model(self, model_type: str, name: str = "", **kwargs) -> str:
        """
        添加Alpha模型

        Args:
            model_type: 模型类型
            name: 自定义名称
            **kwargs: 模型参数

        Returns:
            str: 模型标识
        """
        model = create_alpha_model(model_type, **kwargs)
        model.name = name or f"{model_type}_{len(self._alpha_models)}"
        self._alpha_models[model.name] = model
        return model.name

    def add_risk_model(self, model_type: str, name: str = "", **kwargs) -> str:
        """
        添加风控模型

        Args:
            model_type: 模型类型
            name: 自定义名称
            **kwargs: 模型参数

        Returns:
            str: 模型标识
        """
        model = create_risk_model(model_type, **kwargs)
        model.name = name or f"{model_type}_{len(self._risk_models)}"
        self._risk_models[model.name] = model
        return model.name

    def set_portfolio_model(self, model_type: str, **kwargs) -> None:
        """
        设置组合模型

        Args:
            model_type: 模型类型
            **kwargs: 模型参数
        """
        self._portfolio_model = create_portfolio_model(model_type, **kwargs)

    def add_price_data(self, symbol: str, ohlcv: Dict) -> None:
        """
        添加价格数据

        Args:
            symbol: 股票代码
            ohlcv: 包含 open, high, low, close, volume 的字典
        """
        if symbol not in self._price_history:
            self._price_history[symbol] = []
        self._price_history[symbol].append(ohlcv)

        # 保持最近500条数据
        if len(self._price_history[symbol]) > 500:
            self._price_history[symbol] = self._price_history[symbol][-500:]

    def get_indicators(self, symbol: str) -> Optional[QuantIndicators]:
        """获取标的的技术指标计算器"""
        if symbol not in self._indicators:
            self._indicators[symbol] = QuantIndicators()
        return self._indicators.get(symbol)

    def generate_signals(
        self,
        symbols: List[str],
        price_data: Dict[str, Dict],
        fundamentals: Dict[str, Dict] = None
    ) -> List[QuantSignal]:
        """
        生成交易信号

        Args:
            symbols: 股票代码列表
            price_data: 价格数据 {symbol: {'open':, 'high':, 'low':, 'close':, 'volume':}}
            fundamentals: 财务数据 {symbol: {'pe':, 'pb':, 'roe':, 'earnings_growth':}}

        Returns:
            List[QuantSignal]: 信号列表
        """
        fundamentals = fundamentals or {}
        signals = []

        for symbol in symbols:
            data = price_data.get(symbol, {})
            if not data:
                continue

            # 添加价格数据到历史
            self.add_price_data(symbol, data)

            # 更新技术指标
            indicators = self.get_indicators(symbol)
            if indicators:
                indicator_results = indicators.update(data)

            # 获取当前标的历史数据
            history = self._price_history.get(symbol, [])
            if not history:
                continue

            # 用Alpha模型生成信号
            for model_name, model in self._alpha_models.items():
                try:
                    # 根据模型类型准备数据
                    if isinstance(model, ValueInvestingAlpha):
                        # 价值投资模型需要财务数据
                        fundamental = fundamentals.get(symbol, {})
                        if fundamental:
                            insight = model.update(symbol, {**data, **fundamental})
                        else:
                            insight = None
                    else:
                        # 其他模型使用价格数据
                        insight = model.update(symbol, data)

                    if insight and insight.direction != InsightDirection.FLAT:
                        # 获取指标结果
                        ind_result = {}
                        if indicators:
                            ind_result = {k: v.metadata for k, v in indicators.get_summary().items()}

                        signals.append(QuantSignal(
                            symbol=symbol,
                            direction=insight.direction,
                            confidence=insight.confidence,
                            magnitude=insight.magnitude,
                            period=insight.period,
                            model_name=model_name,
                            indicators=ind_result
                        ))

                except Exception as e:
                    print(f"Error generating signal for {symbol} with model {model_name}: {e}")
                    continue

        return signals

    def assess_risks(
        self,
        positions: Dict[str, Dict],
        market_data: Dict[str, Dict]
    ) -> List[RiskReport]:
        """
        评估风险

        Args:
            positions: 持仓 {symbol: {'quantity': n, 'avg_price': p}}
            market_data: 市场数据 {symbol: {'price': current_price}}

        Returns:
            List[RiskReport]: 风控报告列表
        """
        reports = []

        for symbol, position in positions.items():
            mkt = market_data.get(symbol, {})
            if not mkt:
                continue

            for model_name, model in self._risk_models.items():
                try:
                    report = model.assess(symbol, position, mkt)
                    reports.append(report)
                except Exception as e:
                    print(f"Error assessing risk for {symbol}: {e}")

        return reports

    def construct_portfolio(
        self,
        signals: List[QuantSignal],
        current_positions: Dict[str, Dict],
        total_value: float,
        price_map: Dict[str, float]
    ) -> PortfolioResult:
        """
        构建组合

        Args:
            signals: 信号列表
            current_positions: 当前持仓
            total_value: 总价值
            price_map: 价格映射

        Returns:
            PortfolioResult: 组合结果
        """
        if self._portfolio_model is None:
            self._portfolio_model = EqualWeightPortfolio()

        # 将QuantSignal转换为Insight
        insights = [
            Insight(
                symbol=s.signal,
                direction=s.direction,
                confidence=s.confidence,
                magnitude=s.magnitude,
                period=s.period,
                model_name=s.model_name
            )
            for s in signals
        ]

        return self._portfolio_model.construct(
            insights, current_positions, total_value, price_map
        )

    def run(
        self,
        symbols: List[str],
        price_data: Dict[str, Dict],
        positions: Dict[str, Dict],
        fundamentals: Dict[str, Dict] = None,
        total_value: float = 1000000
    ) -> QuantResult:
        """
        运行完整量化流程

        Args:
            symbols: 股票代码列表
            price_data: 价格数据
            positions: 当前持仓
            fundamentals: 财务数据
            total_value: 总资金

        Returns:
            QuantResult: 量化结果
        """
        fundamentals = fundamentals or {}

        # 1. 生成信号
        signals = self.generate_signals(symbols, price_data, fundamentals)

        # 2. 评估风险
        price_map = {symbol: data.get('close', 0) for symbol, data in price_data.items()}
        risk_reports = self.assess_risks(positions, price_map)

        # 3. 构建组合
        portfolio = self.construct_portfolio(signals, positions, total_value, price_map)

        # 4. 汇总结果
        summary = self._generate_summary(signals, portfolio, risk_reports)

        return QuantResult(
            signals=signals,
            portfolio=portfolio,
            risk_reports=risk_reports,
            summary=summary
        )

    def _generate_summary(
        self,
        signals: List[QuantSignal],
        portfolio: PortfolioResult,
        risk_reports: List[RiskReport]
    ) -> Dict:
        """生成分析摘要"""
        buy_signals = [s for s in signals if s.direction == InsightDirection.UP]
        sell_signals = [s for s in signals if s.direction == InsightDirection.DOWN]

        avg_confidence = sum(s.confidence for s in buy_signals) / len(buy_signals) if buy_signals else 0

        # 风控汇总
        risk_alerts = [r for r in risk_reports if r.decision != RiskDecision.NONE]
        exit_alerts = [r for r in risk_reports if r.decision == RiskDecision.EXIT]

        return {
            'total_signals': len(signals),
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'avg_confidence': avg_confidence,
            'portfolio_targets': len(portfolio.targets),
            'risk_alerts': len(risk_alerts),
            'exit_alerts': len(exit_alerts),
            'top_signals': sorted(buy_signals, key=lambda x: x.confidence, reverse=True)[:5]
        }


class AShareQuantEngine:
    """
    A股专用量化引擎

    针对A股市场优化的量化策略
    """

    def __init__(self):
        self._engine = QuantitativeEngine()
        self._setup_defaults()

    def _setup_defaults(self):
        """设置默认配置"""
        # 添加多个Alpha模型
        self._engine.add_alpha_model('dual_thrust', k1=0.6, k2=0.6, period=20)
        self._engine.add_alpha_model('momentum', fast_period=5, slow_period=20)
        self._engine.add_alpha_model('mean_reversion', period=20, std_threshold=2.0)

        # 添加风控
        self._engine.add_risk_model('stop_loss', stop_loss_pct=0.07, trailing_pct=0.05)
        self._engine.add_risk_model('max_drawdown', max_drawdown=0.15)

        # 设置组合
        self._engine.set_portfolio_model('equal_weight', max_positions=10)

    def analyze_stock(
        self,
        symbol: str,
        price_history: List[Dict],
        fundamentals: Dict = None
    ) -> Dict:
        """
        分析单只股票

        Args:
            symbol: 股票代码
            price_history: 历史价格数据列表
            fundamentals: 财务数据

        Returns:
            Dict: 分析结果
        """
        if not price_history:
            return {}

        # 更新价格数据
        price_data = {}
        for i, bar in enumerate(price_history[-30:]):
            price_data[symbol] = bar

        fundamentals = fundamentals or {}

        # 生成信号
        signals = self._engine.generate_signals([symbol], price_data, {symbol: fundamentals} if fundamentals else None)

        # 获取最新指标
        indicators = self._engine.get_indicators(symbol)
        indicator_summary = indicators.get_summary() if indicators else {}

        # 获取最新价格
        latest = price_history[-1]
        current_price = latest.get('close', 0)

        return {
            'symbol': symbol,
            'current_price': current_price,
            'signals': [
                {
                    'direction': 'UP' if s.direction == InsightDirection.UP else 'DOWN',
                    'confidence': s.confidence,
                    'magnitude': s.magnitude,
                    'period': s.period,
                    'model': s.model_name
                }
                for s in signals
            ],
            'indicators': indicator_summary,
            'recommendation': self._get_recommendation(signals, indicator_summary)
        }

    def _get_recommendation(self, signals: List[QuantSignal], indicators: Dict) -> str:
        """生成投资建议"""
        if not signals:
            return "观望"

        buy_count = sum(1 for s in signals if s.direction == InsightDirection.UP)
        avg_confidence = sum(s.confidence for s in signals) / len(signals)

        if avg_confidence > 0.7 and buy_count >= 2:
            return "强烈买入"
        elif avg_confidence > 0.5:
            return "适量买入"
        elif avg_confidence > 0.3:
            return "谨慎观望"
        else:
            return "建议回避"


def create_quant_engine(engine_type: str = "default") -> QuantitativeEngine:
    """
    工厂函数：创建量化引擎

    Args:
        engine_type: 引擎类型
            - 'default': 默认引擎
            - 'ashare': A股专用引擎

    Returns:
        QuantitativeEngine: 量化引擎实例
    """
    if engine_type == "ashare":
        return AShareQuantEngine()
    return QuantitativeEngine()
