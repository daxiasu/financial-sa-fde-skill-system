#!/usr/bin/env python3
"""
基金经理话术增强生成器 v3 — 深度好氧版
目标：让人说的话更像真人、有逻辑、成段落、带专业分析
数据源: fund_managers_distilled.json (34,437条)
输出: fund_managers_speech_v3.json (按经理x基金扁平)
依赖: requests (DeepSeek API)
"""
import json, os, time, random, re
from datetime import datetime
from collections import defaultdict
import requests

# ═══════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════
# 使用相对于脚本位置的路径，增强跨平台兼容性
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DATA = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "data")
MANAGER_DATA = os.path.join(SKILL_DATA, "fund_managers_distilled.json")
OUTPUT_FILE = os.path.join(SKILL_DATA, "fund_managers_speech_v3.json")
CHECKPOINT = os.path.join(SKILL_DATA, "fund_advisor_v3_checkpoint.json")

# ⚠️ [已废弃] 本模块依赖 DeepSeek API，已被本地话术引擎替代
# 此处仅作占位符保留，请勿用于生产环境
from config import API_KEY, API_URL, MODEL
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

RATE_LIMIT   = 1.5       # 秒间隔防限流
REQUEST_TMO  = 30        # 单次请求超时(秒)

# ═══════════════════════════════════════════════════════
# DeepSeek API 调用
# ═══════════════════════════════════════════════════════
def call_deepseek(messages, max_tokens=1200, temperature=0.75):
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {
        "Authorization": "Bearer " + API_KEY,
        "Content-Type": "application/json",
    }
    for attempt in range(3):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=REQUEST_TMO)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            elif resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            else:
                return None
        except Exception:
            time.sleep(3 * (attempt + 1))
    return None

# ═══════════════════════════════════════════════════════
# Prompt 构建
# ═══════════════════════════════════════════════════════
def build_prompt(name, company, fund, style, years, sector, top_stocks, recent_views, strengths):
    stock_str = ""
    if top_stocks:
        names = [s.get("stock_name","") if isinstance(s,dict) else str(s) for s in top_stocks[:5]]
        names = [n for n in names if n]
        if names:
            stock_str = "当前重仓股包括：" + "、".join(names) + "。"

    view_str = ""
    if recent_views:
        raw_views = []
        if isinstance(recent_views, list):
            for v in recent_views:
                if isinstance(v, dict):
                    raw_views.extend(v.get("views", []))
                elif isinstance(v, str):
                    raw_views.append(v)
        elif isinstance(recent_views, str):
            raw_views = [recent_views]
        if raw_views:
            view_str = "最近季报/年报写道：" + "；".join(raw_views[:2])

    style_desc = {
        "成长型": f"从业{years:.0f}年，风格偏进攻，重点关注{sector}，追求长期资本增值。",
        "均衡型": f"从业{years:.0f}年，风格稳健，注重股债平衡，追求稳健回报。",
        "价值型": f"从业{years:.0f}年，风格偏防御，注重安全边际和股息回报。",
    }.get(style, f"从业{years:.0f}年，风格{style}。")

    return f"""你是{company}的基金经理{name}，正在与客户进行专业、友好的投资沟通。

【个人背景】
{style_desc}
你管理的基金是{fund}。
{stock_str}
{view_str}

【说话要求】
1. 亲切自然，像真人说话，不用"您好，我是XXX"这种念简历开场白
2. 每段2-4句，有逻辑连贯性，不是孤立句子堆砌
3. 提到个股/行业时有具体分析逻辑（估值/基本面/行业趋势）
4. 主动引导客户互动，用反问、设问、"你问我XXX"等方式
5. 说持仓时列出具体股票名称和占比
6. 分析行情时体现专业判断，不是泛泛表态
7. 成段落输出，不要列表格式

请按以下7个场景生成话术，段与段之间用空行分隔，每段150-300字：

【开场白】自然介绍自己，像老朋友聊天，不用念简历）
【市场看法】结合{sector}分析当前行情，要有具体逻辑）
【个股/行业分析】至少提到2-3只具体股票，从基本面/估值/行业趋势角度分析）
【持仓解答】告诉客户重仓了什么，列具体股票和占比）
【亏损安慰】共情+分析原因+引导持有，不要只说"长期持有"）
【盈利恭喜】祝贺+说明驱动因素+提示不要冲动）
【互动引导】主动抛出1-2个问题，让客户参与对话）

确保：自然亲切、有专业逻辑、成段落输出。
"""

