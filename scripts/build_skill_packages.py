#!/usr/bin/env python3
"""Build the web-facing Skill package index from real repository files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "skill_packages.json"

PACKAGE_DEFINITIONS = {
    "B-L2-025": {
        "root": "presales-skill-matrix/ground-zero-credit-risk-analysis/",
        "name": "ground-zero-credit-risk-analysis",
        "summary": "授信走访前风险分析 Skill。文件清单由仓库真实文件生成。",
        "coreFiles": [
            {"path": "SKILL.md", "note": "核心技能定义文件"},
            {"path": "references/risk_rules.md", "note": "规则文件"},
        ],
        "demoFiles": [
            {"path": "授信风险分析工作台Demo.html", "note": "可打开的本地演示页面"},
        ],
    },
    "B-L2-026": {
        "root": "presales-skill-matrix/post-loan-risk-monitoring/",
        "name": "post-loan-risk-monitoring",
        "summary": "贷后风险监测 Skill。文件清单由仓库真实文件生成。",
        "coreFiles": [
            {"path": "SKILL.md", "note": "核心技能定义文件"},
            {"path": "references/monitoring_rules.md", "note": "规则文件"},
        ],
        "demoFiles": [
            {"path": "贷后风险监测工作台Demo.html", "note": "可打开的本地演示页面"},
        ],
    },
    "dumate-equity-industry-research": {
        "root": "presales-skill-matrix/ai-stock-researcher/",
        "name": "ai-stock-researcher",
        "summary": "AI股票研究员 Skill。文件清单来自同事提供的真实 Skill 包。",
        "coreFiles": [
            {"path": "SKILL.md", "note": "核心技能定义文件"},
            {"path": "README.md", "note": "使用说明与能力边界"},
            {"path": "requirements.txt", "note": "依赖清单"},
            {"path": "_meta.json", "note": "Skill 元数据"},
        ],
        "supportFiles": [
            {"path": "mcp_server.py", "note": "MCP Server 集成入口"},
            {"path": "scripts/web_server.py", "note": "Web UI 服务入口"},
            {"path": "scripts/stock_researcher.py", "note": "CLI 分析入口"},
            {"path": "scripts/sector_forecast.py", "note": "板块轮动分析脚本"},
            {"path": "scripts/run_full_daily.py", "note": "每日研究任务脚本"},
            {"path": "pkg/recommendation_engine.py", "note": "多维推荐评分引擎"},
            {"path": "pkg/research_cn.py", "note": "A股研究数据源适配"},
            {"path": "pkg/news_analyzer.py", "note": "新闻舆情分析"},
            {"path": "pkg/fund_analyzer.py", "note": "基金与产品分析"},
            {"path": "pkg/portfolio_tracker.py", "note": "持仓跟踪"},
            {"path": "scripts/stock_researcher/industry_chain/chain_analyzer.py", "note": "产业链分析"},
            {"path": "templates/index.html", "note": "原包自带 Web UI 模板"},
        ],
        "demoFiles": [
            {"path": "AI股票投研工作台Demo.html", "note": "可打开的本地演示页面"},
        ],
    },
    "dumate-wealth-product-interpretation": {
        "root": "presales-skill-matrix/wealth-product-net-value-analysis/",
        "name": "fund-advisor",
        "summary": "基金投资AI客户经理 Skill。文件清单来自同事提供的真实 Skill 包，并配套财富产品净值走势 Demo。",
        "coreFiles": [
            {"path": "SKILL.md", "note": "核心技能定义文件"},
            {"path": "requirements.txt", "note": "依赖清单"},
            {"path": "pyproject.toml", "note": "Python 项目配置"},
            {"path": "_meta.json", "note": "Skill 元数据"},
        ],
        "supportFiles": [
            {"path": "mcp_server.py", "note": "MCP Server 集成入口"},
            {"path": "scripts/web_server.py", "note": "Web UI 服务入口"},
            {"path": "scripts/analysis/fund_quant_analyzer.py", "note": "基金量化分析"},
            {"path": "scripts/analysis/comparison_engine.py", "note": "产品/基金对比引擎"},
            {"path": "scripts/analysis/portfolio_analyzer.py", "note": "投资组合分析"},
            {"path": "scripts/analysis/fund_advisor_speech.py", "note": "投顾沟通话术生成"},
            {"path": "scripts/client_manager/conversation_engine.py", "note": "客户对话引擎"},
            {"path": "scripts/client_manager/holdings_importer.py", "note": "持仓导入识别"},
            {"path": "scripts/client_manager/report_generator.py", "note": "客户报告生成"},
            {"path": "scripts/data_collection/eastmoney_collector.py", "note": "东方财富数据采集"},
            {"path": "scripts/data_collection/amac_collector.py", "note": "基金业协会数据采集"},
            {"path": "references/database_schema.md", "note": "数据结构说明"},
            {"path": "references/eastmoney_api.md", "note": "东方财富接口说明"},
            {"path": "references/amac_api.md", "note": "基金业协会接口说明"},
            {"path": "templates/index.html", "note": "原包自带 Web UI 模板"},
        ],
        "demoFiles": [
            {"path": "wealth-product-net-value-analysis-demo.html", "note": "可打开的本地演示页面"},
        ],
    },
}


def existing_files(root: Path, files: list[dict[str, str]]) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    for item in files:
        path = item["path"]
        if (root / path).is_file():
            kept.append(item)
    return kept


def build_packages() -> dict[str, object]:
    packages: dict[str, object] = {}
    for skill_id, definition in PACKAGE_DEFINITIONS.items():
        root_rel = definition["root"]
        root = ROOT / root_rel
        if not root.is_dir():
            continue

        core_files = existing_files(root, definition.get("coreFiles", []))
        if not any(item["path"] == "SKILL.md" for item in core_files):
            continue

        demo_files = existing_files(root, definition.get("demoFiles", []))
        support_files = existing_files(root, definition.get("supportFiles", []))
        packages[skill_id] = {
            "root": root_rel,
            "name": definition["name"],
            "summary": definition["summary"],
            "coreFiles": core_files,
            "supportFiles": support_files,
            "demoFiles": demo_files,
            "generatedFrom": "real-filesystem-scan",
        }

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "packages": packages,
    }


def main() -> None:
    output = DEFAULT_OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_packages(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
