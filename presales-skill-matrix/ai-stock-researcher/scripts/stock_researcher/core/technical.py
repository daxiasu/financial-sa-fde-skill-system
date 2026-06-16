#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术分析引擎
Technical Analysis Engine
包含：MA/EMA/MACD/RSI/KDJ/布林带/均线多头判断/ADX/Hurst指数
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TechnicalIndicators:
    """技术指标数据"""
    # 均线
    ma5: float = 0
    ma10: float = 0
    ma20: float = 0
    ma60: float = 0
    ma120: float = 0
    ma250: float = 0

    # EMA
    ema12: float = 0
    ema26: float = 0

    # MACD
    macd_dif: float = 0
    macd_dea: float = 0
    macd_hist: float = 0

    # RSI
    rsi6: float = 50
    rsi14: float = 50
    rsi24: float = 50

    # KDJ
    k: float = 50
    d: float = 50
    j: float = 50

    # 布林带
    bb_upper: float = 0
    bb_mid: float = 0
    bb_lower: float = 0
    bb_position: float = 0  # 0-100, 当前价在布林带中的位置

    # ADX
    adx: float = 0

    # 均线状态
    ma_arrangement: str = "混乱"  # 多头排列/空头排列/混乱

    # 综合评分
    tech_score: float = 0
    tech_signal: str = "中性"


