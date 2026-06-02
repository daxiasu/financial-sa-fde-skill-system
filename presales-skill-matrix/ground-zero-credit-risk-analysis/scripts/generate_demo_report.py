#!/usr/bin/env python3
"""生成授信走访前风险分析 Demo 报告。

该脚本读取 data/demo_enterprises.json 中的模拟企业数据，按固定业务规则生成
Markdown 报告。它用于演示 Skill 的输入、规则判断和输出结构，不调用大模型。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "demo_outputs"


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, list):
        return bool(value)
    return True


def data_completeness(case: dict[str, Any]) -> list[tuple[str, str, str]]:
    fields = [
        ("工商信息", "business_registration", "用于判断主体资质、股权和经营异常。"),
        ("财务信息", "financials", "用于判断收入质量、现金流、负债和偿债压力。"),
        ("经营信息", "operations", "用于判断经营真实性、客户集中度和订单情况。"),
        ("司法信息", "legal_records", "用于判断诉讼、被执行、失信等风险。"),
        ("舆情信息", "public_sentiment", "用于判断公开负面事件和声誉风险。"),
        ("关联关系", "related_parties", "用于判断关联交易、关联担保和资金回流。"),
        ("银行内部信息", "bank_internal_data", "用于判断历史还款、授信和账户表现。"),
    ]
    rows = []
    for label, key, comment in fields:
        provided = has_value(case.get(key))
        rows.append((label, "是" if provided else "否", comment if provided else f"缺失，{comment}"))
    return rows


def detect_signals(case: dict[str, Any]) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    financials = case.get("financials") or {}

    if financials.get("operating_cash_flow") and "负" in str(financials["operating_cash_flow"]):
        signals.append({
            "dimension": "财务质量",
            "signal": "经营性现金流为负",
            "basis": f"财务信息显示：{financials['operating_cash_flow']}。",
            "attention": "高",
            "score": "15",
        })

    receivables = financials.get("receivables_to_revenue")
    if isinstance(receivables, (int, float)) and receivables >= 40:
        signals.append({
            "dimension": "财务质量",
            "signal": "应收账款占收入比例偏高",
            "basis": f"应收账款占营收比例为 {receivables}%，超过 40% 的重点核验阈值。",
            "attention": "中",
            "score": "12",
        })

    operations = str(case.get("operations") or "")
    customer_concentration = "客户集中" in operations
    top_five_match = re.search(r"前五大客户[^0-9]{0,12}(\d+)%", operations)
    if top_five_match and int(top_five_match.group(1)) >= 60:
        customer_concentration = True
    if "70%" in operations:
        customer_concentration = True
    if customer_concentration:
        signals.append({
            "dimension": "经营真实性",
            "signal": "客户集中度较高",
            "basis": "经营信息显示前五大客户收入占比较高，需要核验核心客户稳定性和回款质量。",
            "attention": "中",
            "score": "10",
        })

    related = str(case.get("related_parties") or "")
    related_clear = "未发现重大关联" in related
    related_minor = any(word in related for word in ["金额较小", "少量关联", "占比很低"])
    if not related_clear and ("贸易公司" in related or "采购往来" in related or "关联" in related or "关联担保" in related):
        signals.append({
            "dimension": "关联关系",
            "signal": "存在少量关联交易待核验" if related_minor else "存在关联交易或关联关系待核验",
            "basis": f"关联关系信息显示：{related}",
            "attention": "低" if related_minor else "中",
            "score": "6" if related_minor else "10",
        })

    registration = str(case.get("business_registration") or "")
    if "多次变更" in registration or "频繁" in registration:
        signals.append({
            "dimension": "主体资质",
            "signal": "法定代表人或股东频繁变更",
            "basis": f"工商信息显示：{registration}",
            "attention": "高",
            "score": "15",
        })

    legal = str(case.get("legal_records") or "")
    legal_has_material_issue = (
        "被执行金额" in legal
        or "存在多起" in legal
        or "多起" in legal
        or "合计" in legal
        or "失信" in legal and not any(clear in legal for clear in ["无失信", "无失信被执行"])
    )
    if "被执行" in legal and legal_has_material_issue:
        signals.append({
            "dimension": "司法与舆情",
            "signal": "存在被执行记录",
            "basis": f"司法信息显示：{legal}",
            "attention": "高",
            "score": "25",
        })

    public_sentiment = str(case.get("public_sentiment") or "")
    public_sentiment_has_issue = any(word in public_sentiment for word in ["停工", "拖欠", "欠薪", "事故", "整改"])
    public_sentiment_clear = any(clear in public_sentiment for clear in ["暂无明显负面", "无明显负面", "暂无负面", "无负面"])
    if public_sentiment_has_issue and not public_sentiment_clear:
        signals.append({
            "dimension": "司法与舆情",
            "signal": "存在负面舆情或经营异常报道",
            "basis": f"舆情信息显示：{public_sentiment}",
            "attention": "高",
            "score": "18",
        })

    if "短期借款" in str(financials.get("short_term_debt") or ""):
        signals.append({
            "dimension": "财务质量",
            "signal": "短期债务压力上升",
            "basis": f"财务信息显示：{financials['short_term_debt']}。",
            "attention": "中",
            "score": "10",
        })

    if isinstance(financials.get("revenue_growth"), (int, float)) and financials["revenue_growth"] <= -15:
        signals.append({
            "dimension": "财务质量",
            "signal": "收入明显下滑",
            "basis": f"财务信息显示收入增长率为 {financials['revenue_growth']}%。",
            "attention": "中",
            "score": "10",
        })

    if isinstance(financials.get("profit_growth"), (int, float)) and financials["profit_growth"] <= -20:
        signals.append({
            "dimension": "财务质量",
            "signal": "利润明显下滑",
            "basis": f"财务信息显示利润增长率为 {financials['profit_growth']}%。",
            "attention": "中",
            "score": "8",
        })

    if isinstance(financials.get("asset_liability_ratio"), (int, float)) and financials["asset_liability_ratio"] >= 70:
        signals.append({
            "dimension": "财务质量",
            "signal": "资产负债率偏高",
            "basis": f"资产负债率为 {financials['asset_liability_ratio']}%，达到重点关注区间。",
            "attention": "中",
            "score": "8",
        })

    if "缺少完整物流" in operations or "缺少合同" in operations or "缺少" in operations and "凭证" in operations:
        trading_like = any(word in case.get("industry", "") for word in ["贸易", "供应链"])
        signals.append({
            "dimension": "经营真实性",
            "signal": "交易真实性佐证不足",
            "basis": f"经营信息显示：{operations}",
            "attention": "高",
            "score": "25" if trading_like else "15",
        })

    if "库存周转周期拉长" in operations or "库存增加" in operations:
        signals.append({
            "dimension": "经营真实性",
            "signal": "库存周转压力上升",
            "basis": f"经营信息显示：{operations}",
            "attention": "中",
            "score": "10",
        })

    if "环保整改" in public_sentiment or "环保处罚" in public_sentiment:
        signals.append({
            "dimension": "司法与舆情",
            "signal": "环保合规事项待核验",
            "basis": f"舆情信息显示：{public_sentiment}",
            "attention": "高",
            "score": "18",
        })

    if "行业景气度下行" in public_sentiment or "地产链景气度" in case.get("known_background", ""):
        signals.append({
            "dimension": "行业与授信用途",
            "signal": "行业景气度下行",
            "basis": f"背景或舆情信息显示：{case.get('known_background', '')} {public_sentiment}".strip(),
            "attention": "中",
            "score": "8",
        })

    return signals


def score_and_level(case: dict[str, Any], signals: list[dict[str, str]]) -> tuple[int, str]:
    score = sum(int(item["score"]) for item in signals)
    missing_count = sum(1 for _, provided, _ in data_completeness(case) if provided == "否")
    if missing_count >= 5:
        score = max(score, 21)
    if case.get("credit_type") == "首次授信":
        score = max(score, 21)
    if any("关联" in item["signal"] for item in signals):
        score = max(score, 21)
    score = min(score, 100)
    if score <= 20:
        return score, "L1"
    if score <= 40:
        return score, "L2"
    if score <= 60:
        return score, "L3"
    if score <= 80:
        return score, "L4"
    return score, "L5"


def confidence(case: dict[str, Any]) -> str:
    missing_count = sum(1 for _, provided, _ in data_completeness(case) if provided == "否")
    if missing_count >= 5:
        return "低"
    if missing_count >= 2:
        return "中"
    return "高"


def questions_for(case: dict[str, Any], signals: list[dict[str, str]]) -> list[tuple[str, str, str, str]]:
    questions = [
        (
            "本次授信资金的具体支付对象、付款节奏和对应合同是什么？",
            "企业负责人",
            "核验授信用途真实性和合理性",
            "采购合同、付款计划、资金使用说明",
        ),
        (
            "近 12 个月主要客户回款周期是否延长，是否存在逾期未回款客户？",
            "财务负责人",
            "核验应收账款质量和现金流压力",
            "应收账款明细、账龄表、回款凭证、银行流水",
        ),
        (
            "前五大客户订单是否稳定，是否存在单一客户依赖或订单取消风险？",
            "销售负责人",
            "核验客户集中度和未来收入稳定性",
            "主要客户合同、订单、发票、验收单",
        ),
        (
            "关联企业之间交易定价依据是什么，是否存在资金回流或代垫资金？",
            "企业负责人/财务负责人",
            "核验关联交易合理性和资金闭环风险",
            "关联交易合同、发票、付款凭证、关联企业清单",
        ),
    ]

    signal_text = " ".join(item["signal"] for item in signals)
    if "被执行" in signal_text or "负面舆情" in signal_text:
        questions.append(
            (
                "当前诉讼、被执行或负面报道事项的最新进展是什么，是否影响项目履约和现金流？",
                "企业负责人/法务或财务负责人",
                "核验重大风险事项是否仍在持续",
                "法院材料、和解协议、付款证明、项目进展说明",
            )
        )
    if "法定代表人或股东频繁变更" in signal_text:
        questions.append(
            (
                "近一年股权或法定代表人变更的原因是什么，实际控制人是否发生变化？",
                "企业负责人",
                "核验主体稳定性和实际控制关系",
                "工商变更材料、股权转让协议、实际控制人说明",
            )
        )
    if not signals:
        questions.append(
            (
                "企业主营业务模式、主要客户和供应商分别是什么？",
                "企业负责人",
                "在资料不足时建立基础经营画像",
                "营业执照、合同样本、客户供应商清单",
            )
        )
    return questions


def material_list(signals: list[dict[str, str]]) -> list[str]:
    materials = [
        "近 2-3 年审计报告或财务报表",
        "近 12 个月主要银行账户流水",
        "本次授信用途对应的采购合同、付款计划或资金使用说明",
    ]
    signal_text = " ".join(item["signal"] for item in signals)
    if "应收账款" in signal_text or "客户集中" in signal_text:
        materials.extend([
            "主要客户合同、订单、发票、验收单和回款凭证",
            "应收账款明细、账龄表和坏账计提说明",
        ])
    if "关联" in signal_text:
        materials.extend([
            "关联企业清单、关联交易明细和定价说明",
            "关联企业之间资金流水或付款凭证",
        ])
    if "被执行" in signal_text or "负面舆情" in signal_text:
        materials.extend([
            "诉讼、被执行事项最新进展材料",
            "停工、拖欠或负面报道事项的整改和说明材料",
        ])
    if "法定代表人或股东频繁变更" in signal_text:
        materials.append("工商变更材料、股权转让协议和实际控制人说明")
    return materials


def render_report(case: dict[str, Any]) -> str:
    signals = detect_signals(case)
    score, level = score_and_level(case, signals)
    completeness_rows = data_completeness(case)
    confidence_level = confidence(case)
    questions = questions_for(case, signals)
    materials = material_list(signals)
    missing = [label for label, provided, _ in completeness_rows if provided == "否"]

    signal_rows = "\n".join(
        f"| {item['dimension']} | {item['signal']} | {item['basis']} | {item['attention']} |"
        for item in signals
    ) or "| 暂无明确风险线索 | 基于已提供资料暂未识别明确风险线索 | 资料不足或未提供明显异常 | 低 |"

    completeness_table = "\n".join(
        f"| {label} | {provided} | {comment} |" for label, provided, comment in completeness_rows
    )

    question_rows = "\n".join(
        f"| {q} | {role} | {purpose} | {support} |" for q, role, purpose, support in questions
    )

    material_items = "\n".join(f"{idx}. {item}" for idx, item in enumerate(materials, start=1))
    missing_text = "、".join(missing) if missing else "暂无明显资料缺口"

    risk_basis = "；".join(item["signal"] for item in signals) if signals else "当前资料不足，未识别明确风险信号"
    human_review = "建议客户经理人工复核"
    if level in {"L4", "L5"}:
        human_review = "建议风险经理参与或进入人工专项复核"

    return f"""# 授信走访前风险分析报告

