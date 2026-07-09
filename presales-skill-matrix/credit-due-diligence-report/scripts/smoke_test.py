#!/usr/bin/env python3
"""Check whether the demo due-diligence Skill package is structurally complete."""

from __future__ import annotations

from pathlib import Path
import sys


REQUIRED_FILES = [
    "SKILL.md",
    "references/due_diligence_rules.md",
    "references/report_template.md",
    "scripts/smoke_test.py",
    "credit-due-diligence-report-demo.html",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    if missing:
        print("失败：缺少必要文件：")
        for path in missing:
            print(f"- {path}")
        return 1

    print("通过：尽调 demo Skill 包必要文件均存在")
    return 0


if __name__ == "__main__":
    sys.exit(main())
