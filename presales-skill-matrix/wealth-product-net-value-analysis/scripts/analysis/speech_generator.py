"""
基金经理话术系统
根据场景、客户类型自动生成专业且有人情味的投资建议话术
"""
import json
from datetime import datetime

class SpeechGenerator:
    """话术生成器"""

    def __init__(self, db_path='../data'):
        self.db_path = db_path
        self.load_databases()

    def load_databases(self):
        """加载数据库"""
        try:
            with open(f'{self.db_path}/fund_managers.json', 'r', encoding='utf-8') as f:
                self.managers_db = json.load(f)
        except:
            self.managers_db = {'managers': []}

    def generate_manager_profile_intro(self, manager_id):
        """
        生成基金经理介绍话术

        参数:
            manager_id: 经理ID

        返回:
            str: 基金经理介绍文本
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return "未找到该基金经理信息"

        name = manager.get('name', '')
        company = manager.get('company_name', '')
        tenure = self._calculate_tenure(manager)
        style = manager.get('investment_style', {})
        style_type = style.get('type', '均衡型')
        sector = style.get('sector', '')
        scale = self._calculate_total_scale(manager)

        # 话术模板
        intro = f"""
{name}，{company}明星基金经理，从业{tenure}年，目前管理规模约{scale}亿元。

【投资风格】
• 类型：{style_type}
• 专注领域：{sector if sector else '综合配置'}
• 仓位特征：{style.get('position_style', '灵活调整')}
• 换手率：{style.get('turnover', '中等')}

【核心优势】
{self._generate_strengths_text(manager)}

【代表基金】
{self._generate_fund_intro(manager)}
        """.strip()

        return intro

    def generate_comparison_speech(self, manager_ids):
        """
        生成基金经理对比话术

        参数:
            manager_ids: 经理ID列表
        """
        managers = [self._find_manager(mid) for mid in manager_ids]
        managers = [m for m in managers if m]

        if len(managers) < 2:
            return "需要至少两位基金经理进行对比"

        lines = ["【横向对比分析】\n"]

        # 基本信息对比
        lines.append("| 指标 | " + " | ".join([m.get('name', '')[:4] for m in managers]) + " |")
        lines.append("|------|" + "|".join(['---'] * (len(managers) + 1)) + "|")

        # 管理规模
        scales = [self._calculate_total_scale(m) for m in managers]
        lines.append(f"| 管理规模 | " + " | ".join([f"{s}亿" for s in scales]) + " |")

        # 投资风格
        styles = [m.get('investment_style', {}).get('type', '-') for m in managers]
        lines.append(f"| 投资风格 | " + " | ".join(styles) + " |")

        # 业绩对比
        perf1 = managers[0].get('performance', {})
        perf2 = managers[1].get('performance', {}) if len(managers) > 1 else {}
        r1 = perf1.get('one_year', 0)
        r2 = perf2.get('one_year', 0) if perf2 else 0
        lines.append(f"| 近1年收益 | {r1:.1f}% | {r2:.1f}% |")

        # 分析结论
        lines.append("\n【分析结论】")
        lines.append(self._generate_comparison_conclusion(managers))

        return "\n".join(lines)

    def generate_recommendation_speech(self, manager_id, client_risk_profile):
        """
        生成推荐话术

        参数:
            manager_id: 经理ID
            client_risk_profile: 客户风险偏好（保守型/稳健型/积极型/激进型）
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return "未找到该基金经理信息"

        name = manager.get('name', '')
        company = manager.get('company_name', '')
        style = manager.get('investment_style', {})

        # 判断匹配度
        match_result = self._judge_match(manager, client_risk_profile)

        speech = f"""
【基金推荐方案】

推荐基金经理：{name}（{company}）

推荐理由：
{match_result['reasons']}

风险提示：
{match_result['risk_alert']}

适用场景：
{match_result['suitable_scenarios']}
        """.strip()

        return speech

    def generate_bearish_comfort_speech(self, manager_id, loss_percent):
        """
        生成熊市/亏损安抚话术

        参数:
            manager_id: 经理ID
            loss_percent: 亏损百分比
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return "未找到该基金经理信息"

        name = manager.get('name', '')
        style = manager.get('investment_style', {})
        recent_views = manager.get('recent_views', [])
        top_stocks = manager.get('top_stocks', [])[:3]

        speech = f"""
【亏损分析与安抚话术】

{name}管理的基金近期出现约{loss_percent}%的回撤，我理解您的担忧。让我为您分析：

【市场背景】
开年以来成长板块整体承压，AI、科技等热门赛道出现明显调整，这与我们重仓的方向阶段性一致。