## 1. 企业基本画像

- 企业名称：{case['enterprise_name']}
- 所属行业：{case['industry']}
- 所在地区：{case['region']}
- 授信类型：{case['credit_type']}
- 申请金额：{case['requested_amount']}
- 授信用途：{case['use_of_funds']}
- 经营概况：{case.get('known_background') or '暂未提供。'}

## 2. 授信背景摘要

{case['enterprise_name']}本次申请{case['credit_type']}，金额为{case['requested_amount']}，资金用途为{case['use_of_funds']}。基于当前资料，走访前应重点关注：{risk_basis}。本报告用于帮助客户经理在现场走访前形成问题清单和材料核验清单，不构成授信审批结论。

## 3. 资料完整性检查

| 资料类型 | 是否提供 | 评价 |
|---|---|---|
{completeness_table}

## 4. 走访前风险关注等级

- 等级：{level}
- 风险关注分：{score}
- 主要依据：{risk_basis}。
- 需要人工复核的事项：{human_review}。

## 5. 关键风险线索

| 风险维度 | 风险线索 | 依据 | 关注程度 |
|---|---|---|---|
{signal_rows}

## 6. 现场走访问询清单

| 问题 | 询问对象 | 核验目的 | 需要佐证材料 |
|---|---|---|---|
{question_rows}

