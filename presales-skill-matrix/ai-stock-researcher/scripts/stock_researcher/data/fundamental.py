#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本面数据获取
Fundamental Data Fetching
东方财富财务API
"""

import re
import time
import json
from typing import Dict, List, Optional, Tuple

try:
    from crawl_utils import safe_request
    HAS_CRAWL_UTILS = True
except ImportError:
    HAS_CRAWL_UTILS = False


class FundamentalData:
    """
    基本面数据获取

    数据来源：东方财富
    - 财务指标: https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew
    """

    def __init__(self):
        pass

    def safe_float(self, v, default=0.0):
        try:
            f = float(v)
            return f if abs(f) < 1e10 else default
        except:
            return default

    def fetch_financial_indicators(self, code: str) -> Dict:
        """
        获取财务指标

        Args:
            code: 股票代码，如 "600519"

        Returns:
            Dict: 财务指标
        """
        # 自动判断前缀
        if code.startswith(("6", "5", "9")):
            prefix = "SH"
        else:
            prefix = "SZ"

        url = f"https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew?type=0&code={prefix}{code}"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://emweb.securities.eastmoney.com/"
        }

        try:
            if HAS_CRAWL_UTILS:
                raw = safe_request(url, headers=headers, timeout=8)
                if isinstance(raw, tuple):
                    raw = raw[0]
            else:
                import urllib.request
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore")

            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")

            data = json.loads(raw)
            return data
        except Exception as e:
            print(f"[FundamentalData] 获取财务指标失败: {e}")
            return {}

    def parse_financial_data(self, raw: Dict) -> Dict:
        """
        解析财务数据

        Args:
            raw: 原始财务数据

        Returns:
            Dict: 解析后的数据
        """
        result = {
            "roe": 0,
            "eps": 0,
            "bvps": 0,  # 每股净资产
            "pe": 0,    # 市盈率
            "pb": 0,    # 市净率
            "revenue": 0,
            "net_profit": 0,
            "total_assets": 0,
            "total_liabilities": 0,
            "current_assets": 0,
            "gross_margin": 0,
            "operating_margin": 0,
            "net_margin": 0,
        }

        try:
            # 解析最新季度数据
            data_list = raw.get("result", {}).get("data", [])
            if data_list and len(data_list) > 0:
                latest = data_list[0]

                # ROE
                roe_str = latest.get("ROE", "")
                if roe_str and roe_str not in ("-", "", "N/A"):
                    result["roe"] = self.safe_float(roe_str.replace("%", ""))

                # EPS
                eps_str = latest.get("BASIC_EPS", "")
                if eps_str and eps_str not in ("-", "", "N/A"):
                    result["eps"] = self.safe_float(eps_str)

                # 每股净资产
                bvps_str = latest.get("BPS", "")
                if bvps_str and bvps_str not in ("-", "", "N/A"):
                    result["bvps"] = self.safe_float(bvps_str)

                # 营业收入
                revenue_str = latest.get("TOTAL_OPERATE_INCOME", "")
                if revenue_str and revenue_str not in ("-", "", "N/A"):
                    result["revenue"] = self.safe_float(revenue_str)

                # 净利润
                profit_str = latest.get("PARENT_NETPROFIT", "")
                if profit_str and profit_str not in ("-", "", "N/A"):
                    result["net_profit"] = self.safe_float(profit_str)

                # 资产负债率
                debt_str = latest.get("DEBT_ASSET_RATIO", "")
                if debt_str and debt_str not in ("-", "", "N/A"):
                    result["debt_ratio"] = self.safe_float(debt_str.replace("%", ""))

        except Exception as e:
            print(f"[FundamentalData] 解析财务数据失败: {e}")

        return result

    def get_valuation(self, code: str) -> Dict:
        """
        获取估值指标（PE/PB/PS等）

        Args:
            code: 股票代码

        Returns:
            Dict: 估值指标
        """
        # 使用东方财富估值API
        if code.startswith(("6", "5", "9")):
            mkt = "1"  # 上海
        else:
            mkt = "0"  # 深圳

        url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_VALUATION&columns=ALL&filter=(SECUCODE%3D%22{code}.SH%22)"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://data.eastmoney.com/"
        }

        try:
            if HAS_CRAWL_UTILS:
                raw = safe_request(url, headers=headers, timeout=8)
                if isinstance(raw, tuple):
                    raw = raw[0]
            else:
                import urllib.request
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore")

            data = json.loads(raw)
            result = data.get("result", {}).get("data", [])
            if result:
                item = result[0]
                return {
                    "pe": self.safe_float(item.get("PE_TTM")),
                    "pb": self.safe_float(item.get("PB")),
                    "ps": self.safe_float(item.get("PS_TTM")),
                    "pcf": self.safe_float(item.get("PCF")),
                }
        except Exception as e:
            print(f"[FundamentalData] 获取估值失败: {e}")

        return {}

    def get_financial_summary(self, code: str) -> Dict:
        """
        获取财务摘要（综合）

        Args:
            code: 股票代码

        Returns:
            Dict: 财务摘要
        """
        fin_data = self.fetch_financial_indicators(code)
        parsed = self.parse_financial_data(fin_data)
        valuation = self.get_valuation(code)

        result = {**parsed, **valuation}
        return result