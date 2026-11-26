import re
import unicodedata
from decimal import Decimal


DISCLAIMER = '以医生意见为准'
GOUT = '《中国高尿酸血症与痛风诊疗指南（2019）》问题3（DOI: 10.3760/cma.j.issn.1000-6699.2020.01.001）'
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
}
RENAL_RANGES = {
    ('男', '20-59'): ((57, 97), (3.1, 8.0)), ('男', '60-79'): ((57, 111), (3.6, 9.5)),
    ('女', '20-59'): ((41, 73), (2.6, 7.5)), ('女', '60-79'): ((41, 81), (3.1, 8.8)),
}
EMERGENCY = re.compile(
    r'胸痛|胸口.{0,4}(?:痛|疼|压榨|压迫)|胸疼|胸部疼痛|'
    r'(?:一侧|单侧|半边|左|右).{0,5}(?:肢体|手臂|腿|胳膊|手脚|手|脚).{0,5}(?:无力|没力|麻木|抬不起来|动不了)|'
    r'口角歪斜|嘴歪|突然.{0,4}(?:说不清|言语不清)|'
    r'(?:突发|突然).{0,6}(?:头痛|头疼)|(?:剧烈|爆炸般).{0,4}(?:头痛|头疼)|'
    r'意识(?:改变|障碍|模糊|不清)|叫不醒|昏迷|昏厥|晕倒|'
    r'呕血|吐血|咖啡渣样呕吐|黑便|柏油样(?:便|大便)|呼吸困难|喘不上气'
)
URGENT_FEVER = re.compile(r'高[热烧].{0,6}(?:不退|持续|反复)|持续.{0,5}高[热烧]')
NEGATED = re.compile(r'(?:没有|并无|从无|否认|未见|未出现|无|没|不伴|不是)[：: ]*$')
NOT_NEGATED = re.compile(r'(?:不是没有|不能排除|不确定有没有|不只是|不止|不只)[：: ]*$')
ACUTE = '请立即联系当地急救（中国大陆拨打 120）或前往急诊，不要等线上解读。'
FEVER = '请尽快就医；高热伴呼吸困难、意识改变或迅速恶化时，立即联系当地急救。'
RED_FLAGS = '新发胸痛、突然一侧肢体无力、突发剧烈头痛、意识改变、呕血或柏油样黑便、严重呼吸困难：立即联系当地急救；高热不退：尽快就医。'


def normalized(text):
    return unicodedata.normalize('NFKC', text)


def triage(text):
    text = normalized(text)
    for pattern, advice in ((EMERGENCY, ACUTE), (URGENT_FEVER, FEVER)):
        for clause in re.split(r'[，,。！？!?；;\n]|但(?:是)?|不过|然而', text):
            for match in pattern.finditer(clause):
                prefix = clause[:match.start()]
                if NOT_NEGATED.search(prefix) or not NEGATED.search(prefix):
                    return advice
    return None


def rule_for(item, profile):
    name, unit = item['metric'], item['unit']
    conditions = set(profile.get('conditions', []))
    goal = profile.get('targets', {}).get(name)
    if goal:
        source = '档案中的医生个人目标（本人确认；非通用阈值）'
        if goal['unit'] != unit:
            return None, f'{source}与报告单位不同；请核对，不自动换算或降级。'
        return goal, source
    if name == '血尿酸' and '痛风' in conditions:
        if unit != 'μmol/L':
            return None, f'{GOUT}：单位不匹配；请用原单位向医生核对目标。'
        if conditions.intersection({
            '慢性肾病', '慢性肾脏疾病', '肾结石', '高血压', '糖尿病', '2型糖尿病',
            '血脂异常', '脑卒中', '缺血性心脏病', '心力衰竭', '痛风发病年龄小于40岁',
        }):
            return None, '存在需个别判断的痛风情况；请用医生个人目标，不自动套用一般痛风目标。'
        stricter = conditions.intersection({'痛风石', '痛风每年至少发作2次', '慢性痛风性关节炎'})
        return {'op': '<', 'value': 300 if stricter else 360, 'unit': unit}, GOUT
    if 'reference' in item:
        return item['reference'], '本张报告印明的参考范围（不是治疗目标）'
    group = profile.get('sex'), profile.get('age_band')
    renal_metric = {'血清肌酐': ('μmol/L', 0), '血清尿素': ('mmol/L', 1)}.get(name)
    if renal_metric and item.get('lab_range_applicable') is True and group in RENAL_RANGES and unit == renal_metric[0]:
        lower, upper = RENAL_RANGES[group][renal_metric[1]]
        return {'min': lower, 'max': upper}, f'{RENAL}（{group[0]}，{group[1]}岁；实验室已确认适用）'
    return None, '没有可核实且适用的标准；请向开单机构核对，不判断高低。'


def assessment(item, profile):
    rule, source = rule_for(item, profile)
    value, unit = item['value'], item['unit']
    if not rule:
        return f'暂不判断。{source}'
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


def medication_note(profile):
    drugs = set(profile.get('medications', []))
    if '痛风' in profile.get('conditions', []) and drugs.intersection({'氢氯噻嗪', '阿司匹林', '低剂量阿司匹林'}):
        return f'复诊时告诉医生有痛风，并带上现用药清单；不要自行停药或调量。参考：{ACR}。'
    return None