## 7. 补充材料清单

{material_items}

## 8. 交叉验证建议

- 将财务报表中的收入、应收账款与主要客户合同、发票、验收单、回款凭证进行交叉验证。
- 将企业说明的资金用途与采购合同、付款计划、银行流水进行交叉验证。
- 将关联交易说明与关联企业清单、交易合同、发票和资金流水进行交叉验证。
- 将司法舆情事项与公开记录、企业说明、整改材料和银行内部风险记录进行交叉验证。

## 9. 数据缺口与置信度

- 当前数据缺口：{missing_text}
- 对分析结果的影响：资料缺口越多，风险等级越偏向“走访前关注”，但不代表最终授信判断。
- 置信度：{confidence_level}
- 后续建议：优先补齐缺失资料，并由客户经理或风险经理结合现场走访情况复核。

## 10. 合规提示与人工复核建议

本报告仅用于授信走访前准备和风险线索整理，不构成最终授信审批意见。涉及客户敏感数据、个人信息、征信数据和银行内部数据时，应在合规授权和受控环境中处理。客户经理、风险经理或审批人员必须进行人工复核。
"""


def write_summary(cases: list[dict[str, Any]], output_dir: Path) -> None:
    rows = []
    for case in cases:
        signals = detect_signals(case)
        score, level = score_and_level(case, signals)
        signal_names = "；".join(item["signal"] for item in signals) or "暂无明确风险线索"
        expected = case.get("expected_level", "未设置")
        match = "是" if expected == "未设置" or expected == level else "否"
        rows.append(
            f"| {case['case_id']} | {case['enterprise_name']} | {case['industry']} | {score} | {level} | {expected} | {match} | {signal_names} |"
        )

    change_rows = []
    for case in cases:
        for change in case.get("change_tests", []):
            change_rows.append(
                f"| {case['case_id']} | {case['enterprise_name']} | {change['name']} | {change['change']} | {change['expected_level_after_change']} | {change['reason']} |"
            )

    content = f"""# 模拟数据集评级对照表

## 1. 当前样例评级结果

| 编号 | 企业名称 | 行业 | 风险关注分 | 规则输出等级 | 预期等级 | 是否匹配 | 主要风险线索 |
|---|---|---|---:|---|---|---|---|
{chr(10).join(rows)}

## 2. 评级变化测试项

| 编号 | 企业名称 | 改动项 | 改动内容 | 改动后预期等级 | 业务原因 |
|---|---|---|---|---|---|
{chr(10).join(change_rows)}
"""
    (output_dir / "simulation_summary.md").write_text(content, encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data_file = ROOT / "data" / "demo_enterprises.json"
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        data_file = candidate if candidate.is_absolute() else ROOT / candidate
    cases = json.loads(data_file.read_text(encoding="utf-8"))
    for case in cases:
        report = render_report(case)
        output_file = OUTPUT_DIR / f"demo_report_{case['case_id']}_{case['enterprise_name']}.md"
        output_file.write_text(report, encoding="utf-8")
        print(f"已生成：{output_file}")
    write_summary(cases, OUTPUT_DIR)
    print(f"已生成：{OUTPUT_DIR / 'simulation_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
