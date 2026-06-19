"""
基金公司与基金经理综合分析脚本
包含：头牌经理分析、产品分布、用户评价、产品周期
"""
import json
import os
import random
from datetime import datetime, timedelta
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')

class ComprehensiveAnalyzer:
    """综合分析器"""

    def __init__(self):
        self.stage_templates = {
            '萌芽期': [
                "基金成立不久，正处于建仓期运作，需要一定时间验证投资策略的有效性。",
                "新基金还在磨合期，基金经理正在逐步调整持仓，建议观望一段时间再做决策。",
            ],
            '成长期': [
                "基金已经度过建仓期，开始展现出一定的投资特色，业绩弹性较大。",
                "规模适中，基金经理操作灵活，适合看好其投资方向的投资者。",
            ],
            '成熟期': [
                "基金运作成熟，风格稳定，业绩归因清晰，是配置的好选择。",
                "长期业绩稳健，经历过市场牛熊考验，值得信赖。",
            ],
            '老牌期': [
                "老牌基金，经历过多次市场周期，风格非常稳定。",
                "长期业绩优异，是基金中的常青树，适合长期配置。",
            ],
        }

        self.risk_templates = {
            '高风险': ['成长型', '积极型'],
            '中风险': ['均衡型', '稳健型'],
            '低风险': ['价值型', '保守型'],
        }

    def load_data(self):
        """加载数据"""
        with open(f'{DATA_DIR}/fund_companies.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)
        with open(f'{DATA_DIR}/fund_managers.json', 'r', encoding='utf-8') as f:
            managers_raw = json.load(f)
        managers = managers_raw.get('managers', managers_raw) if isinstance(managers_raw, dict) else managers_raw
        companies_list = companies.get('companies', companies) if isinstance(companies, dict) else companies
        return companies_list, managers

    def analyze_top_manager(self, manager, company_name):
        """分析头牌基金经理"""
        analysis = {
            'manager_id': manager.get('manager_id', ''),
            'name': manager.get('name', ''),
            'company': company_name,
            'fund_name': manager.get('current_fund_name', ''),
            'fund_code': manager.get('current_fund_code', ''),
            'investment_style': manager.get('investment_style', '均衡型'),
            'tenure_days': manager.get('tenure_days', 0),
            'tenure_years': round(manager.get('tenure_days', 0) / 365, 1),
            'personality_intro': manager.get('personality_intro', ''),
            'recent_views': manager.get('recent_views', []),
        }

        # 管理产品分析
        analysis['products'] = self._analyze_products(manager)

        # 持仓特点
        analysis['holdings_analysis'] = self._analyze_holdings(manager)

        # 投资风格详解
        analysis['style_detail'] = self._analyze_style_detail(manager)

        # 优势与风险
        analysis['strengths'] = self._extract_strengths(manager)
        analysis['risks'] = self._extract_risks(manager)

        # 产品周期
        analysis['fund_stage'] = self._analyze_fund_stage(manager)

        return analysis

    def _analyze_products(self, manager):
        """分析管理产品"""
        products = []

        # 当前基金
        current = {
            'name': manager.get('current_fund_name', ''),
            'code': manager.get('current_fund_code', ''),
            'type': self._infer_fund_type(manager),
            'scale': manager.get('current_fund_scale', 0),
        }
        if current['name']:
            products.append(current)

        # 历史产品列表
        fund_list = manager.get('fund_list', [])
        for fund in fund_list[:5]:
            products.append({
                'name': fund.get('fund_name', ''),
                'code': fund.get('fund_code', ''),
                'type': fund.get('fund_type', '混合型'),
            })

        return products

    def _infer_fund_type(self, manager):
        """推断基金类型"""
        style = manager.get('investment_style', '均衡型')
        if style == '成长型':
            return '股票型/偏股型'
        elif style == '价值型':
            return '混合型/偏债型'
        else:
            return '混合型/灵活配置'

    def _analyze_holdings(self, manager):
        """分析持仓特点"""
        top_stocks = manager.get('top_stocks', [])

        if not top_stocks:
            return {
                'stock_count': 0,
                'sectors': [],
                'concentration': '未知',
                'description': '暂无持仓数据'
            }

        # 行业分布
        sectors = []
        for s in top_stocks:
            sector = self._detect_sector(s.get('stock_name', ''))
            if sector:
                sectors.append(sector)

        sector_count = Counter(sectors)
        main_sectors = [s for s, _ in sector_count.most_common(3)]

        # 集中度
        weights = [s.get('weight', 0) for s in top_stocks]
        total_weight = sum(weights)
        top3_weight = sum(weights[:3]) if len(weights) >= 3 else total_weight
        concentration = '高集中' if top3_weight > 50 else ('中集中' if top3_weight > 30 else '分散')

        return {
            'stock_count': len(top_stocks),
            'sectors': main_sectors,
            'concentration': concentration,
            'top_stocks': [s.get('stock_name', '') for s in top_stocks[:5]],
            'total_weight': round(total_weight, 1) if total_weight else 0,
            'description': f"重仓{main_sectors[0] if main_sectors else '综合'}行业，前十大持仓占净值{round(top3_weight, 1)}%，{concentration}化配置。"
        }

    def _analyze_style_detail(self, manager):
        """详细分析投资风格"""
        style = manager.get('investment_style', '均衡型')
        holdings = manager.get('top_stocks', [])

        # 持仓换手率特征（从名称推断）
        stock_names = [s.get('stock_name', '') for s in holdings]
        has_long_term = any('茅台' in n or '万科' in n or '平安' in n for n in stock_names)
        has_tech = any('科技' in n or '半导体' in n or '芯片' in n for n in stock_names)

        detail = {
            'style_type': style,
            'market': 'A股为主',
            'position_style': '高仓位' if style == '成长型' else ('中仓位' if style == '均衡型' else '灵活仓位'),
            'turnover': '偏低' if style == '价值型' else ('中等' if style == '均衡型' else '偏高'),
            'focus_sectors': list(set(self._detect_sector(s.get('stock_name', '')) for s in holdings if self._detect_sector(s.get('stock_name', '')))),
        }

        if style == '成长型':
            detail['description'] = "偏好高成长赛道，如科技、新能源，持仓集中度高，追求超额收益。"
        elif style == '价值型':
            detail['description'] = "注重估值安全边际，偏好大盘蓝筹，换手率低，追求稳健回报。"
        else:
            detail['description'] = "成长与价值均衡配置，行业分散，控制回撤，追求长期稳健增值。"

        return detail

    def _extract_strengths(self, manager):
        """提取优势"""
        strengths = []
        style = manager.get('investment_style', '均衡型')

        tenure = manager.get('tenure_days', 0)
        if tenure > 365 * 5:
            strengths.append(f"任职超{tenure//365}年，经验丰富")

        top_stocks = manager.get('top_stocks', [])
        if len(top_stocks) >= 5:
            strengths.append("持仓数据完整，投研逻辑清晰")

        if style == '成长型':
            strengths.append("擅长挖掘成长股，投资风格进攻性强")
        elif style == '价值型':
            strengths.append("价值投资理念成熟，注重风险控制")
        else:
            strengths.append("风格均衡稳健，适应不同市场环境")

        if not strengths:
            strengths.append("专业背景扎实，投资逻辑清晰")

        return strengths

    def _extract_risks(self, manager):
        """提取风险点"""
        risks = []
        style = manager.get('investment_style', '均衡型')

        if style == '成长型':
            risks.append("市场波动较大，回撤可能较高")
            risks.append("高仓位运作，受市场风格切换影响大")

        if not manager.get('top_stocks'):
            risks.append("持仓数据较少，难以准确评估")

        tenure = manager.get('tenure_days', 0)
        if tenure < 365:
            risks.append("任职时间较短，业绩稳定性待验证")

        if not risks:
            risks.append("暂无明显风险提示")

        return risks

    def _analyze_fund_stage(self, manager):
        """分析产品所处阶段"""
        tenure = manager.get('tenure_days', 0)

        if tenure < 180:
            stage = '萌芽期'
        elif tenure < 365 * 2:
            stage = '成长期'
        elif tenure < 365 * 5:
            stage = '成熟期'
        else:
            stage = '老牌期'

        return {
            'stage': stage,
            'description': random.choice(self.stage_templates.get(stage, self.stage_templates['成熟期'])),
            'tenure_days': tenure,
            'suggestion': self._generate_stage_suggestion(stage, manager.get('investment_style', '均衡型'))
        }

    def _generate_stage_suggestion(self, stage, style):
        """生成阶段建议"""
        if stage == '萌芽期':
            return "建议观望，等基金度过建仓期后再考虑配置。"
        elif stage == '成长期':
            if style == '成长型':
                return "弹性较大，适合能承受波动的投资者。"
            else:
                return "风格趋于稳定，可以适当关注。"
        elif stage == '成熟期':
            return "长期业绩已验证，是核心配置的好选择。"
        else:
            return "常青树产品，适合长期定投或一次性配置。"

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

    def analyze_company_products(self, company, managers):
        """分析公司产品分布"""
        # 收集所有基金信息
        all_funds = []
        style_count = Counter()
        sector_count = Counter()

        for m in managers:
            style = m.get('investment_style', '均衡型')
            style_count[style] += 1

            for s in m.get('top_stocks', []):
                sector = self._detect_sector(s.get('stock_name', ''))
                if sector:
                    sector_count[sector] += 1

            if m.get('current_fund_name'):
                all_funds.append({
                    'fund_name': m.get('current_fund_name'),
                    'fund_code': m.get('current_fund_code'),
                    'style': style,
                    'manager': m.get('name')
                })

        # 风格分布
        total = sum(style_count.values())
        style_distribution = {
            style: {
                'count': count,
                'percentage': round(count / total * 100, 1) if total > 0 else 0
            }
            for style, count in style_count.items()
        }

        # 行业分布
        sector_distribution = {
            sector: {
                'count': count,
                'percentage': round(count / sum(sector_count.values()) * 100, 1) if sector_count else 0
            }
            for sector, count in sector_count.most_common()
        }

        return {
            'total_funds': len(all_funds),
            'style_distribution': style_distribution,
            'sector_distribution': sector_distribution,
            'product_highlights': self._generate_product_highlights(style_distribution, sector_distribution)
        }

    def _generate_product_highlights(self, style_dist, sector_dist):
        """生成产品亮点"""
        highlights = []

        # 找出占比最大的风格
        if style_dist:
            top_style = max(style_dist.items(), key=lambda x: x[1]['count'])
            style_names = {'成长型': '成长', '价值型': '价值', '均衡型': '均衡'}
            highlights.append(f"{style_names.get(top_style[0], top_style[0])}风格产品占比最高，达{top_style[1]['percentage']}%")

        # 找出最受关注的行业
        if sector_dist:
            top_sectors = list(sector_dist.items())[:2]
            sector_str = '、'.join([f"{s[0]}({s[1]['percentage']}%)" for s in top_sectors])
            highlights.append(f"重点布局行业：{sector_str}")

        return highlights

    def generate_company_report(self, company_name):
        """生成公司综合分析报告"""
        companies, managers = self.load_data()

        # 找到目标公司（支持简称匹配）
        target_company = None
        company_short = company_name.replace('基金管理有限公司', '').replace('基金有限公司', '').replace('股份有限公司', '')
        for c in companies:
            c_name = c['name']
            c_short = c.get('short_name', c_name.replace('基金管理有限公司', '').replace('基金有限公司', '').replace('股份有限公司', ''))
            if c_name == company_name or c_short == company_name or company_name in c_name or c_short in company_name:
                target_company = c
                break

        if not target_company:
            return None

        # 该公司经理（支持多种匹配方式）
        company_managers = []
        for m in managers:
            m_company = m.get('company_name', '')
            m_company_short = m_company.replace('基金管理有限公司', '').replace('基金有限公司', '').replace('股份有限公司', '')
            if m_company == company_name or m_company_short == company_short or company_short == m_company_short:
                company_managers.append(m)

        # 找头牌经理（有持仓、任期长）
        star_manager = None
        for m in company_managers:
            if m.get('tenure_days', 0) > 365 * 3 and m.get('top_stocks'):
                if not star_manager or m.get('tenure_days', 0) > star_manager.get('tenure_days', 0):
                    star_manager = m

        result = {
            'company': target_company,
            'manager_count': len(company_managers),
            'top_manager': None,
            'company_products': None,
        }

        if star_manager:
            result['top_manager'] = self.analyze_top_manager(star_manager, company_name)

        result['company_products'] = self.analyze_company_products(target_company, company_managers)

        return result


def main():
    analyzer = ComprehensiveAnalyzer()

    print("=" * 70)
    print("基金公司与基金经理综合分析")
    print("=" * 70)

    companies, managers = analyzer.load_data()
    print(f"已加载 {len(companies)} 家公司, {len(managers)} 位经理")

    # 测试：华夏基金
    print("\n" + "=" * 70)
    print("示例：华夏基金")
    print("=" * 70)

    report = analyzer.generate_company_report("华夏基金管理有限公司")
    if report:
        c = report['company']
        print(f"\n【公司概况】")
        print(f"  名称: {c['name']}")
        print(f"  简称: {c.get('short_name', c['name'])}")
        print(f"  管理规模: {c.get('total_scale', 0):.0f}亿元")
        print(f"  基金经理: {c.get('manager_count', 0)}位")
        print(f"  主导风格: {c.get('dominant_style', '均衡型')}")
        print(f"  行业聚焦: {', '.join(c.get('sector_focus', []))}")

        if report['top_manager']:
            tm = report['top_manager']
            print(f"\n【头牌基金经理】")
            print(f"  姓名: {tm['name']}")
            print(f"  管理基金: {tm['fund_name']}")
            print(f"  投资风格: {tm['investment_style']}")
            print(f"  任职年限: {tm['tenure_years']}年")
            print(f"\n  【持仓特点】")
            ha = tm['holdings_analysis']
            print(f"    重仓股数: {ha['stock_count']}")
            print(f"    行业分布: {', '.join(ha['sectors'])}")
            print(f"    集中度: {ha['concentration']}")
            print(f"    描述: {ha['description']}")
            print(f"\n  【投资风格】")
            sd = tm['style_detail']
            print(f"    风格类型: {sd['style_type']}")
            print(f"    仓位特征: {sd['position_style']}")
            print(f"    换手率: {sd['turnover']}")
            print(f"    描述: {sd['description']}")
            print(f"\n  【优势】")
            for s in tm['strengths'][:3]:
                print(f"    ✓ {s}")
            print(f"\n  【风险】")
            for r in tm['risks'][:2]:
                print(f"    ! {r}")
            print(f"\n  【产品阶段】")
            fs = tm['fund_stage']
            print(f"    阶段: {fs['stage']}")
            print(f"    描述: {fs['description']}")
            print(f"    建议: {fs['suggestion']}")

        if report['company_products']:
            cp = report['company_products']
            print(f"\n【产品分布】")
            print(f"  基金总数: {cp['total_funds']}")
            print(f"  风格分布:")
            for style, info in cp['style_distribution'].items():
                print(f"    {style}: {info['count']}只({info['percentage']}%)")
            print(f"  行业分布:")
            for sector, info in list(cp['sector_distribution'].items())[:5]:
                print(f"    {sector}: {info['count']}次({info['percentage']}%)")
            print(f"  产品亮点:")
            for h in cp['product_highlights']:
                print(f"    • {h}")

    print("\n" + "=" * 70)
    print("分析完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()