【基金特性】
作为{style.get('type', '均衡')}型基金，在市场调整期波动较大是正常的。
经理保持{style.get('position_style', '灵活')}的仓位配置，{style.get('turnover', '中等')}换手率，
意味着在下跌市中会承受压力，但未来反弹时也会更有弹性。

【持仓分析】
前三大重仓股：{', '.join([s.get('name', '') for s in top_stocks]) if top_stocks else '数据加载中'}
这些标的的基本面没有发生显著变化，短期波动更多是情绪和估值因素。

【经理观点】
{recent_views[0].get('content', '保持稳健运作') if recent_views else '保持稳健运作'}

【后续策略】
1. 建议保持定投，当前点位下适度加仓
2. 如风险承受能力有限，可考虑转换为同公司旗下更稳健的债基
3. 历史上看，经理经历多次类似调整后都创出净值新高

【关键信息】
• 本次回撤主要集中在{style.get('sector', '成长')}板块
• 经理未进行大幅调仓，保持投资逻辑一致性
• 建议持有期限：建议至少6-12个月观察

请放心，我们的投研团队持续跟踪市场，基金经理也在积极调整应对。
        """.strip()

        return speech

    def generate_bullish_encourage_speech(self, manager_id, gain_percent):
        """
        生成牛市追涨鼓励话术

        参数:
            manager_id: 经理ID
            gain_percent: 收益百分比
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return "未找到该基金经理信息"

        name = manager.get('name', '')
        style = manager.get('investment_style', {})
        perf = manager.get('performance', {})

        speech = f"""
【收益分析与建议话术】

恭喜您！{name}管理的基金近期表现优异，已实现{gain_percent}%的正收益。

【业绩归因】
• 近1年收益：{perf.get('one_year', 0):.1f}%
• 夏普比率：{perf.get('sharpe_ratio', 0):.2f}（风险调整收益表现优秀）
• 最大回撤：{perf.get('max_drawdown', 0):.1f}%（控制较好）

【投资逻辑】
经理坚持{style.get('type', '均衡')}风格，专注{style.get('sector', '优质')}赛道，
在市场反弹中把握住了机会。

【风险提示】
虽然近期表现强劲，但建议您：
1. 不要追涨加仓过大，保持原有定投节奏
2. 注意分散风险，可考虑配置部分债基平衡组合
3. 设定合理的收益预期，不要期望持续如此高增长

【后续展望】
{style.get('type', '均衡')}型基金的合理预期年化收益约为15-25%，
建议适时考虑部分止盈，锁定收益。
        """.strip()

        return speech

    def generate_portfolio_analysis_speech(self, manager_id):
        """
        生成持仓分析话术
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return "未找到该基金经理信息"

        name = manager.get('name', '')
        top_stocks = manager.get('top_stocks', [])
        top_bonds = manager.get('top_bonds', [])
        style = manager.get('investment_style', {})

        # 构建持仓表格
        stock_table = "| 序号 | 股票名称 | 持仓占比 | 变动 |"
        stock_table += "\n|------|---------|---------|------|"
        for i, s in enumerate(top_stocks[:10], 1):
            change = s.get('change', 0)
            change_str = f"+{change}%" if change > 0 else (f"{change}%" if change < 0 else "-")
            stock_table += f"\n| {i} | {s.get('name', '')} | {s.get('weight', 0):.1f}% | {change_str} |"

        speech = f"""
【{name}持仓分析】

【股票持仓】（前十大重仓股）
{stock_table}

【债券持仓】（前十大重仓债）
{self._generate_bond_table(top_bonds)}

【持仓特征】
• 集中度：前十大占比约{sum(s.get('weight', 0) for s in top_stocks[:10]):.1f}%
• 风格：{style.get('type', '均衡')} / {style.get('position_style', '灵活')}
• 行业：{style.get('sector', '综合配置')}

