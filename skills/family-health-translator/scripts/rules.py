import re
import unicodedata
from decimal import Decimal


DISCLAIMER = '以医生意见为准'
GOUT = '《中国高尿酸血症与痛风诊疗指南（2019）》问题3（DOI: 10.3760/cma.j.issn.1000-6699.2020.01.001）'
HYPERTENSION = '《中国高血压防治指南（2024年修订版）》5.1.3 要点5C（一般患者诊室目标；是否进一步降压由医生判断）'
DIABETES = '《中国糖尿病防治指南（2024版）》第六章一、表6（一般成人2型糖尿病目标）'
OLDER_BP = '《中国高血压防治指南（2024年修订版）》5.1.3（老年诊室目标）'
OLDER_DIABETES = '《中国老年2型糖尿病防治临床指南（2026年版）》表4'
LIPIDS = '《中国血脂管理指南（2023年）》图1、§9.2表6及§12.5（英文全文编号）'
KDIGO = 'KDIGO慢性肾病指南（2024）表1、表2及§4.2'
BONE = '《原发性骨质疏松症诊疗指南（2022）》骨密度测定与诊断标准'
HEMOGLOBIN = 'WS/T 405—2012 表1、第5章及附录A'
PIM = '《中国老年人潜在不适当用药判断标准（2017年版）》表2'
GLUCOSE_ADULT = '《中国糖尿病防治指南（2024版）》第六章一、表6（第29页；一般成人2型糖尿病毛细血管血糖目标）'
GLUCOSE_OLDER = '《中国老年2型糖尿病防治临床指南（2026年版）》表4（第213页）'
GLUCOSE_LOW = '《中国糖尿病防治指南（2024版）》第十七章低血糖（第77–78页）'
PERSONAL_GOAL_QUESTION = '这项要按医生给你家人定的目标看，复诊时问一句：我的目标是多少？'
LDL_QUESTION = '复诊时问一句：我的低密度脂蛋白目标是多少？'
ADULT_AGES = {'18-19', '20-59'}
NO_TREND = '没有更早且确认可比的记录，不判断趋势。'
BP_LIMITS = {'收缩压': 140, '舒张压': 90}
DIABETES_TYPES = {'糖尿病', '1型糖尿病', '2型糖尿病', '其他类型糖尿病'}
OLDER_AGES = {'60-64', '65-79', '60-79', '80+'}
ASCVD = {'已确诊ASCVD', '冠心病', '动脉粥样硬化性缺血性脑卒中'}
BP_COMORBIDITIES = DIABETES_TYPES | ASCVD | {'缺血性心脏病', '脑卒中', '缺血性脑卒中', '脑梗死', '脑出血', '慢性肾病', '慢性肾脏疾病', '心力衰竭'}
OLDER_ANSWERS = {
    'self_care': ('independent', 'limited', 'dependent'),
    'hypoglycemia': ('low', 'risk', 'severe_history'),
    'health': ('early_stable', 'moderate', 'major_impact'),
}
LDL_LIMITS = {'very_high': 1.8, 'ultra_high': 1.4}
LDL = '低密度脂蛋白胆固醇'
EGFR = '估算肾小球滤过率'
T_SCORE = '骨密度T值'
EGFR_UNIT = 'mL/min/1.73m²'
RENAL = 'WS/T 404.5—2015 表1及第5章'
ACR = '《2020 ACR 痛风管理指南》表8（DOI: 10.1002/acr.24180）'
METRICS = {
    '血尿酸': ('μmol/L', 'mg/dL'), '血清肌酐': ('μmol/L', 'mg/dL'),
    '血清尿素': ('mmol/L', 'mg/dL'), '空腹血糖': ('mmol/L', 'mg/dL'),
    '非空腹血糖': ('mmol/L', 'mg/dL'), '餐后2小时血糖': ('mmol/L', 'mg/dL'),
    '血糖': ('mmol/L', 'mg/dL'), '糖化血红蛋白': ('%',),
    '收缩压': ('mmHg',), '舒张压': ('mmHg',),
    '总胆固醇': ('mmol/L', 'mg/dL'), '甘油三酯': ('mmol/L', 'mg/dL'),
    '低密度脂蛋白胆固醇': ('mmol/L', 'mg/dL'), '高密度脂蛋白胆固醇': ('mmol/L', 'mg/dL'),
    '丙氨酸氨基转移酶': ('U/L',), '天门冬氨酸氨基转移酶': ('U/L',),
    EGFR: (EGFR_UNIT,), T_SCORE: ('SD',), '血红蛋白': ('g/L',),
}
GLUCOSE = {'空腹血糖', '非空腹血糖', '餐后2小时血糖', '血糖'}
# 控制目标只覆盖 2 型；没写型别的「糖尿病」按「如果是 2 型」比对。
GLUCOSE_TYPES = {'糖尿病', '2型糖尿病'}
GLUCOSE_LOW_LINE = 3.9
# (档名, 下限, 上限, 是否含上限)
ADULT_GLUCOSE = {
    '空腹血糖': (('一般成人', 4.4, 7.0, True),),
    '非空腹血糖': (('一般成人', None, 10.0, False),),
    '餐后2小时血糖': (('一般成人', None, 10.0, False),),
}
OLDER_GLUCOSE = {
    '空腹血糖': (('良好', 4.4, 7.0, True), ('过渡', 5.0, 7.5, False), ('可接受', 5.6, 8.5, False)),
    '餐后2小时血糖': (('良好', None, 10.0, False), ('过渡', None, 11.1, False), ('可接受', None, 13.9, False)),
}
RENAL_RANGES = {
    ('男', '20-59'): ((57, 97), (3.1, 8.0)), ('男', '60-79'): ((57, 111), (3.6, 9.5)),
    ('女', '20-59'): ((41, 73), (2.6, 7.5)), ('女', '60-79'): ((41, 81), (3.1, 8.8)),
}
HEMOGLOBIN_RANGES = {'男': (130, 175), '女': (115, 150)}
# 按意思判断：口语说法同样要命中。填充词用白名单，避免把「没歪」「不黑」里的否定吞掉。
FILL = r'(?:突然|忽然|一下子|一下|有点|有些|好像|开始|已经|变得|特别|很|好|太|都|也|就|又|总|老|完全|还|直|一直|是)'
SIDE_ONLY = r'(?:一侧|单侧|半侧|半边|一边)'
SIDE = r'(?:一侧|单侧|半侧|半边|一边|一只|一条|(?<!左)右(?:边|侧)?|左(?!右)(?:边|侧)?)'
LIMB = r'(?:的)?(?:身子|身体|身|肢体|手臂|胳膊|胳臂|手脚|腿脚|手指|大腿|小腿|手|脚|腿|脸)'
WEAK = (r'(?:无力|没(?:有)?(?:什么)?(?:力气|力|劲儿|劲)|使不(?:上|出)(?:力气|力|劲)|用不上(?:力|劲)|不听使唤|发麻|麻木|麻了|'
        r'发软|抬不起|抬不动|举不起|动不了|不能动|迈不动|耷拉)')
