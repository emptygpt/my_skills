import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from datetime import date

sys.dont_write_bytecode = True
from rules import BP_LIMITS, DISCLAIMER, METRICS, PERSONAL_GOAL_QUESTION, RED_FLAGS, assessment, medication_note, normalized, trend, triage


AGE_BANDS = ('18-19', '20-59', '60-79', '80+', '未知')
PROFILE_FIELDS = {'alias', 'age_band', 'sex', 'conditions', 'medications', 'allergies', 'targets'}
NAME = re.compile(r'[\u3400-\u9fffA-Za-z0-9 ·＋+（）()\-]{1,40}')
IDENTIFIER = re.compile(r'[a-z0-9][a-z0-9-]{0,31}')
SCOPES = ('adult', 'minor', 'pregnant', 'unknown')
CONSENT = '我确认资料本人已单独同意：仅为本机报告整理与趋势比较，保存代称、年龄段、性别、病史、用药、过敏、医生目标及指标记录；可随时查看、修改、删除。'
MAX_BYTES = 2_000_000


class InputError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def fields(data, allowed, required=()):
    require(isinstance(data, dict) and set(data) <= set(allowed) and set(required) <= set(data), '字段不符合本命令格式。')


def unique_object(pairs):
    result = dict(pairs)
    require(len(result) == len(pairs), 'JSON 含重复字段。')
    return result


def read_json(stream):
    data = stream.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES, 'JSON 超出大小上限。')
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)


def number(value):
    require(type(value) is int or type(value) is float and math.isfinite(value), '数值必须是有限数字。')
    require(0 <= value <= 1_000_000_000, '请核对数值格式和单位。')


def name(value):
    require(isinstance(value, str) and NAME.fullmatch(value), '代称、病名或药名格式不符。')


def unit_for(metric, unit):
    require(isinstance(metric, str) and metric in METRICS and unit in METRICS[metric], '指标或单位不受支持；不要猜测或换算。')


def check_profile(profile):
    fields(profile, PROFILE_FIELDS, PROFILE_FIELDS)
    name(profile['alias'])
    require(profile['age_band'] in AGE_BANDS and profile['sex'] in ('男', '女', '未知'), '年龄段或性别字段不符。')
    for key in ('conditions', 'medications', 'allergies'):
        require(isinstance(profile[key], list) and len(profile[key]) <= 30, '病史、药名、过敏需用简短列表。')
        for entry in profile[key]:
            name(entry)
    require(isinstance(profile['targets'], dict), '医生目标须是对象。')
    for metric, goal in profile['targets'].items():
        fields(goal, ('op', 'value', 'unit'), ('op', 'value', 'unit'))
        require(goal['op'] in ('<', '<=', '>', '>='), '医生目标必须确认方向。')
        unit_for(metric, goal['unit'])
        number(goal['value'])


def check_measurement(item):
    core = {'metric', 'unit', 'value', 'date'}
    fields(item, core | {'reference', 'series', 'lab_range_applicable', 'general_goal_applicable', 'bp_context'}, core)
    unit_for(item['metric'], item['unit'])
    number(item['value'])
    day = item['date']
    require(isinstance(day, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) and date.fromisoformat(day) <= date.today(), '请提供有效、非未来的采样日期。')
    if 'series' in item:
        require(isinstance(item['series'], str) and IDENTIFIER.fullmatch(item['series']), '可比组编号格式不符。')
    if 'reference' in item:
        interval = item['reference']
        fields(interval, ('min', 'max'), ('min', 'max'))
        number(interval['min'])
        number(interval['max'])
        require(interval['min'] <= interval['max'], '报告参考区间上下限颠倒。')
    if 'lab_range_applicable' in item:
        require(type(item['lab_range_applicable']) is bool, '实验室适用性必须为布尔值。')
    if 'general_goal_applicable' in item:
        require(type(item['general_goal_applicable']) is bool, '一般成人目标适用性必须为布尔值。')
    if 'bp_context' in item:
        require(item['metric'] in BP_LIMITS and item['bp_context'] in ('clinic', 'home', 'ambulatory', 'unknown'), '请核对血压测量场景。')


def profile_path(args):
    require(IDENTIFIER.fullmatch(args.person), '档案编号只能使用小写英文、数字及连字符。')
    path = Path(args.store).expanduser().absolute()
    require(not any(part.is_symlink() for part in (path, *path.parents)), '不使用符号链接作为档案目录。')
    if args.command == 'create' and not path.exists():
        path.mkdir(mode=0o700)
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode) and not info.st_mode & 0o077 and info.st_uid == os.getuid(), '档案目录必须由当前用户拥有，权限为 700。')
    if args.command == 'create':
        guard = path / '.gitignore'
        try:
            with guard.open('x', encoding='utf-8') as stream:
                stream.write('*\n')
        except FileExistsError:
            require(not guard.is_symlink() and guard.is_file() and guard.read_text(encoding='utf-8') == '*\n', '请使用专用档案目录。')
    return path / f'{args.person}.json'


