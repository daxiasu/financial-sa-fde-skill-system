# -*- coding: utf-8 -*-
"""
量化模型模块
Quantitative Models Module

基于 QuantConnect Lean 架构的A股量化模型：
- Alpha模型：信号生成
- Risk模型：风险管理
- Portfolio模型：组合构建
- 技术指标：技术分析

适配A股市场数据源（东方财富/腾讯财经）
"""

from .alpha_models import (
    DualThrustAlpha,
    RateOfChangeAlpha,
    MeanReversionAlpha,
    MomentumAlpha,
    ValueInvestingAlpha,
)
from .risk_models import (
    MaximumDrawdownRiskModel,
    StopLossRiskModel,
    TargetProfitRiskModel,
)
from .portfolio_models import (
    EqualWeightPortfolio,
    RiskParityPortfolio,
    ValueWeightedPortfolio,
)
from .indicators import (
    QuantIndicators,
    BollingerBands,
    MACD,
    RSI,
    ADX,
    HurstIndex,
)
from .engine import QuantitativeEngine

__all__ = [
    # Alpha模型
    "DualThrustAlpha",
    "RateOfChangeAlpha",
    "MeanReversionAlpha",
    "MomentumAlpha",
    "ValueInvestingAlpha",
    # 风险模型
    "MaximumDrawdownRiskModel",
    "StopLossRiskModel",
    "TargetProfitRiskModel",
    # 组合模型
    "EqualWeightPortfolio",
    "RiskParityPortfolio",
    "ValueWeightedPortfolio",
    # 指标
    "QuantIndicators",
    "BollingerBands",
    "MACD",
    "RSI",
    "ADX",
    "HurstIndex",
    # 引擎
    "QuantitativeEngine",
]
