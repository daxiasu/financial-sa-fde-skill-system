"""
增强型公司报告生成器
整合：基金评级、收益概率、风险指标、产品周期
"""
import json
import os
from datetime import datetime
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')

class EnhancedCompanyReport:
    """增强型公司报告生成器"""

    def __init__(self):
        self.stage_templates = {
            '萌芽期': {
                'desc': '基金成立不久，正处于建仓期运作，需要一定时间验证投资策略的有效性。',
                'advice': '建议观望，等基金度过建仓期后再考虑配置。',
                'risk_level': '高',
                'suitability': '高风险偏好投资者'
            },
            '成长期': {
                'desc': '基金已经度过建仓期，开始展现出一定的投资特色，业绩弹性较大。',
                'advice': '风格趋于稳定，可以适当关注。',
                'risk_level': '中高',
                'suitability': '中高风险偏好投资者'
            },
            '成熟期': {
                'desc': '基金运作成熟，风格稳定，业绩归因清晰，是配置的好选择。',
                'advice': '长期业绩已验证，是核心配置的好选择。',
                'risk_level': '中',
                'suitability': '中等风险偏好投资者'
            },
            '老牌期': {
                'desc': '老牌基金，经历过多次市场周期，风格非常稳定。',
                'advice': '常青树产品，适合长期定投或一次性配置。',
                'risk_level': '中低',
                'suitability': '各类投资者均可考虑'
            },
        }

    def load_all_data(self):
        """加载所有数据"""
        with open(f'{DATA_DIR}/fund_companies.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)
        with open(f'{DATA_DIR}/fund_managers.json', 'r', encoding='utf-8') as f:
            managers_raw = json.load(f)
        with open(f'{DATA_DIR}/company_reports.json', 'r', encoding='utf-8') as f:
            reports = json.load(f)
        with open(f'{DATA_DIR}/external_data.json', 'r', encoding='utf-8') as f:
            external = json.load(f)

        managers = managers_raw.get('managers', managers_raw)
        companies_list = companies.get('companies', companies)

        # 建立基金代码到评级的映射
        ratings_map = {}
        for r in external.get('ratings', []):
            code = r.get('fund_code', '')
            ratings_map[code] = r

        # 建立基金代码到分析的映射
        analysis_map = {}
        for a in external.get('analysis', []):
            code = a.get('fund_code', '')
            if code not in analysis_map:
                analysis_map[code] = []
            analysis_map[code].append(a)

        # 建立基金代码到收益概率的映射
        profit_map = {}
        for p in external.get('profit_probability', []):
            code = p.get('fund_code', '')
            if code not in profit_map:
                profit_map[code] = []
            profit_map[code].append(p)

        return companies_list, managers, reports, ratings_map, analysis_map, profit_map

    def detect_sector(self, stock_name):
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
        return '综合'

    def determine_stage(self, tenure_days):
        """判断产品所处阶段"""
        if tenure_days < 180:
            return '萌芽期'
        elif tenure_days < 365 * 2:
            return '成长期'
        elif tenure_days < 365 * 5:
            return '成熟期'
        else:
            return '老牌期'

    def generate_enhanced_reports(self):
        """生成增强型报告"""
        print("=" * 60)
        print("开始生成增强型公司报告")
        print("=" * 60)

        companies, managers, reports_data, ratings_map, analysis_map, profit_map = self.load_all_data()
        reports = reports_data.get('reports', reports_data)  # 支持列表或 {'reports': [...]}
        print(f"公司: {len(companies)}, 经理: {len(managers)}, 已有报告: {len(reports)}")

        enhanced = []
        stats = {'updated': 0, 'ratings_found': 0, 'analysis_found': 0}

        for report in reports:
            company_name = report['name']

            # 获取该公司的经理
            company_managers = []
            for m in managers:
                m_company = m.get('company_name', '')
                m_short = m_company.replace('基金管理有限公司', '').replace('基金有限公司', '').replace('股份有限公司', '')
                c_short = company_name.replace('基金管理有限公司', '').replace('基金有限公司', '').replace('股份有限公司', '')
                if m_company == company_name or m_short == c_short:
                    company_managers.append(m)

            # 收集该公司所有基金的评级和分析数据
            all_ratings = []
            all_analysis = []
            all_profit = []

            for m in company_managers:
                fund_code = str(m.get('current_fund_code', ''))
                if fund_code and fund_code in ratings_map:
                    all_ratings.append(ratings_map[fund_code])
                    stats['ratings_found'] += 1
                if fund_code and fund_code in analysis_map:
                    all_analysis.extend(analysis_map[fund_code])
                    stats['analysis_found'] += 1
                if fund_code and fund_code in profit_map:
                    all_profit.extend(profit_map[fund_code])

            # 计算公司整体评级情况
            company_rating_info = self._analyze_company_ratings(all_ratings)
            company_analysis_info = self._analyze_company_analysis(all_analysis)
            company_profit_info = self._analyze_company_profit(all_profit)

            # 更新报告
            report['company_rating'] = company_rating_info
            report['company_analysis'] = company_analysis_info
            report['company_profit'] = company_profit_info

            # 更新头牌经理的评级信息
            if report.get('top_manager'):
                tm = report['top_manager']
                fund_code = ''

                # 找到该经理对应的基金代码
                for m in company_managers:
                    if m.get('name') == tm['name']:
                        fund_code = str(m.get('current_fund_code', ''))
                        break

                if fund_code and fund_code in ratings_map:
                    tm['rating'] = ratings_map[fund_code]
                if fund_code and fund_code in analysis_map:
                    tm['analysis'] = analysis_map.get(fund_code, [])
                if fund_code and fund_code in profit_map:
                    tm['profit_probability'] = profit_map.get(fund_code, [])

                # 更新产品周期
                for m in company_managers:
                    if m.get('name') == tm['name']:
                        tenure = m.get('tenure_days', 0)
                        stage = self.determine_stage(tenure)
                        stage_info = self.stage_templates.get(stage, self.stage_templates['成熟期'])
                        tm['fund_stage'] = stage
                        tm['stage_info'] = stage_info
                        break

            # 产品周期分布
            stage_dist = Counter()
            for m in company_managers:
                tenure = m.get('tenure_days', 0)
                stage = self.determine_stage(tenure)
                stage_dist[stage] += 1

            report['stage_distribution'] = {
                stage: {'count': count, 'percentage': round(count/len(company_managers)*100, 1)}
                for stage, count in stage_dist.items()
            }

            # 生成综合评价
            report['overall_evaluation'] = self._generate_evaluation(report)

            stats['updated'] += 1
            if stats['updated'] % 20 == 0:
                print(f"进度: {stats['updated']}/{len(reports)}")

            enhanced.append(report)

        # 保存增强型报告
        output_path = f'{DATA_DIR}/company_reports_enhanced.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'reports': enhanced,
                'meta': {
                    'total': len(enhanced),
                    'last_update': datetime.now().strftime('%Y-%m-%d'),
                    'stats': stats
                }
            }, f, ensure_ascii=False, indent=2)

        print(f"\n生成完成!")
        print(f"增强报告: {len(enhanced)}")
        print(f"找到评级: {stats['ratings_found']}")
        print(f"找到分析: {stats['analysis_found']}")
        print(f"保存至: {output_path}")

        return enhanced

    def _analyze_company_ratings(self, ratings):
        """分析公司评级情况"""
        if not ratings:
            return {'has_data': False, 'avg_star': 0, 'distribution': {}}

        # 计算平均星级
        stars = []
        for r in ratings:
            ms = r.get('morning_star', 0)
            if ms and ms > 0:
                stars.append(ms)

        avg_star = sum(stars) / len(stars) if stars else 0

        # 星级分布
        star_dist = Counter(stars)
        distribution = {i: star_dist.get(i, 0) for i in range(1, 6)}

        # 5星基金数量
        five_star_count = sum(1 for r in ratings if r.get('morning_star', 0) == 5)

        return {
            'has_data': True,
            'avg_star': round(avg_star, 2),
            'five_star_count': five_star_count,
            'total_rated_funds': len(ratings),
            'distribution': distribution,
        }

    def _analyze_company_analysis(self, analysis):
        """分析公司风险收益特征"""
        if not analysis:
            return {'has_data': False}

        # 按周期分组
        by_period = {}
        for a in analysis:
            period = a.get('period', '')
            if period not in by_period:
                by_period[period] = []
            by_period[period].append(a)

        # 计算各周期平均
        period_avg = {}
        for period, items in by_period.items():
            sharpe = [i.get('sharpe_ratio', 0) for i in items if i.get('sharpe_ratio')]
            drawdown = [i.get('max_drawdown', 0) for i in items if i.get('max_drawdown')]
            volatility = [i.get('annual_volatility', 0) for i in items if i.get('annual_volatility')]

            period_avg[period] = {
                'avg_sharpe': sum(sharpe) / len(sharpe) if sharpe else 0,
                'avg_drawdown': sum(drawdown) / len(drawdown) if drawdown else 0,
                'avg_volatility': sum(volatility) / len(volatility) if volatility else 0,
            }

        # 获取最好的几个指标
        best_sharpe = max((a['sharpe_ratio'] for a in analysis if a.get('sharpe_ratio')), default=0)
        worst_drawdown = min((a['max_drawdown'] for a in analysis if a.get('max_drawdown')), default=0)

        return {
            'has_data': True,
            'periods': list(period_avg.keys()),
            'period_avg': period_avg,
            'best_sharpe': round(best_sharpe, 2),
            'worst_drawdown': round(worst_drawdown, 2),
        }

    def _analyze_company_profit(self, profit):
        """分析公司收益概率"""
        if not profit:
            return {'has_data': False}

        # 按持有期分组
        by_period = {}
        for p in profit:
            period = p.get('holding_period', '')
            if period not in by_period:
                by_period[period] = []
            by_period[period].append(p)

        # 计算各期平均
        period_stats = {}
        for period, items in by_period.items():
            prob = [i.get('profit_probability', 0) for i in items]
            ret = [i.get('avg_return', 0) for i in items]
            period_stats[period] = {
                'avg_profit_prob': sum(prob) / len(prob) if prob else 0,
                'avg_return': sum(ret) / len(ret) if ret else 0,
            }

        return {
            'has_data': True,
            'periods': list(period_stats.keys()),
            'period_stats': period_stats,
        }

    def _generate_evaluation(self, report):
        """生成综合评价"""
        evals = []

        # 规模评价
        scale = report.get('total_scale', 0)
        if scale > 10000:
            evals.append("行业龙头，规模领先")
        elif scale > 5000:
            evals.append("第一梯队，综合实力强")
        elif scale > 1000:
            evals.append("中大型，稳健发展")
        else:
            evals.append("特色发展，专注细分领域")

        # 评级评价
        cr = report.get('company_rating', {})
        if cr.get('has_data') and cr.get('avg_star', 0) >= 4:
            evals.append(f"平均{cr['avg_star']}星评级，投研实力强")
        elif cr.get('has_data') and cr.get('avg_star', 0) >= 3:
            evals.append(f"平均{cr['avg_star']}星评级，业绩中上")

        # 风险收益评价
        ca = report.get('company_analysis', {})
        if ca.get('has_data') and ca.get('best_sharpe', 0) > 1.5:
            evals.append("风险收益比优异")

        # 产品周期
        sd = report.get('stage_distribution', {})
        if '老牌期' in sd and sd['老牌期']['percentage'] > 30:
            evals.append("拥有多只老牌明星基金")

        return evals


