#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "simulated_post_loan_portfolio.json"


def evaluate(customer):
    score = 0
    hits = []

    overdue_days = customer["overdue_days"]
    if 1 <= overdue_days <= 7:
      score += 18
      hits.append("逾期 1-7 天")
    elif 8 <= overdue_days <= 30:
      score += 35
      hits.append("逾期 8-30 天")
    elif overdue_days > 30:
      score += 55
      hits.append("逾期超过 30 天")

    if customer["extension_or_refinance"]:
      score += 20
      hits.append("最近 3 个月展期或借新还旧")
    if customer["repayment_source_unclear"]:
      score += 12
      hits.append("还款资金来源解释不足")

    revenue_drop = customer["revenue_yoy_change_pct"]
    if -30 <= revenue_drop <= -15:
      score += 12
      hits.append("营收同比下降 15%-30%")
    elif revenue_drop < -30:
      score += 25
      hits.append("营收同比下降超过 30%")

    if customer["operating_cashflow_negative"]:
      score += 18
      hits.append("经营性现金流为负")
    if customer["debt_ratio_pct"] > 75:
      score += 15
      hits.append("资产负债率超过 75%")
    if customer["receivable_turnover_slow"]:
      score += 12
      hits.append("应收账款周转明显放缓")
    if customer["inventory_turnover_slow"]:
      score += 10
      hits.append("存货周转明显放缓")

    public_risk = customer["public_risk"]
    if public_risk == "administrative_penalty":
      score += 12
      hits.append("行政处罚或经营异常")
    elif public_risk in {"lawsuit", "negative_news"}:
      score += 25
      hits.append("诉讼、被执行或重大负面舆情")
    elif public_risk == "regulatory_penalty":
      score += 35
      hits.append("监管处罚或重大负面事件")

    related_ratio = customer["related_transaction_ratio_pct"]
    if 10 <= related_ratio <= 25:
      score += 8
      hits.append("关联交易占比 10%-25%")
    elif related_ratio > 25:
      score += 18
      hits.append("关联交易占比超过 25%")
    if customer["related_party_negative"]:
      score += 20
      hits.append("关联方出现重大负面")
    if customer["abnormal_fund_flow"]:
      score += 15
      hits.append("异常资金往来解释不足")

    if customer["industry_downturn"]:
      score += 8
      hits.append("行业景气度下行")
    if customer["regional_event"]:
      score += 8
      hits.append("区域风险事件影响")

    if score >= 60:
      level = "重大预警"
    elif score >= 35:
      level = "明显上升"
    elif score >= 15:
      level = "轻微上升"
    else:
      level = "稳定"

    return score, level, hits


def main():
    customers = json.loads(DATA.read_text(encoding="utf-8"))
    assert len(customers) == 10, "演示数据应包含 10 个存量授信客户"

    levels = {}
    for customer in customers:
      score, level, hits = evaluate(customer)
      levels[level] = levels.get(level, 0) + 1
      assert isinstance(score, int)
      assert hits or level == "稳定"

    assert "重大预警" in levels, "应至少包含一个重大预警样例"
    assert "明显上升" in levels, "应至少包含一个明显上升样例"
    assert "轻微上升" in levels, "应至少包含一个轻微上升样例"
    assert "稳定" in levels, "应至少包含一个稳定样例"
    assert levels["重大预警"] <= 3, "重大预警样例不应过多，避免演示中过度报高风险"
    print("贷后风险监测 smoke test passed")
    print(levels)


if __name__ == "__main__":
    main()
