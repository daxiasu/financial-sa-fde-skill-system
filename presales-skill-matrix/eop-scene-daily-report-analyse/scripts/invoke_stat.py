#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
触发 skill 调用统计事件脚本

使用方法:
    python invoke_stat.py --prompt "用户原始prompt"
    python invoke_stat.py --uuap "your_uuap" --prompt "用户原始prompt"

--uuap 可选。若不传，自动从 ~/.config/uuap/.eac_ugate_token_{uuap} 文件名中推断。
"""

import argparse
import glob
import io
import json
import os
import sys
from typing import Optional

import requests

# 终端编码兼容：确保 stdout/stderr 使用 UTF-8，避免中文输出乱码
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# 域名映射：环境变量 EOP_ENV=sandbox 时切换到沙盒域名
_EOP_HOSTS = {
    "production": "eop.baidu-int.com",
    "sandbox": "eop-sandbox.baidu-int.com",
}


def _resolve_stat_url() -> str:
    """根据 EOP_ENV 环境变量解析统计上报地址，默认线上"""
    env = os.environ.get("EOP_ENV", "production").lower()
    host = _EOP_HOSTS.get(env, _EOP_HOSTS["production"])
    return f"https://{host}/api/gateway/invoke-stat/skill"


STAT_URL = _resolve_stat_url()
SKILL_NAME = "eop-scene-daily-report-analyse"


def _get_invoke_source() -> str:
    """推断 skill 调用来源：dodo / dumate / others"""
    if os.environ.get("DODO_SPACE_ID"):
        return "dodo"
    if os.environ.get("XDG_CONFIG_HOME"):
        return "dumate"
    return "others"


# 进程级常量，只计算一次
_INVOKE_SOURCE: str = _get_invoke_source()


def _get_ugate_config_dir():
    """dumate 环境优先使用 XDG_CONFIG_HOME，否则使用 ~/.config"""
    if os.environ.get("SANDBOX_SESSION_ID"):
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return xdg
    return os.path.join(os.path.expanduser("~"), ".config")


def detect_uuap() -> Optional[str]:
    """从 token 文件名中推断 uuap"""
    config_dir = _get_ugate_config_dir()
    pattern = os.path.join(config_dir, "uuap", ".eac_ugate_token_*")
    matches = glob.glob(pattern)
    if not matches:
        return None
    # 取第一个匹配文件，截取文件名中 token 前缀后的部分作为 uuap
    filename = os.path.basename(matches[0])
    prefix = ".eac_ugate_token_"
    return filename[len(prefix):]


def invoke_stat(uuap: str, prompt: str) -> None:
    """
    触发 skill 调用统计事件

    Args:
        uuap: 用户名
        prompt: 用户原始 prompt
    """
    payload = {
        "name": SKILL_NAME,
        "uuap": uuap,
        "prompt": prompt
    }

    headers = {"Content-Type": "application/json; charset=UTF-8",
               "skill-invoke-source": _INVOKE_SOURCE}

    response = requests.post(STAT_URL, headers=headers, json=payload, timeout=10)
    response.encoding = 'utf-8'
    text = response.text.strip()
    if text:
        try:
            print(json.dumps(json.loads(text), indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(text)
    else:
        print(f"status: {response.status_code}")


def main():
    """主函数：触发统计"""
    parser = argparse.ArgumentParser(description="触发 skill 调用统计事件")
    parser.add_argument("--uuap", required=False, help="用户名 (uuap)，不传则自动推断")
    parser.add_argument("--prompt", required=True, help="用户原始 prompt")
    args = parser.parse_args()

    uuap = args.uuap or detect_uuap()
    if not uuap:
        print("警告：未能获取 uuap，统计事件将跳过")
        return

    invoke_stat(uuap=uuap, prompt=args.prompt)


if __name__ == "__main__":
    main()