def main():
    generator = EnhancedCompanyReport()

    print("=" * 60)
    print("增强型公司报告生成")
    print("整合：评级、风险指标、收益概率、产品周期")
    print("=" * 60)

    reports = generator.generate_enhanced_reports()

    # 展示示例
    print("\n" + "=" * 60)
    print("示例 - 华夏基金")
    print("=" * 60)

    for r in reports:
        if '华夏' in r['name']:
            print(f"\n【公司】{r['name']}")
            print(f"  规模: {r['total_scale']:.0f}亿元")
            print(f"  经理: {r['manager_count']}位")
            print(f"  主导风格: {r['dominant_style']}")

            # 评级
            cr = r.get('company_rating', {})
            if cr.get('has_data'):
                print(f"\n  【评级情况】")
                print(f"    平均星级: {cr['avg_star']}星")
                print(f"    5星基金: {cr['five_star_count']}只")
                print(f"    评级分布: {cr['distribution']}")
            else:
                print(f"\n  【评级情况】暂无数据")

            # 风险收益
            ca = r.get('company_analysis', {})
            if ca.get('has_data'):
                print(f"\n  【风险收益】")
                print(f"    最佳夏普比率: {ca['best_sharpe']}")
                print(f"    最大回撤: {ca['worst_drawdown']}%")

            # 收益概率
            cp = r.get('company_profit', {})
            if cp.get('has_data'):
                print(f"\n  【收益概率】")
                for period, stats in cp.get('period_stats', {}).items():
                    print(f"    {period}: 盈利概率{stats['avg_profit_prob']}%, 平均收益{stats['avg_return']}%")

            # 产品周期分布
            sd = r.get('stage_distribution', {})
            print(f"\n  【产品周期分布】")
            for stage, info in sd.items():
                print(f"    {stage}: {info['count']}只({info['percentage']}%)")

            # 综合评价
            print(f"\n  【综合评价】")
            for e in r.get('overall_evaluation', []):
                print(f"    ✓ {e}")

            # 头牌经理
            if r.get('top_manager'):
                tm = r['top_manager']
                print(f"\n  【头牌经理】{tm['name']}")
                print(f"    基金: {tm['fund_name']}")
                print(f"    风格: {tm['investment_style']}, 任期: {tm['tenure_years']}年")
                print(f"    阶段: {tm.get('fund_stage', '未知')}")
                if tm.get('stage_info'):
                    print(f"    建议: {tm['stage_info']['advice']}")

            break

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()