class TechnicalAnalyzer:
    """技术分析指标计算器"""

    @staticmethod
    def calc_ma(prices: List[float], period: int) -> float:
        """简单移动平均"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period

    @staticmethod
    def calc_ema(prices: List[float], period: int) -> float:
        """指数移动平均"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        k = 2.0 / (period + 1)
        ema = sum(prices[:period]) / period
        for v in prices[period:]:
            ema = v * k + ema * (1 - k)
        return ema

    @staticmethod
    def calc_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """MACD计算 (DIF, DEA, MACD柱)"""
        if len(prices) < slow + signal:
            return 0, 0, 0

        # 计算EMA
        k_fast = 2.0 / (fast + 1)
        ema_fast = sum(prices[:fast]) / fast
        for v in prices[fast:]:
            ema_fast = v * k_fast + ema_fast * (1 - k_fast)

        k_slow = 2.0 / (slow + 1)
        ema_slow = sum(prices[:slow]) / slow
        for v in prices[slow:]:
            ema_slow = v * k_slow + ema_slow * (1 - k_slow)

        dif = ema_fast - ema_slow
        # 简化DEA计算
        dea = dif * 0.9
        macd_hist = (dif - dea) * 2

        return dif, dea, macd_hist

    @staticmethod
    def calc_rsi(prices: List[float], period: int = 14) -> float:
        """RSI计算"""
        if len(prices) < period + 1:
            return 50

        gains, losses = [], []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - 100 / (1 + rs)

    @staticmethod
    def calc_kdj(highs: List[float], lows: List[float], closes: List[float], period: int = 9) -> Tuple[float, float, float]:
        """KDJ计算

        注意：KDJ需要历史数据才能正确平滑计算，仅有近期数据时返回估算值
        """
        if len(closes) < period:
            return 50, 50, 50

        recent_highs = highs[-period:] if len(highs) >= period else highs
        recent_lows = lows[-period:] if len(lows) >= period else lows
        high = max(recent_highs) if recent_highs else closes[-1]
        low = min(recent_lows) if recent_lows else closes[-1]

        if high == low:
            return 50, 50, 50

        rsv = (closes[-1] - low) / (high - low) * 100

        # KDJ平滑计算（简化版）
        # 注意：完整实现需要保存历史K/D值，这里使用简化估算
        k = 50 + (rsv - 50) * 0.3  # 简化平滑
        d = 50 + (k - 50) * 0.3
        j = 3 * k - 2 * d

        # 限制范围
        k = max(0, min(100, k))
        d = max(0, min(100, d))
        j = max(0, min(100, j))

        return k, d, j

    @staticmethod
    def calc_bollinger(prices: List[float], period: int = 20, std_mult: float = 2) -> Tuple[float, float, float]:
        """布林带计算 (上轨, 中轨, 下轨)"""
        if len(prices) < period:
            return 0, 0, 0

        recent = prices[-period:]
        mid = sum(recent) / period
        variance = sum((p - mid) ** 2 for p in recent) / period
        std = math.sqrt(variance)

        return mid + std_mult * std, mid, mid - std_mult * std

    @staticmethod
    def calc_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """ADX平均趋向指数计算"""
        if len(closes) < period + 1:
            return 0

        # 计算True Range
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []

        for i in range(1, len(closes)):
            high = highs[i] if i < len(highs) else closes[i]
            low = lows[i] if i < len(lows) else closes[i]
            prev_high = highs[i-1] if i-1 < len(highs) else closes[i-1]
            prev_low = lows[i-1] if i-1 < len(lows) else closes[i-1]
            prev_close = closes[i-1]

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)

            plus_dm = max(high - prev_high, 0) if max(high - prev_high, 0) > max(prev_low - low, 0) else 0
            minus_dm = max(prev_low - low, 0) if max(prev_low - low, 0) > max(high - prev_high, 0) else 0

            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

        if len(tr_list) < period:
            return 0

        # 计算平滑值
        atr = sum(tr_list[-period:]) / period
        plus_dm_smooth = sum(plus_dm_list[-period:]) / period
        minus_dm_smooth = sum(minus_dm_list[-period:]) / period

        # 计算DI
        if atr == 0:
            return 0
        plus_di = plus_dm_smooth / atr * 100
        minus_di = minus_dm_smooth / atr * 100

        # 计算DX
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return 0

        dx = abs(plus_di - minus_di) / di_sum * 100

        # 平滑ADX
        adx = dx  # 简化处理
        return adx

    @staticmethod
    def calc_hurst(returns: List[float], lookback: int = 100) -> float:
        """
        Hurst指数计算 - 区分趋势/均值回归/随机
        H < 0.5: 均值回归
        H = 0.5: 随机游走
        H > 0.5: 趋势延续
        """
        if len(returns) < lookback:
            lookback = len(returns)
        if lookback < 10:
            return 0.5

        data = returns[-lookback:]
        n = len(data)

        # R/S分析
        def range_over_std(n):
            if n > len(data):
                return 1
            subseries = [data[i:i+n] for i in range(0, len(data), n)]
            if len(subseries) < 2:
                return 1

            ranges = []
            for sub in subseries:
                if len(sub) < 2:
                    continue
                mean = sum(sub) / len(sub)
                cumsum = [0]
                for v in sub:
                    cumsum.append(cumsum[-1] + v - mean)
                r = max(cumsum) - min(cumsum)
                s = math.sqrt(sum((v - mean)**2 for v in sub) / len(sub)) if len(sub) > 1 else 1
                ranges.append(r / s if s > 0 else 1)

            return sum(ranges) / len(ranges) if ranges else 1

        # 计算不同窗口的R/S
        log_n = []
        log_rs = []

        for n_size in [5, 10, 20, 50]:
            if n_size <= len(data):
                rs = range_over_std(n_size)
                log_n.append(math.log(n_size))
                log_rs.append(math.log(rs) if rs > 0 else 0)

        if len(log_n) < 2:
            return 0.5

        # 线性回归
        n_mean = sum(log_n) / len(log_n)
        rs_mean = sum(log_rs) / len(log_rs)

        numerator = sum((x - n_mean) * (y - rs_mean) for x, y in zip(log_n, log_rs))
        denominator = sum((x - n_mean)**2 for x in log_n)

        if denominator == 0:
            return 0.5

        hurst = numerator / denominator
        return max(0, min(1, hurst))

    @staticmethod
    def check_ma_arrangement(prices: List[float]) -> str:
        """判断均线多头/空头排列"""
        if len(prices) < 60:
            return "数据不足"

        ma5 = TechnicalAnalyzer.calc_ma(prices, 5)
        ma10 = TechnicalAnalyzer.calc_ma(prices, 10)
        ma20 = TechnicalAnalyzer.calc_ma(prices, 20)
        ma60 = TechnicalAnalyzer.calc_ma(prices, 60)

        if ma5 > ma10 > ma20 > ma60:
            return "多头排列"
        elif ma5 < ma10 < ma20 < ma60:
            return "空头排列"
        else:
            return "混乱"

    @staticmethod
    def calc_bb_position(price: float, upper: float, mid: float, lower: float) -> float:
        """计算价格在布林带中的位置 (0-100)"""
        if upper == lower or upper == 0:
            return 50
        return (price - lower) / (upper - lower) * 100

    def analyze(self, code: str, prices: List[float], highs: List[float] = None, lows: List[float] = None) -> TechnicalIndicators:
        """
        综合技术分析

        参数:
            code: 股票代码
            prices: 收盘价列表（至少20个数据点）
            highs: 最高价列表（可选）
            lows: 最低价列表（可选）

        返回:
            TechnicalIndicators 对象

        注意:
            - 数据不足时（<20个点）会抛出ValueError
            - KDJ指标因需要历史平滑值，短期内可能有误差
            - 均线多头判断需要至少60个数据点
        """
        if len(prices) < 20:
            raise ValueError(f"[数据不足] 需要至少20个数据点进行技术分析，当前只有{len(prices)}个数据点。请检查股票代码是否正确或获取更多历史数据。")

        # 如果没有提供highs/lows，使用closes模拟
        if highs is None or len(highs) == 0:
            highs = prices
        if lows is None or len(lows) == 0:
            lows = prices

        current = prices[-1]

        # 均线计算
        ma5 = self.calc_ma(prices, 5)
        ma10 = self.calc_ma(prices, 10)
        ma20 = self.calc_ma(prices, 20)
        ma60 = self.calc_ma(prices, 60)
        ma120 = self.calc_ma(prices, 120) if len(prices) >= 120 else current
        ma250 = self.calc_ma(prices, 250) if len(prices) >= 250 else current

        # EMA计算
        ema12 = self.calc_ema(prices, 12)
        ema26 = self.calc_ema(prices, 26)

        # MACD
        macd_dif, macd_dea, macd_hist = self.calc_macd(prices)

        # RSI
        rsi6 = self.calc_rsi(prices, 6)
        rsi14 = self.calc_rsi(prices, 14)
        rsi24 = self.calc_rsi(prices, 24)

        # KDJ
        k, d, j = self.calc_kdj(highs, lows, prices)

        # 布林带
        bb_upper, bb_mid, bb_lower = self.calc_bollinger(prices)
        bb_position = self.calc_bb_position(current, bb_upper, bb_mid, bb_lower)

        # ADX
        adx = self.calc_adx(highs, lows, prices)

        # 均线排列
        ma_arrangement = self.check_ma_arrangement(prices)

        # 综合技术评分
        tech_score = self._calc_tech_score(
            current=current,
            ma5=ma5, ma10=ma10, ma20=ma20, ma60=ma60,
            rsi14=rsi14,
            macd_hist=macd_hist,
            bb_position=bb_position,
            ma_arrangement=ma_arrangement
        )

        return TechnicalIndicators(
            ma5=round(ma5, 2), ma10=round(ma10, 2), ma20=round(ma20, 2),
            ma60=round(ma60, 2), ma120=round(ma120, 2), ma250=round(ma250, 2),
            ema12=round(ema12, 2), ema26=round(ema26, 2),
            macd_dif=round(macd_dif, 4), macd_dea=round(macd_dea, 4), macd_hist=round(macd_hist, 4),
            rsi6=round(rsi6, 1), rsi14=round(rsi14, 1), rsi24=round(rsi24, 1),
            k=round(k, 1), d=round(d, 1), j=round(j, 1),
            bb_upper=round(bb_upper, 2), bb_mid=round(bb_mid, 2), bb_lower=round(bb_lower, 2),
            bb_position=round(bb_position, 1),
            adx=round(adx, 1),
            ma_arrangement=ma_arrangement,
            tech_score=tech_score,
            tech_signal=self._get_tech_signal(tech_score)
        )

    def _calc_tech_score(self, current: float, ma5: float, ma10: float, ma20: float, ma60: float,
                         rsi14: float, macd_hist: float, bb_position: float, ma_arrangement: str) -> float:
        """计算技术综合评分 (-100 ~ +100)"""
        score = 0

        # 均线状态 (40分)
        if ma_arrangement == "多头排列":
            score += 40
        elif ma_arrangement == "空头排列":
            score -= 40
        else:
            # 部分多头
            if ma5 > ma20:
                score += 20
            else:
                score -= 20

        # RSI (30分)
        if rsi14 < 30:
            score += 15  # 超卖，看涨
        elif rsi14 > 70:
            score -= 15  # 超买，看跌
        else:
            # 中性区间
            if rsi14 > 50:
                score += 5
            else:
                score -= 5

        # MACD (20分)
        if macd_hist > 0:
            score += 20
        else:
            score -= 20

        # 布林带位置 (10分)
        if bb_position > 80:
            score -= 10  # 接近上轨，可能回调
        elif bb_position < 20:
            score += 10  # 接近下轨，可能反弹

        return score

    def _get_tech_signal(self, score: float) -> str:
        """根据评分给出信号"""
        if score > 20:
            return "买入"
        elif score > -10:
            return "观望"
        else:
            return "卖出"

    def get_trading_signal(self, tech: TechnicalIndicators) -> Dict:
        """
        获取交易信号
        返回: {"action": "buy/sell/hold", "reason": "...", "confidence": 0-1}
        """
        signals = []

        # 均线信号
        if tech.ma_arrangement == "多头排列":
            signals.append(("买入", 0.8))
        elif tech.ma_arrangement == "空头排列":
            signals.append(("卖出", 0.8))

        # RSI信号
        if tech.rsi14 < 30:
            signals.append(("买入", 0.7))
        elif tech.rsi14 > 70:
            signals.append(("卖出", 0.7))

        # MACD信号
        if tech.macd_hist > 0:
            signals.append(("买入", 0.6))
        else:
            signals.append(("卖出", 0.6))

        # 布林带信号
        if tech.bb_position < 20:
            signals.append(("买入", 0.5))
        elif tech.bb_position > 80:
            signals.append(("卖出", 0.5))

        # 统计
        buy_signals = sum(1 for s, _ in signals if s == "买入")
        sell_signals = sum(1 for s, _ in signals if s == "卖出")

        if buy_signals > sell_signals:
            action = "买入"
            confidence = buy_signals / len(signals)
        elif sell_signals > buy_signals:
            action = "卖出"
            confidence = sell_signals / len(signals)
        else:
            action = "观望"
            confidence = 0.5

        reasons = [r for r, _ in signals]

        return {
            "action": action,
            "reasons": reasons,
            "confidence": round(confidence, 2),
            "tech_score": tech.tech_score,
            "tech_signal": tech.tech_signal
        }