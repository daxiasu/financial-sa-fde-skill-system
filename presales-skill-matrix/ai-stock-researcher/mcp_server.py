#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-stock-researcher MCP Server — A股智能投研工具
通过 MCP 协议暴露持仓导入/导出、股票研究、技术分析、情绪分析等工具，
让 Claude Code 可以直接调用股票研究员的核心功能。

使用方式（Claude Code 配置 mcpServers）:
{
  "mcpServers": {
    "ai-stock-researcher": {
      "command": "python",
      "args": ["D:/claude 开发/skill of me/ai-stock-researcher/mcp_server.py"],
      "env": {
        "PYTHONDONTWRITEBYTECODE": "1"
      }
    }
  }
}
"""
from __future__ import annotations

import json
import sys
import os
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR
sys.path.insert(0, str(SKILL_DIR / "scripts"))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    print("请安装 MCP SDK: pip install mcp", file=sys.stderr)
    sys.exit(1)

from stock_researcher.import_engine import StockImportEngine
from stock_researcher.industry_chain import (
    IndustryChainAnalyzer, AShareChainAnalyzer,
    get_preset_chain, list_presets,
    ChainNode, CompetitorProfile, SubstitutionProgress,
    StockRecommendation, DynamicAnalysis, ASignals,
)

engine = StockImportEngine()

server = Server("ai-stock-researcher")


# ==================== 持仓导入 ====================

@server.tool()
async def import_holdings_screenshot(image_path: str, client_id: str = "") -> str:
    """从截图OCR识别股票/基金持仓。支持中英文混合识别，自动区分股票和基金，
    解析代码、名称、数量、成本价、止盈止损比例。
    适用场景：客户发送了持仓页面截图。

    Args:
        image_path: 截图文件完整路径
        client_id: 客户姓名或ID（可选）
    """
    result = engine.import_from_screenshot(
        image_path, client_id=client_id if client_id else None
    )
    if result['success']:
        items = result['items']
        lines = [f"识别到 {len(items)} 条持仓:"]
        for item in items:
            itype = '股票' if item.get('item_type') == 'stock' else '基金'
            lines.append(
                f"  [{itype}] {item.get('code')} {item.get('name', '未知')} "
                f"数量:{item.get('shares', '?')} 成本:{item.get('cost', '?')}"
            )
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        return f"识别失败: {'; '.join(result['errors'])}"


@server.tool()
async def import_holdings_ppt(file_path: str, client_id: str = "") -> str:
    """从PPT幻灯片导入股票/基金持仓。解析PPT中的表格和文本框内容。
    适用场景：客户提供了PPT格式的资产配置或持仓分析报告。

    Args:
        file_path: PPT文件完整路径
        client_id: 客户姓名或ID（可选）
    """
    result = engine.import_from_ppt(
        file_path, client_id=client_id if client_id else None
    )
    if result['success']:
        items = result['items']
        lines = [f"从PPT识别到 {len(items)} 条持仓:"]
        for item in items:
            itype = '股票' if item.get('item_type') == 'stock' else '基金'
            lines.append(
                f"  [{itype}] {item.get('code')} {item.get('name', '未知')} "
                f"数量:{item.get('shares', '?')} 成本:{item.get('cost', '?')}"
            )
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        return f"导入失败: {'; '.join(result['errors'])}"


@server.tool()
async def import_holdings_docx(file_path: str, client_id: str = "") -> str:
    """从Word文档(.docx)导入股票/基金持仓。

    Args:
        file_path: Word文档完整路径
        client_id: 客户姓名或ID（可选）
    """
    result = engine.import_from_docx(
        file_path, client_id=client_id if client_id else None
    )
    if result['success']:
        items = result['items']
        lines = [f"从Word文档识别到 {len(items)} 条持仓:"]
        for item in items:
            itype = '股票' if item.get('item_type') == 'stock' else '基金'
            lines.append(
                f"  [{itype}] {item.get('code')} {item.get('name', '未知')} "
                f"数量:{item.get('shares', '?')} 成本:{item.get('cost', '?')}"
            )
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        return f"导入失败: {'; '.join(result['errors'])}"


@server.tool()
async def import_holdings_pdf(file_path: str, client_id: str = "") -> str:
    """从PDF文档导入股票/基金持仓。注意：扫描件请使用截图导入。

    Args:
        file_path: PDF文件完整路径
        client_id: 客户姓名或ID（可选）
    """
    result = engine.import_from_pdf(
        file_path, client_id=client_id if client_id else None
    )
    if result['success']:
        items = result['items']
        lines = [f"从PDF识别到 {len(items)} 条持仓:"]
        for item in items:
            itype = '股票' if item.get('item_type') == 'stock' else '基金'
            lines.append(
                f"  [{itype}] {item.get('code')} {item.get('name', '未知')} "
                f"数量:{item.get('shares', '?')} 成本:{item.get('cost', '?')}"
            )
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        return f"导入失败: {'; '.join(result['errors'])}"


@server.tool()
async def import_holdings_url(url: str, client_id: str = "",
                              username: str = "", password: str = "") -> str:
    """从浏览器链接抓取股票/基金持仓。支持东方财富、天天基金等平台。

    Args:
        url: 持仓页面URL
        client_id: 客户姓名或ID（可选）
        username: 登录用户名（可选）
        password: 登录密码（可选）
    """
    credentials = None
    if username:
        credentials = {"username": username, "password": password}

    result = engine.import_from_url(
        url,
        client_id=client_id if client_id else None,
        credentials=credentials
    )
    if result['success']:
        items = result['items']
        lines = [f"从链接抓取到 {len(items)} 条持仓:"]
        for item in items:
            itype = '股票' if item.get('item_type') == 'stock' else '基金'
            lines.append(
                f"  [{itype}] {item.get('code')} {item.get('name', '未知')} "
                f"价格:{item.get('price', item.get('nav', '?'))}"
            )
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        return f"抓取失败: {'; '.join(result['errors'])}"


# ==================== 持仓导出 ====================

@server.tool()
async def export_holdings_excel(client_id: str = "",
                                output_path: str = "") -> str:
    """导出客户持仓为Excel表格，包含持仓明细和汇总sheet。

    Args:
        client_id: 客户姓名或ID
        output_path: 输出路径（可选）
    """
    if client_id:
        items = engine.load_client_items(client_id)
        if not items:
            return f"客户「{client_id}」暂无持仓记录。"
    else:
        return "请提供 client_id 参数。"

    try:
        path = engine.export_to_excel(
            items,
            output_path=output_path if output_path else None,
            client_id=client_id
        )
        return f"Excel已生成！\n  客户: {client_id}\n  持仓: {len(items)}条\n  路径: {path}"
    except ImportError:
        return "需要安装 openpyxl: pip install openpyxl"
    except Exception as e:
        return f"导出失败: {str(e)}"


@server.tool()
async def export_holdings_csv(client_id: str = "",
                              output_path: str = "") -> str:
    """导出客户持仓为CSV文件。

    Args:
        client_id: 客户姓名或ID
        output_path: 输出路径（可选）
    """
    if client_id:
        items = engine.load_client_items(client_id)
        if not items:
            return f"客户「{client_id}」暂无持仓记录。"
    else:
        return "请提供 client_id 参数。"

    try:
        path = engine.export_to_csv(
            items,
            output_path=output_path if output_path else None,
            client_id=client_id
        )
        return f"CSV已生成！\n  客户: {client_id}\n  持仓: {len(items)}条\n  路径: {path}"
    except Exception as e:
        return f"导出失败: {str(e)}"


# ==================== 客户管理 ====================

@server.tool()
async def list_clients() -> str:
    """列出所有已导入持仓的客户及概览。"""
    clients = engine.list_clients()
    if not clients:
        return "暂无客户持仓记录。使用导入工具添加客户持仓。"

    lines = ["【客户持仓仓库】"]
    for client_id, info in clients.items():
        count = info.get('items_count', 0)
        value = info.get('total_value', 0)
        updated = info.get('last_updated', '')
        lines.append(f"  {client_id}    {count}条    ¥{value:,.2f}    {updated}")
    return '\n'.join(lines)


@server.tool()
async def get_client_holdings(client_id: str) -> str:
    """查看指定客户持仓详情，包括每只股票/基金的市值和盈亏。

    Args:
        client_id: 客户姓名或ID
    """
    items = engine.load_client_items(client_id)
    if not items:
        return f"客户「{client_id}」暂无持仓记录。"

    lines = [f"【{client_id} 持仓明细】共 {len(items)} 条"]
    total_cost = 0
    total_value = 0
    for item in items:
        itype = '股' if item.get('item_type') == 'stock' else '基'
        shares = item.get('shares', 0) or 0
        cost = item.get('cost', 0) or 0
        price = item.get('price') or item.get('nav') or cost
        market_value = shares * price
        cost_value = shares * cost
        profit = market_value - cost_value
        profit_pct = (profit / cost_value * 100) if cost_value > 0 else 0
        total_cost += cost_value
        total_value += market_value

        name = (item.get('name') or '')[:16]
        lines.append(
            f"  [{itype}] {item.get('code')} {name:<16s} "
            f"数量:{shares:>8,.0f} 成本:{cost:>8.2f} 现价:{price:>8.2f} "
            f"市值:{market_value:>12,.2f} 盈亏:{profit:>+10,.2f}({profit_pct:>+.1f}%)"
        )

    total_profit = total_value - total_cost
    total_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0
    lines.append(f"───")
    lines.append(f"  合计: 成本 ¥{total_cost:,.2f}  市值 ¥{total_value:,.2f}  "
                 f"盈亏 ¥{total_profit:+,.2f} ({total_pct:+.1f}%)")
    return '\n'.join(lines)


@server.tool()
async def get_import_history(client_id: str) -> str:
    """查看客户历史导入记录。

    Args:
        client_id: 客户姓名或ID
    """
    history = engine.get_import_history(client_id)
    if not history:
        return f"客户「{client_id}」暂无导入记录。"

    lines = [f"【{client_id} 导入历史】共 {len(history)} 次"]
    for record in history[:20]:
        lines.append(
            f"  {record.get('timestamp', '')}  来源:{record.get('source', '')}  "
            f"数量:{record.get('count', 0)}条"
        )
    return '\n'.join(lines)


@server.tool()
async def auto_import_file(file_path: str, client_id: str = "") -> str:
    """智能导入：根据文件扩展名自动选择导入方式。
    支持: .png/.jpg (截图OCR), .pptx (PPT), .docx (Word), .pdf (PDF)

    Args:
        file_path: 文件完整路径
        client_id: 客户姓名或ID（可选）
    """
    ext = Path(file_path).suffix.lower()
    cid = client_id if client_id else None

    if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif'):
        result = engine.import_from_screenshot(file_path, client_id=cid)
        method = "截图OCR"
    elif ext == '.pptx':
        result = engine.import_from_ppt(file_path, client_id=cid)
        method = "PPT导入"
    elif ext == '.docx':
        result = engine.import_from_docx(file_path, client_id=cid)
        method = "Word导入"
    elif ext == '.pdf':
        result = engine.import_from_pdf(file_path, client_id=cid)
        method = "PDF导入"
    else:
        return f"不支持的文件类型: {ext}。支持: .png/.jpg/.pptx/.docx/.pdf"

    if result.get('success'):
        items = result.get('items', [])
        lines = [f"{method}成功，识别到 {len(items)} 条持仓:"]
        for item in items:
            itype = '股票' if item.get('item_type') == 'stock' else '基金'
            lines.append(f"  [{itype}] {item.get('code')} {item.get('name', '未知')}")
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        errors = result.get('errors', ['未知错误'])
        return f"{method}失败: {'; '.join(errors)}"


# ==================== 股票研究 ====================

@server.tool()
async def analyze_stock(code: str, period: str = "short") -> str:
    """对指定股票进行全面分析（技术面+估值+三维预测）。
    支持短期(1-5日)、中期(20-60日)、长期(120+日)三个周期。

    Args:
        code: 6位股票代码，如 600519（贵州茅台）、000858（五粮液）
        period: 分析周期，可选 short/medium/long，默认 short
    """
    try:
        from stock_researcher.core.analyzer import StockResearcher

        researcher = StockResearcher()
        result = researcher.analyze_stock(code, period=period)

        if not result:
            return f"未能获取股票 {code} 的数据，请检查代码是否正确或网络是否可用。"

        tech = result.technical
        pred = result.prediction

        lines = [
            f"【{result.name} {code}】{period}期分析",
            f"",
            f"行情: 现价 {result.price}  涨跌 {result.change_pct}%",
        ]

        if tech:
            lines += [
                f"",
                f"技术指标:",
                f"  RSI(6): {tech.rsi6}  RSI(14): {tech.rsi14}",
                f"  MACD: DIF={tech.macd_dif} DEA={tech.macd_dea}",
                f"  均线: MA5={tech.ma5} MA20={tech.ma20} MA60={tech.ma60}",
                f"  技术评分: {tech.tech_score}",
            ]

        if pred:
            lines += [
                f"",
                f"三维预测评分: {pred.composite_score}/100",
                f"  情绪面: {pred.sentiment_score}  估值面: {pred.valuation_score}",
                f"  历史案例: {pred.historical_score}  技术面: {pred.technical_score}",
                f"操作建议: {pred.final_signal}",
            ]

        return '\n'.join(lines)
    except ImportError as e:
        return f"缺少依赖: {e}"
    except Exception as e:
        return f"分析失败: {str(e)}"


@server.tool()
async def get_stock_technical_indicators(code: str) -> str:
    """获取股票的技术指标详情：MA均线系统、RSI、MACD、布林带、ADX等。

    Args:
        code: 6位股票代码
    """
    try:
        from stock_researcher.core.technical import TechnicalAnalyzer
        ta = TechnicalAnalyzer()
        result = ta.analyze(code)

        if not result:
            return f"无法获取 {code} 的技术数据。"

        lines = [
            f"【{code} 技术指标】",
            f"",
            f"均线系统:",
            f"  MA5: {result.get('ma5', '?')}  MA10: {result.get('ma10', '?')}  MA20: {result.get('ma20', '?')}",
            f"  MA60: {result.get('ma60', '?')}  MA120: {result.get('ma120', '?')}",
            f"  排列: {result.get('ma_pattern', '?')}",
            f"",
            f"摆动指标:",
            f"  RSI(6): {result.get('rsi6', '?')}  RSI(14): {result.get('rsi14', '?')}  RSI(24): {result.get('rsi24', '?')}",
            f"  KDJ: K={result.get('kdj_k', '?')} D={result.get('kdj_d', '?')} J={result.get('kdj_j', '?')}",
            f"",
            f"趋势与波动:",
            f"  MACD: DIF={result.get('dif', '?')} DEA={result.get('dea', '?')} Hist={result.get('macd_hist', '?')}",
            f"  ADX: {result.get('adx', '?')}  {'趋势明显' if result.get('adx', 0) > 25 else '震荡整理'}",
            f"  布林带: 上轨={result.get('boll_upper', '?')} 中轨={result.get('boll_mid', '?')} 下轨={result.get('boll_lower', '?')}",
            f"  Hurst: {result.get('hurst', '?')}",
        ]
        return '\n'.join(lines)
    except ImportError as e:
        return f"缺少依赖: {e}"
    except Exception as e:
        return f"技术分析失败: {str(e)}"


@server.tool()
async def get_stock_sentiment(code: str) -> str:
    """分析股票的市场情绪，基于东方财富股吧和雪球的讨论内容。

    Args:
        code: 6位股票代码
    """
    try:
        sys.path.insert(0, str(SKILL_DIR / "scripts"))
        from stock_researcher.data.sentiment_forum_crawler import SentimentForumCrawler
        crawler = SentimentForumCrawler()
        result = crawler.analyze(code)

        if not result:
            return f"无法获取 {code} 的情绪数据。可能该股票讨论较少。"

        sentiment_score = result.get('sentiment_score', 0)
        sentiment_label = result.get('sentiment_label', '未知')
        bullish_ratio = result.get('bullish_ratio', 0)

        lines = [
            f"【{code} 市场情绪分析】",
            f"",
            f"情绪评分: {sentiment_score} ({sentiment_label})",
            f"多头比例: {bullish_ratio:.1%}",
            f"热门话题: {', '.join(result.get('hot_topics', ['无']))}",
            f"",
            f"情绪告警:",
        ]
        if bullish_ratio > 0.85:
            lines.append("  极度乐观 — 注意分批减仓")
        elif bullish_ratio < 0.15:
            lines.append("  极度悲观 — 关注超跌机会")
        elif sentiment_score > 50:
            lines.append("  偏乐观 — 持股观望")
        elif sentiment_score < -50:
            lines.append("  偏悲观 — 谨慎操作")
        else:
            lines.append("  中性 — 无异常信号")

        return '\n'.join(lines)
    except ImportError as e:
        return f"缺少依赖: {e}"
    except Exception as e:
        return f"情绪分析失败: {str(e)}"


@server.tool()
async def analyze_index(index_code: str = "") -> str:
    """分析大盘指数（上证、沪深300、创业板、科创50）。

    Args:
        index_code: 指数代码，可选: sh000001(上证) sh000300(沪深300) sz399006(创业板) sh000688(科创50)
                    不填则分析全部主要指数
    """
    try:
        from stock_researcher.index_analysis.indices import IndexAnalyzer
        analyzer = IndexAnalyzer()

        if index_code:
            result = analyzer.analyze_single(index_code)
            if result:
                return (
                    f"【{result.get('name')} {index_code}】\n"
                    f"点位: {result.get('price')}  涨跌: {result.get('change_pct')}%\n"
                    f"MA5: {result.get('ma5')}  MA20: {result.get('ma20')}  MA60: {result.get('ma60')}\n"
                    f"RSI: {result.get('rsi')}  MACD: {result.get('macd_signal')}\n"
                    f"趋势: {result.get('trend')}  情绪: {result.get('sentiment')}"
                )
            return f"无法获取指数 {index_code} 的数据。"

        # 分析全部主要指数
        results = analyzer.analyze_all()
        lines = ["【主要指数概览】", ""]
        for r in results:
            lines.append(
                f"  {r.get('name', ''):<10s} {r.get('price', '?'):>8s}  "
                f"{r.get('change_pct', '?'):>6s}%  {r.get('trend', '')}"
            )
        return '\n'.join(lines)
    except ImportError as e:
        return f"缺少依赖: {e}"
    except Exception as e:
        return f"指数分析失败: {str(e)}"


@server.tool()
async def track_stock(code: str, action: str = "add") -> str:
    """添加/移除/查看股票跟踪。跟踪后可以监控价格变动和止损止盈。

    Args:
        code: 6位股票代码
        action: 操作类型 — add(添加) / remove(移除) / check(检查) / list(列表)
    """
    try:
        from stock_researcher.tracker.portfolio import PortfolioTracker
        tracker = PortfolioTracker(data_dir=str(SKILL_DIR / "data"))

        if action == "add":
            tracker.add_stock(code)
            return f"已添加 {code} 到跟踪列表。"
        elif action == "remove":
            tracker.remove_stock(code)
            return f"已从跟踪列表移除 {code}。"
        elif action == "check":
            result = tracker.check_stock(code)
            if result:
                return (
                    f"【{code} 跟踪状态】\n"
                    f"现价: {result.get('price')}  涨跌: {result.get('change_pct')}%\n"
                    f"止损: {result.get('stop_loss')}  止盈: {result.get('take_profit')}\n"
                    f"信号: {result.get('signal', '正常')}\n"
                    f"建议: {result.get('advice', '继续持有')}"
                )
            return f"未找到 {code} 的跟踪数据。"
        elif action == "list":
            stocks = tracker.list_all()
            if not stocks:
                return "暂无跟踪股票。"
            lines = ["【跟踪列表】"]
            for s in stocks:
                lines.append(f"  {s.get('code')} {s.get('name', '')}  "
                            f"成本:{s.get('cost', '?')} 现价:{s.get('price', '?')}")
            return '\n'.join(lines)
        else:
            return f"未知操作: {action}。支持: add/remove/check/list"
    except ImportError as e:
        return f"缺少依赖: {e}"
    except Exception as e:
        return f"操作失败: {str(e)}"


@server.tool()
async def get_sector_analysis(sector_name: str = "") -> str:
    """分析行业板块的强弱和轮动信号。

    Args:
        sector_name: 板块名称，如 银行、医药生物、电子、新能源 等。不填则显示所有板块排行。
    """
    try:
        from stock_researcher.sector_analysis.sectors import SectorAnalyzer
        analyzer = SectorAnalyzer()

        if sector_name:
            result = analyzer.analyze_sector(sector_name)
            if result:
                return (
                    f"【{sector_name} 板块分析】\n"
                    f"平均涨跌: {result.avg_change_pct:.2f}%\n"
                    f"上涨/下跌: {result.up_count}/{result.down_count}\n"
                    f"资金净流入: {result.total_net_flow:.2f}万\n"
                    f"轮动信号: {result.rotation_signal}"
                )
            return f"未找到板块「{sector_name}」。"

        # 全板块排行
        results = analyzer.get_sector_ranking()
        lines = ["【板块强弱排行】", ""]
        for i, r in enumerate(results[:10], 1):
            lines.append(
                f"  {i:>2}. {r.name:<10s}  "
                f"涨跌:{r.avg_change_pct:>+6.2f}%  "
                f"资金:{r.total_net_flow:>+8.2f}万  "
                f"{r.signal}"
            )
        return '\n'.join(lines)
    except ImportError as e:
        return f"缺少依赖: {e}"
    except Exception as e:
        return f"板块分析失败: {str(e)}"


# ==================== 产业链分析 ====================

@server.tool()
async def list_industry_presets() -> str:
    """列出所有预设产业链名称。每条产业链包含上中下游节点结构。"""
    presets = list_presets()
    lines = ["【预设产业链列表】", ""]
    for name in presets:
        chain = get_preset_chain(name)
        up = " → ".join(chain["upstream"][:3])
        mid = " → ".join(chain["midstream"][:3])
        down = " → ".join(chain["downstream"][:3])
        lines.append(f"  {name}")
        lines.append(f"    上游: {up}")
        lines.append(f"    中游: {mid}")
        lines.append(f"    下游: {down}")
        lines.append("")
    return "\n".join(lines)


@server.tool()
async def analyze_industry_chain(
    industry: str,
    mode: str = "general"
) -> str:
    """分析产业链上下游格局。支持通用模式和A股专版模式。

    通用模式（general）六层框架：地图→价值分布→竞争格局→战略控制点→动态演化→投资判断
    A股模式（ashare）六层框架：地图(参与度)→价值(A股利润)→竞争矩阵→国产替代→动态→标的推荐

    Args:
        industry: 产业链名称，如 半导体、新能源汽车、光伏、AI芯片、医药、消费电子、军工、机器人
        mode: 分析模式，general(通用) 或 ashare(A股专版)
    """
    preset = get_preset_chain(industry)
    if not preset:
        return f"未找到「{industry}」的预设产业链。可用: {', '.join(list_presets())}"

    if mode == "ashare":
        analyzer = AShareChainAnalyzer()
        nodes = analyzer.build_chain_map(
            industry,
            [{"name": n, "participation": "🟡"} for n in preset["upstream"]],
            [{"name": n, "participation": "🟡"} for n in preset["midstream"]],
            [{"name": n, "participation": "🟡"} for n in preset["downstream"]]
        )
    else:
        analyzer = IndustryChainAnalyzer()
        nodes = analyzer.build_chain_map(
            industry, preset["upstream"], preset["midstream"], preset["downstream"]
        )

    # 构建基础结果
    from stock_researcher.industry_chain.chain_analyzer import ChainAnalysisResult
    import time
    result = ChainAnalysisResult(
        industry=industry,
        analysis_mode=mode,
        timestamp=time.strftime("%Y-%m-%d %H:%M"),
        nodes=nodes
    )

    return analyzer.format_report(result) + \
        "\n\n骨架已生成。使用 update_chain_node 补充各节点数据后可生成完整分析。"


@server.tool()
async def get_chain_preset_detail(industry: str) -> str:
    """查看指定产业链的详细节点结构。

    Args:
        industry: 产业链名称
    """
    preset = get_preset_chain(industry)
    if not preset:
        return f"未找到「{industry}」。可用: {', '.join(list_presets())}"

    lines = [f"【{industry} 产业链结构】", ""]
    level_names = {"upstream": "上游", "midstream": "中游", "downstream": "下游"}
    for level, nodes in preset.items():
        label = level_names.get(level, level)
        for i, node in enumerate(nodes):
            prefix = "└─" if i == len(nodes) - 1 else "├─"
            lines.append(f"  [{label}] {prefix} {node}")
    return "\n".join(lines)


# ==================== Web UI ====================

_web_server_thread = None

@server.tool()
async def launch_web_ui(port: int = 5003) -> str:
    """启动 AI 股票研究员 Web UI 仪表盘。
    包含：市场概览、股票分析、多智能体研究、板块分析四大模块。
    浏览器会自动打开 http://localhost:{port}

    Args:
        port: Web服务端口号，默认5003
    """
    global _web_server_thread
    import threading, time as _time
    if _web_server_thread and _web_server_thread.is_alive():
        return f"Web UI 已在运行: http://localhost:{port}"

    try:
        sys.path.insert(0, str(SCRIPT_DIR / "scripts"))
        from web_server import create_app
        app = create_app()
        def run():
            app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
        _web_server_thread = threading.Thread(target=run, daemon=True)
        _web_server_thread.start()
        _time.sleep(1)
        return f"Web UI 已启动！\n访问地址: http://localhost:{port}\n功能模块: 市场概览 | 股票分析 | 多智能体研究 | 板块分析"
    except Exception as e:
        return f"启动失败: {e}"


# ==================== 多智能体分析 ====================

@server.tool()
async def run_multi_agent_analysis(
    ticker: str,
    trade_date: str = "",
    llm_provider: str = "deepseek",
    quick_model: str = "deepseek-chat",
    deep_model: str = "deepseek-chat"
) -> str:
    """使用 TradingAgents 多智能体框架对A股进行深度分析。
    7位AI分析师（市场/情绪/新闻/基本面/政策/资金/解禁）→ 多空辩论 → 风控评估 → 最终决策。

    Args:
        ticker: 6位股票代码或中文股票名称，如 600519 或 贵州茅台
        trade_date: 分析日期 YYYY-MM-DD，默认今天
        llm_provider: LLM提供商，deepseek/openai/anthropic/qwen
        quick_model: 快速思考模型（分析师用）
        deep_model: 深度思考模型（经理/风控用）
    """
    if not trade_date:
        from datetime import date as _date
        trade_date = _date.today().strftime("%Y-%m-%d")

    try:
        sys.path.insert(0, str(SCRIPT_DIR / "scripts"))
        from multi_agent.default_config import DEFAULT_CONFIG
        from multi_agent.graph.trading_graph import TradingAgentsGraph

        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = llm_provider
        config["quick_think_llm"] = quick_model
        config["deep_think_llm"] = deep_model
        config["output_language"] = "Chinese"
        config["max_debate_rounds"] = 1
        config["max_risk_discuss_rounds"] = 1

        graph = TradingAgentsGraph(
            selected_analysts=["market", "social", "news", "fundamentals", "policy", "hot_money", "lockup"],
            config=config,
        )

        final_state, signal = graph.propagate(ticker, trade_date)

        lines = [
            f"【TradingAgents 多智能体分析】{ticker} {trade_date}",
            f"{'='*50}",
            f"",
            f"最终信号: {signal}",
            f"",
        ]

        report_keys = [
            ("market_report", "市场分析师"),
            ("sentiment_report", "社交情绪分析师"),
            ("news_report", "新闻分析师"),
            ("fundamentals_report", "基本面分析师"),
            ("policy_report", "政策分析师"),
            ("hot_money_report", "资金流向追踪"),
            ("lockup_report", "限售解禁监控"),
        ]

        for key, label in report_keys:
            content = final_state.get(key, "")
            if content:
                lines.append(f"--- {label} ---")
                lines.append(content[:500] + ("..." if len(content) > 500 else ""))
                lines.append("")

        debate = final_state.get("investment_debate_state", {})
        if debate.get("judge_decision"):
            lines.append("--- 研究员裁决 ---")
            lines.append(debate["judge_decision"][:500])
            lines.append("")

        if final_state.get("final_trade_decision"):
            lines.append("--- 最终决策 ---")
            lines.append(final_state["final_trade_decision"][:800])

        return '\n'.join(lines)
    except ImportError as e:
        return f"缺少依赖: {e}\n请安装: pip install langchain-core langchain-openai langgraph"
    except Exception as e:
        return f"分析失败: {type(e).__name__}: {e}"


# ==================== 主入口 ====================

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
