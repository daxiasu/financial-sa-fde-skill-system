"""自包含爬虫工具集（零第三方依赖）

可用数据源（已验证 2026-05-18）:
  腾讯行情API: https://qt.gtimg.cn/q=sh600519,sz000001 (GBK编码，必须.decode("gbk"))
  天天基金净值: https://fundgz.1234567.com.cn/js/110022.js?rt=1 (JSONP格式，UTF-8)
  东方财富首页: https://finance.eastmoney.com/ (UTF-8，需字符串查找法提取新闻)
  凤凰财经首页: https://finance.ifeng.com/ (UTF-8，需字符串查找法提取新闻)
  新浪财经首页: https://finance.sina.com.cn/ (UTF-8，需字符串查找法提取新闻)
  同花顺首页: https://www.10jqka.com.cn/ (UTF-8)
  东方财富 push2 API: 需要特殊认证，已失效
  新浪hq行情: Referer验证，已失效
  东方财富搜索so.eastmoney.com: 返回HTML页面而非JSON

编码注意（2026-05-18修正）:
  - 腾讯API: 必须GBK解码
  - 天天基金: UTF-8
  - 其他财经站（新浪/凤凰/东财/同花顺）: 全部是UTF-8
  - safe_request 统一返回bytes，由调用方负责解码
  - detect_encoding(data): 优先UTF-8，自动降级GBK
"""

import json, time, urllib.request, urllib.error, random, re
from pathlib import Path
from datetime import datetime

def today_str():
    return datetime.now().strftime("%Y%m%d")

def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def detect_encoding(data):
    """自动检测HTML编码，返回解码后字符串。优先UTF-8，失败则降级GBK。"""
    if not isinstance(data, bytes):
        return data
    sample = data[:500]
    try:
        sample_str = sample.decode("ascii", errors="ignore")
    except:
        sample_str = ""
    m = re.search(r"<meta[^>]+charset=([^\s>]+)", sample_str, re.I)
    if m:
        charset = m.group(1).strip().lower()
        # 去掉首尾引号和空白
        for q in ('"', "'", " "):
            charset = charset.strip(q)
        if charset in ("gbk", "gb2312", "gb18030"):
            return data.decode(charset, errors="replace")
        if "utf" in charset:
            return data.decode("utf-8", errors="replace")
    try:
        data.decode("utf-8", errors="strict")
        return data.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        pass
    for enc in ("gbk", "gb2312", "gb18030"):
        try:
            return data.decode(enc, errors="replace")
        except:
            pass
    return data.decode("utf-8", errors="replace")

def safe_request(url, headers=None, timeout=10, retries=3, delay=2):
    """带重试的HTTP请求，优雅降级。返回bytes或None。"""
    h = headers or {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://finance.qq.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["time", "timeout", "refused", "connection", "resolve"]):
                if attempt < retries - 1:
                    time.sleep(delay * (2 ** attempt) + random.uniform(0, 1))
                    continue
            return None
    return None

def fetch_json(url, headers=None, timeout=10):
    """获取JSON响应（自动解码）。"""
    data = safe_request(url, headers=headers, timeout=timeout)
    if not data:
        return {}
    text = detect_encoding(data)
    try:
        return json.loads(text)
    except:
        return {}

def extract_codes(text):
    """从文本中提取A股股票代码"""
    codes = re.findall(r"\b(\d{6})\b", text)
    valid = [c for c in codes if c.startswith(("0","3","6"))]
    return list(dict.fromkeys(valid))

def parse_date(date_str):
    """解析多种日期格式"""
    for fmt in ["%Y-%m-%d","%Y/%m/%d","%Y%m%d","%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            pass
    return None