EMERGENCY = re.compile('|'.join((
    r'胸痛|胸口(?:(?![不没]).){0,4}(?:痛|疼|压榨|压迫)|胸疼|胸部疼痛',
    rf'(?:心口窝|心口|心窝|心前区|心脏){FILL}{{0,3}}(?:绞痛|闷痛|刺痛|痛|疼|压得慌|揪着疼)',
    r'(?:一侧|单侧|半边|左(?!右)|(?<!左)右).{0,5}(?:肢体|手臂|腿|胳膊|手脚|手|脚).{0,5}(?:无力|没力|麻木|抬不起来|动不了)',
    rf'{SIDE}{LIMB}(?:(?:和|跟)?{LIMB})?{FILL}{{0,3}}{WEAK}',
    rf'{SIDE_ONLY}{FILL}{{0,3}}{WEAK}',
    rf'(?:突然|忽然).{{0,4}}(?:手|胳膊|胳臂|腿)(?:脚)?{FILL}{{0,3}}{WEAK}',
    r'(?:突然|忽然).{0,10}(?:拿不住|端不住|握不住|拿不稳)(?:东西|杯子|筷子|碗|勺)',
    rf'口角歪斜|(?:嘴巴|嘴角|口角|嘴|脸){FILL}{{0,3}}(?:歪|斜)',
    rf'(?:说话|讲话|吐字|言语|口齿){FILL}{{0,4}}(?:不清|不太清|不利索|不利落|含糊|含混|困难|大舌头|打结)',
    rf'话{FILL}{{0,3}}(?:说|讲)不(?:清|清楚|利索|利落|出来|出话)',
    rf'大舌头|舌头{FILL}{{0,3}}(?:大了|发硬|发僵|打结|不听使唤|捋不直)|(?:突然|忽然).{{0,4}}(?:说不清|说不出话)',
    r'(?:突发|突然).{0,6}(?:头痛|头疼)|(?:剧烈|爆炸般).{0,4}(?:头痛|头疼)',
    rf'(?:突然|忽然)(?:间)?头{FILL}{{0,3}}(?:痛|疼)',
    r'(?:突发|突然|忽然).{0,8}(?:失去平衡|走路不稳|行走困难|站不稳|站不起来|(?:头晕|眩晕)[，,、 ]?.{0,6}(?:跌倒|摔倒|摔了一跤|摔了))',
    r'意识(?:改变|障碍|模糊|不清)|(?:叫|喊|摇)不(?:太)?醒|叫不应|不省人事|人事不省|昏迷|昏厥|晕倒|(?:突然|忽然)(?:犯)?糊涂|(?:突然|忽然).{0,4}不认(?:识)?人',
    r'呕血|(?:吐|呕)(?:了|出)?(?:很多|好多|一大口|几口|一口|点)?(?:鲜)?血(?![压糖脂红氧])|咖啡渣样呕吐|呕咖啡',
    r'黑便|柏油样(?:便|大便)|拉(?:的)?黑(?:屎|便|色)|黑色(?:的)?(?:大便|粪便|屎|便便)',
    rf'(?:大便|粪便|便便|拉的屎|屎)(?:的)?(?:颜色)?(?:{FILL}|发|像){{0,4}}(?:黑色|黑的|黑乎乎|黑得|发黑|黑)',
    r'呼吸困难|喘不上气|喘不过气|上不来气|透不过气|憋得喘不',
)))
# 第六版补的卒中口语。这几类词常用来说老毛病，只有这一组按分句排除既往和假设说法。
STROKE_WORDS = re.compile('|'.join((
    r'没(?:有|了)?知觉|失去(?:了)?知觉',
    rf'(?:{SIDE_ONLY}|{SIDE}{LIMB}|手|胳膊|胳臂){FILL}{{0,3}}麻(?![烦药醉将辣花婆酱油利雀团袋])',
    r'(?<![不得])(?:迷糊|迷迷糊糊)',
    r'(?:突发|突然|忽然)(?:了|性)?(?:脑梗|中风|脑卒中)',
)))
PAST = re.compile(r'平时|平常|长期|多年|几年|几个月|老是|总是|经常|常常|以前|从前|过去|去年|前年|年前|个月前|'
                  r'[0-9一二三四五六七八九十]\s*月|有一?天|那次|那天|当时|上次|既往|病史|后遗症|有过|得过')
