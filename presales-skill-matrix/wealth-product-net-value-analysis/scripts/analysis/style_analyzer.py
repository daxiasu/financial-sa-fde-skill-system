"""
投资风格分析引擎
基于持仓数据、净值波动、季报表述综合判断基金经理/基金公司的投资风格
"""
import json
import math
from collections import Counter

class StyleAnalyzer:
    """投资风格分析器"""

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
            with open(f'{self.db_path}/style_profiles.json', 'r', encoding='utf-8') as f:
                self.style_profiles = json.load(f)
        except:
            self.style_profiles = {'styles': []}

    def analyze_manager_style(self, manager_id):
        """
        分析基金经理的投资风格

        返回风格标签如：GROWTH-A_SHARE-HIGH_POS-SECTOR_CONCENTRATED
        """
        manager = self._find_manager(manager_id)
        if not manager:
            return None

        # 1. 基于持仓数据判断
        style_factors = []

        # 股票仓位判断
        top_stocks = manager.get('top_stocks', [])
        total_weight = sum(s.get('weight', 0) for s in top_stocks)
        if total_weight > 70:
            style_factors.append('HIGH_POS')
        elif total_weight > 50:
            style_factors.append('MED_POS')
        else:
            style_factors.append('LOW_POS')

        # 行业集中度判断
        sector = manager.get('investment_style', {}).get('sector', '')
        if sector and len(sector.split(',')) <= 2:
            style_factors.append('SECTOR_CONCENTRATED')
        else:
            style_factors.append('SECTOR_DIVERSIFIED')

        # 换手率判断
        turnover = manager.get('investment_style', {}).get('turnover', '')
        if '高' in turnover or '150%' in turnover or '200%' in turnover:
            style_factors.append('HIGH_TURNOVER')
        elif '低' in turnover or '50%' in turnover or '80%' in turnover:
            style_factors.append('LOW_TURNOVER')
        else:
            style_factors.append('MED_TURNOVER')

        # 2. 基于投资类型判断
        inv_type = manager.get('investment_style', {}).get('type', '')
        if '成长' in inv_type:
            style_factors.insert(0, 'GROWTH')
        elif '价值' in inv_type:
            style_factors.insert(0, 'VALUE')
        elif '均衡' in inv_type or '平衡' in inv_type:
            style_factors.insert(0, 'BALANCED')
        else:
            style_factors.insert(0, 'BALANCED')

        # 3. 基于市场覆盖判断
        market = manager.get('investment_style', {}).get('market', '')
        if '港股' in market:
            style_factors.append('HK_SHARE')
        if '美股' in market:
            style_factors.append('US_SHARE')
        if 'QDII' in market or '全球' in market:
            style_factors.append('GLOBAL')
        if not any(x in style_factors for x in ['HK_SHARE', 'US_SHARE', 'GLOBAL']):
            style_factors.append('A_SHARE')

        return '-'.join(style_factors)

    def analyze_company_style(self, company_id):
        """
        分析基金公司的整体投资风格
        """
        company = self._find_company(company_id)
        if not company:
            return None

        # 统计旗下基金经理的风格分布
        manager_ids = company.get('manager_list', [])
        style_counter = Counter()

        for mid in manager_ids:
            style = self.analyze_manager_style(mid)
            if style:
                # 取第一个主要风格
                main_style = style.split('-')[0]
                style_counter[main_style] += 1

        if style_counter:
            dominant_style = style_counter.most_common(1)[0][0]
        else:
            dominant_style = 'BALANCED'

        return dominant_style

    def match_investor_style(self, risk_preference):
        """
        根据投资者风险偏好匹配风格

        参数:
            risk_preference: 保守型/稳健型/积极型/激进型

        返回:
            list: 适合的风格标签列表
        """
        mapping = {
            '保守型': ['VALUE-A_SHARE-MED_POS-SECTOR_DIVERSIFIED', 'VALUE-A_SHARE-LOW_POS-LOW_TURNOVER', 'DIVIDEND_LOW_VOL'],
            '稳健型': ['BALANCED-A_SHARE-MED_POS-MED_TURNOVER', 'VALUE-GROWTH-A_SHARE-HIGH_POS', 'FLEXIBLE_ALLOCATION'],
            '积极型': ['GROWTH-A_SHARE-HIGH_POS-HIGH_TURNOVER', 'GROWTH-HK_SHARE-HIGH_POS', 'AGGRESSIVE_GROWTH'],
            '激进型': ['GROWTH-A_SHARE-HIGH_POS-SECTOR_CONCENTRATED', 'GROWTH-US_SHARE-HIGH_POS-HIGH_TURNOVER']
        }

        return mapping.get(risk_preference, mapping['稳健型'])

    def compare_styles(self, style1, style2):
        """
        比较两个风格的相似度

        返回:
            float: 相似度 0-1
        """
        set1 = set(style1.split('-'))
        set2 = set(style2.split('-'))

        if not set1 or not set2:
            return 0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0

    def find_similar_managers(self, manager_id, top_n=5):
        """
        查找风格相似的基金经理
        """
        target_style = self.analyze_manager_style(manager_id)
        if not target_style:
            return []

        similar = []
        for manager in self.managers_db.get('managers', []):
            if manager.get('manager_id') == manager_id:
                continue

            style = self.analyze_manager_style(manager.get('manager_id'))
            if style:
                similarity = self.compare_styles(target_style, style)
                similar.append({
                    'manager_id': manager.get('manager_id'),
                    'name': manager.get('name'),
                    'style': style,
                    'similarity': similarity
                })

        similar.sort(key=lambda x: x['similarity'], reverse=True)
        return similar[:top_n]

    def _find_manager(self, manager_id):
        """查找基金经理"""
        for m in self.managers_db.get('managers', []):
            if m.get('manager_id') == manager_id:
                return m
        return None

    def _find_company(self, company_id):
        """查找基金公司"""
        try:
            with open(f'{self.db_path}/fund_companies.json', 'r', encoding='utf-8') as f:
                companies_db = json.load(f)
                for c in companies_db.get('companies', []):
                    if c.get('company_id') == company_id:
                        return c
        except:
            pass
        return None

    def get_style_description(self, style_code):
        """获取风格的文字描述"""
        descriptions = {
            'GROWTH': '成长型 - 偏好高成长标的，容忍较高估值',
            'VALUE': '价值型 - 偏好低估值、高分红标的',
            'BALANCED': '均衡型 - 兼顾成长与价值',
            'HIGH_POS': '高仓位 - 股票仓位长期高于85%',
            'MED_POS': '中等仓位 - 股票仓位60-85%',
            'LOW_POS': '低仓位 - 股票仓位低于60%',
            'SECTOR_CONCENTRATED': '行业集中 - 专注2个以内行业',
            'SECTOR_DIVERSIFIED': '行业分散 - 配置多个行业',
            'HIGH_TURNOVER': '高换手 - 年换手率高于200%',
            'MED_TURNOVER': '中等换手 - 年换手率100-200%',
            'LOW_TURNOVER': '低换手 - 年换手率低于100%',
            'A_SHARE': 'A股为主',
            'HK_SHARE': '配置港股',
            'US_SHARE': '配置美股',
            'GLOBAL': '全球配置'
        }

        parts = style_code.split('-')
        desc_parts = [descriptions.get(p, p) for p in parts]
        return ' / '.join(desc_parts)

def main():
    analyzer = StyleAnalyzer()

    # 示例：分析某经理风格
    print("投资风格分析器已加载")
    print(f"共有 {len(analyzer.managers_db.get('managers', []))} 位基金经理数据")

def __name__ == "__main__":
    main()