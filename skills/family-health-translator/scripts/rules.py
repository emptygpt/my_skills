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
PERSONAL_GOAL_QUESTION = '这项要按医生给你家人定的目标看，复诊时问一句：我的目标是多少？'
LDL_QUESTION = '复诊时问一句：我的低密度脂蛋白目标是多少？'
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
    '血糖': ('mmol/L', 'mg/dL'), '糖化血红蛋白': ('%',),
    '收缩压': ('mmHg',), '舒张压': ('mmHg',),
    '总胆固醇': ('mmol/L', 'mg/dL'), '甘油三酯': ('mmol/L', 'mg/dL'),
    '低密度脂蛋白胆固醇': ('mmol/L', 'mg/dL'), '高密度脂蛋白胆固醇': ('mmol/L', 'mg/dL'),
    '丙氨酸氨基转移酶': ('U/L',), '天门冬氨酸氨基转移酶': ('U/L',),
    EGFR: (EGFR_UNIT,), T_SCORE: ('SD',), '血红蛋白': ('g/L',),
}
RENAL_RANGES = {
    ('男', '20-59'): ((57, 97), (3.1, 8.0)), ('男', '60-79'): ((57, 111), (3.6, 9.5)),
    ('女', '20-59'): ((41, 73), (2.6, 7.5)), ('女', '60-79'): ((41, 81), (3.1, 8.8)),
}
HEMOGLOBIN_RANGES = {'男': (130, 175), '女': (115, 150)}
EMERGENCY = re.compile(
    r'胸痛|胸口.{0,4}(?:痛|疼|压榨|压迫)|胸疼|胸部疼痛|'
    r'(?:一侧|单侧|半边|左|右).{0,5}(?:肢体|手臂|腿|胳膊|手脚|手|脚).{0,5}(?:无力|没力|麻木|抬不起来|动不了)|'
    r'口角歪斜|嘴歪|突然.{0,4}(?:说不清|言语不清)|'
    r'(?:突发|突然).{0,6}(?:头痛|头疼)|(?:剧烈|爆炸般).{0,4}(?:头痛|头疼)|'
    r'(?:突发|突然|忽然).{0,8}(?:失去平衡|走路不稳|行走困难|站不稳|(?:头晕|眩晕)[，,、 ]?.{0,6}(?:跌倒|摔倒|摔了一跤|摔了))|'
    r'意识(?:改变|障碍|模糊|不清)|叫不醒|昏迷|昏厥|晕倒|'
    r'呕血|吐血|咖啡渣样呕吐|黑便|柏油样(?:便|大便)|呼吸困难|喘不上气'
)
URGENT_FEVER = re.compile(r'高[热烧].{0,6}(?:不退|持续|反复)|持续.{0,5}高[热烧]')
FALL_PAUSE = re.compile(r'((?:突发|突然|忽然).{0,8}(?:头晕|眩晕))[，,](?=.{0,6}(?:跌倒|摔倒|摔了一跤|摔了|站不稳))')
NEGATED = re.compile(r'(?:没有|并无|从无|否认|未见|未出现|无|没|不伴|不是)[：: ]*$')
NOT_NEGATED = re.compile(r'(?:不是没有|不能排除|不确定有没有|不只是|不止|不只)[：: ]*$')
ACUTE = '请立即联系当地急救（中国大陆拨打 120）或前往急诊，不要等线上解读。'
FEVER = '请尽快就医；高热伴呼吸困难、意识改变或迅速恶化时，立即联系当地急救。'
RED_FLAGS = '新发胸痛、突然一侧肢体无力、突发剧烈头痛或失去平衡（如突发头晕后跌倒）、意识改变、呕血或柏油样黑便、严重呼吸困难：立即联系当地急救；高热不退：尽快就医。'


def normalized(text):
    return unicodedata.normalize('NFKC', text)


def confirmed_conditions(profile):
    return {normalized(condition).replace(' ', '') for condition in profile.get('conditions', [])}


def triage(text):
    text = FALL_PAUSE.sub(r'\1 ', normalized(text))
    clauses = re.split(r'[，,。！？!?；;\n]|但(?:是)?|不过|然而', text)
    for pattern, advice in ((EMERGENCY, ACUTE), (URGENT_FEVER, FEVER)):
        for clause in clauses:
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
            return None, f'存在需个别判断的痛风情况，不自动套用一般痛风目标。{PERSONAL_GOAL_QUESTION}'
        stricter = conditions.intersection({'痛风石', '痛风每年至少发作2次', '慢性痛风性关节炎'})
        return {'op': '<', 'value': 300 if stricter else 360, 'unit': unit}, GOUT
    general = age in ('18-19', '20-59') and item.get('general_goal_applicable') is True
    if name in BP_LIMITS and conditions.intersection({'高血压'} | BP_COMORBIDITIES):
        if general and conditions == {'高血压'} and unit == 'mmHg' and item.get('bp_context') == 'clinic':
            return {'op': '<', 'value': BP_LIMITS[name], 'unit': unit}, HYPERTENSION
        if age in OLDER_AGES and '高血压' in conditions:
            age_goal = {'65-79': '＜140/90', '80+': '＜150/90'}.get(age)
            if conditions & BP_COMORBIDITIES and item.get('bp_context') == 'clinic':
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
            return None, f'{OLDER_DIABETES}所需的自理、低血糖和健康情况不全或不一致，不能替医生定档。{PERSONAL_GOAL_QUESTION}'
        return None, PERSONAL_GOAL_QUESTION
    if name == LDL and age in OLDER_AGES:
        if not conditions & ASCVD or unit != 'mmol/L':
            return None, f'目前不能套用二级预防目标；不拿报告参考区间当控制目标。{LDL_QUESTION}'
        risk = profile.get('ldl_risk')
        if risk not in LDL_LIMITS:
            return {'ldl_limit': None}, LIPIDS
        return {'ldl_limit': LDL_LIMITS[risk]}, LIPIDS
    if 'reference' in item:
        return item['reference'], '本张报告印明的参考范围（不是治疗目标）'
    group = profile.get('sex'), '60-79' if age in ('60-64', '65-79') else age
    renal_metric = {'血清肌酐': ('μmol/L', 0), '血清尿素': ('mmol/L', 1)}.get(name)
    if renal_metric and item.get('lab_range_applicable') is True and group in RENAL_RANGES and unit == renal_metric[0]:
        lower, upper = RENAL_RANGES[group][renal_metric[1]]
        return {'min': lower, 'max': upper}, f'{RENAL}（{group[0]}，{group[1]}岁；实验室已确认适用）'
    if name == '血红蛋白' and unit == 'g/L' and item.get('lab_range_applicable') is True and group[0] in HEMOGLOBIN_RANGES and group[1] in ('20-59', '60-79'):
        lower, upper = HEMOGLOBIN_RANGES[group[0]]
        return {'min': lower, 'max': upper}, f'{HEMOGLOBIN}（{group[0]}；实验室已确认适用；不是贫血诊断线）'
    return None, '没有可核实且适用的标准；请向开单机构核对，不判断高低。'