# 「高血压好几年突然……」里的旧病只是背景，后面的发作是现在的事；「三年前突然……」不算。
NOW = re.compile(r'现在|目前|今天|今早|刚|这会|又|好好的|好端端|(?:高血压|血压高|糖尿病|病史|多年|几年|年了)了?(?:突然|忽然)')
NOT_HAPPENING = re.compile(r'预防|担心|害怕|会不会|万一|对.{0,10}迷糊|(?:看|听|搞|弄|整|说)得.{0,4}迷糊')
URGENT_FEVER = re.compile(r'高[热烧].{0,6}(?:不退|持续|反复)|持续.{0,5}高[热烧]')
FALL_PAUSE = re.compile(r'((?:突发|突然|忽然).{0,8}(?:头晕|眩晕))[，,](?=.{0,6}(?:跌倒|摔倒|摔了一跤|摔了|站不稳))')
NEGATED = re.compile(r'(?:没有|并无|从无|否认|未见|未出现|无|没|不伴|不是)(?:出现|发生|过|什么|任何)*[：: ]*$')
NOT_NEGATED = re.compile(r'(?:不是没有|不能排除|不确定有没有|不只是|不止|不只)[：: ]*$')
SHEET_RANGE = '本张报告印明的参考范围（不是治疗目标）'
LOW_GLUCOSE_ACTION = ('低血糖：低于 3.9 mmol/L。人清醒就马上吃 15–20 g 葡萄糖或含糖食物，15 分钟后复测，并马上联系医生；'
                      '叫不醒或突然糊涂马上打 120')
ACUTE = '请立即联系当地急救（中国大陆拨打 120）或前往急诊，不要等线上解读。'
FEVER = '请尽快就医；高热伴呼吸困难、意识改变或迅速恶化时，立即联系当地急救。'
RED_FLAGS = ('🚨 **马上打 120**：胸痛／一边手脚没力／说话不清、嘴歪／剧烈头痛／突然站不稳／叫不醒／喘不上气／吐血、黑便\n'
             '🏥 **尽快就医**：高热不退')


def normalized(text):
    return unicodedata.normalize('NFKC', text)


