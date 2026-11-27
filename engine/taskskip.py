"""Complete the one ambient task whose active and finished layouts were observed in paired saves."""
import json

import featurelib as fl
import tasks as t

TASK_ID = 0xad8c8a22
KEY = 'ad8c8a22'
MARKER = '$0xa7840733'
ACTIVE = fl.key('ActiveAmbientObjectiveSaveData')
STEPS = fl.key('CompletedTasks')
FIELDS = (
    (t.SEC_COMPLETION, t.K_RECORDS, t.K_ID),
    (t.SEC_AMBIENT, t.K_AO, t.K_AO_ID),
    (t.SEC_AMBIENT, ACTIVE, t.K_AO_ID),
    (t.SEC_DISCOVERY, t.K_FLAGSTATE, t.K_NAME),
    (t.SEC_DISCOVERY, fl.key('Discovered'), None),
    (t.SEC_DISCOVERY, fl.key('DiscoveryOrder'), None),
)
ID_VALUE = {'$data': '0x' + KEY}


def rows(save, sec, field, identity):
    path = [fl.CODE, fl.key(sec)] if sec == t.SEC_DISCOVERY else [t.SCRIPT, fl.key(sec), t.SCRIPT_INNER]
    text = save.text(sec)
    start, end = fl.walk(text, *path, field)
    entries = []
    for a, z in fl.elements(text, start):
        token = text[a:z]
        row = json.loads(token)
        i = t._hash(row[identity] if identity else row)
        entries.append((i, token))
    return text, start, end, entries


def snapshot(save):
    result = []
    for spec in FIELDS:
        found = [token for i, token in rows(save, *spec)[3] if i == TASK_ID]
        if len(found) > 1:
            raise fl.FeatureError('task_layout')
        result.append(found[0] if found else None)
    return result


def phase(tokens):
    record, objective, active, flag, discovered, ordered = [json.loads(v) if v else None for v in tokens]
    if not objective or type(objective.get(MARKER)) is not int:
        return 'unavailable'
    base = {t.K_AO_ID: ID_VALUE, MARKER: objective[MARKER]}
    if (record is None and objective == {**base, t.K_AO_STATE: 2, t.K_AO_FLAGS: 0}
            and active == {t.K_AO_ID: ID_VALUE, STEPS: 0}
            and flag == {t.K_NAME: ID_VALUE, t.K_STATEFLAGS: 64} and discovered == ordered == ID_VALUE):
        return 'active'
    if (record == {t.K_ID: ID_VALUE, t.K_TYPE: 2}
            and objective == {**base, t.K_AO_STATE: 3, t.K_AO_FLAGS: 65}
            and flag == {t.K_NAME: ID_VALUE, t.K_STATEFLAGS: 192} and active is discovered is ordered is None):
        return 'done'
    return 'unavailable'


def status(data):
    return phase(snapshot(fl.Save(data)))


def apply(data, reference):
    save = fl.Save(data)
    current = phase(snapshot(save))
    if current == 'done':
        return data, []
    if current != 'active' or not reference:
        raise fl.FeatureError('task_layout')
    finished = snapshot(fl.Save(reference))
    if phase(finished) != 'done':
        raise fl.FeatureError('task_layout')

    records = t.records(save)
    ids = [t._s32(i) for i, _ in records]
    count = sum(kind in (2, 3) for _, kind in records)
    stats = fl.Stats(save.text(fl.STATS))
    if ids != sorted(set(ids)) or stats.value(*t.COUNTER) != count:
        raise fl.FeatureError('task_layout')
    for (sec, field, identity), replacement in zip(FIELDS, finished):
        text, start, end, entries = rows(save, sec, field, identity)
        if sec == t.SEC_COMPLETION:
            entries.append((TASK_ID, replacement))
            entries.sort(key=lambda entry: t._s32(entry[0]))
        else:
            entries = [(i, replacement if i == TASK_ID else token) for i, token in entries
                       if i != TASK_ID or replacement is not None]
        save.set_text(sec, text[:start] + b'[' + b','.join(token for _, token in entries) + b']' + text[end:])
    if not (stats.set(*t.COUNTER, count + 1, 'Optional tasks')
            and stats.set(*t.PCT, t.percent_for(count + 1), 'Optional task progress')):
        raise fl.FeatureError('task_layout')
    save.set_text(fl.STATS, stats.apply()[0])
    if phase(snapshot(save)) != 'done' or set(t.records(save)) != set(records) | {(TASK_ID, 2)}:
        raise fl.FeatureError('verify_failed')
    return save.build(), [{'what': 'optional_task', 'label': 'Optional task 0xad8c8a22', 'from': count, 'to': count + 1}]
