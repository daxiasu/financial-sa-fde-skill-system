"""
持仓分析引擎
分析基金经理的持仓特征、重仓股、配置风格
"""
import json
from collections import Counter

class PortfolioAnalyzer:
    """持仓分析器"""

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

        try:
            with open(f'{self.db_path}/holdings_database.json', 'r', encoding='utf-8') as f:
                self.holdings_db = json.load(f)
        except:
            self.holdings_db = {'holdings': []}

    def analyze_portfolio_concentration(self, manager_id):
        """
        分析持仓集中度

        返回:
            dict: 集中度分析结果
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return None

        top_stocks = manager.get('top_stocks', [])
        top_bonds = manager.get('top_bonds', [])

        # 股票集中度
        stock_weight = sum(s.get('weight', 0) for s in top_stocks[:5])
        stock_concentration = '高集中' if stock_weight > 50 else ('中等' if stock_weight > 30 else '分散')

        # 债券集中度
        bond_weight = sum(b.get('weight', 0) for b in top_bonds[:5])
        bond_concentration = '高集中' if bond_weight > 50 else ('中等' if bond_weight > 30 else '分散')

        return {
            'stock_top5_weight': round(stock_weight, 2),
            'stock_concentration': stock_concentration,
            'bond_top5_weight': round(bond_weight, 2),
            'bond_concentration': bond_concentration,
            'overall_concentration': self._calculate_overall(top_stocks, top_bonds)
        }

    def analyze_sector_allocation(self, manager_id):
        """
        分析行业配置
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return None

        # 从持仓推断行业
        # 实际应该从详细持仓数据中获取，这里简化处理
        style = manager.get('investment_style', {})
        sector = style.get('sector', '')

        sectors = sector.split(',') if sector else []
        sector_details = []

        for s in sectors:
            sector_details.append({
                'name': s.strip(),
                'allocation': '主力' if len(sectors) <= 2 else '配置'
            })

        return {
            'sectors': sector_details,
            'diversification': '集中' if len(sectors) <= 2 else ('均衡' if len(sectors) <= 4 else '分散')
        }

    def analyze_holding_change(self, manager_id, period='quarter'):
        """
        分析持仓变动（从历史持仓中分析）

        参数:
            period: quarter/half_year/year
        """
        holdings = self.holdings_db.get('holdings', [])

        # 查找该经理管理的基金的持仓变化
        manager = self._find_manager(manager_id)
        if not manager:
            return None

        fund_codes = [f.get('code') for f in manager.get('fund_list', [])]
        fund_holdings = [h for h in holdings if h.get('fund_code') in fund_codes]

        if len(fund_holdings) < 2:
            return {'changes': [], 'summary': '数据不足'}

        # 简化：比较最近两个季度的持仓
        sorted_holdings = sorted(fund_holdings, key=lambda x: x.get('report_date', ''), reverse=True)

        if len(sorted_holdings) >= 2:
            latest = sorted_holdings[0]
            previous = sorted_holdings[1]

            changes = self._compare_holdings(latest, previous)
        else:
            changes = []

        return {
            'changes': changes,
            'summary': self._generate_change_summary(changes)
        }

    def find_stock_overlap(self, manager_id1, manager_id2):
        """
        计算两位经理的持仓重叠度
        """
        m1 = self._find_manager(manager_id1)
        m2 = self._find_manager(manager_id2)

        if not m1 or not m2:
            return 0

        stocks1 = set(s.get('name') for s in m1.get('top_stocks', [])[:10])
        stocks2 = set(s.get('name') for s in m2.get('top_stocks', [:10]))

        if not stocks1 or not stocks2:
            return 0

        overlap = len(stocks1 & stocks2)
        total = len(stocks1 | stocks2)

        return round(overlap / total * 100, 1) if total > 0 else 0

    def get_popular_stocks(self, top_n=20):
        """
        获取被最多基金经理持有的股票
        """
        stock_counter = Counter()

        for manager in self.managers_db.get('managers', []):
            for stock in manager.get('top_stocks', [])[:10]:
                name = stock.get('name', '')
                if name:
                    stock_counter[name] += 1

        return stock_counter.most_common(top_n)

    def get_sector_distribution(self):
        """
        获取全市场行业分布
        """
        sector_counter = Counter()

        for manager in self.managers_db.get('managers', []):
            style = manager.get('investment_style', {})
            sector = style.get('sector', '')
            if sector:
                for s in sector.split(','):
                    sector_counter[s.strip()] += 1

        return dict(sector_counter.most_common(20))

    def analyze_fof_holdings(self, manager_id):
        """
        分析FOF基金的持仓（基金投资组合）
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return None

        fof_holdings = manager.get('fof_holdings', [])

        if not fof_holdings:
            return {'has_fof': False, 'holdings': []}

        return {
            'has_fof': True,
            'holdings': fof_holdings,
            'internal_fund_ratio': self._calculate_internal_ratio(fof_holdings)
        }

    def analyze_index_tracking(self, manager_id):
        """
        分析指数跟踪情况
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return None

        tracked_index = manager.get('tracked_index', '')

        if not tracked_index:
            return {'is_index_fund': False, 'tracking_index': None}

        return {
            'is_index_fund': True,
            'tracking_index': tracked_index,
            'tracking_error': self._estimate_tracking_error(manager)
        }

    def _find_manager(self, manager_id):
        """查找基金经理"""
        for m in self.managers_db.get('managers', []):
            if m.get('manager_id') == manager_id:
                return m
        return None

    def _calculate_overall(self, stocks, bonds):
        """计算整体集中度"""
        total_weight = sum(s.get('weight', 0) for s in stocks[:10])
        total_weight += sum(b.get('weight', 0) for b in bonds[:10])

        if total_weight > 70:
            return '极高集中'
        elif total_weight > 50:
            return '高集中'
        elif total_weight > 30:
            return '中等'
        else:
            return '分散'

    def _compare_holdings(self, latest, previous):
        """比较两个时期的持仓"""
        changes = []

        latest_stocks = {s.get('name'): s.get('weight') for s in latest.get('stocks', [])}
        prev_stocks = {s.get('name'): s.get('weight') for s in previous.get('stocks', [])}

        # 新增
        for name, weight in latest_stocks.items():
            if name not in prev_stocks:
                changes.append({'stock': name, 'change': '新增', 'weight': weight})

        # 减持
        for name, weight in latest_stocks.items():
            if name in prev_stocks:
                diff = weight - prev_stocks[name]
                if diff < -0.5:
                    changes.append({'stock': name, 'change': '减持', 'diff': f"{diff:.1f}%"})

        # 增持
        for name, weight in latest_stocks.items():
            if name in prev_stocks:
                diff = weight - prev_stocks[name]
                if diff > 0.5:
                    changes.append({'stock': name, 'change': '增持', 'diff': f"+{diff:.1f}%"})

        return changes

    def _generate_change_summary(self, changes):
        """生成变动摘要"""
        if not changes:
            return '持仓基本稳定'

        adds = sum(1 for c in changes if c.get('change') == '新增')
        increases = sum(1 for c in changes if '增持' in c.get('change', ''))
        decreases = sum(1 for c in changes if '减持' in c.get('change', ''))

        parts = []
        if adds > 0:
            parts.append(f"新增{adds}只")
        if increases > 0:
            parts.append(f"增持{increases}只")
        if decreases > 0:
            parts.append(f"减持{decreases}只")

        return ', '.join(parts) if parts else '持仓基本稳定'

    def _calculate_internal_ratio(self, fof_holdings):
        """计算内部基金占比（自家产品vs外部）"""
        # 简化实现
        return 0

    def _estimate_tracking_error(self, manager):
        """估算跟踪误差"""
        # 简化实现
        return '<0.5%'

def main():
    analyzer = PortfolioAnalyzer()
    print("持仓分析引擎已加载")
    print(f"共有 {len(analyzer.holdings_db.get('holdings', []))} 条持仓记录")

if __name__ == "__main__":
    main()