def confirmed_conditions(profile):
    return {normalized(condition).replace(' ', '') for condition in profile.get('conditions', [])}


def triage(text):
    text = FALL_PAUSE.sub(r'\1 ', normalized(text))
    clauses = re.split(r'[，,。！？!?；;\n]|但(?:是)?|不过(?!气)|然而', text)
    for pattern, advice in ((EMERGENCY, ACUTE), (STROKE_WORDS, ACUTE), (URGENT_FEVER, FEVER)):
        for clause in clauses:
            if pattern is STROKE_WORDS and (NOT_HAPPENING.search(clause) or PAST.search(clause) and not NOW.search(clause)):
                continue
            for match in pattern.finditer(clause):
                prefix = clause[:match.start()]
                if NOT_NEGATED.search(prefix) or not NEGATED.search(prefix):
                    return advice
    return None


def older_diabetes_band(profile):
    answers = profile.get('older_diabetes', {})
    self_care, hypo, health = (answers.get(field) for field in OLDER_ANSWERS)
    if not all((self_care, hypo, health)):
        return None
    if (self_care, hypo, health) == ('independent', 'low', 'early_stable'):
        return '良好', None, 7.0
    if self_care == 'limited' and hypo == 'risk' and health == 'moderate':
        return '过渡', 7.0, 8.0
    if self_care == 'dependent' and hypo == 'severe_history' and health == 'major_impact':
        return '可接受', 8.0, 8.5
    return None


def both_pressure_lines(item, age_limit):
    stricter = 130 if item['metric'] == '收缩压' else 80
    lines = f'年龄线 ＜{age_limit}、合并症耐受时 ＜{stricter} mmHg'
    if item['value'] >= age_limit:
        return {'agree': 'over', 'lines': lines, 'limit': age_limit}
    if item['value'] < stricter:
        return {'agree': 'within', 'lines': lines}
    return None