def load(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o077 and info.st_uid == os.getuid() and info.st_nlink == 1, '档案须为当前用户独占的普通本地文件。')
        data = read_json(stream)
    fields(data, ('profile', 'history', 'consent'), ('profile', 'history', 'consent'))
    require(data['consent'] == 'separate-v1' and isinstance(data['history'], list), '档案版本或同意记录无法确认。')
    check_profile(data['profile'])
    for row in data['history']:
        check_measurement(row)
    return data


def save(path, data, create=False):
    payload = (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    require(len(payload) <= MAX_BYTES, '档案已达大小上限，未保存。')
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            if create:
                os.link(temp, path)
            else:
                os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def medication_table(data, profile):
    schedule = data.get('schedule', [])
    require(isinstance(schedule, list) and len(schedule) <= 30, '用药条目格式不符。')
    if not schedule or data.get('schedule_verified') is not True:
        return '未获得经本人确认的现行医嘱，不生成时间表。请向医生或药师核对用法。'
    if any(not isinstance(row, dict) or not row.get('time') or not row.get('dose') for row in schedule):
        return '现行医嘱有缺项，不生成时间表。请向医生或药师核对用法。'
    lines = []
    slots = set()
    allergies = set(profile.get('allergies', []))
    for row in schedule:
        fields(row, ('drug', 'time', 'dose', 'source'), ('drug', 'time', 'dose', 'source'))
        name(row['drug'])
        require(row['source'] in ('现行处方', '药师确认'), '仅可转录本人确认的现行处方或药师说明，不能用药盒推断。')
        require(isinstance(row['dose'], str) and re.fullmatch(r'\d{1,5}(?:\.\d{1,4})?\s?(?:mg|g|μg|mL|片|粒|袋|单位|吸|滴)', row['dose']), '剂量格式不清楚；请向医生或药师核对。')
        require(isinstance(row['time'], str) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d|早饭前|早饭后|午饭前|午饭后|晚饭前|晚饭后|睡前', row['time']), '时间格式不清楚；请向医生或药师核对。')
        require(not triage(f'{row["drug"]}'), '药名可能不清楚；不制作时间表。')
        slot = row['drug'], row['time']
        if slot in slots or row['drug'] in allergies:
            return '有重复、冲突或可能涉及已知过敏的条目，不生成时间表。请向医生或药师核对。'
        slots.add(slot)
        lines.append(f'### {row["time"]} ｜ {row["drug"]} ｜ {row["dose"]}（{row["source"]}原样转录）')
    return '\n'.join(lines) + '\n\n建议打印时将字号设为 20 磅以上。以现行医嘱为准，不自行改动。'


def review(data, args):
    require(isinstance(data, dict), '须提供一份 JSON 对象。')
    symptoms = data.get('symptoms', '')
    require(isinstance(symptoms, str), '当前症状须为文字。')
    alert = triage(symptoms)
    if alert:
        return f'{alert}\n\n{DISCLAIMER}'
    if data.get('critical_flag') is True:
        return f'请立即联系开单医院或急诊核对报告危急值，不要等待线上解读。\n\n{DISCLAIMER}'
    fields(data, ('scope', 'symptoms', 'critical_flag', 'measurements', 'schedule', 'schedule_verified'), ('scope',))
    require(data['scope'] in SCOPES, '适用人群字段不符。')
    require(all(key not in data or type(data[key]) is bool for key in ('critical_flag', 'schedule_verified')), '危急值和医嘱确认字段须明确填写 true 或 false。')
    if data['scope'] != 'adult':
        return f'暂不套用成人规则、不建档或记录。请联系相应科室；如尚未确认，请先说明是否成年且不在孕期。\n\n{DISCLAIMER}'
    require(args.person or not args.persist, '保存指标前须指定已同意建档的人。')
    path = profile_path(args) if args.person else None
    record = load(path) if path else {'profile': {}, 'history': []}
    profile, history = record['profile'], record['history']
    items = data.get('measurements', [])
    require(isinstance(items, list) and len(items) <= 50, '指标必须是列表，每次最多 50 条。')
    lines = []
    pending = []
    goals_to_ask = []
    for item in items:
        check_measurement(item)
        comparison = assessment(item, profile)
        if comparison.endswith(PERSONAL_GOAL_QUESTION) and item['metric'] not in goals_to_ask:
            goals_to_ask.append(item['metric'])
        lines.append(f'- {item["metric"]} {item["value"]} {item["unit"]}（{item["date"]}）：{comparison} {trend(item, history)}')
        row = {key: item[key] for key in ('date', 'metric', 'value', 'unit', 'series') if key in item}
        if row not in history and row not in pending:
            pending.append(row)
    table = medication_table(data, profile)
    questions = [f'- {"、".join(goals_to_ask)}：{PERSONAL_GOAL_QUESTION}'] if goals_to_ask else [
        '- 这次结果在我的情况下应看哪个目标，什么时候复查？']
    note = medication_note(profile)
    if note:
        questions.append(f'- {note}')
    if profile.get('allergies'):
        questions.append('- 复诊时告诉医生已知的药物过敏史。')
    if args.persist and pending:
        save(path, {**record, 'history': history + pending})
    status = '指标已按授权记录到本地档案。' if args.persist and pending else '本次未新增档案记录。'
    return '\n\n'.join((
        '## ① 大白话解读\n\n' + ('\n'.join(lines) or '未提供确认过的指标。') + '\n\n区间或目标比较不能判断病因、严重程度，也不能排除急症。' + status,
        '## ② 大字版用药时间表\n\n' + table,
        '## ③ 下次复诊的问题\n\n' + '\n'.join(questions),
        '## ④ 哪些情况要立刻就医\n\n' + RED_FLAGS,
        '## ⑤ 可以念给家人听\n\n这张单子咱们先收好。下次去医院，咱们带上原单，问医生哪些要再查、你的目标是多少。药还是照医生现在交代的吃，咱们不自己改。',
        DISCLAIMER,
    ))


def cli():
    parser = argparse.ArgumentParser(description='在可信本机整理体检资料。健康 JSON 从标准输入读取，不传网络。', epilog=CONSENT)
    parser.add_argument('--store', default='家人健康档案', help='专用、当前用户独占的本地目录；不要使用同步盘')
    commands = parser.add_subparsers(dest='command', required=True)
    for action, description in (
        ('create', '建档：先单独征得资料本人同意'), ('show', '仅在本地查看服药、病史、目标和历史'),
        ('update', '修改档案；targets 逐项合并，某项目为 null 表示删除'), ('delete', '撤回同意并删除档案'),
        ('review', '解读确认过的结构化测量和现行医嘱'), ('triage', '匹配当前症状的紧急关键词'),
    ):
        command = commands.add_parser(action, help=description, description=description)
        if action in ('create', 'show', 'update', 'delete', 'review'):
            command.add_argument('--person', required=action != 'review', help='指定对象的本地档案编号')
        if action == 'create':
            command.add_argument('--consent', action='store_true', help=CONSENT)
            command.add_argument('--scope', required=True, choices=SCOPES, help='先确认是非孕成年人才能建档')
        if action == 'delete':
            command.add_argument('--confirm', action='store_true', help='已确认删除的是这个人的档案')
        if action == 'review':
            command.add_argument('--persist', action='store_true', help='本人已同意长期保存，追加已核对指标')
    args = parser.parse_args()
    try:
        if args.command == 'triage':
            text = sys.stdin.buffer.read(MAX_BYTES + 1)
            require(len(text) <= MAX_BYTES, '请仅输入简短的当前症状。')
            print((triage(normalized(text.decode('utf-8'))) or '未命中关键词不代表没有急症。') + '\n\n' + DISCLAIMER)
            return 0
        if args.command == 'review':
            print(review(read_json(sys.stdin.buffer), args))
            return 0
        if args.command == 'create':
            require(args.scope == 'adult' and args.consent, '仅非孕成年人；未经资料本人单独同意不建档。')
            profile = read_json(sys.stdin.buffer)
            check_profile(profile)
            save(profile_path(args), {'profile': profile, 'consent': 'separate-v1', 'history': []}, create=True)
            print('本地档案已建立。')
            return 0
        if args.command == 'delete':
            require(args.confirm, '先核对对象并确认删除。')
            path = profile_path(args)
            require(not path.is_symlink() and path.is_file(), '找不到普通本地档案。')
            path.unlink()
            print('本地档案已删除。不包含对话、备份或打印件。')
            return 0
        path = profile_path(args)
        record = load(path)
        if args.command == 'show':
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0
        changes = read_json(sys.stdin.buffer)
        fields(changes, PROFILE_FIELDS)
        profile = {**record['profile'], **changes}
        if 'targets' in changes:
            require(isinstance(changes['targets'], dict) and set(changes['targets']) <= set(METRICS), '医生目标须指定对应指标。')
            targets = {**record['profile']['targets'], **changes['targets']}
            profile['targets'] = {key: value for key, value in targets.items() if value is not None}
        check_profile(profile)
        save(path, {**record, 'profile': profile})
        print('本地档案已更新。')
        return 0
    except InputError as error:
        print(str(error) + '\n' + DISCLAIMER, file=sys.stderr)
    except (ValueError, RecursionError):
        print('无法读取输入格式，未输出个人数据。\n' + DISCLAIMER, file=sys.stderr)
    except OSError:
        print('无法安全访问档案：请检查对象、目录权限和文件是否已存在。\n' + DISCLAIMER, file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(cli())
