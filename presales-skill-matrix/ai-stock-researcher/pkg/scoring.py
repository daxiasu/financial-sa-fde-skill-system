#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一评分引擎 v2.0 - 股票/基金/政策三维评分"""
import json, re, math
from pathlib import Path
from datetime import datetime

def _sf(v, default=None):
    """safe float"""
    try:
        return float(v) if v not in ("", "-", None, "N/A", "nan") else default
    except:
        return default

class StockScorer:
    """股票统一评分（0-100）"""

    POLICY_WEIGHT = 20   # 政策影响权重
    TECH_WEIGHT = 30     # 技术面权重
    VAL_WEIGHT = 25      # 估值面权重
    MONEY_WEIGHT = 25    # 资金面权重

    def __init__(self, policy_data=None, blacklist_codes=None):
        self.policy_data = policy_data or {}
        self.blacklist_codes = blacklist_codes or set()

    def score(self, stock):
        """综合评分"""
        code = str(stock.get("code", "")).zfill(6)
        if code in self.blacklist_codes:
            return 0, "blacklist"

        tech = self._tech_score(stock)
        val = self._valuation_score(stock)
        money = self._money_score(stock)
        policy = self._policy_score(stock)

        total = (
            tech * self.TECH_WEIGHT / 100 +
            val * self.VAL_WEIGHT / 100 +
            money * self.MONEY_WEIGHT / 100 +
            policy * self.POLICY_WEIGHT / 100
        )
        total = max(0, min(100, round(total, 1)))

        # 判定类型
        if total >= 70:
            tag = "强烈推荐"
        elif total >= 55:
            tag = "建议持有"
        elif total >= 40:
            tag = "谨慎观望"
        else:
            tag = "建议回避"

        return total, tag

    def _tech_score(self, s):
        """技术面评分（30%）"""
        score = 50
        # 涨跌
        chg = _sf(s.get("change_pct") or s.get("pct_change"))
        if chg is not None:
            if chg > 5:
                score += 10
            elif chg > 2:
                score += 5
            elif chg < -5:
                score -= 15
            elif chg < -2:
                score -= 8
            # 动量
            p1 = _sf(s.get("predict_1d") or s.get("predict_1"))
            p3 = _sf(s.get("predict_3d") or s.get("predict_3"))
            p5 = _sf(s.get("predict_5d") or s.get("predict_5"))
            momentum = 0
            if p1: momentum += p1
            if p3: momentum += p3 / 3
            if p5: momentum += p5 / 5
            score += int(momentum / 3)
        return max(0, min(100, score))

    def _valuation_score(self, s):
        """估值面评分（25%）"""
        score = 50
        pe = _sf(s.get("pe") or s.get("pe_ttm") or s.get("市盈率"))
        pb = _sf(s.get("pb") or s.get("市净率"))
        if pe is not None:
            if pe < 0:
                score -= 5  # 亏损
            elif pe < 15:
                score += 15
            elif pe < 25:
                score += 5
            elif pe < 40:
                score -= 5
            else:
                score -= 15
        if pb is not None:
            if pb < 0:
                score -= 5
            elif pb < 2:
                score += 10
            elif pb < 4:
                score += 5
            elif pb < 6:
                score -= 5
            else:
                score -= 10
        return max(0, min(100, score))

    def _money_score(self, s):
        """资金面评分（25%）"""
        score = 50
        inflow = _sf(s.get("主力净流入") or s.get("money_inflow"))
        turnover = _sf(s.get("换手率") or s.get("turnover_rate"))
        if inflow is not None:
            main_ratio = _sf(s.get("主力净流入占比") or s.get("main_ratio"), 0)
            if main_ratio > 10:
                score += 20
            elif main_ratio > 5:
                score += 10
            elif main_ratio < -10:
                score -= 20
            elif main_ratio < -5:
                score -= 10
        if turnover is not None:
            if turnover > 20:
                score += 5  # 高活跃
            elif turnover < 1:
                score -= 10  # 低流动性
        return max(0, min(100, score))

    def _policy_score(self, s):
        """政策面评分（20%）"""
        code = str(s.get("code", "")).zfill(6)
        analysis = self.policy_data.get("analysis", {})
        impact = analysis.get("stock_impact", {})
        if code in impact:
            return 50 + impact[code].get("policy_score", 0)
        return 50  # 无政策数据给中性

    def batch_score(self, stocks):
        """批量评分"""
        results = []
        for stock in stocks:
            total, tag = self.score(stock)
            stock_copy = dict(stock)
            stock_copy["quant_score"] = total
            stock_copy["score_tag"] = tag
            results.append(stock_copy)
        results.sort(key=lambda x: x.get("quant_score", 0), reverse=True)
        return results