def rule_for(item, profile):
    name, unit = item['metric'], item['unit']
    age = profile.get('age_band')
    conditions = confirmed_conditions(profile)
    goal = profile.get('targets', {}).get(name)
    if goal:
        source = '档案中的医生个人目标（本人确认；非通用阈值）'
        if goal['unit'] != unit:
            return None, f'{source}与报告单位不同；请核对，不自动换算或降级。'
        if name in BP_LIMITS and item.get('bp_context') != goal.get('bp_context', 'clinic'):
            return None, f'本次读数与医生个人目标的测量场景未确认一致。{PERSONAL_GOAL_QUESTION}'
        return goal, source
    if name == '血尿酸' and '痛风' in conditions:
        if unit != 'μmol/L':
            return None, f'{GOUT}：单位不匹配；请用原单位向医生核对目标。'
        if conditions.intersection({
            '慢性肾病', '慢性肾脏疾病', '肾结石', '高血压', '糖尿病', '2型糖尿病',
            '血脂异常', '脑卒中', '缺血性心脏病', '心力衰竭', '痛风发病年龄小于40岁',
        }):
            if item['value'] >= 360:
                return {'agree': 'over', 'lines': '指南的 ＜360 和 ＜300 μmol/L'}, GOUT
            if 180 <= item['value'] < 300:
                return {'agree': 'within', 'lines': '指南的 ＜360 和 ＜300 μmol/L'}, GOUT
            note = '两条线结论不同' if item['value'] >= 300 else '数值偏低，请与医生核对'
            return None, f'{GOUT}：存在需个别判断的痛风情况，{note}，不自动套用一般痛风目标。{PERSONAL_GOAL_QUESTION}'
        stricter = conditions.intersection({'痛风石', '痛风每年至少发作2次', '慢性痛风性关节炎'})
        return {'op': '<', 'value': 300 if stricter else 360, 'unit': unit}, GOUT
    general = age in ('18-19', '20-59') and item.get('general_goal_applicable') is True
    if name in GLUCOSE and conditions & DIABETES_TYPES:
        return glucose_rule(item, profile, general)
    if name in BP_LIMITS and conditions.intersection({'高血压'} | BP_COMORBIDITIES):
        if general and conditions == {'高血压'} and unit == 'mmHg' and item.get('bp_context') == 'clinic':
            return {'op': '<', 'value': BP_LIMITS[name], 'unit': unit}, HYPERTENSION
        if (age in ADULT_AGES and '高血压' in conditions and conditions & BP_COMORBIDITIES and unit == 'mmHg'
                and item.get('bp_context') == 'clinic' and item.get('general_goal_applicable') is not False):
            agreed = both_pressure_lines(item, BP_LIMITS[name])
            if agreed:
                return agreed, HYPERTENSION
        if age in OLDER_AGES and '高血压' in conditions:
            age_goal = {'65-79': '＜140/90', '80+': '＜150/90'}.get(age)
            if conditions & BP_COMORBIDITIES and item.get('bp_context') == 'clinic':
                if age_goal and unit == 'mmHg' and item.get('older_bp_applicable') is not False:
                    agreed = both_pressure_lines(item, 150 if age == '80+' and name == '收缩压' else BP_LIMITS[name])
                    if agreed:
                        return agreed, OLDER_BP
                conflict = f'年龄线通常先看 {age_goal} mmHg，但' if age_goal else ''
                return None, f'{OLDER_BP}：{conflict}合并症在耐受时总则建议更严格（＜130/80 mmHg），两者不能自动择一；请医生综合病史、衰弱及跌倒风险确定。{PERSONAL_GOAL_QUESTION}'
            if not age_goal:
                return None, f'{OLDER_BP}未为该分组单列老年诊室目标。{PERSONAL_GOAL_QUESTION}'
            if item.get('bp_context') == 'clinic' and item.get('older_bp_applicable') is True:
                limit = 150 if age == '80+' and name == '收缩压' else BP_LIMITS[name]
                stronger = '＜140/90' if age == '80+' else '＜130/80'
                return {'op': '<', 'value': limit, 'unit': unit}, f'{OLDER_BP}；如能耐受可进一步到 {stronger} mmHg，复诊问医生'
        return None, PERSONAL_GOAL_QUESTION
    if name == '糖化血红蛋白' and conditions.intersection(DIABETES_TYPES):
        if general and conditions == {'2型糖尿病'} and unit == '%':
            return {'op': '<', 'value': 7.0, 'unit': unit}, DIABETES
        if age in OLDER_AGES and unit == '%' and (conditions & DIABETES_TYPES) == {'2型糖尿病'}:
            band = older_diabetes_band(profile)
            if band:
                return {'band': band}, OLDER_DIABETES
            if item['value'] > 8.5:
                return {'agree': 'a1c_over'}, OLDER_DIABETES
            if item['value'] <= 7.0:
                return {'agree': 'a1c_within'}, OLDER_DIABETES
            return None, f'{OLDER_DIABETES}：最严一档不超过 7.0%，放宽档到 8.0% 或 8.5%；算不算达标看医生定哪一档，所需情况不全或不一致，不能替医生定档。{PERSONAL_GOAL_QUESTION}'
        return None, PERSONAL_GOAL_QUESTION
    if name == LDL and age in OLDER_AGES:
        if not conditions & ASCVD or unit != 'mmol/L':
            return None, f'目前不能套用二级预防目标；不拿报告参考区间当控制目标。{LDL_QUESTION}'
        risk = profile.get('ldl_risk')
        if risk not in LDL_LIMITS:
            return {'ldl_limit': None}, LIPIDS
        return {'ldl_limit': LDL_LIMITS[risk]}, LIPIDS
    if 'reference' in item:
        return item['reference'], SHEET_RANGE
    group = profile.get('sex'), '60-79' if age in ('60-64', '65-79') else age
    renal_metric = {'血清肌酐': ('μmol/L', 0), '血清尿素': ('mmol/L', 1)}.get(name)
    if renal_metric and item.get('lab_range_applicable') is True and group in RENAL_RANGES and unit == renal_metric[0]:
        lower, upper = RENAL_RANGES[group][renal_metric[1]]
        return {'min': lower, 'max': upper}, f'{RENAL}（{group[0]}，{group[1]}岁；实验室已确认适用）'
    if name == '血红蛋白' and unit == 'g/L' and item.get('lab_range_applicable') is True and group[0] in HEMOGLOBIN_RANGES and group[1] in ('20-59', '60-79'):
        lower, upper = HEMOGLOBIN_RANGES[group[0]]
        return {'min': lower, 'max': upper}, f'{HEMOGLOBIN}（{group[0]}；实验室已确认适用；不是贫血诊断线）'
    if name in GLUCOSE:
        return None, '没有确诊糖尿病的记录，不套控制目标，也不凭这个数判断是不是糖尿病；没有适用的单子参考范围可对照。带上单子或测量记录问开单医生要不要复查'
    return None, '没有可核实且适用的标准；请向开单机构核对，不判断高低。'


