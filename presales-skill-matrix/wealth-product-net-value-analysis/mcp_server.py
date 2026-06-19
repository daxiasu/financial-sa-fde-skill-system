#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fund-advisor MCP Server — 基金投资智能顾问
通过 MCP 协议暴露持仓导入/导出、客户管理、组合分析等工具。

使用方式（配置 mcpServers）:
{
  "mcpServers": {
    "fund-advisor": {
      "command": "python",
      "args": ["D:/claude 开发/skill of me/fund-advisor/mcp_server.py"],
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

# 添加项目路径
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "scripts"))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    print("请安装 MCP SDK: pip install mcp", file=sys.stderr)
    sys.exit(1)

from client_manager.holdings_importer import HoldingsImporter

# 初始化导入引擎
importer = HoldingsImporter()

server = Server("fund-advisor")


# ==================== 持仓导入 ====================

@server.tool()
async def import_holdings_screenshot(image_path: str, client_id: str = "") -> str:
    """从截图OCR识别基金持仓信息。支持中英文混合识别，自动解析基金代码、名称、份额、成本价。
    适用场景：客户发送了基金持仓页面的手机截图或电脑截图。

    Args:
        image_path: 截图文件的完整路径，如 D:\\客户资料\\张先生持仓.png
        client_id: 客户姓名或ID（可选），如 "张先生"
    """
    result = importer.import_from_screenshot(
        image_path, client_id=client_id if client_id else None
    )
    if result['success']:
        items = result['holdings']
        lines = [f"识别到 {len(items)} 条基金持仓:"]
        for h in items:
            lines.append(
                f"  {h.get('fund_code')} {h.get('fund_name', '未知')} "
                f"份额:{h.get('shares', '?')} 成本:{h.get('cost', '?')}"
            )
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        return f"识别失败: {'; '.join(result['errors'])}"


@server.tool()
async def import_holdings_docx(file_path: str, client_id: str = "") -> str:
    """从Word文档(.docx)导入基金持仓信息。自动解析文档中的表格和文本段落。
    适用场景：客户提供了Word格式的基金持仓清单。

    Args:
        file_path: Word文档的完整路径，如 D:\\客户资料\\持仓明细.docx
        client_id: 客户姓名或ID（可选）
    """
    result = importer.import_from_docx(
        file_path, client_id=client_id if client_id else None
    )
    if result['success']:
        items = result['holdings']
        lines = [f"从Word文档识别到 {len(items)} 条基金持仓:"]
        for h in items:
            lines.append(
                f"  {h.get('fund_code')} {h.get('fund_name', '未知')} "
                f"份额:{h.get('shares', '?')} 成本:{h.get('cost', '?')}"
            )
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        return f"导入失败: {'; '.join(result['errors'])}"


@server.tool()
async def import_holdings_pdf(file_path: str, client_id: str = "") -> str:
    """从PDF文档导入基金持仓信息。支持文本型PDF和含表格的PDF。
    适用场景：客户提供了PDF格式的基金对账单或持仓报告。
    注意：扫描版PDF（图片型）请使用截图导入功能。

    Args:
        file_path: PDF文件的完整路径，如 D:\\客户资料\\对账单.pdf
        client_id: 客户姓名或ID（可选）
    """
    result = importer.import_from_pdf(
        file_path, client_id=client_id if client_id else None
    )
    if result['success']:
        items = result['holdings']
        lines = [f"从PDF识别到 {len(items)} 条基金持仓:"]
        for h in items:
            lines.append(
                f"  {h.get('fund_code')} {h.get('fund_name', '未知')} "
                f"份额:{h.get('shares', '?')} 成本:{h.get('cost', '?')}"
            )
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        return f"导入失败: {'; '.join(result['errors'])}"


@server.tool()
async def import_holdings_url(url: str, client_id: str = "",
                              username: str = "", password: str = "") -> str:
    """从浏览器链接抓取基金持仓信息。支持天天基金等平台的公开页面，
    也可处理需要登录的平台（提供用户名密码）。
    适用场景：客户提供了基金平台的持仓页面链接。

    Args:
        url: 持仓页面URL，如 https://fund.eastmoney.com/001924.html
        client_id: 客户姓名或ID（可选）
        username: 登录用户名（可选，仅需登录的平台需要）
        password: 登录密码（可选，仅需登录的平台需要）
    """
    credentials = None
    if username:
        credentials = {"username": username, "password": password}

    result = importer.import_from_url(
        url,
        client_id=client_id if client_id else None,
        credentials=credentials
    )
    if result['success']:
        items = result['holdings']
        lines = [f"从链接抓取到 {len(items)} 条基金持仓:"]
        for h in items:
            lines.append(
                f"  {h.get('fund_code')} {h.get('fund_name', '未知')} "
                f"净值:{h.get('current_nav', h.get('estimated_nav', '?'))}"
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
    """将客户持仓导出为Excel表格（.xlsx），包含格式化的持仓明细和汇总sheet。
    适用场景：需要生成客户持仓报表或打印存档。

    Args:
        client_id: 客户姓名或ID
        output_path: 输出文件路径（可选，默认自动生成到客户目录下）
    """
    if client_id:
        holdings = importer.load_client_holdings(client_id)
        if not holdings:
            return f"客户「{client_id}」暂无持仓记录。请先导入持仓数据。"
    else:
        return "请提供 client_id 参数指定客户。使用 list_clients 查看所有客户。"

    try:
        path = importer.export_to_excel(
            holdings,
            output_path=output_path if output_path else None,
            client_id=client_id
        )
        return (f"Excel文件已生成！\n"
                f"  客户: {client_id}\n"
                f"  持仓数: {len(holdings)}条\n"
                f"  文件路径: {path}")
    except ImportError:
        return "需要安装 openpyxl: pip install openpyxl"
    except Exception as e:
        return f"导出失败: {str(e)}"


@server.tool()
async def export_holdings_csv(client_id: str = "",
                              output_path: str = "") -> str:
    """将客户持仓导出为CSV文件，方便导入其他系统或Excel打开。
    适用场景：需要将持仓数据导入到其他系统或进行自定义分析。

    Args:
        client_id: 客户姓名或ID
        output_path: 输出文件路径（可选）
    """
    if client_id:
        holdings = importer.load_client_holdings(client_id)
        if not holdings:
            return f"客户「{client_id}」暂无持仓记录。请先导入持仓数据。"
    else:
        return "请提供 client_id 参数指定客户。"

    try:
        path = importer.export_to_csv(
            holdings,
            output_path=output_path if output_path else None,
            client_id=client_id
        )
        return (f"CSV文件已生成！\n"
                f"  客户: {client_id}\n"
                f"  持仓数: {len(holdings)}条\n"
                f"  文件路径: {path}")
    except Exception as e:
        return f"导出失败: {str(e)}"


# ==================== 客户管理 ====================

@server.tool()
async def list_clients() -> str:
    """列出所有已导入持仓的客户及其概览信息。
    返回每个客户的持仓数量、总市值和最后更新时间。
    """
    clients = importer.list_clients()
    if not clients:
        return "暂无客户持仓记录。使用导入工具开始添加客户持仓。"

    lines = ["【客户持仓仓库】"]
    for client_id, info in clients.items():
        count = info.get('holdings_count', 0)
        value = info.get('total_value', 0)
        updated = info.get('last_updated', '')
        lines.append(f"  {client_id}    {count}条    ¥{value:,.2f}    {updated}")
    return '\n'.join(lines)


@server.tool()
async def get_client_holdings(client_id: str) -> str:
    """查看指定客户的当前持仓详情，包括每只基金的代码、名称、份额、成本、市值和盈亏。

    Args:
        client_id: 客户姓名或ID
    """
    holdings = importer.load_client_holdings(client_id)
    if not holdings:
        return f"客户「{client_id}」暂无持仓记录。"

    lines = [f"【{client_id} 的持仓明细】共 {len(holdings)} 条"]
    total_cost = 0
    total_value = 0
    for h in holdings:
        shares = h.get('shares', 0) or 0
        cost = h.get('cost', 0) or 0
        nav = h.get('current_nav', cost)
        market_value = shares * nav
        cost_value = shares * cost
        profit = market_value - cost_value
        profit_pct = (profit / cost_value * 100) if cost_value > 0 else 0
        total_cost += cost_value
        total_value += market_value

        lines.append(
            f"  {h.get('fund_code')} {h.get('fund_name', '未知'):<20s} "
            f"份额:{shares:>10,.0f} 成本:{cost:>8.4f} "
            f"市值:{market_value:>12,.2f} 盈亏:{profit:>+10,.2f} ({profit_pct:>+.1f}%)"
        )

    total_profit = total_value - total_cost
    total_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0
    lines.append(f"───")
    lines.append(f"  合计: 总成本 ¥{total_cost:,.2f}  总市值 ¥{total_value:,.2f}  "
                 f"总盈亏 ¥{total_profit:+,.2f} ({total_pct:+.1f}%)")
    return '\n'.join(lines)


@server.tool()
async def get_import_history(client_id: str) -> str:
    """查看指定客户的历史导入记录。包括每次导入的时间、来源和持仓数量。

    Args:
        client_id: 客户姓名或ID
    """
    history = importer.get_import_history(client_id)
    if not history:
        return f"客户「{client_id}」暂无导入记录。"

    lines = [f"【{client_id} 的导入历史】共 {len(history)} 次"]
    for record in history[:20]:  # 最近20次
        ts = record.get('timestamp', '')
        source = record.get('source', '')
        count = record.get('count', 0)
        lines.append(f"  {ts}  来源:{source}  数量:{count}条")
    return '\n'.join(lines)


@server.tool()
async def auto_import_file(file_path: str, client_id: str = "") -> str:
    """智能导入：根据文件扩展名自动选择导入方式。
    支持: .png/.jpg/.jpeg (截图OCR), .docx (Word), .pdf (PDF)

    Args:
        file_path: 文件完整路径
        client_id: 客户姓名或ID（可选）
    """
    ext = Path(file_path).suffix.lower()
    cid = client_id if client_id else None

    if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.gif'):
        result = importer.import_from_screenshot(file_path, client_id=cid)
        method = "截图OCR识别"
    elif ext == '.docx':
        result = importer.import_from_docx(file_path, client_id=cid)
        method = "Word文档导入"
    elif ext == '.pdf':
        result = importer.import_from_pdf(file_path, client_id=cid)
        method = "PDF文档导入"
    else:
        return f"不支持的文件类型: {ext}。支持的格式: .png/.jpg/.docx/.pdf"

    if result.get('success'):
        items = result.get('holdings', [])
        if isinstance(items, list):
            items = items
        else:
            items = []
        lines = [f"{method}成功，识别到 {len(items)} 条持仓:"]
        for h in items:
            lines.append(
                f"  {h.get('fund_code', h.get('code', ''))} "
                f"{h.get('fund_name', h.get('name', '未知'))}"
            )
        if client_id:
            lines.append(f"已保存到客户「{client_id}」的持仓仓库。")
        return '\n'.join(lines)
    else:
        errors = result.get('errors', ['未知错误'])
        return f"{method}失败: {'; '.join(errors)}"


# ==================== Web UI ====================

_web_server_thread = None

@server.tool()
async def launch_web_ui(port: int = 5002) -> str:
    """启动基金顾问Web界面。在浏览器中访问 http://localhost:{port} 打开交互式仪表盘。
    功能包括：市场行情、持仓分析、基金查询、量化分析、新闻资讯、智能对话。

    Args:
        port: Web服务端口号，默认5002
    """
    global _web_server_thread
    import threading

    if _web_server_thread and _web_server_thread.is_alive():
        return f"Web UI 已在运行中，请访问 http://localhost:{port}"

    try:
        from web_server import create_app
        app = create_app()
        _web_server_thread = threading.Thread(
            target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True),
            daemon=True
        )
        _web_server_thread.start()
        return (f"Web UI 已启动！\n"
                f"  地址: http://localhost:{port}\n"
                f"  功能: 市场概览 | 持仓分析 | 基金查询 | 量化分析 | 资讯 | 智能对话\n"
                f"  数据源: akshare / 东财 / 新浪 / 腾讯 / 和讯")
    except Exception as e:
        return f"启动失败: {e}"


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
