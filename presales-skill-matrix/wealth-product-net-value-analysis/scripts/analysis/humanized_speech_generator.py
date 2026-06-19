"""
基金经理话术生成器 - 优化版
生成更有人情味、更像真人的表达
"""
import json
import os
import random
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')

class HumanizedSpeechGenerator:
    """更人性化的话术生成器"""

    def __init__(self):
        # 口语化开头
        self.casual_openings = [
            "说实话，",
            "我觉得吧，",
            "这个嘛，",
            "最近不少朋友问我",
            "说实话，最近行情",
            "你们问我这只基金怎么样",
            "聊聊我的想法",
            "我就直说了",
        ]

        # 自然表达
        self.natural_phrases = [
            "说实话我挺看好",
            "这些年下来我的体会是",
            "我对这块还是比较有信心的",
            "我们的想法比较简单，就是",
            "我不喜欢赌，更倾向于",
            "配置上会比较均衡一些",
            "说实话，波动大的时候我也会担心，但",
            "我觉得买基金这事，心态很重要",
        ]

        # 观点模板 - 更像人说的话
        self.view_templates = {
            '科技': [
                "说实话，科技这块机会是有的，但波动也不小。我更多会关注那些真正能落地的东西，不是概念。",
                "我觉得AI这波行情还没走完，但接下来会更挑股票，不是眉毛胡子一把抓的时候了。",
                "半导体这块，我还是比较有信心的。国产替代这条逻辑没变，估值也回调了不少。",
                "说实话，科技股研究起来挺累的，但机会也确实多。我更偏好龙头的确定性。",
            ],
            '新能源': [
                "新能源车这块渗透率还在往上走，但竞争也激烈了。我会更关注格局稳定的环节。",
                "光伏最近压力不小，产能过剩的问题还没消化完。但长期看，清洁能源的方向没问题。",
                "储能这块我比较看好，逻辑很简单，新能源要大规模用，储能必须跟上。",
                "电动车渗透率起来了，但竞争也到了白热化阶段。我更看重有成本优势的公司。",
            ],
            '消费': [
                "消费复苏比我想象的慢，但龙头公司的韧性还是可以的。",
                "说实话，白酒我还在观察，商务消费可以，但大众消费还没完全起来。",
                "我对消费的理解是，找到那些有品牌溢价能力的公司，长期拿着问题不大。",
                "消费这块现在估值不算贵了，但需要耐心等待。逆向布局的感觉。",
            ],
            '医药': [
                "医药跌了这么久，估值确实有吸引力了。但创新药的不确定性还是要注意。",
                "说实话，医疗器械这块我看的时间比较长，国产替代的逻辑很清晰。",
                "中药最近有动静，但我更关注有真正疗效和产品力的公司。",
                "我觉得医药需要精选，不是整个板块都能买。分化会很明显。",
            ],
            '金融': [
                "银行板块估值确实低，但弹性也一般。我更多是当作压舱石配置。",
                "券商这两年比较难，但熊市的时候反而应该多看看。",
                "保险我觉得是被低估了，人均收入在提高，对保险的需求也会上来。",
                "地产链还在调整，但我比较关注有独特性的物业公司。",
            ],
            '制造': [
                "制造业是中国经济的老本行了，我比较看重有技术壁垒的公司。",
                "军工这块有点特殊性，我的配置思路是聚焦核心零部件。",
                "化工行业周期性强，我更关注有差异化产品的公司。",
                "机械装备这块，国产替代的空间还挺大的。",
            ],
        }

        # 通用观点
        self.general_views = [
            "我觉得吧，市场短期波动很难预测，但长期看，中国经济的韧性还是很强的。",
            "这些年在市场里摸爬滚打，我最大的体会是不要太贪，也不要太慌。",
            "说实话，我更愿意慢慢赚钱，不追求一夜暴富。",
            "我更看重公司的质地，而不是择时。选好公司，长期持有，这话说起来容易，做起来难。",
            "大家都知道A股波动大，我的做法是不去猜，专心找好公司。",
        ]

        # 安慰话术
        self.comfort_templates = [
            "亏钱了肯定不好受，但我想说的是，这市场谁没亏过。",
            "回撤大的时候我也睡不好觉，但这时候最重要的还是保持冷静。",
            "说实话，能理解你的心情。但投资就是这样，有高峰有低谷。",
            "亏损的时候最重要的不是想着回本，而是搞清楚逻辑有没有变。",
            "我想跟你说，市场波动是正常的，谁都会经历。重要的是你的资金周期能不能承受。",
        ]

        # 追涨话术
        self.excitement_templates = [
            "涨得好确实让人开心，但我想提醒一下，别追太猛。",
            "看着账户飘红心情好，但也要注意风险。",
            "说实话，这波行情能走多远我也不知道，但享受当下就好。",
            "涨得快的时候人容易冲动，我想泼点冷水。",
        ]

    def load_managers(self):
        """加载经理数据"""
        with open(f'{DATA_DIR}/fund_managers.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def generate_view_for_manager(self, manager):
        """为经理生成更人性化的观点"""
        manager_id = manager.get('manager_id', '')
        style = manager.get('investment_style', '均衡型')
        top_stocks = manager.get('top_stocks', [])

        # 根据持仓行业选择观点
        sector_views = []
        for stock in top_stocks[:3]:
            name = stock.get('stock_name', '')
            sector = self._detect_sector(name)
            if sector and sector in self.view_templates:
                sector_views.append(random.choice(self.view_templates[sector]))

        # 组合观点
        views = []

        # 开头
        views.append(random.choice(self.natural_phrases))

        # 行业观点
        if sector_views:
            views.extend(sector_views[:2])
        else:
            views.append(random.choice(self.general_views))

        # 收尾
        if style == '成长型':
            views.append("我不太喜欢择时，更愿意把精力放在选股上。好的成长股，持有时间越长，回报越可观。")
        elif style == '价值型':
            views.append("我觉得投资还是得看估值，便宜买好货，这才是本质。耐心等，好公司总会给机会。")
        else:
            views.append("我的想法比较简单，均衡配置，不赌单一方向。长期下来这样可能更稳一些。")

        # 打乱顺序避免模板感
        random.shuffle(views)
        return views[:4]  # 留4条精华观点

    def generate_comfort_speech(self, manager, loss_percent):
        """生成亏损安抚话术"""
        views = []

        # 开场共情
        views.append(random.choice(self.comfort_templates))

        # 分析原因
        style = manager.get('investment_style', '均衡型')
        if style == '成长型':
            views.append("这只基金是成长风格的，最近科技、新能源调整比较大，你的亏损主要来自这里。")
        elif style == '价值型':
            views.append("虽然这段时间也跌了，但相比市场整体，回撤控制还算可以。")
        else:
            views.append("市场整体不好的时候，偏股型基金都会受影响，这是正常的。")

        # 分析持仓
        top_stocks = manager.get('top_stocks', [])
        if top_stocks:
            stock_names = [s.get('stock_name', '') for s in top_stocks[:3]]
            views.append(f"前几大重仓像{'、'.join(stock_names)}，基本面其实没有太大变化。")

        # 后续建议
        views.append(f"我的建议是，如果是闲钱投资，不妨给点时间。市场调整的时候，反而是检验自己持仓的机会。")

        # 结束的温暖
        endings = [
            "投资这事，心态很重要。有什么问题随时聊。",
            "你的心情我理解，咱们保持沟通。",
            "希望我的想法对你有帮助。",
        ]
        views.append(random.choice(endings))

        return views

    def generate_excitement_speech(self, manager, gain_percent):
        """生成盈利恭喜话术"""
        views = []

        views.append(random.choice(self.excitement_templates))

        # 归因分析
        style = manager.get('investment_style', '均衡型')
        if style == '成长型':
            views.append("这段时间科技、新能源表现不错，你的基金赶上这波了。")
        else:
            views.append("整体市场氛围不错，加上基金配置的方向对路了。")

        # 风险提示
        views.append("但说实话，涨幅大的时候我也会有点紧张。适度收割一些收益，可能是个好选择。")

        # 建议
        views.append(f"如果仓位比较重，可以考虑分批减一点。落袋为安嘛，这市场什么都可能发生。")

        return views

    def generate_profile_intro(self, manager):
        """生成经理介绍"""
        name = manager.get('name', '')
        company = manager.get('company_name', '')
        style = manager.get('investment_style', '均衡型')
        tenure_days = manager.get('tenure_days', 0)
        tenure_years = tenure_days / 365 if tenure_days else 0

        lines = []
        lines.append(f"你好，我是{name}。")

        if tenure_years >= 3:
            lines.append(f"在这个市场里摸爬滚打有{round(tenure_years)}年了，现在在{company}。")

        # 风格描述
        if style == '成长型':
            lines.append("我比较喜欢挖掘成长股的机会，像科技、新能源这些赛道我研究得比较多。")
            lines.append("风格上偏进攻，波动可能会大一些，但我觉得长期回报会更好。")
        elif style == '价值型':
            lines.append("我更偏向价值投资的思路，买东西讲究性价比。")
            lines.append("不喜欢追涨，更愿意在估值合理的时候布局，然后耐心等。")
        else:
            lines.append("我的风格比较均衡，不会押注单一方向。")
            lines.append("目标是让净值走势稳一点，不要大起大落。")

        # 重仓股
        top_stocks = manager.get('top_stocks', [])
        if top_stocks:
            stock_names = [s.get('stock_name', '') for s in top_stocks[:3]]
            lines.append(f"现在我比较看好{'、'.join(stock_names)}这些公司。")

        return lines

    def _detect_sector(self, stock_name):
        """判断股票所属行业"""
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

def main():
    generator = HumanizedSpeechGenerator()

    print("=" * 60)
    print("话术系统优化 - 人性化版本")
    print("=" * 60)

    # 测试生成
    data = generator.load_managers()
    managers = data.get('managers', [])

    # 找到有持仓的经理
    manager_with_holdings = next((m for m in managers if m.get('top_stocks')), None)

    if manager_with_holdings:
        print(f"\n测试经理: {manager_with_holdings['name']}")

        # 生成观点
        print("\n--- 投资观点 ---")
        views = generator.generate_view_for_manager(manager_with_holdings)
        for v in views:
            print(f"• {v}")

        # 生成经理介绍
        print("\n--- 经理介绍 ---")
        intro = generator.generate_profile_intro(manager_with_holdings)
        for line in intro:
            print(line)

        # 生成安抚话术
        print("\n--- 亏损安抚话术 ---")
        comfort = generator.generate_comfort_speech(manager_with_holdings, 15)
        for c in comfort:
            print(f"• {c}")

        # 生成恭喜话术
        print("\n--- 盈利恭喜话术 ---")
        excitement = generator.generate_excitement_speech(manager_with_holdings, 20)
        for e in excitement:
            print(f"• {e}")

    print("\n" + "=" * 60)
    print("话术测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()