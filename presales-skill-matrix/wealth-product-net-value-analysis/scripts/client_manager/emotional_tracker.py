"""
投资心态跟踪器 v1.0
跟踪客户的情绪变化，分析亏损/盈利原因，生成调整建议，及时提醒客户调整投资
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"


class EmotionalTracker:
    """投资心态跟踪器"""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        self.emotions_path = self.data_dir / 'emotional_records.json'
        self.alerts_path = self.data_dir / 'emotional_alerts.json'
        self.emotions = self._load_emotions()
        self.alerts = self._load_alerts()

    def _load_emotions(self) -> dict:
        """加载情绪记录"""
        try:
            if self.emotions_path.exists():
                with open(self.emotions_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_emotions(self):
        """保存情绪记录"""
        try:
            with open(self.emotions_path, 'w', encoding='utf-8') as f:
                json.dump(self.emotions, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_alerts(self) -> dict:
        """加载告警记录"""
        try:
            if self.alerts_path.exists():
                with open(self.alerts_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_alerts(self):
        """保存告警记录"""
        try:
            with open(self.alerts_path, 'w', encoding='utf-8') as f:
                json.dump(self.alerts, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def record_emotion(self, user_id: str, emotion_data: dict) -> dict:
        """
        记录用户情绪变化

        Args:
            user_id: 用户ID
            emotion_data: 情绪数据，包含：
                - emotion: 情绪类型（焦虑、恐惧、贪婪、平静、乐观等）
                - cause: 原因（亏损、盈利、市场波动等）
                - intensity: 强度 1-10
                - timestamp: 时间戳（可选，自动使用当前时间）

        Returns:
            dict: 情绪分析结果
        """
        if user_id not in self.emotions:
            self.emotions[user_id] = []

        record = {
            'timestamp': emotion_data.get('timestamp', datetime.now().isoformat()),
            'emotion': emotion_data.get('emotion', '未知'),
            'cause': emotion_data.get('cause', ''),
            'intensity': emotion_data.get('intensity', 5),
            'profit_pct': emotion_data.get('profit_pct'),  # 当前盈亏百分比
            'notes': emotion_data.get('notes', '')
        }

        self.emotions[user_id].append(record)

        # 限制记录数量（保留最近100条）
        if len(self.emotions[user_id]) > 100:
            self.emotions[user_id] = self.emotions[user_id][-100:]

        self._save_emotions()

        # 生成分析和建议
        analysis = self.analyze_emotion_change(user_id)

        return analysis

    def analyze_emotion_change(self, user_id: str) -> dict:
        """分析用户情绪变化"""
        if user_id not in self.emotions or len(self.emotions[user_id]) == 0:
            return {'status': 'no_records', 'message': '暂无情绪记录'}

        records = self.emotions[user_id]
        latest = records[-1]

        # 计算情绪趋势
        analysis = {
            'latest_emotion': latest['emotion'],
            'latest_timestamp': latest['timestamp'],
            'intensity': latest['intensity'],
            'cause': latest['cause'],
            'trend': self._calculate_trend(user_id),
            'warning': self._check_warning(latest),
            'suggestion': self._generate_suggestion(latest)
        }

        return analysis

    def _calculate_trend(self, user_id: str) -> str:
        """计算情绪趋势"""
        records = self.emotions[user_id]
        if len(records) < 2:
            return 'stable'

        recent = records[-3:]  # 最近3条

        # 计算平均强度变化
        intensities = [r.get('intensity', 5) for r in recent]

        if len(intensities) >= 2:
            change = intensities[-1] - intensities[0]
            if change > 2:
                return 'worsening'  # 情绪恶化
            elif change < -2:
                return 'improving'  # 情绪好转
        return 'stable'

    def _check_warning(self, latest_record: dict) -> Optional[str]:
        """检查是否需要告警"""
        emotion = latest_record.get('emotion', '')
        intensity = latest_record.get('intensity', 5)
        cause = latest_record.get('cause', '')

        # 高强度负面情绪
        if intensity >= 8 and emotion in ['焦虑', '恐惧', '崩溃']:
            return 'HIGH_INTENSITY_NEGATIVE'

        # 持续亏损导致的情绪波动
        if '亏' in cause and intensity >= 7:
            return 'LOSS_INDUCED_ANXIETY'

        # 贪婪信号
        if emotion == '贪婪' and intensity >= 7:
            return 'GREED_SIGNAL'

        return None

    def _generate_suggestion(self, latest_record: dict) -> str:
        """生成调整建议"""
        emotion = latest_record.get('emotion', '')
        intensity = latest_record.get('intensity', 5)
        cause = latest_record.get('cause', '')

        suggestions = []

        # 基于情绪类型的建议
        if emotion in ['焦虑', '恐惧', '崩溃']:
            if intensity >= 7:
                suggestions.append("我理解你现在很难受，但建议先冷静下来，不要在情绪激动时做决定。")
                suggestions.append("可以考虑暂时不看账户，给自己的情绪一个缓冲期。")
            else:
                suggestions.append("波动期有些焦虑是正常的，但长期投资需要保持理性。")

        if emotion == '贪婪':
            suggestions.append("看到行情好时要保持清醒，不要被贪念左右决策。")
            suggestions.append("建议分批减仓，锁定部分收益，不要一次全部抛出。")

        if emotion == '平静' or emotion == '乐观':
            suggestions.append("保持这种平和的心态很重要，继续坚持自己的投资逻辑。")

        # 基于原因的建议
        if '亏' in cause:
            suggestions.append("亏损时最重要的是分析原因，不要单纯因为亏损就割肉。")
            suggestions.append("可以考虑是否需要调整仓位，让组合更加均衡。")

        if '盈利' in cause:
            suggestions.append("恭喜你！但达到目标收益后要学会止盈。")
            suggestions.append("可以考虑分批卖出，锁定利润。")

        return " ".join(suggestions) if suggestions else "保持理性投资，有问题随时联系我。"

    def get_emotion_analysis(self, user_id: str) -> str:
        """获取情绪分析报告（格式化）"""
        if user_id not in self.emotions or len(self.emotions[user_id]) == 0:
            return "你还没有情绪记录。我会持续关注你的投资心态变化。"

        records = self.emotions[user_id]
        latest = records[-1]

        lines = []
        lines.append("\n【投资心态分析报告】")
        lines.append("")

        # 最新情绪
        lines.append(f"最近情绪：{latest['emotion']}")
        lines.append(f"发生时间：{latest['timestamp']}")
        lines.append(f"诱因：{latest.get('cause', '未记录')}")
        lines.append(f"强度：{'❤️' * min(latest.get('intensity', 5), 5)}")
        lines.append("")

        # 趋势分析
        trend = self._calculate_trend(user_id)
        trend_desc = {
            'stable': '情绪保持稳定',
            'improving': '情绪有所好转',
            'worsening': '情绪趋于负面'
        }
        lines.append(f"趋势：{trend_desc.get(trend, '稳定')}")
        lines.append("")

        # 告警检查
        warning = self._check_warning(latest)
        if warning:
            lines.append("⚠️ 告警提示：")
            warning_msgs = {
                'HIGH_INTENSITY_NEGATIVE': '你目前的负面情绪较强，建议先冷静，避免冲动决策。',
                'LOSS_INDUCED_ANXIETY': '亏损带来的焦虑较强，建议重新评估持仓和风险承受能力。',
                'GREED_SIGNAL': '贪念信号较强，注意不要追高，建议分批减仓。'
            }
            lines.append(f"  {warning_msgs.get(warning, '')}")
            lines.append("")

        # 建议
        suggestion = self._generate_suggestion(latest)
        lines.append("💡 建议：")
        lines.append(f"  {suggestion}")
        lines.append("")

        return "\n".join(lines)

    def daily_check(self, user_id: str, holdings: list) -> list:
        """
        每日检查 - 检查是否需要发送提醒

        Args:
            user_id: 用户ID
            holdings: 用户持仓列表

        Returns:
            list: 需要提醒的列表
        """
        alerts = []

        if user_id not in self.emotions or len(self.emotions[user_id]) == 0:
            return alerts

        records = self.emotions[user_id]
        latest = records[-1]

        # 检查是否需要提醒
        warning = self._check_warning(latest)
        if warning:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'warning_type': warning,
                'emotion': latest['emotion'],
                'intensity': latest['intensity'],
                'cause': latest.get('cause', ''),
                'message': self._generate_alert_message(warning, latest)
            }
            alerts.append(alert)

            # 保存告警
            if user_id not in self.alerts:
                self.alerts[user_id] = []
            self.alerts[user_id].append(alert)
            self._save_alerts()

        return alerts

    def _generate_alert_message(self, warning: str, latest_record: dict) -> str:
        """生成告警消息"""
        messages = {
            'HIGH_INTENSITY_NEGATIVE': (
                f"检测到您当前情绪波动较大（{latest_record['emotion']}，强度{intensity}）。"
                f"建议先冷静一下，不要在情绪激动时做投资决策。"
            ),
            'LOSS_INDUCED_ANXIETY': (
                f"亏损可能给您带来了较大的心理压力。"
                f"建议我们一起分析一下持仓情况，看看是否需要调整。"
            ),
            'GREED_SIGNAL': (
                f"检测到您可能有追高的倾向。"
                f"建议不要被行情左右，可以考虑分批减仓锁定收益。"
            )
        }
        return messages.get(warning, "我注意到您最近情绪有些波动，有什么需要帮忙的吗？")

    def get_recent_emotions(self, user_id: str, days: int = 7) -> list:
        """获取最近的情绪记录"""
        if user_id not in self.emotions:
            return []

        cutoff = datetime.now().timestamp() - days * 86400
        recent = []

        for record in reversed(self.emotions[user_id]):
            timestamp = datetime.fromisoformat(record['timestamp']).timestamp()
            if timestamp >= cutoff:
                recent.append(record)
            else:
                break

        return recent

    def clear_old_records(self, user_id: str, days: int = 30):
        """清除旧记录"""
        if user_id not in self.emotions:
            return

        cutoff = datetime.now().timestamp() - days * 86400
        filtered = []

        for record in self.emotions[user_id]:
            timestamp = datetime.fromisoformat(record['timestamp']).timestamp()
            if timestamp >= cutoff:
                filtered.append(record)

        self.emotions[user_id] = filtered
        self._save_emotions()


def main():
    """测试"""
    tracker = EmotionalTracker()

    user_id = "test_user"

    print("=== 投资心态跟踪器测试 ===\n")

    # 记录情绪
    print("记录焦虑情绪...")
    result = tracker.record_emotion(user_id, {
        'emotion': '焦虑',
        'cause': '亏损15%',
        'intensity': 7,
        'profit_pct': -15
    })
    print(f"分析结果: {result}")
    print()

    # 记录乐观情绪
    print("记录乐观情绪...")
    result = tracker.record_emotion(user_id, {
        'emotion': '乐观',
        'cause': '盈利5%',
        'intensity': 6,
        'profit_pct': 5
    })
    print(f"分析结果: {result}")
    print()

    # 获取分析报告
    print("获取情绪分析报告...")
    report = tracker.get_emotion_analysis(user_id)
    print(report)


if __name__ == '__main__':
    main()