# ═══════════════════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════════════════
def generate_speech_for_manager(m):
    name     = m.get("name", "")
    company  = m.get("company_name", "")
    fund     = m.get("current_fund_name", "在管基金")
    style    = m.get("investment_style", "均衡型")
    years    = float(m.get("tenure_years", 0))
    sector   = m.get("sector_description", m.get("sectors", [""])[0] if m.get("sectors") else "")
    top_stocks = m.get("top_stocks", [])
    recent_views = m.get("recent_views", [])
    suitable  = m.get("suitable_investors", "")
    inv_period= m.get("investment_period", "")

    prompt = build_prompt(name, company, fund, style, years, sector,
                          top_stocks, recent_views, m.get("strengths", []))

    raw = call_deepseek([
        {"role": "user", "content": prompt}
    ], max_tokens=1500, temperature=0.75)

    if not raw:
        return None

    # holdings 字符串
    holdings_text = ""
    if top_stocks:
        parts = []
        for i, s in enumerate(top_stocks[:5], 1):
            if isinstance(s, dict):
                n = s.get("stock_name", "")
                w = s.get("weight", 0)
                if n and w:
                    parts.append(f"{i}. {n}（占比 {w:.1f}%）")
        if parts:
            holdings_text = "你问我持仓，我直接跟你说。\n" + "\n".join(parts) + "\n老实说，基本面没什么大问题。"

    # 简单解析：从 raw 中提取各段
    sections = {"开场白":"", "市场看法":"", "个股/行业分析":"", "持仓解答":"",
                 "亏损安慰":"", "盈利恭喜":"", "互动引导":""}
    
    current = None
    buf = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            if current and buf:
                sections[current] = "\n".join(buf).strip()
                current = None
                buf = []
            continue
        hit = False
        for k in sections:
            if line.startswith("【") and k in line:
                if current and buf:
                    sections[current] = "\n".join(buf).strip()
                    buf = []
                current = k
                # 去掉标签
                idx = line.find("】")
                if idx >= 0:
                    buf = [line[idx+1:].strip()]
                else:
                    buf = [line.split(":",1)[-1].strip()] if ":" in line else []
                hit = True
                break
        if not hit:
            if current is not None:
                buf.append(line)

    if current and buf:
        sections[current] = "\n".join(buf).strip()

    return {
        "manager_id": m.get("manager_id", ""),
        "name": name,
        "company_name": company,
        "current_fund_name": fund,
        "current_fund_code": m.get("current_fund_code", ""),
        "investment_style": style,
        "tenure_years": years,
        "sector": sector,
        "intro": sections.get("开场白", ""),
        "market_view": sections.get("市场看法", ""),
        "stock_analysis": sections.get("个股/行业分析", ""),
        "holding_query": sections.get("持仓解答", "") or holdings_text,
        "loss_comfort_pct_10": sections.get("亏损安慰", ""),
        "gain_speech_pct_10": sections.get("盈利恭喜", ""),
        "interactive_prompt": sections.get("互动引导", ""),
        "suitable": f"适合{suitable}，投资周期{inv_period or '3-5年'}以上。" if suitable else "",
        "advice": _build_advice(style),
        "warning": _build_warning(style),
        "raw_llm_output": raw,
        "generated_at": datetime.now().isoformat(),
    }

def _build_advice(style):
    return {"成长型": "波动较大，建议用闲置资金配置，避免追涨杀跌，持有周期建议3年以上。",
            "价值型": "注重安全边际和股息回报，中长期持有体验更佳，建议至少2年。",
            }.get(style, "均衡配置，建议持有周期2-3年，分批买入效果更好。")

def _build_warning(style):
    return {"成长型": "高波动品种，短期回撤可能较大，请评估自身风险承受能力后再投资。",
            "价值型": "价值回归需要时间，请保持耐心，避免短期操作。",
            }.get(style, "市场有波动，请保持理性，闲置资金配置为宜。")

# ═══════════════════════════════════════════════════════
# 断点续传
# ═══════════════════════════════════════════════════════
def load_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"done_ids": [], "results": [], "errors": []}

def save_checkpoint(cp):
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(cp, f, ensure_ascii=False, indent=2)

# ═══════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 加载经理数据...")
    with open(MANAGER_DATA, "r", encoding="utf-8") as f:
        managers = json.load(f)["managers"]
    print(f"  总记录: {len(managers)}")

    # 过滤有效记录
    managers = [m for m in managers
                if m.get("name") and m.get("company_name")
                and (m.get("top_stocks") or m.get("sector_description"))]
    print(f"  有效记录: {len(managers)}")

    cp = load_checkpoint()
    done_ids = set(cp["done_ids"])
    results = cp["results"]
    errors = cp["errors"]

    todo = [m for m in managers if m.get("manager_id") not in done_ids]
    print(f"  待处理: {len(todo)}")

    if not todo:
        print("所有记录已处理完毕。")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始生成话术（DeepSeek API）...")
        for i, m in enumerate(todo):
            mid = m.get("manager_id", "")
            try:
                speech = generate_speech_for_manager(m)
                if speech:
                    results.append(speech)
                    done_ids.add(mid)
                else:
                    errors.append({"manager_id": mid, "name": m.get("name"), "reason": "LLM返回为空"})
                    done_ids.add(mid)
            except Exception as e:
                errors.append({"manager_id": mid, "name": m.get("name"), "reason": str(e)})
                done_ids.add(mid)

            if (i + 1) % 10 == 0:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] {i+1}/{len(todo)} | 成:{len(results)} 败:{len(errors)}")
                save_checkpoint({"done_ids": list(done_ids), "results": results, "errors": errors})

            time.sleep(RATE_LIMIT)

        save_checkpoint({"done_ids": list(done_ids), "results": results, "errors": errors})

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 写入输出文件...")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "meta": {
                    "total": len(results),
                    "failed": len(errors),
                    "generated_at": datetime.now().isoformat(),
                    "engine": "deepseek-v3-humanized",
                    "model": MODEL,
                },
                "speeches": results,
            }, f, ensure_ascii=False, indent=2)

        sz = os.path.getsize(OUTPUT_FILE) / 1024 / 1024
        print(f"  -> {OUTPUT_FILE} ({sz:.1f} MB)")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 完成！成功:{len(results)} 失败:{len(errors)}")
