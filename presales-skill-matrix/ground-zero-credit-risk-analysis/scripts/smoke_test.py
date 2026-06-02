#!/usr/bin/env python3
"""授信走访前风险分析 Skill 的最小冒烟测试。

该脚本用于检查 Skill 包结构是否完整，并对内置样例做一轮确定性规则评分。
它不调用大模型，也不依赖外部网络。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "SKILL.md",
    "references/risk_rules.md",
    "references/report_template.md",
    "references/test_cases.md",
    "data/demo_enterprises.json",
]


@dataclass
class Case:
    name: str
    signals: list[str]
    missing_categories: int = 0


WEIGHTS = {
    "经营性现金流为负": 15,
    "高应收账款": 12,
    "客户集中": 10,
    "关联交易": 10,
    "股东或法定代表人频繁变更": 15,
    "被执行记录": 25,
    "负面舆情": 18,
    "短期债务增加": 10,
    "资料严重不足": 21,
}


def level_for_score(score: int) -> str:
    if score <= 20:
        return "L1"
    if score <= 40:
        return "L2"
    if score <= 60:
        return "L3"
    if score <= 80:
        return "L4"
    return "L5"


def score_case(case: Case) -> tuple[int, str]:
    score = sum(WEIGHTS.get(signal, 0) for signal in case.signals)
    if case.missing_categories >= 5:
        score = max(score, WEIGHTS["资料严重不足"])
    score = min(score, 100)
    return score, level_for_score(score)


def check_required_files() -> list[str]:
    missing = []
    for file_name in REQUIRED_FILES:
        path = ROOT / file_name
        if not path.exists() or path.stat().st_size == 0:
            missing.append(file_name)
    return missing


def main() -> int:
    missing = check_required_files()
    if missing:
        print("失败：缺少必要文件：")
        for file_name in missing:
            print(f"- {file_name}")
        return 1

    cases = [
        Case(
            name="样例 A",
            signals=[
                "经营性现金流为负",
                "高应收账款",
                "客户集中",
                "关联交易",
            ],
        ),
        Case(name="样例 B", signals=[], missing_categories=7),
        Case(
            name="样例 C",
            signals=[
                "股东或法定代表人频繁变更",
                "被执行记录",
                "负面舆情",
                "短期债务增加",
                "经营性现金流为负",
            ],
        ),
    ]

    print("通过：必要文件均存在")
    print("确定性样例评分：")
    for case in cases:
        score, level = score_case(case)
        print(f"- {case.name}：风险关注分={score}，走访前风险关注等级={level}")

    expected_levels = {
        "样例 A": "L3",
        "样例 B": "L2",
        "样例 C": "L5",
    }
    failures = []
    for case in cases:
        _, level = score_case(case)
        if level != expected_levels[case.name]:
            failures.append(f"{case.name}：预期 {expected_levels[case.name]}，实际 {level}")

    if failures:
        print("失败：样例等级与预期不一致")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("通过：样例等级符合预期")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