def assessment(item, profile):
    name = item['metric']
    value, unit = item['value'], item['unit']
    if name == EGFR:
        category = next(label for bound, label in (
            (90, 'G1：正常或较高'), (60, 'G2：轻度下降'), (45, 'G3a：轻到中度下降'),
            (30, 'G3b：中到重度下降'), (15, 'G4：重度下降'), (0, 'G5：最低一档，需尽快联系医生核对'),
        ) if value >= bound)
        return f'这次估算值落在 {category}。单次结果不能诊断慢性肾病，也不能仅凭这项确定用药剂量；出处：{KDIGO}。'
    if name == T_SCORE:
        if profile.get('age_band') not in OLDER_AGES or item.get('dxa_applicable') is not True:
            return '暂不判断。请核对是不是适用人群、部位和方法的 DXA T 值，复诊请医生结合骨折史解释。'
        band = '达到指南的低骨密度阈值（≤−2.5）' if value <= -2.5 else '落在骨量减少读数范围（−2.5＜T＜−1.0）' if value < -1 else '未落在上述低骨量读数范围（T≥−1.0）'
        return f'{band}。这里只解释读数，不判断是否患骨质疏松，也不能排除骨折风险；出处：{BONE}。'
    rule, source = rule_for(item, profile)
    if not rule:
        return f'暂不判断。{source}'
    if 'band' in rule:
        label, lower, upper = rule['band']
        bounds = f'≤{upper}%' if lower is None else f'＞{lower}% 至 ≤{upper}%'
        result = '高于该档上界' if value > upper else '低于或等于该档的排除下界；不表示需要把血糖升高' if lower is not None and value <= lower else '在该档范围内'
        return f'按已确认资料对照「{label}」档（{bounds}）：{result}。这是表4对照，不是个人治疗目标或调药依据；出处：{source}。'
    if 'ldl_limit' in rule:
        limit = rule['ldl_limit']
        if limit is None:
            partial = '本次读数对照两档的绝对值门槛都未达到。' if value >= LDL_LIMITS['very_high'] else '单凭这次数值不能判断达标。'
            return f'{source}：极高危＜1.8、超高危＜1.4 mmol/L，均还要较基线下降＞50%。{partial}不自动替你选档。{LDL_QUESTION}'
        result = '未达到该档的绝对值门槛' if value >= limit else '低于该档的绝对值门槛'
        baseline = item.get('ldl_baseline')
        if baseline is None:
            relative = '缺少已核对的治疗前基线，不能核定是否完整达标'
        else:
            half = Decimal(str(value)) * 2 < Decimal(str(baseline))
            relative = ('较基线下降超过50%，两项均符合该档对照' if value < limit else '虽较基线下降超过50%，仍未满足两项') if half else '较基线未下降超过50%，未满足两项目标'
        return f'{result}（＜{limit} mmol/L）；{relative}。出处：{source}。{LDL_QUESTION}'
    if 'op' in rule:
        limit, op = rule['value'], rule['op']
        reached = {'<': value < limit, '<=': value <= limit, '>': value > limit, '>=': value >= limit}[op]
        result = '符合此目标' if reached else '未达到此目标'
        if source == GOUT and value < 180:
            result = '数值偏低于该指南讨论的长期下限；单次结果不能判断是否长期偏低，请与医生核对'
        display_op = {'<': '＜', '<=': '≤', '>': '＞', '>=': '≥'}[op]
        return f'{result}。采用 {display_op}{limit} {unit}；出处：{source}。'
    lower, upper = rule['min'], rule['max']
    result = '低于参考区间' if value < lower else '高于参考区间' if value > upper else '在参考区间内'
    return f'{result}。采用 {lower}–{upper} {unit}；出处：{source}。'


def trend(item, history):
    related = [record for record in history if all(record.get(key) == item.get(key) for key in
               ('metric', 'unit', 'series')) and record['date'] < item['date']]
    if not item.get('series') or not related:
        return '没有更早且确认可比的记录，不判断趋势。'
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
