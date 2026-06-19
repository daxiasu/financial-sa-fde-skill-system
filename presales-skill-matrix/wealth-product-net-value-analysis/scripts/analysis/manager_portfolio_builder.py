"""
基金经理投资组合设计器 v1.0
根据基金经理投资风格和持仓信息，结合用户风险偏好设计投资组合
客户可以与基金经理数字人互动，同时基于经理风格构建自己的投资组合
"""
from __future__ import annotations
import json, os, random
from datetime import datetime
from pathlib import Path

# 路径推断
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"


class ManagerPortfolioBuilder:
    """
    基金经理投资组合设计器
    根据基金经理的投资风格、持仓偏好、风险特征，为客户构建投资组合
    """

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        self.managers_db = {}
        self.holdings_db = {}
        self._load_data()

    def _load_data(self):
        """加载本地数据库"""
        # 加载基金经理档案
        try:
            path = self.data_dir / 'fund_managers_distilled.json'
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for m in data.get('managers', []):
                    key = m.get('name', '')
                    if key:
                        self.managers_db[key] = m
        except Exception:
            pass

        # 加载持仓数据
        try:
            path = self.data_dir / 'holdings_database.json'
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    self.holdings_db = json.load(f)
        except Exception:
            pass

    def find_managers(self, name=None, style=None, company=None, sector=None, top_n=10):
        """查找符合条件的基金经理"""
        results = []
        seen = set()

        for key, m in self.managers_db.items():
            if name:
                kw = name.strip()
                if not (kw in key or key in kw or kw.replace(' ', '') in key.replace(' ', '')):
                    continue

            if style and style not in m.get('investment_style', ''):
                continue
            if company and company not in m.get('company_name', ''):
                continue
            if sector:
                sector_desc = m.get('sector_description', '')
                if sector not in sector_desc and sector not in sector_desc.replace('重点布局', ''):
                    continue

            key_str = (key, m.get('company_name', ''), m.get('current_fund_code', ''))
            if key_str in seen:
                continue
            seen.add(key_str)
            results.append(m)

            if len(results) >= top_n * 2:
                break

        # 排序：优先从业年限长、规模适中的
        results.sort(key=lambda x: (
            -x.get('tenure_years', 0),
            -x.get('total_scale', 0) if 10 < x.get('total_scale', 0) < 500 else 0,
        ))

        return results[:top_n]

    def get_manager_portfolio_style(self, manager_name):
        """获取基金经理的组合风格详情"""
        managers = self.find_managers(name=manager_name, top_n=1)
        if not managers:
            return None

        m = managers[0]
        return {
            'manager_name': m.get('name', ''),
            'company': m.get('company_name', ''),
            'fund_name': m.get('current_fund_name', ''),
            'fund_code': m.get('current_fund_code', ''),
            'style': m.get('investment_style', ''),
            'tenure_years': m.get('tenure_years', 0),
            'sector': m.get('sector_description', ''),
            'stock_pool': m.get('stock_pool', []),
            'bond_pool': m.get('bond_pool', {}),
            'fund_pool': m.get('fund_pool', []),
            'stage': m.get('fund_stage', ''),
            'risk_warning': m.get('risk_warning', ''),
            'investment_advice': m.get('investment_advice', ''),
            'suitable_investors': m.get('suitable_investors', ''),
            'infrastructure': m.get('infrastructure_investment', False),
        }

    def build_portfolio_by_manager(self, manager_name, client_risk='稳健型',
                                  client_investment_amount=10,
                                  client_investment_period=3,
                                  client_max_loss=15):
        """
        基于基金经理风格构建投资组合

        参数:
            manager_name: 基金经理名称
            client_risk: 客户风险偏好
            client_investment_amount: 投资金额（万元）
            client_investment_period: 投资周期（年）
            client_max_loss: 最大可承受亏损（%）

        返回:
            dict: 投资组合
        """
        style = self.get_manager_portfolio_style(manager_name)
        if not style:
            return {'error': f'未找到基金经理: {manager_name}'}

        # 分析风险画像
        profile = self._analyze_client_profile(
            client_risk, client_investment_period, client_max_loss
        )

        # 匹配基金经理风格
        manager_style = style['style']
        stock_ratio = self._calculate_stock_ratio(profile, manager_style)

        # 计算金额分配
        stock_amount = int(client_investment_amount * stock_ratio / 100)
        bond_amount = client_investment_amount - stock_amount

        # 构建组合
        portfolio = {
            'based_on_manager': style,
            'client_profile': profile,
            'total_amount': client_investment_amount,
            'stock_ratio': stock_ratio,
            'bond_ratio': 100 - stock_ratio,
            'stock_amount': stock_amount,
            'bond_amount': bond_amount,
            'funds': self._allocate_funds_by_style(style, stock_amount, bond_amount),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

        return portfolio

    def _analyze_client_profile(self, risk_tolerance, investment_period, max_loss):
        """分析客户风险画像"""
        risk_multiplier = {
            '保守型': 0.5, '稳健型': 0.75, '平衡型': 1.0,
            '积极型': 1.25, '激进型': 1.5
        }
        multiplier = risk_multiplier.get(risk_tolerance, 1.0)

        # 基于年龄的经验法则
        base_ratio = 100 - 35  # 默认35岁
        stock_ratio = min(90, max(10, int(base_ratio * multiplier)))

        if investment_period < 1:
            stock_ratio = min(stock_ratio, 20)
        elif investment_period < 3:
            stock_ratio = min(stock_ratio, 50)
        elif investment_period >= 5:
            stock_ratio = min(stock_ratio + 10, 95)

        if max_loss < 5:
            stock_ratio = min(stock_ratio, 30)
        elif max_loss < 10:
            stock_ratio = min(stock_ratio, 50)
        elif max_loss > 20:
            stock_ratio = min(stock_ratio + 10, 95)

        bond_ratio = 100 - stock_ratio

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

    def _calculate_stock_ratio(self, profile, manager_style):
        """计算股票比例（融合客户画像和经理风格）"""
        base = profile['stock_ratio']

        # 基金经理风格调整
        style_adjustments = {
            '成长型': 15,   # 成长型偏积极
            '均衡型': 0,    # 均衡型不变
            '价值型': -15,  # 价值型偏保守
        }
        adjustment = style_adjustments.get(manager_style, 0)

        # 与客户风格偏好融合
        if profile['style_preference'] == manager_style:
            adjustment += 5  # 风格一致时略增加

        return min(95, max(10, base + adjustment))

    def _allocate_funds_by_style(self, manager_style, stock_amount, bond_amount):
        """根据经理风格分配资金"""
        style = manager_style['style']
        stock_pool = manager_style.get('stock_pool', [])
        bond_pool = manager_style.get('bond_pool', {})
        fund_pool = manager_style.get('fund_pool', [])

        funds = []

        # 股票型配置（基于经理持仓风格）
        if stock_amount > 0 and stock_pool:
            stock_alloc = {
                'category': '股票型基金',
                'allocated_amount': round(stock_amount * 0.6, 1),
                'description': f"基于{manager_style['manager_name']}经理的持仓风格配置",
                'stock_pool': stock_pool[:5],
            }
            funds.append(stock_alloc)

        # 指数型配置
        if stock_amount > 0:
            index_alloc = {
                'category': '指数型基金',
                'allocated_amount': round(stock_amount * 0.25, 1),
                'description': '指数型基金作为组合底层工具',
            }
            funds.append(index_alloc)

        # QDII海外配置（成长型经理建议配置）
        if style == '成长型' and stock_amount > 0:
            qdii_alloc = {
                'category': 'QDII海外基金',
                'allocated_amount': round(stock_amount * 0.15, 1),
                'description': '海外资产分散配置',
            }
            funds.append(qdii_alloc)

        # 债券型配置
        if bond_amount > 0:
            bond_alloc = {
                'category': '债券型基金',
                'allocated_amount': round(bond_amount * 0.7, 1),
                'description': '债券类资产作为组合压舱石',
            }
            funds.append(bond_alloc)

        # 货币型配置
        if bond_amount > 0:
            money_alloc = {
                'category': '货币基金',
                'allocated_amount': round(bond_amount * 0.3, 1),
                'description': '流动性管理',
            }
            funds.append(money_alloc)

        return funds

    def get_manager_comparison(self, manager_names):
        """对比多位基金经理的投资风格"""
        managers_styles = []
        for name in manager_names:
            style = self.get_manager_portfolio_style(name)
            if style:
                managers_styles.append(style)

        if len(managers_styles) < 2:
            return {'error': '需要至少两位基金经理进行对比'}

        comparison = {
            'managers': managers_styles,
            'comparison_points': []
        }

        # 风格对比
        styles = [m['style'] for m in managers_styles]
        comparison['comparison_points'].append({
            'point': '投资风格',
            'values': styles,
            'verdict': '一致' if len(set(styles)) == 1 else '不一致'
        })

        # 行业偏好对比
        sectors = [m['sector'].replace('重点布局', '').replace('行业', '') for m in managers_styles]
        comparison['comparison_points'].append({
            'point': '行业偏好',
            'values': sectors,
            'verdict': '相似' if sectors[0] == sectors[1] else '不同'
        })

        # 风险等级对比
        risk_levels = []
        for m in managers_styles:
            warning = m.get('risk_warning', '')
            if '高波动' in warning or '短期回撤' in warning:
                risk_levels.append('高风险')
            elif '稳健' in warning or '控制回撤' in warning:
                risk_levels.append('低风险')
            else:
                risk_levels.append('中风险')
        comparison['comparison_points'].append({
            'point': '风险等级',
            'values': risk_levels,
            'verdict': f"{risk_levels[0]} vs {risk_levels[1]}"
        })

        return comparison

    def format_manager_portfolio_report(self, portfolio):
        """格式化基金经理组合报告"""
        if 'error' in portfolio:
            return f"错误: {portfolio['error']}"

        lines = []
        lines.append('\n' + '=' * 70)
        lines.append('  基金经理投资组合设计报告')
        lines.append('=' * 70)

        # 基于哪位经理
        mgr = portfolio.get('based_on_manager', {})
        lines.append(f"\n【组合设计来源】")
        lines.append(f"  基金经理: {mgr.get('manager_name', '')}")
        lines.append(f"  管理基金: {mgr.get('fund_name', '')} ({mgr.get('fund_code', '')})")
        lines.append(f"  所在公司: {mgr.get('company', '')}")
        lines.append(f"  投资风格: {mgr.get('style', '')}")
        lines.append(f"  从业年限: {mgr.get('tenure_years', 0):.1f}年")

        # 经理持仓偏好
        stock_pool = mgr.get('stock_pool', [])
        if stock_pool:
            lines.append(f"  偏好持仓: {'、'.join(stock_pool[:5])}")

        # 客户画像
        profile = portfolio.get('client_profile', {})
        lines.append(f"\n【您的风险画像】")
        lines.append(f"  风险偏好: {profile.get('risk_level', '')}")
        lines.append(f"  投资周期: {profile.get('investment_horizon', 0)}年")
        lines.append(f"  最大可承受亏损: {profile.get('max_loss_tolerance', 0)}%")

        # 资产配置
        lines.append(f"\n【资产配置方案】")
        lines.append(f"  股票类资产: {portfolio.get('stock_ratio', 0)}% ({portfolio.get('stock_amount', 0):.1f}万元)")
        lines.append(f"  债券/货币: {portfolio.get('bond_ratio', 0)}% ({portfolio.get('bond_amount', 0):.1f}万元)")

        # 基金明细
        lines.append(f"\n【基金配置明细】")
        for fund in portfolio.get('funds', []):
            lines.append(f"\n  ▶ {fund.get('category', '')} (约{fund.get('allocated_amount', 0):.1f}万元)")
            lines.append(f"    说明: {fund.get('description', '')}")
            if fund.get('stock_pool'):
                lines.append(f"    参考持仓: {'、'.join(fund.get('stock_pool', [])[:3])}")

        # 投资建议
        lines.append(f"\n【投资建议】")
        advice = mgr.get('investment_advice', '')
        if advice:
            lines.append(f"  {advice}")

        lines.append(f"\n【风险提示】")
        warning = mgr.get('risk_warning', '')
        if warning:
            lines.append(f"  {warning}")
        lines.append(f"  以上推荐仅供参考，不构成投资建议。")
        lines.append(f"  请评估自身风险承受能力后决策。")

        lines.append('\n' + '=' * 70)
        lines.append(f"生成时间: {portfolio.get('generated_at', '')}")
        lines.append('=' * 70 + '\n')

        return '\n'.join(lines)

    def format_manager_comparison_report(self, comparison):
        """格式化经理对比报告"""
        if 'error' in comparison:
            return f"错误: {comparison['error']}"

        lines = []
        lines.append('\n' + '=' * 70)
        lines.append('  基金经理风格对比报告')
        lines.append('=' * 70)

        for m in comparison.get('managers', []):
            lines.append(f"\n【{m.get('manager_name', '')}】")
            lines.append(f"  基金: {m.get('fund_name', '')}")
            lines.append(f"  风格: {m.get('style', '')}")
            lines.append(f"  行业: {m.get('sector', '')}")
            lines.append(f"  阶段: {m.get('stage', '')}")

        lines.append(f"\n【对比分析】")
        for point in comparison.get('comparison_points', []):
            lines.append(f"  {point['point']}: {' vs '.join(str(v) for v in point['values'])}")
            lines.append(f"    结论: {point['verdict']}")

        lines.append('\n' + '=' * 70)
        return '\n'.join(lines)


def main():
    """测试"""
    builder = ManagerPortfolioBuilder()

    print("基金经理投资组合设计器 v1.0")
    print(f"加载了 {len(builder.managers_db)} 位基金经理")

    # 测试：查找经理
    print("\n--- 测试: 查找成长型经理 ---")
    managers = builder.find_managers(style='成长型', top_n=5)
    for m in managers[:3]:
        print(f"  {m.get('name')} - {m.get('company')} - {m.get('current_fund_name')}")

    # 测试：基于经理构建组合
    if managers:
        name = managers[0].get('name')
        print(f"\n--- 测试: 基于{name}构建组合 ---")
        portfolio = builder.build_portfolio_by_manager(
            name,
            client_risk='积极型',
            client_investment_amount=20,
            client_investment_period=5,
            client_max_loss=20
        )
        print(builder.format_manager_portfolio_report(portfolio))


if __name__ == '__main__':
    main()