def glucose_rule(item, profile, general):
    """已确诊糖尿病者的血糖控制目标；不套用时返回问医生，不降级到单子参考范围。"""
    name, age = item['metric'], profile.get('age_band')
    conditions = confirmed_conditions(profile)
    types = conditions & DIABETES_TYPES
    source = GLUCOSE_OLDER if age in OLDER_AGES else GLUCOSE_ADULT

    def ask(reason):
        return None, f'{source}：{reason}。{PERSONAL_GOAL_QUESTION}'

    if not types <= GLUCOSE_TYPES:
        return ask('这里的目标只覆盖 2 型糖尿病')
    if item['unit'] != 'mmol/L':
        return ask('单位不是 mmol/L，请核对原单位，不换算')
    if name == '血糖':
        return ask('先说清是空腹还是饭后多久测的，两种目标不同')
    if age in OLDER_AGES:
        if name not in OLDER_GLUCOSE:
            return ask('老年标准只列了空腹和饭后 2 小时，先说清是不是饭后 2 小时测的')
        band = older_diabetes_band(profile)
        tiers = tuple(tier for tier in OLDER_GLUCOSE[name] if not band or tier[0] == band[0])
        return {'glucose': tiers}, source
    if general and conditions == types:
        return {'glucose': ADULT_GLUCOSE[name]}, source
    return ask('一般成人目标要先确认适用；低血糖风险高、有严重并发症或合并症等情况医生可能放宽')


def grade_glucose(item, tiers, source, profile):
    value = item['value']
    older = source == GLUCOSE_OLDER
    states, shown = [], []
    for label, lower, upper, inclusive in tiers:
        over = value > upper or not inclusive and value == upper
        states.append('over' if over else 'below' if lower is not None and value < lower else 'in')
        top = f'{upper}' if inclusive else f'＜{upper}'
        shown.append(f'{label} {lower}–{top}' if lower is not None else f'{label} {"≤" if inclusive else ""}{top}')
    lines = f'{"、".join(shown)} mmol/L'
    premise = '' if '2型糖尿病' in confirmed_conditions(profile) else '没说是几型，如果是 2 型：'
    gap = None
    if all(state == 'over' for state in states):
        top = max(tier[2] for tier in tiers)
        gap = ('↑', f'线是 {top}' if value == top else f'高出 {Decimal(str(value)) - Decimal(str(top)):f}')
    if len(tiers) == 1:
        mark, word = {'over': ('🔴', '超过'), 'in': ('✅', '在'), 'below': ('🟡', '低于')}[states[0]]
        word = {'超过': '超过目标', '在': '在目标内', '低于': '低于目标下限；告诉医生，不自己调药'}[word]
        if older:
            verdict = f'按已确认资料对照「{tiers[0][0]}」档：{word}（{lines}）'
        else:
            verdict = f'{word}（{lines}，指尖血糖目标；低血糖风险高、有严重并发症或合并症时医生可能放宽）'
        return graded(mark, premise + verdict, source, '' if mark == '✅' else PERSONAL_GOAL_QUESTION, gap)
    if len(set(states)) == 1:
        mark, verdict = {
            'over': ('🔴', '不管按哪一档都超过'),
            'in': ('✅', '不管按哪一档都在内'),
            'below': ('🟡', '低于各档下限；告诉医生，不自己调药'),
        }[states[0]]
        verdict = f'{verdict}（{lines}）；该用哪一档请医生定'
    else:
        mark = '🟡'
        parts = []
        for state, word in (('over', '超过'), ('in', '在内'), ('below', '低于下限')):
            labels = [f'{tier[0]}档' for tier, found in zip(tiers, states) if found == state]
            if labels:
                parts.append(f'按{"、".join(labels)}{word}' if state == 'over' else f'{"、".join(labels)}{word}')
        verdict = f'{"，".join(parts)}（{lines}）；算不算达标看医生定哪一档'
    return graded(mark, premise + verdict, source, PERSONAL_GOAL_QUESTION, gap)


def graded(mark, verdict, source=None, question='', gap=None, urgent=False):
    return {'mark': mark, 'verdict': verdict, 'source': source, 'question': question, 'gap': gap, 'urgent': urgent}


def low_glucose(item, profile):
    return (item['metric'] in GLUCOSE and item['unit'] == 'mmol/L' and item['value'] < GLUCOSE_LOW_LINE
            and bool(confirmed_conditions(profile) & DIABETES_TYPES))


