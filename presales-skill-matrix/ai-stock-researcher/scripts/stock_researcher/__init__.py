"""
专业股票研究员模块
Professional Stock Researcher Module
"""
import sys
sys.dont_write_bytecode = True

from .core.analyzer import StockResearcher

__all__ = ["StockResearcher"]