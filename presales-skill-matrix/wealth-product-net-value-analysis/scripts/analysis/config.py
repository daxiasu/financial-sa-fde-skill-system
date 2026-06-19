"""
Fund Advisor 配置模块
统一管理所有环境变量和路径配置。
所有脚本应从此模块导入配置，禁止硬编码路径和凭证。

环境变量：
  DEEPSEEK_API_KEY     DeepSeek API 密钥（必须）
  DEEPSEEK_API_URL     API 地址（可选，默认 api.deepseek.com）
  DEEPSEEK_MODEL       模型名（可选，默认 deepseek-chat）
  DEEPSEEK_TIMEOUT     请求超时秒数（可选，默认 30）
  FUND_ADVISOR_BASE_DIR  技能根目录（可选，默认从本文件位置推断）

路径说明（2026-05-25优化）：
  所有脚本路径通过本模块的相对路径推断实现，禁止硬编码绝对路径。
  BASE_DIR: 技能根目录（即 fund-advisor 目录，scripts/analysis 向上三层）
  DATA_DIR: BASE_DIR / "data"
  SCRIPTS_ANALYSIS_DIR: BASE_DIR / "scripts" / "analysis"
  SCRIPTS_COLLECTION_DIR: BASE_DIR / "scripts" / "data_collection"
"""
import os
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────────────────
# 技能根目录：从 scripts/analysis 向上三层（scripts/analysis → scripts → fund-advisor）
_BASE_DIR = os.environ.get("FUND_ADVISOR_BASE_DIR")
if _BASE_DIR:
    BASE_DIR = Path(_BASE_DIR)
else:
    BASE_DIR = Path(__file__).parent.parent.parent

DATA_DIR = BASE_DIR / "data"
SCRIPTS_ANALYSIS_DIR = BASE_DIR / "scripts" / "analysis"
SCRIPTS_COLLECTION_DIR = BASE_DIR / "scripts" / "data_collection"

# ── DeepSeek API 配置 ─────────────────────────────────────────────────
# 默认使用占位符（离线模式），如需启用AI功能请在环境变量中设置真实的 API_KEY
API_KEY = os.getenv("DEEPSEEK_API_KEY") or "***"

API_URL = os.environ.get(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/v1/chat/completions"
)
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
REQUEST_TIMEOUT = int(os.environ.get("DEEPSEEK_TIMEOUT", "30"))