def grade(item, profile):
    """标记只表示和对照线的关系：🔴 超过线；🟡 要医生定目标或补信息；✅ 在范围内；⚪ 本工具看不了。"""
    name = item['metric']
    value, unit = item['value'], item['unit']
    # 低血糖排在任何控制目标（含医生个人目标）之前。
    if low_glucose(item, profile):
        return graded('🔴', LOW_GLUCOSE_ACTION, GLUCOSE_LOW, gap=('↓', '低血糖线是 3.9'), urgent=True)
    if name == EGFR:
        category = next(label for bound, label in (
            (90, 'G1：正常或较高'), (60, 'G2：轻度下降'), (45, 'G3a：轻到中度下降'),
            (30, 'G3b：中到重度下降'), (15, 'G4：重度下降'), (0, 'G5：最低一档，需尽快联系医生核对'),
        ) if value >= bound)
        mark = '✅' if value >= 90 else '🔴' if value < 15 else '🟡'
        return graded(mark, f'这次估算值落在 {category}。单次结果不能诊断慢性肾病，也不能仅凭这项确定用药剂量', KDIGO)
    if name == T_SCORE:
        age = profile.get('age_band')
        population = age in OLDER_AGES or age == '20-59' and item.get('dxa_population_confirmed') is True
        if not population or item.get('dxa_applicable') is not True:
            return graded('🟡', '暂不判断。请核对是不是适用人群（绝经后女性或 50 岁及以上男性）、部位和方法的 DXA T 值，复诊请骨科结合骨折史解释', BONE)
        mark, band = ('🔴', '达到指南的低骨密度阈值（≤−2.5）') if value <= -2.5 else (
            ('🟡', '落在骨量减少读数范围（−2.5＜T＜−1.0）') if value < -1 else ('✅', '未落在上述低骨量读数范围（T≥−1.0）'))
        gap = ('↓', '达到 −2.5 线') if mark == '🔴' else None
        return graded(mark, f'{band}。这里只解释读数，不判断是否患骨质疏松，也不能排除骨折风险', BONE, gap=gap)
    rule, source = rule_for(item, profile)
    if not rule:
        for question in (PERSONAL_GOAL_QUESTION, LDL_QUESTION):
            if source.endswith(question):
                reason = source[:-len(question)].rstrip('。')
                cited, _, detail = reason.partition('：') if reason.startswith('《') else ('', '', reason)
                return graded('🟡', f'暂不判断。{detail or "看医生定的目标"}', cited or None, question)
        return graded('⚪', f'暂不判断。{source.rstrip("。")}')
    if 'agree' in rule:
        kind = rule['agree']
        if kind == 'a1c_over':
            return graded('🔴', '不管按哪一档都超过（三档上限 7.0%、8.0%、8.5%）；该用哪一档请医生定', source,
                          PERSONAL_GOAL_QUESTION, ('↑', '超过最宽的 8.5%'))
        if kind == 'a1c_within':
            return graded('✅', '哪一档的上限都没超过（最严 7.0%）；该用哪一档请医生定，不是越低越好', source, PERSONAL_GOAL_QUESTION)
        word = '超过' if kind == 'over' else '在内'
        gap = None
        if kind == 'over':
            gap = ('↑', f'超过 {rule["limit"]}' if 'limit' in rule else '超过 360')
        return graded('🔴' if kind == 'over' else '✅', f'不管按哪条线都{word}（{rule["lines"]}）；该用哪条请医生定', source,
                      PERSONAL_GOAL_QUESTION, gap)
    if 'glucose' in rule:
        return grade_glucose(item, rule['glucose'], source, profile)
    if 'band' in rule:
        label, lower, upper = rule['band']
        bounds = f'≤{upper}%' if lower is None else f'＞{lower}% 至 ≤{upper}%'
        below = lower is not None and value <= lower
        result = '高于该档上界' if value > upper else '低于或等于该档的排除下界；不表示需要把血糖升高' if below else '在该档范围内'
        mark = '🔴' if value > upper else '🟡' if below else '✅'
        return graded(mark, f'按已确认资料对照「{label}」档（{bounds}）：{result}。这是表4对照，不是个人治疗目标或调药依据', source,
                      gap=above_or_below(value, None, upper))
    if 'ldl_limit' in rule:
        limit = rule['ldl_limit']
        if limit is None:
            over = value >= LDL_LIMITS['very_high']
            partial = '不管按哪一档都超过：本次读数对照两档的绝对值门槛都未达到。' if over else '单凭这次数值不能判断达标。'
            return graded('🔴' if over else '🟡', f'{partial}极高危＜1.8、超高危＜1.4 mmol/L，均还要较基线下降＞50%。不自动替你选档',
                          source, LDL_QUESTION, above_or_below(value, None, LDL_LIMITS['very_high']) if over else None)
        result = '未达到该档的绝对值门槛' if value >= limit else '低于该档的绝对值门槛'
        baseline = item.get('ldl_baseline')
        mark = '🔴' if value >= limit else '🟡'
        if baseline is None:
            relative = '缺少已核对的治疗前基线，不能核定是否完整达标'
        else:
            half = Decimal(str(value)) * 2 < Decimal(str(baseline))
            relative = ('较基线下降超过50%，两项均符合该档对照' if value < limit else '虽较基线下降超过50%，仍未满足两项') if half else '较基线未下降超过50%，未满足两项目标'
            if half and value < limit:
                mark = '✅'
            elif not half:
                mark = '🔴'
        gap = ('↑', f'线是＜{limit}') if value >= limit else None
        return graded(mark, f'{result}（＜{limit} mmol/L）；{relative}', source, LDL_QUESTION, gap)
    if 'op' in rule:
        limit, op = rule['value'], rule['op']
        reached = {'<': value < limit, '<=': value <= limit, '>': value > limit, '>=': value >= limit}[op]
        result = '符合此目标' if reached else '未达到此目标'
        mark = '✅' if reached else '🔴'
        gap = None
        if not reached:
            gap = above_or_below(value, limit, None) if op.startswith('>') else above_or_below(value, None, limit)
            if value == limit:
                gap = ('↑' if op == '<' else '↓', '正好到线，目标不含这个数')
        if source == GOUT and value < 180:
            result, mark = '数值偏低于该指南讨论的长期下限；单次结果不能判断是否长期偏低，请与医生核对', '🟡'
        display_op = {'<': '＜', '<=': '≤', '>': '＞', '>=': '≥'}[op]
        return graded(mark, f'{result}。采用 {display_op}{limit} {unit}', source, gap=gap)
    lower, upper = rule['min'], rule['max']
    result = '低于参考区间' if value < lower else '高于参考区间' if value > upper else '在参考区间内'
    return graded('✅' if lower <= value <= upper else '🔴', f'{result}。采用 {lower}–{upper} {unit}', source,
                  gap=above_or_below(value, lower, upper))


