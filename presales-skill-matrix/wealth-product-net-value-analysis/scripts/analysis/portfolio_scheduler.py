"""
灵活反馈调度器 v1.0
支持自由设置 N 日报（如1日报、2日报、3日报等）
日报内容包含：财经新闻汇总 + 单产品收益率 + 组合收益率 + 量化分析信号
"""
from __future__ import annotations
import json, os, time
from datetime import datetime, timedelta, date
from pathlib import Path

# 路径推断
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"


class FeedbackScheduler:
    """
    灵活反馈调度器 v1.0

    支持设置：
    - N日报（每N天发送一次，如1日/2日/3日报）
    - 周报（每7天）
    - 自定义间隔

    每次报告内容：
    1. 当天财经新闻汇总
    2. 单个持仓产品收益率
    3. 投资组合整体收益率
    4. 每日量化分析信号
    5. 止盈止损触发检查
    """

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        self.settings_file = self.data_dir / "feedback_settings_v2.json"
        self.alerts_file = self.data_dir / "alert_history.json"
        self._ensure_files()

    def _ensure_files(self):
        """确保设置文件存在"""
        if not self.settings_file.exists():
            self._save_settings(self._default_settings())

        if not self.alerts_file.exists():
            self._save_alerts([])

    def _default_settings(self):
        return {
            'frequency': 'none',      # 'daily', 'ndays', 'weekly', 'monthly', 'none'
            'interval_days': 1,        # N日报间隔天数
            'notify_time': '09:00',   # 提醒时间 HH:MM
            'enabled': False,
            'last_feedback': None,
            'next_feedback': None,
            'include_news': True,     # 包含财经新闻
            'include_quant': True,     # 包含量化分析
            'include_yield': True,    # 包含收益率
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

    def _load_settings(self):
        try:
            return json.loads(self.settings_file.read_text(encoding='utf-8'))
        except:
            return self._default_settings()

    def _save_settings(self, settings):
        self.settings_file.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def _load_alerts(self):
        try:
            return json.loads(self.alerts_file.read_text(encoding='utf-8'))
        except:
            return []

    def _save_alerts(self, alerts):
        self.alerts_file.write_text(
            json.dumps(alerts, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    # ==================== 设置管理 ====================

    def set_schedule(self, frequency, interval_days=1, notify_time='09:00',
                     include_news=True, include_quant=True, include_yield=True,
                     enabled=True):
        """
        设置反馈 schedule

        参数:
            frequency: 'daily' | 'ndays' | 'weekly' | 'monthly' | 'none'
                      'daily' = 每日
                      'ndays' = 每N天（如2日报=每2天）
                      'weekly' = 每周
                      'monthly' = 每月
                      'none' = 关闭
            interval_days: N日报的天数间隔（当 frequency='ndays' 时生效）
            notify_time: 提醒时间 HH:MM
            include_news: 包含财经新闻
            include_quant: 包含量化分析
            include_yield: 包含收益率
            enabled: 是否启用
        """
        next_feedback = self._calc_next_feedback(frequency, interval_days, notify_time)

        settings = {
            'frequency': frequency,
            'interval_days': interval_days,
            'notify_time': notify_time,
            'include_news': include_news,
            'include_quant': include_quant,
            'include_yield': include_yield,
            'enabled': enabled,
            'last_feedback': None,
            'next_feedback': next_feedback,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

        self._save_settings(settings)
        return {'success': True, 'settings': settings}

    def _calc_next_feedback(self, frequency, interval_days, notify_time):
        now = datetime.now()
        hour, minute = map(int, notify_time.split(':'))

        next_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if frequency == 'none' or not frequency:
            return None

        if frequency == 'daily':
            if next_dt <= now:
                next_dt += timedelta(days=1)

        elif frequency == 'ndays':
            if next_dt <= now:
                next_dt += timedelta(days=1)
            # 计算下一个N日周期
            last = self._load_settings().get('last_feedback')
            if last:
                last_dt = datetime.strptime(last, '%Y-%m-%d %H:%M')
                days_since = (now - last_dt).days
                remainder = days_since % interval_days
                if remainder == 0:
                    next_dt = now
                else:
                    next_dt += timedelta(days=interval_days - remainder)

        elif frequency == 'weekly':
            # 下周一
            days_ahead = (7 - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_dt = now + timedelta(days=days_ahead)
            next_dt = next_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

        elif frequency == 'monthly':
            # 下月1日，如果是非工作日则顺延到周一
            year = now.year
            month = now.month + 1
            if month > 12:
                month = 1
                year += 1
            next_dt = next_dt.replace(year=year, month=month, day=1)
            # 如果是非工作日（周六=5，周日=6），顺延到周一
            if next_dt.weekday() >= 5:
                days_to_add = 7 - next_dt.weekday()
                next_dt = next_dt + timedelta(days=days_to_add)
            if next_dt <= now:
                # 已经是下月了但已过，走下下月1日逻辑
                next_dt = next_dt.replace(month=month + 1 if month < 12 else 1,
                                          year=year + 1 if month == 12 else year)

        return next_dt.strftime('%Y-%m-%d %H:%M')

    def get_schedule(self):
        """获取当前设置"""
        return self._load_settings()

    def get_schedule_description(self):
        """获取可读的时间描述"""
        settings = self._load_settings()
        freq = settings.get('frequency', 'none')
        interval = settings.get('interval_days', 1)
        notify_time = settings.get('notify_time', '09:00')

        freq_map = {
            'daily': '每日',
            'ndays': f'每{interval}日',
            'weekly': '每周',
            'monthly': '每月',
            'none': '关闭'
        }

        desc = freq_map.get(freq, '未设置')
        if freq != 'none':
            desc += f' {notify_time} 发送'

        enabled = '已开启' if settings.get('enabled') else '已关闭'
        last = settings.get('last_feedback', '无')
        next_f = settings.get('next_feedback', '无')

        return {
            'schedule': desc,
            'enabled': enabled,
            'last_feedback': last,
            'next_feedback': next_f,
            'include_news': settings.get('include_news', True),
            'include_quant': settings.get('include_quant', True),
            'include_yield': settings.get('include_yield', True),
        }

    # ==================== 反馈触发检查 ====================

    def check_feedback_due(self):
        """检查是否该发送反馈"""
        settings = self._load_settings()
        if not settings.get('enabled') or settings.get('frequency') == 'none':
            return False

        now = datetime.now()
        next_feedback = settings.get('next_feedback')
        if not next_feedback:
            return False

        next_dt = datetime.strptime(next_feedback, '%Y-%m-%d %H:%M')
        return now >= next_dt

    def record_feedback_sent(self):
        """记录已发送反馈"""
        settings = self._load_settings()
        now = datetime.now()

        settings['last_feedback'] = now.strftime('%Y-%m-%d %H:%M')
        settings['next_feedback'] = self._calc_next_feedback(
            settings.get('frequency', 'none'),
            settings.get('interval_days', 1),
            settings.get('notify_time', '09:00')
        )

        self._save_settings(settings)

    # ==================== 止盈止损告警 ====================

    def check_stop_orders(self, holdings, target_return=None, stop_loss=None):
        """
        检查止盈止损条件

        参数:
            holdings: list[dict], 持仓列表
            target_return: float, 年化目标收益率（%），达到此收益率触发止盈提醒
            stop_loss: float, 年化止损收益率（%），跌破此收益率触发止损提醒

        返回:
            list[dict]: 触发的告警列表
        """
        alerts = []

        for h in holdings:
            fund_code = h.get('fund_code', '')
            fund_name = h.get('fund_name', '未知')
            current_value = h.get('current_value', 0)
            cost_value = h.get('cost_value', 0)
            cost = h.get('cost', 0)
            shares = h.get('shares', 0)
            purchase_date = h.get('purchase_date', '')
            current_nav = h.get('current_nav', 0)

            if not fund_code or cost_value <= 0:
                continue

            # 计算收益率
            profit_pct = (current_value - cost_value) / cost_value * 100

            # 计算年化收益率
            if purchase_date:
                try:
                    purchase_dt = datetime.strptime(purchase_date, '%Y-%m-%d')
                    days = (datetime.now() - purchase_dt).days
                    years = days / 365
                    annual_return = ((current_value / cost_value) ** (1/years) - 1) * 100 if years > 0 else 0
                except:
                    annual_return = 0
            else:
                annual_return = 0

            # 检查止盈
            if target_return and annual_return >= target_return:
                alerts.append({
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'alert_type': '止盈',
                    'action': '建议部分止盈',
                    'reason': f'年化收益率 {annual_return:.1f}% 已达到目标 {target_return}%，建议锁定利润',
                    'annual_return': round(annual_return, 2),
                    'profit_pct': round(profit_pct, 2),
                    'triggered_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                })

            # 检查止损
            if stop_loss and annual_return <= stop_loss:
                alerts.append({
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'alert_type': '止损',
                    'action': '建议减仓或转换',
                    'reason': f'年化收益率 {annual_return:.1f}% 已跌破止损线 {stop_loss}%，建议评估是否继续持有',
                    'annual_return': round(annual_return, 2),
                    'profit_pct': round(profit_pct, 2),
                    'triggered_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                })

        # 保存告警历史
        if alerts:
            existing = self._load_alerts()
            existing.extend(alerts)
            # 只保留最近100条
            self._save_alerts(existing[-100:])

        return alerts

    def get_alert_history(self, limit=20):
        """获取告警历史"""
        alerts = self._load_alerts()
        return alerts[-limit:]

    def clear_alert_history(self):
        """清空告警历史"""
        self._save_alerts([])

    def trigger_immediate_alert(self, holdings, target_return=None, stop_loss=None):
        """
        临时设置止盈止损条件，立即检查并返回告警
        不修改默认设置，仅本次检查有效

        参数:
            holdings: list[dict], 持仓列表
            target_return: 年化目标收益率（%），如 20
            stop_loss: 年化止损收益率（%），如 -15

        返回:
            list[dict]: 触发的告警列表
        """
        return self.check_stop_orders(holdings, target_return, stop_loss)

    # ==================== 生成综合报告 ====================

    def generate_daily_report(self, holdings, client_risk='稳健型',
                              target_return=None, stop_loss=None):
        """
        生成每日综合报告

        参数:
            holdings: list[dict], 持仓列表
            client_risk: 客户风险偏好
            target_return: 年化目标收益率（%）
            stop_loss: 年化止损收益率（%）

        返回:
            dict: 报告内容
        """
        settings = self._load_settings()
        report_sections = {}

        # 1. 财经新闻汇总
        if settings.get('include_news', True):
            try:
                from scripts.analysis.news_advisor import NewsAdvisor
                advisor = NewsAdvisor()
                try:
                    advisor.crawl_news()
                except:
                    pass
                report_sections['news'] = {
                    'summary': advisor.get_news_summary(),
                    'signal': advisor.get_portfolio_adjustment_signal(),
                }
            except:
                report_sections['news'] = {'error': '无法获取新闻'}

        # 2. 收益率信息
        if settings.get('include_yield', True):
            total_value = sum(h.get('current_value', 0) for h in holdings)
            total_cost = sum(h.get('cost_value', 0) for h in holdings)
            total_profit = total_value - total_cost
            total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0

            individual_yields = []
            for h in holdings:
                cv = h.get('current_value', 0)
                ct = h.get('cost_value', 0)
                individual_yields.append({
                    'fund_code': h.get('fund_code', ''),
                    'fund_name': h.get('fund_name', ''),
                    'current_value': round(cv, 2),
                    'cost_value': round(ct, 2),
                    'profit': round(cv - ct, 2),
                    'profit_pct': round((cv - ct) / ct * 100, 2) if ct > 0 else 0,
                })

            report_sections['yield'] = {
                'total_value': round(total_value, 2),
                'total_cost': round(total_cost, 2),
                'total_profit': round(total_profit, 2),
                'total_profit_pct': round(total_profit_pct, 2),
                'individual_yields': individual_yields,
            }

        # 3. 量化分析信号
        if settings.get('include_quant', True):
            try:
                from scripts.analysis.fund_quant_analyzer import FundQuantAnalyzer
                analyzer = FundQuantAnalyzer(data_dir=self.data_dir)
                quant_results = []
                for h in holdings:
                    fund_code = h.get('fund_code', '')
                    if fund_code:
                        result = analyzer.analyze_fund(fund_code, client_risk)
                        quant_results.append(result)
                report_sections['quant'] = {
                    'signals': quant_results,
                }
            except:
                report_sections['quant'] = {'error': '无法获取量化分析'}

        # 4. 止盈止损检查
        alerts = self.check_stop_orders(holdings, target_return, stop_loss)
        if alerts:
            report_sections['alerts'] = {'triggered': alerts}

        report_sections['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        return report_sections

    def format_daily_report(self, report):
        """格式化每日综合报告"""
        lines = []
        lines.append('\n' + '=' * 70)
        lines.append('  每日基金投资报告')
        lines.append('=' * 70)

        # 收益率
        if 'yield' in report and 'error' not in report.get('yield', {}):
            y = report['yield']
            lines.append(f"\n【组合收益率】")
            lines.append(f"  总市值: {y['total_value']:.2f}万元")
            lines.append(f"  总成本: {y['total_cost']:.2f}万元")
            lines.append(f"  总收益: {y['total_profit']:+.2f}万元 ({y['total_profit_pct']:+.2f}%)")

            lines.append(f"\n【持仓明细】")
            for ind in y.get('individual_yields', []):
                sign = "+" if ind['profit_pct'] > 0 else ""
                lines.append(f"  {ind['fund_name']} ({ind['fund_code']})")
                lines.append(f"    市值: {ind['current_value']:.2f}万元 | 收益: {sign}{ind['profit']:.2f}万元 ({sign}{ind['profit_pct']}%)")

        # 量化信号
        if 'quant' in report and 'error' not in report.get('quant', {}):
            signals = report['quant'].get('signals', [])
            if signals:
                lines.append(f"\n【量化分析信号】")
                for s in signals:
                    action = s.get('action', '观望')
                    signal = s.get('combined_signal', 0)
                    sign = "+" if signal > 0 else ""
                    lines.append(f"  {s.get('fund_code', '')}: {action} [{sign}{signal:.2f}]")

        # 止盈止损
        if 'alerts' in report:
            alerts = report['alerts'].get('triggered', [])
            if alerts:
                lines.append(f"\n【⚠️ 止盈止损提醒】")
                for a in alerts:
                    emoji = "🎯" if a['alert_type'] == '止盈' else "🛑"
                    lines.append(f"  {emoji} {a['fund_name']} ({a['fund_code']})")
                    lines.append(f"    类型: {a['alert_type']} | 操作: {a['action']}")
                    lines.append(f"    理由: {a['reason']}")

        # 财经新闻
        if 'news' in report and 'error' not in report.get('news', {}):
            ns = report['news'].get('summary', {})
            signal = report['news'].get('signal', {})
            lines.append(f"\n【财经新闻汇总】")
            lines.append(f"  今日新闻: {ns.get('total', 0)}条 | 情绪: {ns.get('overall', '中性')}")
            lines.append(f"  调仓信号: {signal.get('signal', '未知')} - {signal.get('action', '持有')}")
            lines.append(f"  理由: {signal.get('reason', '')}")

        lines.append('\n' + '=' * 70)
        lines.append(f"生成时间: {report.get('generated_at', '')}")
        lines.append('=' * 70 + '\n')
        return '\n'.join(lines)

    # ==================== 快捷设置命令 ====================

    def set_nday_report(self, interval, notify_time='09:00'):
        """设置N日报"""
        return self.set_schedule('ndays', interval_days=interval, notify_time=notify_time)

    def set_daily_report(self, notify_time='09:00'):
        """设置日报"""
        return self.set_schedule('daily', notify_time=notify_time)

    def set_weekly_report(self, notify_time='09:00'):
        """设置周报"""
        return self.set_schedule('weekly', notify_time=notify_time)

    def set_monthly_report(self, notify_time='09:00'):
        """设置月报"""
        return self.set_schedule('monthly', notify_time=notify_time)

    def disable_report(self):
        """关闭报告"""
        return self.set_schedule('none')


def main():
    """测试"""
    scheduler = FeedbackScheduler()
    print("灵活反馈调度器 v1.0")

    # 测试设置
    print("\n--- 测试: 设置3日报 ---")
    result = scheduler.set_nday_report(interval=3, notify_time='08:30')
    print(f"设置结果: {result}")

    print("\n--- 当前设置 ---")
    desc = scheduler.get_schedule_description()
    for k, v in desc.items():
        print(f"  {k}: {v}")

    print("\n--- 测试: 检查止盈止损 ---")
    # 模拟持仓数据
    holdings = [
        {
            'fund_code': '001924',
            'fund_name': '华夏国企改革混合',
            'shares': 10000,
            'cost': 1.5,
            'purchase_date': '2024-01-15',
            'current_nav': 1.65,
            'current_value': 16500,
            'cost_value': 15000,
        }
    ]
    alerts = scheduler.check_stop_orders(holdings, target_return=20, stop_loss=-15)
    print(f"触发告警: {len(alerts)}条")
    for a in alerts:
        print(f"  {a}")


if __name__ == '__main__':
    main()