【配置逻辑】
{self._generate_allocation_logic(manager)}
        """.strip()

        return speech

    def adapt_speech_style(self, base_speech, client_type):
        """
        自适应话术风格

        参数:
            base_speech: 基础话术
            client_type: 客户类型（专业型/通俗型/权威型）

        返回:
            str: 调整后的话术
        """
        if client_type == '专业型':
            # 增加数据和逻辑
            return base_speech  # 保持原样
        elif client_type == '通俗型':
            # 简化术语，增加比喻
            speech = base_speech.replace('夏普比率', '风险收益比')
            speech = speech.replace('回撤', '下跌幅度')
            speech = speech.replace('超额收益', '跑赢大盘的部分')
            return speech
        elif client_type == '权威型':
            # 增加背书和机构数据
            return base_speech  # 保持原样

        return base_speech

    def _find_manager(self, manager_id):
        """查找基金经理"""
        for m in self.managers_db.get('managers', []):
            if m.get('manager_id') == manager_id:
                return m
        return None

    def _calculate_tenure(self, manager):
        """计算从业年限"""
        companies = manager.get('companies_history', [])
        if companies:
            return 5  # 简化
        return 3

    def _calculate_total_scale(self, manager):
        """计算总管理规模"""
        funds = manager.get('fund_list', [])
        return sum(f.get('scale', 0) for f in funds)

    def _generate_strengths_text(self, manager):
        """生成优势描述"""
        style = manager.get('investment_style', {})
        perf = manager.get('performance', {})

        strengths = []

        # 收益能力
        if perf.get('one_year', 0) > 20:
            strengths.append("近1年收益超过20%，表现出色")

        # 回撤控制
        if perf.get('max_drawdown', 0) > -20:
            strengths.append("回撤控制较好，下跌市中表现稳健")

        # 风格稳定
        strengths.append(f"投资风格稳定，{style.get('type', '均衡')}策略一贯执行")

        return "\n".join([f"• {s}" for s in strengths]) if strengths else "• 综合投资能力突出"

    def _generate_fund_intro(self, manager):
        """生成代表基金介绍"""
        funds = manager.get('fund_list', [])
        if not funds:
            return "数据加载中"

        main_fund = funds[0]
        return f"{main_fund.get('name', '')}（{main_fund.get('code', '')}），规模{main_fund.get('scale', 0)}亿"

    def _judge_match(self, manager, client_risk_profile):
        """判断匹配度"""
        style = manager.get('investment_style', {})
        style_type = style.get('type', '均衡')
        position = style.get('position_style', '灵活')

        # 简化匹配逻辑
        if client_risk_profile == '保守型':
            if '价值' in style_type or '债' in str(manager.get('fund_list', [{}])[0])):
                return {'reasons': '基金风格稳健，适合保守型投资者', 'risk_alert': '波动较小，收益适中', 'suitable_scenarios': '适合养老、子女教育等长期资金'}
            else:
                return {'reasons': '需注意：基金波动较大，可能不适合保守型', 'risk_alert': '建议充分了解后投资', 'suitable_scenarios': '建议少量配置'}
        elif client_risk_profile == '积极型':
            if '成长' in style_type or '高仓位' in position:
                return {'reasons': '成长风格匹配积极型投资者', 'risk_alert': '波动较大，需承受风险', 'suitable_scenarios': '适合追求高收益、风险承受力强的投资者'}

        return {'reasons': '风格适配，建议关注', 'risk_alert': '请详细了解基金风险', 'suitable_scenarios': '适合长期持有'}

    def _generate_comparison_conclusion(self, managers):
        """生成对比结论"""
        if len(managers) < 2:
            return ""

        m1_style = managers[0].get('investment_style', {}).get('type', '')
        m2_style = managers[1].get('investment_style', {}).get('type', '')

        conclusions = []

        if m1_style == m2_style:
            conclusions.append("两位经理风格相近，适合做组合配置分散风险")
        else:
            conclusions.append("两位经理风格互补，可搭配不同市场环境")

        perf1 = managers[0].get('performance', {}).get('one_year', 0)
        perf2 = managers[1].get('performance', {}).get('one_year', 0)

        if perf1 > perf2:
            conclusions.append(f"{managers[0].get('name', '')}近期业绩更优")
        else:
            conclusions.append(f"{managers[1].get('name', '')}近期业绩更优")

        return "\n".join([f"• {c}" for c in conclusions])

    def _generate_bond_table(self, bonds):
        """生成债券表格"""
        if not bonds:
            return "暂无债券持仓数据"

        table = "| 序号 | 债券名称 | 持仓占比 |"
        table += "\n|------|---------|---------|"
        for i, b in enumerate(bonds[:10], 1):
            table += f"\n| {i} | {b.get('name', '')} | {b.get('weight', 0):.1f}% |"

        return table

    def _generate_allocation_logic(self, manager):
        """生成配置逻辑说明"""
        style = manager.get('investment_style', {})
        sector = style.get('sector', '')

        if '科技' in sector or '新能源' in sector:
            return "围绕科技和新能源两条主线配置，把握产业升级机遇"
        elif '消费' in sector:
            return "以消费为核心配置，兼顾经济复苏带来的机会"
        else:
            return "采用均衡配置策略，分散单一行业风险"

def main():
    generator = SpeechGenerator()
    print("话术生成器已加载")
    print(f"共有 {len(generator.managers_db.get('managers', []))} 位基金经理数据")

if __name__ == "__main__":
    main()