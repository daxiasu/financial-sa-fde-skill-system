"""
投资组合推荐引擎 v1.0
根据用户画像（年龄、风险承受能力、投资金额、投资时长、可承担损失）
推荐基金产品和配置组合
"""
import json
import os
import random
from datetime import datetime, date

# 使用相对于脚本位置的路径，增强跨平台兼容性
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(SCRIPT_DIR)), "data")


class PortfolioRecommender:
    """投资组合推荐引擎"""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        self.managers_db = {}
        self.companies_db = {}
        self.holdings_db = {}
        self._load_data()

    def _load_data(self):
        """加载数据库"""
        try:
            path = os.path.join(self.data_dir, 'fund_managers_distilled.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for m in data.get('managers', []):
                    key = m.get('manager_id', '')
                    if key:
                        self.managers_db[key] = m
        except Exception:
            pass

        try:
            path = os.path.join(self.data_dir, 'fund_companies_distilled.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for c in data.get('companies', []):
                    key = c.get('company_id', '')
                    if key:
                        self.companies_db[key] = c
        except Exception:
            pass

    # ==================== 风险画像分析 ====================

    def analyze_risk_profile(self, age, risk_tolerance, investment_period, max_loss):
        """
        分析用户风险画像

        参数:
            age: 年龄
            risk_tolerance: 风险承受能力 ('保守型', '稳健型', '平衡型', '积极型', '激进型')
            investment_period: 投资时长（年）
            max_loss: 可承担最大损失 (%)

        返回:
            dict: 风险画像分析结果
        """
        # 基于年龄计算股债比例
        stock_ratio = self._age_to_stock_ratio(age)
        bond_ratio = 100 - stock_ratio

        # 基于风险承受能力调整
        risk_multiplier = {
            '保守型': 0.5, '稳健型': 0.75, '平衡型': 1.0,
            '积极型': 1.25, '激进型': 1.5
        }
        multiplier = risk_multiplier.get(risk_tolerance, 1.0)
        stock_ratio = min(100, int(stock_ratio * multiplier))

        # 基于投资时长调整
        if investment_period < 1:
            stock_ratio = min(stock_ratio, 20)
        elif investment_period < 3:
            stock_ratio = min(stock_ratio, 50)
        elif investment_period >= 5:
            stock_ratio = min(stock_ratio + 10, 95)

        # 基于最大损失承受调整
        if max_loss < 5:
            stock_ratio = min(stock_ratio, 30)
        elif max_loss < 10:
            stock_ratio = min(stock_ratio, 50)
        elif max_loss > 20:
            stock_ratio = min(stock_ratio + 10, 95)

        bond_ratio = 100 - stock_ratio

        # 确定投资风格偏好
        if stock_ratio >= 70:
            style_preference = '成长型'
        elif stock_ratio >= 40:
            style_preference = '均衡型'
        else:
            style_preference = '价值型'

        return {
            'stock_ratio': stock_ratio,
            'bond_ratio': bond_ratio,
            'style_preference': style_preference,
            'investment_horizon': investment_period,
            'max_loss_tolerance': max_loss,
            'risk_level': risk_tolerance
        }

    def _age_to_stock_ratio(self, age):
        """基于年龄计算偏股比例（经验法则：100-年龄）"""
        ratio = max(10, min(90, 100 - age))
        return ratio

    # ==================== 组合推荐 ====================

    def recommend_portfolio(self, age, risk_tolerance, investment_amount, investment_period, max_loss):
        """
        推荐投资组合

        参数:
            age: 年龄
            risk_tolerance: 风险承受能力
            investment_amount: 投资金额（万元）
            investment_period: 投资时长（年）
            max_loss: 可承担最大损失 (%)

        返回:
            dict: 推荐结果
        """
        # 分析风险画像
        profile = self.analyze_risk_profile(age, risk_tolerance, investment_period, max_loss)
        stock_ratio = profile['stock_ratio']
        bond_ratio = profile['bond_ratio']
        style_preference = profile['style_preference']

        # 计算各类型配置金额
        stock_amount = int(investment_amount * stock_ratio / 100)
        bond_amount = investment_amount - stock_amount

        # 分配到不同基金类型
        allocation = self._allocate_funds(stock_amount, bond_amount, style_preference)

        # 选基金
        fund_recommendations = self._select_funds(allocation, style_preference)

        # 生成分组合成
        portfolio = {
            'profile': profile,
            'total_amount': investment_amount,
            'allocation': allocation,
            'funds': fund_recommendations,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

        return portfolio

    def _allocate_funds(self, stock_amount, bond_amount, style_preference):
        """分配资金到不同基金类型"""
        allocation = {
            'stock_funds': {'amount': 0, 'ratio': 0, 'types': []},
            'bond_funds': {'amount': 0, 'ratio': 0, 'types': []},
            'money_funds': {'amount': 0, 'ratio': 0, 'types': []},
            'qdii_funds': {'amount': 0, 'ratio': 0, 'types': []},
            'index_funds': {'amount': 0, 'ratio': 0, 'types': []}
        }

        if stock_amount > 0:
            if style_preference == '成长型':
                allocation['stock_funds'] = {'amount': stock_amount * 0.7, 'ratio': 70, 'types': ['股票型', '偏股混合']}
                allocation['index_funds'] = {'amount': stock_amount * 0.2, 'ratio': 20, 'types': ['指数型']}
                allocation['qdii_funds'] = {'amount': stock_amount * 0.1, 'ratio': 10, 'types': ['QDII']}
            elif style_preference == '价值型':
                allocation['stock_funds'] = {'amount': stock_amount * 0.4, 'ratio': 40, 'types': ['偏债混合', '灵活配置']}
                allocation['index_funds'] = {'amount': stock_amount * 0.4, 'ratio': 40, 'types': ['指数型']}
                allocation['money_funds'] = {'amount': stock_amount * 0.2, 'ratio': 20, 'types': ['货币型']}
            else:  # 均衡型
                allocation['stock_funds'] = {'amount': stock_amount * 0.5, 'ratio': 50, 'types': ['灵活配置', '偏股混合']}
                allocation['index_funds'] = {'amount': stock_amount * 0.3, 'ratio': 30, 'types': ['指数型']}
                allocation['qdii_funds'] = {'amount': stock_amount * 0.1, 'ratio': 10, 'types': ['QDII']}
                allocation['money_funds'] = {'amount': stock_amount * 0.1, 'ratio': 10, 'types': ['货币型']}

        if bond_amount > 0:
            allocation['bond_funds'] = {'amount': bond_amount * 0.7, 'ratio': 70, 'types': ['纯债', '一级债']}
            allocation['money_funds']['amount'] += bond_amount * 0.3
            allocation['money_funds']['ratio'] = allocation['money_funds'].get('ratio', 0) + 30

        # 归一化
        total = sum(v['amount'] for v in allocation.values())
        if total > 0:
            for k in allocation:
                if allocation[k]['amount'] > 0:
                    allocation[k]['ratio'] = round(allocation[k]['amount'] / total * 100, 1)

        return allocation

    def _select_funds(self, allocation, style_preference):
        """根据配置选择基金"""
        recommendations = []

        # 按风格筛选经理
        style = style_preference.replace('型', '')

        managers = list(self.managers_db.values())
        # 按风格过滤
        filtered = [m for m in managers if style in m.get('investment_style', '')]

        # 排序：优先选择规模适中、从业年限长、阶段成熟的
        filtered.sort(key=lambda x: (
            -x.get('total_scale', 0) if 10 < x.get('total_scale', 0) < 500 else 0,
            -x.get('tenure_years', 0),
            {'成熟期': 3, '老牌期': 4, '成长期': 2, '萌芽期': 1}.get(x.get('fund_stage', ''), 0)
        ))

        # 选择代表
        selected = filtered[:20]

        # 根据配置分配
        for fund_type, alloc in allocation.items():
            if alloc['amount'] <= 0 or not selected:
                continue

            amount = alloc['amount']
            fund_count = max(1, min(3, int(amount / 10)))  # 每10万一只

            type_recommendations = []
            for m in selected[:fund_count * 2]:
                fund_name = m.get('current_fund_name', '')
                fund_code = m.get('current_fund_code', '')
                if not fund_code or any(x['fund_code'] == fund_code for x in type_recommendations):
                    continue

                type_recommendations.append({
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'manager': m.get('name', ''),
                    'company': m.get('company_name', ''),
                    'style': m.get('investment_style', ''),
                    'tenure_years': m.get('tenure_years', 0),
                    'sector': m.get('sector_description', ''),
                    'suggested_amount': round(amount / fund_count, 1),
                    'risk_warning': m.get('risk_warning', '')[:40]
                })

                if len(type_recommendations) >= fund_count:
                    break

            if type_recommendations:
                recommendations.append({
                    'category': fund_type,
                    'allocated_amount': round(amount, 1),
                    'allocated_ratio': alloc['ratio'],
                    'fund_count': len(type_recommendations),
                    'funds': type_recommendations
                })

        return recommendations

    # ==================== 单品推荐 ====================

    def recommend_single_fund(self, risk_tolerance, investment_period, max_loss, amount=None):
        """
        推荐单只基金

        参数:
            risk_tolerance: 风险承受能力
            investment_period: 投资时长（年）
            max_loss: 可承担最大损失 (%)
            amount: 投资金额（可选）

        返回:
            list: 推荐基金列表
        """
        # 确定风格
        if risk_tolerance in ['保守型']:
            style = '价值型'
        elif risk_tolerance in ['激进型', '积极型']:
            style = '成长型'
        else:
            style = '均衡型'

        # 过滤
        managers = list(self.managers_db.values())
        candidates = []

        for m in managers:
            if style in m.get('investment_style', ''):
                # 排除风险过高的
                warning = m.get('risk_warning', '')
                if max_loss < 10 and '高波动' in warning:
                    continue

                # 投资周期匹配
                period_suggested = m.get('investment_period', '3年')
                period_num = int(period_suggested.replace('年以上', '').replace('年', '').split('-')[0] or '3')
                if investment_period < period_num:
                    continue

                candidates.append(m)

        # 排序
        candidates.sort(key=lambda x: (
            -x.get('tenure_years', 0),
            {'成熟期': 3, '老牌期': 4}.get(x.get('fund_stage', ''), 0)
        ))

        results = []
        for m in candidates[:10]:
            results.append({
                'fund_code': m.get('current_fund_code', ''),
                'fund_name': m.get('current_fund_name', ''),
                'manager': m.get('name', ''),
                'company': m.get('company_name', ''),
                'style': m.get('investment_style', ''),
                'tenure_years': m.get('tenure_years', 0),
                'stage': m.get('fund_stage', ''),
                'sector': m.get('sector_description', ''),
                'advice': m.get('investment_advice', ''),
                'warning': m.get('risk_warning', ''),
                'suitable': m.get('suitable_investors', ''),
                'period': m.get('investment_period', ''),
            })

        return results

    # ==================== 输出格式化 ====================

    def format_portfolio_report(self, portfolio):
        """格式化输出组合推荐报告"""
        lines = []
        profile = portfolio['profile']

        lines.append('\n' + '=' * 70)
        lines.append('  投资组合推荐报告')
        lines.append('=' * 70)
        lines.append(f"\n【您的风险画像】")
        lines.append(f"  年龄: {profile.get('risk_level', 'N/A')} ({portfolio.get('_age', 'N/A')}岁)")
        lines.append(f"  风险承受: {profile.get('risk_level', 'N/A')}")
        lines.append(f"  投资周期: {profile.get('investment_horizon', 0)}年")
        lines.append(f"  最大可承受亏损: {profile.get('max_loss_tolerance', 0)}%")

        lines.append(f"\n【资产配置方案】")
        lines.append(f"  股票类资产: {profile.get('stock_ratio', 0)}%")
        lines.append(f"  债券/货币: {profile.get('bond_ratio', 0)}%")
        lines.append(f"  建议风格: {profile.get('style_preference', 'N/A')}")

        lines.append(f"\n【基金配置明细】")
        total = portfolio.get('total_amount', 0)
        for cat in portfolio.get('funds', []):
            cat_name = {
                'stock_funds': '股票型基金',
                'bond_funds': '债券型基金',
                'money_funds': '货币基金',
                'qdii_funds': 'QDII海外基金',
                'index_funds': '指数基金'
            }.get(cat['category'], cat['category'])

            lines.append(f"\n  ▶ {cat_name} (占比{cat['allocated_ratio']}%，约{cat['allocated_amount']}万元)")
            for fund in cat.get('funds', []):
                lines.append(f"    {fund['fund_code']} {fund['fund_name']}")
                lines.append(f"      经理: {fund['manager']} | 公司: {fund['company']}")
                lines.append(f"      建议买入: {fund['suggested_amount']}万元 | 风格: {fund['style']}")

        lines.append(f"\n【投资建议】")
        advice_map = {
            '成长型': '建议采用定投方式参与，分批买入平滑成本。成长风格波动大，避免追涨杀跌。',
            '价值型': '可以一次性买入，长期持有。价值风格稳健，适合作为组合的压舱石。',
            '均衡型': '定投和一次性配置都可以，适合作为核心持仓。'
        }
        lines.append(f"  {advice_map.get(profile.get('style_preference', ''), '')}")

        lines.append(f"\n【风险提示】")
        lines.append(f"  以上推荐仅供参考，不构成投资建议。")
        lines.append(f"  投资基金有风险，请评估自身风险承受能力后决策。")
        lines.append(f"  建议分散投资，不要把鸡蛋放在一个篮子里。")

        lines.append('\n' + '=' * 70)
        lines.append(f"生成时间: {portfolio.get('generated_at', '')}")
        lines.append('=' * 70 + '\n')

        return '\n'.join(lines)

    def format_single_recommendation(self, funds, risk_tolerance, period, amount=None):
        """格式化单品推荐"""
        lines = []

        lines.append('\n' + '=' * 70)
        lines.append('  单品基金推荐')
        lines.append('=' * 70)
        lines.append(f"\n筛选条件:")
        lines.append(f"  风险偏好: {risk_tolerance}")
        lines.append(f"  投资周期: {period}年")
        if amount:
            lines.append(f"  投资金额: {amount}万元")

        lines.append(f"\n推荐基金 (Top {len(funds)}):")
        lines.append('-' * 70)

        for i, f in enumerate(funds, 1):
            lines.append(f"\n{i}. {f['fund_name']} ({f['fund_code']})")
            lines.append(f"   经理: {f['manager']} | 公司: {f['company']}")
            lines.append(f"   风格: {f['style']} | 阶段: {f['stage']} | 年限: {f['tenure_years']:.1f}年")
            lines.append(f"   重点: {f['sector']}")
            lines.append(f"   适合: {f['suitable']}")
            lines.append(f"   周期: {f['period']}")
            lines.append(f"   建议: {f['advice'][:50]}...")

        lines.append('\n' + '-' * 70)
        lines.append('风险提示: 以上推荐仅供参考，不构成投资建议。')
        lines.append('=' * 70 + '\n')

        return '\n'.join(lines)


def main():
    """测试"""
    recommender = PortfolioRecommender()

    print('投资组合推荐引擎 v1.0')
    print(f'加载了 {len(recommender.managers_db)} 位基金经理')

    # 测试1: 完整组合推荐
    print('\n--- 测试1: 30岁，积极型，20万，5年，可承受20%亏损 ---')
    portfolio = recommender.recommend_portfolio(
        age=30,
        risk_tolerance='积极型',
        investment_amount=20,
        investment_period=5,
        max_loss=20
    )
    print(recommender.format_portfolio_report(portfolio))

    # 测试2: 单品推荐
    print('\n--- 测试2: 50岁，稳健型，3年，可承受10%亏损 ---')
    funds = recommender.recommend_single_fund(
        risk_tolerance='稳健型',
        investment_period=3,
        max_loss=10
    )
    print(recommender.format_single_recommendation(funds, '稳健型', 3))


if __name__ == '__main__':
    main()