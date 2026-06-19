"""
基金经理和基金公司综合蒸馏脚本
优化：字段补全、数据增强、投顾话术
"""
import json
import os
import random
from datetime import datetime
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')


class ManagerDistiller:
    """基金经理蒸馏器"""

    def __init__(self):
        self.investment_advice = {
            '成长型': [
                "适合风险承受能力较强、追求长期资本增值的投资者，建议采用定投方式参与。",
                "波动较大，建议闲置资金配置，避免追涨杀跌，长期持有效果更佳。",
                "适合投资周期3年以上的投资者，可作为卫星配置。",
            ],
            '价值型': [
                "适合追求稳健收益、控制回撤的投资者，波动相对较小。",
                "建议长期持有，享受复利增长，适合养老金、教育金规划。",
                "适合1-3年中长期投资，是资产组合的压舱石。",
            ],
            '均衡型': [
                "适合希望均衡配置、分散风险的投资者，风格稳健。",
                "不赌单一方向，适应不同市场环境，适合定投和一次性配置。",
                "适合2-5年投资周期，作为核心配置值得关注。",
            ],
        }

        self.risk_warnings = {
            '成长型': "高波动品种，短期回撤可能较大，请评估自身风险承受能力。",
            '价值型': "注意估值波动，价值回归需要时间，需保持耐心。",
            '均衡型': "均衡配置不等于无风险，市场大幅下跌时仍可能受损。",
        }

    def load_data(self):
        """加载数据 - 优先使用天天基金原始数据文件"""
        # 优先从天天基金原始数据加载
        ttj_raw_path = f'{DATA_DIR}/全市场基金经理名录_天天基金.json'
        if os.path.exists(ttj_raw_path):
            with open(ttj_raw_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            managers = self._convert_ttj_format(raw_data.get('raw', []))
            print(f"从天天基金原始数据加载 {len(managers)} 条记录")
        else:
            # 回退到fund_managers.json（如果存在）
            with open(f'{DATA_DIR}/fund_managers.json', 'r', encoding='utf-8') as f:
                managers_raw = json.load(f)
            managers = managers_raw.get('managers', managers_raw)

        with open(f'{DATA_DIR}/external_data.json', 'r', encoding='utf-8') as f:
            external = json.load(f)
        return managers, external

    def _convert_ttj_format(self, raw_list):
        """将天天基金原始格式转换为标准经理格式"""
        managers = []
        for row in raw_list:
            if len(row) < 6:
                continue
            funds = row[4].split(',') if row[4] else []
            fund_names = row[5].split(',') if row[5] else []
            primary_fund = funds[0] if funds else ''
            primary_fund_name = fund_names[0] if fund_names else ''

            manager = {
                'manager_id': str(row[0]),
                'name': str(row[1]),
                'company_id': str(row[2]),
                'company_name': str(row[3]),
                'current_fund_code': primary_fund,
                'current_fund_name': primary_fund_name,
                'tenure_days': int(row[6]) if row[6].isdigit() else 0,
                'best_return': str(row[7]) if len(row) > 7 else '',
                'all_funds': funds,
                'all_fund_names': fund_names,
            }
            managers.append(manager)
        return managers

    def distill(self):
        """蒸馏所有经理"""
        managers, external = self.load_data()
        print(f"开始蒸馏 {len(managers)} 位基金经理...")

        # 保存原始数据用于最终返回
        managers_raw = {'managers': managers, 'meta': {}}

        # 建立基金代码到外部数据的映射
        ratings_map = {}
        for r in external.get('ratings', []):
            code = r.get('fund_code', '')
            if code:
                ratings_map[code] = r

        analysis_map = {}
        for a in external.get('analysis', []):
            code = a.get('fund_code', '')
            if code not in analysis_map:
                analysis_map[code] = []
            analysis_map[code].append(a)

        profit_map = {}
        for p in external.get('profit_probability', []):
            code = p.get('fund_code', '')
            if code not in profit_map:
                profit_map[code] = []
            profit_map[code].append(p)

        distilled = []
        for m in managers:
            distilled_m = self.distill_manager(m, ratings_map, analysis_map, profit_map)
            distilled.append(distilled_m)

            if len(distilled) % 5000 == 0:
                print(f"进度: {len(distilled)}/{len(managers)}")

        return {'managers': distilled, 'meta': {'total': len(distilled), 'last_update': datetime.now().strftime('%Y-%m-%d')}}

    def distill_manager(self, m, ratings_map, analysis_map, profit_map):
        """蒸馏单个经理"""
        fund_code = str(m.get('current_fund_code', ''))
        style = m.get('investment_style', '均衡型')
        top_stocks = m.get('top_stocks', [])
        tenure = m.get('tenure_days', 0)

        # 提取行业
        sectors = []
        for s in top_stocks:
            sector = self._detect_sector(s.get('stock_name', ''))
            if sector:
                sectors.append(sector)
        sector_count = Counter(sectors)
        main_sectors = [s for s, _ in sector_count.most_common(3)]

        # 外部数据
        rating = ratings_map.get(fund_code, {})
        analysis = analysis_map.get(fund_code, [])
        profit = profit_map.get(fund_code, [])

        # 确定阶段
        if tenure < 180:
            stage = '萌芽期'
        elif tenure < 365 * 2:
            stage = '成长期'
        elif tenure < 365 * 5:
            stage = '成熟期'
        else:
            stage = '老牌期'

        # 构建完整档案
        distilled = {
            # 基本信息
            'manager_id': m.get('manager_id', ''),
            'name': m.get('name', ''),
            'company_id': m.get('company_id', ''),
            'company_name': m.get('company_name', ''),
            'current_fund_name': m.get('current_fund_name', ''),
            'current_fund_code': m.get('current_fund_code', ''),
            'investment_style': style,
            'tenure_days': tenure,
            'tenure_years': round(tenure / 365, 1),

            # 持仓信息
            'top_stocks': top_stocks,
            'sectors': main_sectors,
            'sector_description': f"重点布局{main_sectors[0] if main_sectors else '综合'}行业",
            'holdings_count': len(top_stocks),

            # 评级数据
            'rating': {
                'morning_star': rating.get('morning_star', 0),
                'cms': rating.get('cms_star', 0),
                'jajx': rating.get('jajx_star', 0),
                'shanghai': rating.get('shanghai_star', 0),
                'fund_type': rating.get('fund_type', ''),
            } if rating else None,

            # 风险收益指标
            'risk_metrics': self._extract_risk_metrics(analysis),

            # 收益概率
            'profit_probability': self._extract_profit_probability(profit),

            # 投资目标与范围
            'investment_goal': m.get('investment_goal', '追求长期稳健的资本增值'),
            'investment_scope': m.get('investment_scope', ''),

            # 近期观点（人性化话术）
            'recent_views': m.get('recent_views', []),
            'personality_intro': m.get('personality_intro', ''),

            # 投顾建议
            'investment_advice': random.choice(self.investment_advice.get(style, self.investment_advice['均衡型'])),
            'risk_warning': self.risk_warnings.get(style, ''),
            'suitable_investors': self._get_suitable_investors(style),
            'investment_period': self._get_investment_period(style),

            # 产品阶段
            'fund_stage': stage,
            'stage_description': self._get_stage_description(stage),

            # 优势特点
            'strengths': self._extract_strengths(m),

            # 最后更新
            'last_updated': datetime.now().strftime('%Y-%m-%d'),
        }

        return distilled

    def _detect_sector(self, stock_name):
        """判断股票行业"""
        sector_keywords = {
            '科技': ['科技', '软', '硬', '电子', '通信', '计算机', '半导体', '芯片', 'AI', '人工智能'],
            '新能源': ['新能源', '光伏', '锂', '电池', '储能', '电动车', '汽车', '动力'],
            '消费': ['酒', '消费', '食品', '饮料', '家电', '商贸', '旅游', '酒店'],
            '医药': ['医药', '医疗', '生物', '疫苗', '中药', '健康'],
            '金融': ['银行', '保险', '券商', '信托', '地产', '物业'],
            '制造': ['机械', '化工', '材料', '军工', '航空', '制造', '设备'],
        }
        for sector, keywords in sector_keywords.items():
            if any(kw in stock_name for kw in keywords):
                return sector
        return None

    def _extract_risk_metrics(self, analysis):
        """提取风险指标"""
        if not analysis:
            return None

        best = {'sharpe_ratio': 0, 'max_drawdown': 0, 'volatility': 0}
        for a in analysis:
            period = a.get('period', '')
            if '近1年' in period:
                if a.get('sharpe_ratio', 0) > best['sharpe_ratio']:
                    best['sharpe_ratio'] = a['sharpe_ratio']
                if a.get('max_drawdown', 0) < best['max_drawdown']:
                    best['max_drawdown'] = a['max_drawdown']
                best['volatility'] = a.get('annual_volatility', 0)

        if best['sharpe_ratio'] > 0:
            return {
                'sharpe_ratio': round(best['sharpe_ratio'], 2),
                'max_drawdown': round(best['max_drawdown'], 2),
                'annual_volatility': round(best['volatility'], 2),
            }
        return None

    def _extract_profit_probability(self, profit):
        """提取收益概率"""
        if not profit:
            return None

        # 找1年和3年的数据
        result = {}
        for p in profit:
            period = p.get('holding_period', '')
            if '满1年' in period:
                result['1year'] = {'prob': p.get('profit_probability', 0), 'avg_return': p.get('avg_return', 0)}
            elif '满3年' in period:
                result['3year'] = {'prob': p.get('profit_probability', 0), 'avg_return': p.get('avg_return', 0)}

        return result if result else None

    def _get_suitable_investors(self, style):
        """适合的投资者类型"""
        mapping = {
            '成长型': '积极型投资者，能承受较大波动，追求长期高收益',
            '价值型': '稳健型投资者，注重风险控制，追求稳定回报',
            '均衡型': '平衡型投资者，希望收益与风险平衡',
        }
        return mapping.get(style, '平衡型投资者')

    def _get_investment_period(self, style):
        """建议投资周期"""
        mapping = {
            '成长型': '3-5年以上',
            '价值型': '1-3年',
            '均衡型': '2-5年',
        }
        return mapping.get(style, '3年')

    def _get_stage_description(self, stage):
        """阶段描述"""
        desc = {
            '萌芽期': '新基金，建仓期运作，需要时间验证',
            '成长期': '风格形成，业绩弹性较大',
            '成熟期': '业绩稳定，风格清晰',
            '老牌期': '历经牛熊，长期稳健',
        }
        return desc.get(stage, '')

    def _extract_strengths(self, m):
        """提取优势"""
        strengths = []
        style = m.get('investment_style', '均衡型')
        tenure = m.get('tenure_days', 0)

        if tenure > 365 * 5:
            strengths.append(f"{tenure//365}年投资经验")
        elif tenure > 365 * 3:
            strengths.append(f"近{tenure//365}年任职经验")

        if m.get('top_stocks'):
            strengths.append("持仓透明，逻辑清晰")

        if style == '成长型':
            strengths.append("成长投资能力")
        elif style == '价值型':
            strengths.append("价值挖掘能力")
        else:
            strengths.append("均衡配置能力")

        return strengths[:3]


class CompanyDistiller:
    """基金公司蒸馏器"""

    def load_data(self):
        """加载数据"""
        with open(f'{DATA_DIR}/fund_companies.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)
        with open(f'{DATA_DIR}/company_reports_enhanced.json', 'r', encoding='utf-8') as f:
            enhanced = json.load(f)
        return companies.get('companies', companies), enhanced.get('reports', enhanced)

    def distill(self):
        """蒸馏所有公司"""
        companies, enhanced_reports = self.load_data()
        print(f"开始蒸馏 {len(companies)} 家基金公司...")

        # 建立公司名到增强报告的映射
        enhanced_map = {}
        for r in enhanced_reports:
            name = r.get('name', '')
            enhanced_map[name] = r

        distilled = []
        for c in companies:
            name = c.get('name', '')
            enhanced = enhanced_map.get(name, {})
            distilled_c = self.distill_company(c, enhanced)
            distilled.append(distilled_c)

        return {'companies': distilled, 'meta': {'total': len(distilled), 'last_update': datetime.now().strftime('%Y-%m-%d')}}

    def distill_company(self, c, enhanced):
        """蒸馏单个公司"""
        # 整合所有数据
        rating = enhanced.get('company_rating', {})
        analysis = enhanced.get('company_analysis', {})
        profit = enhanced.get('company_profit', {})
        stage_dist = enhanced.get('stage_distribution', {})
        evaluation = enhanced.get('overall_evaluation', [])

        return {
            # 基本信息
            'company_id': c.get('company_id', ''),
            'name': c.get('name', ''),
            'short_name': c.get('short_name', ''),
            'type': c.get('type', '公募'),
            'total_scale': c.get('total_scale', 0),
            'scale_category': c.get('scale_category', ''),
            'founded_date': c.get('founded_date', ''),
            'manager_count': c.get('manager_count', 0),
            'total_funds': c.get('total_funds', 0),

            # 风格分布
            'dominant_style': c.get('dominant_style', '均衡型'),
            'style_distribution': c.get('style_distribution', {}),

            # 行业分布
            'top_sectors': c.get('top_sectors', []),
            'sector_focus': c.get('sector_focus', []),

            # 评级情况
            'rating_info': {
                'has_data': rating.get('has_data', False),
                'avg_star': rating.get('avg_star', 0),
                'five_star_count': rating.get('five_star_count', 0),
                'total_rated': rating.get('total_rated_funds', 0),
            } if rating else None,

            # 风险收益
            'risk_analysis': {
                'has_data': analysis.get('has_data', False),
                'best_sharpe': analysis.get('best_sharpe', 0),
                'worst_drawdown': analysis.get('worst_drawdown', 0),
            } if analysis else None,

            # 收益概率
            'profit_analysis': {
                'has_data': profit.get('has_data', False),
                '1year_prob': profit.get('period_stats', {}).get('满1年', {}).get('avg_profit_prob', 0),
                '3year_prob': profit.get('period_stats', {}).get('满3年', {}).get('avg_profit_prob', 0),
            } if profit else None,

            # 产品周期分布
            'stage_distribution': stage_dist,

            # 综合评价
            'highlights': c.get('highlights', []),
            'overall_evaluation': evaluation,

            # 公司画像
            'company_intro': c.get('company_intro', ''),
            'investment_philosophy': c.get('investment_philosophy', ''),
            'culture': c.get('culture', ''),
            'recommendation': c.get('recommendation', ''),
            'slogan': c.get('slogan', ''),

            # 头牌经理
            'top_manager': enhanced.get('top_manager') if enhanced else None,

            # 竞争力分析
            'competitive_advantages': self._extract_advantages(c, enhanced),
            'suitable_investors': self._extract_suitable_investors(c),
            'investment_suggestion': self._extract_suggestion(c),

            # 更新时间
            'last_updated': datetime.now().strftime('%Y-%m-%d'),
        }

    def _extract_advantages(self, c, enhanced):
        """提取竞争优势"""
        advantages = []
        scale = c.get('total_scale', 0)

        if scale > 10000:
            advantages.append("行业龙头，规模领先")
        elif scale > 5000:
            advantages.append("第一梯队，综合实力强")
        elif scale > 1000:
            advantages.append("中大型，稳健发展")
        else:
            advantages.append("特色发展，专注细分")

        rating = enhanced.get('company_rating', {})
        if rating.get('has_data') and rating.get('avg_star', 0) >= 3.5:
            advantages.append(f"平均{rating['avg_star']}星评级")

        analysis = enhanced.get('company_analysis', {})
        if analysis.get('has_data') and analysis.get('best_sharpe', 0) > 1.5:
            advantages.append("风险收益比优异")

        return advantages[:4]

    def _extract_suitable_investors(self, c):
        """适合的投资者"""
        style = c.get('dominant_style', '均衡型')
        mapping = {
            '成长型': '积极型投资者',
            '价值型': '稳健型投资者',
            '均衡型': '各类投资者',
        }
        return mapping.get(style, '各类投资者')

    def _extract_suggestion(self, c):
        """投资建议"""
        scale = c.get('total_scale', 0)
        style = c.get('dominant_style', '均衡型')

        suggestions = []
        if scale > 5000:
            suggestions.append("综合实力强，可作为核心配置")
        if style == '成长型':
            suggestions.append("成长风格突出，适合定投")
        elif style == '价值型':
            suggestions.append("价值风格稳健，适合长期持有")
        else:
            suggestions.append("均衡风格，适合资产配置")

        return '；'.join(suggestions) if suggestions else "综合实力较强，可关注"


def main():
    print("=" * 60)
    print("基金经理和基金公司综合蒸馏")
    print("=" * 60)

    # 1. 蒸馏基金经理
    print("\n[1/2] 蒸馏基金经理...")
    manager_distiller = ManagerDistiller()
    managers_result = manager_distiller.distill()

    managers_path = f'{DATA_DIR}/fund_managers_distilled.json'
    with open(managers_path, 'w', encoding='utf-8') as f:
        json.dump(managers_result, f, ensure_ascii=False, indent=2)
    print(f"基金经理档案已保存: {len(managers_result['managers'])} 条")

    # 2. 蒸馏基金公司
    print("\n[2/2] 蒸馏基金公司...")
    company_distiller = CompanyDistiller()
    companies_result = company_distiller.distill()

    companies_path = f'{DATA_DIR}/fund_companies_distilled.json'
    with open(companies_path, 'w', encoding='utf-8') as f:
        json.dump(companies_result, f, ensure_ascii=False, indent=2)
    print(f"基金公司档案已保存: {len(companies_result['companies'])} 条")

    # 展示示例
    print("\n" + "=" * 60)
    print("示例 - 华夏基金头牌经理")
    print("=" * 60)

    for m in managers_result['managers']:
        if '艾邦妮' in m.get('name', '') and m.get('top_stocks'):
            print(f"\n【艾邦妮】")
            print(f"  公司: {m['company_name']}")
            print(f"  基金: {m['current_fund_name']}")
            print(f"  风格: {m['investment_style']}")
            print(f"  任期: {m['tenure_years']}年")
            print(f"  行业: {m['sector_description']}")
            print(f"  评级: 晨星{int(m['rating']['morning_star']) if m['rating'] else 0}星" if m.get('rating') else "  评级: 无数据")
            print(f"  风险指标: 夏普{int(m['risk_metrics']['sharpe_ratio']) if m.get('risk_metrics') else '无'} | 回撤{m['risk_metrics']['max_drawdown'] if m.get('risk_metrics') else '无'}%")
            print(f"  收益概率: 1年{m['profit_probability']['1year']['prob'] if m.get('profit_probability') else '无'}%")
            print(f"  适合投资者: {m['suitable_investors']}")
            print(f"  投资周期: {m['investment_period']}")
            print(f"  投资建议: {m['investment_advice'][:50]}...")
            print(f"  风险提示: {m['risk_warning'][:30]}...")
            print(f"  优势: {', '.join(m['strengths'])}")
            print(f"  产品阶段: {m['fund_stage']} - {m['stage_description']}")
            break

    print("\n" + "=" * 60)
    print("蒸馏完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()