def above_or_below(value, lower, upper):
    if upper is not None and value > upper:
        return '↑', f'高出 {Decimal(str(value)) - Decimal(str(upper)):f}'
    if lower is not None and value < lower:
        return '↓', f'低 {Decimal(str(lower)) - Decimal(str(value)):f}'
    return None


def assessment(item, profile):
    result = grade(item, profile)
    source = f'出处：{result["source"]}。' if result['source'] else ''
    return f'{result["verdict"]}。{source}{result["question"]}'


def trend(item, history):
    related = [record for record in history if all(record.get(key) == item.get(key) for key in
               ('metric', 'unit', 'series')) and record['date'] < item['date']]
    if not item.get('series') or not related:
        return NO_TREND
    latest = max(record['date'] for record in related)
    values = {record['value'] for record in related if record['date'] == latest}
    if len(values) != 1:
        return '上一可比日期有多个不同数值，不自动选择。'
    delta = Decimal(str(item['value'])) - Decimal(str(next(iter(values))))
    if not delta:
        return f'与 {latest} 的可比记录数值相同。'
    direction = '上升' if delta > 0 else '下降'
    return f'较 {latest} {direction} {abs(delta):f} {item["unit"]}；变化不等于病情变化。'


def medication_notes(profile):
    drugs = {normalized(drug).replace(' ', '') for drug in profile.get('medications', [])}
    conditions = confirmed_conditions(profile)
    if '痛风' in conditions and drugs & {'氢氯噻嗪', '阿司匹林', '低剂量阿司匹林'}:
        yield f'复诊时告诉医生有痛风，并带上现用药清单；不要自行停药或调量。参考：{ACR}。'
    if profile.get('age_band') not in OLDER_AGES:
        return
    for matches, labels, fact in (
        (conditions & {'高血压', '肾功能不全', '心力衰竭'}, {'非甾体抗炎药', '布洛芬'}, '这项病史和正在用的非甾体抗炎药（如布洛芬）'),
        (conditions & {'痛风'}, {'噻嗪类利尿药', '氢氯噻嗪'}, '痛风病史和正在用的噻嗪类利尿药'),
        (conditions & DIABETES_TYPES, {'长期使用糖皮质激素'}, '糖尿病病史和长期使用糖皮质激素的情况'),
    ):
        if matches and drugs & labels:
            yield f'复诊时告诉医生{fact}，带上药盒；不自行停药、换药或改量。参考：{PIM}。'