class FundScorer:
    """基金统一评分（0-100）"""

    def __init__(self, blacklist_rules=None):
        self.blacklist_rules = blacklist_rules or {}

    def score(self, fund):
        """综合评分"""
        rule = fund.get("blacklist_rule") or fund.get("rule")
        if rule:
            return 0, "blacklist", self.blacklist_rules.get(rule, {}).get("name", "黑名单")

        score = 50
        details = {}

        # 1. 收益维度（30%）
        y1 = _sf(fund.get("yield_1y") or fund.get("annual_yield_1y") or fund.get("近1年年化%"))
        if y1 is not None:
            y_score = 30 if y1 >= 30 else 25 if y1 >= 20 else 20 if y1 >= 10 else 15 if y1 >= 5 else 10 if y1 >= 0 else 5
        else:
            y_score = 15
        score += y_score - 15
        details["yield_score"] = y_score

        # 2. 风险维度（30%）
        md = _sf(fund.get("max_drawdown") or fund.get("最大回撤"))
        if md is not None:
            risk_score = 30 if md <= 5 else 25 if md <= 10 else 20 if md <= 20 else 15 if md <= 30 else 10
        else:
            risk_score = 15
        score += risk_score - 15
        details["risk_score"] = risk_score

        # 3. 规模维度（15%）
        scale_str = str(fund.get("asset_scale", fund.get("规模", "")))
        scale_val = 0
        if "亿" in scale_str:
            try:
                scale_val = float(scale_str.replace("亿","").replace(",",""))
            except:
                scale_val = 0
        scale_score = 15 if 2 <= scale_val <= 50 else 12 if scale_val > 50 else 10 if scale_val >= 0.5 else 5
        score += scale_score - 7.5
        details["scale_score"] = scale_score

        # 4. 费率维度（15%）
        pf = _sf(fund.get("purchase_fee") or fund.get("申购费"))
        fee_score = 15 if pf == 0 else 12 if pf <= 0.1 else 10 if pf <= 0.5 else 7 if pf <= 1.0 else 5
        score += fee_score - 7.5
        details["fee_score"] = fee_score

        # 5. 稳定性维度（10%）
        vol = _sf(fund.get("volatility") or fund.get("波动率"))
        stab_score = 10 if vol and vol < 10 else 8 if vol and vol < 15 else 6 if vol and vol < 20 else 4 if vol else 5
        score += stab_score - 5
        details["stability_score"] = stab_score

        final = max(0, min(100, round(score + 50, 1)))

        if final >= 70:
            tag = "推荐持有"
        elif final >= 55:
            tag = "可以持有"
        elif final >= 40:
            tag = "谨慎观望"
        else:
            tag = "不建议持有"

        return final, tag, details

    def batch_score(self, funds):
        """批量评分"""
        results = []
        for fund in funds:
            total, tag, details = self.score(fund)
            fund_copy = dict(fund)
            fund_copy["quant_score"] = total
            fund_copy["score_tag"] = tag
            fund_copy["score_details"] = details
            results.append(fund_copy)
        results.sort(key=lambda x: x.get("quant_score", 0), reverse=True)
        return results
