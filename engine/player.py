# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Lucia's and Jason's attributes, criminal profile and relationship, and a vest for a character who wears no armour
(Save Garage feature module, shown on the World tab).

WHAT IT CHANGES (each value is replaced in place after its old token is checked; everything else stays as written)
  PlayerCharacter section 22a87829: attributeSet $0xdad204f6 holds one entry per character, found by its Name
  $0xacec22be (joaat 'lucia' or 'jason'), with attributes $0x749dbb9e (int_array of 37) and the criminal profile
  $0x177caa16 (a float). The relationship $0xab1347a3 belongs to the pair and sits next to relationshipScriptCap
  $0x41319109, relationshipScriptLowerCap $0xe32a3fbf, relationshipLevel $0x650b110b, relationshipDisabled $0xa166f47a
  and relationshipLocked $0x5a51aa09.
  PlayerAppearance section 9653b39d: PlayerSavedOutfits $0x32fe6867 holds one entry per character, found by its $key
  (joaat 'player_lucia' or 'player_jason'; Jason's comes first in every save), with ArmourParts $0x5e8a4ee1 (6 parts
  of fArmour $0x45b925e3, fMaxArmour $0x9f8e2fa0 and $0x8034969a) and bCachedArmourValues $0x65be54f8.

  * Special meter: attribute slot 24 raised to 100. Raise only.
  * Skills: attribute slots 9, 10, 13, 14, 15, 19, 20 and 35 raised to a chosen value up to 99. Raise only.
  * Criminal profile: set to a value from -100 to 0.25, written as the game writes it (float32, six decimals).
  * Relationship: write a 0–100 score and its estimated level together while both story switches are off.
    The stored script bounds are retained as metadata.
  * Vest: for a character whose six armour parts are all 0/0 and who owns the vest garment, part 1 becomes 150/150
    and bCachedArmourValues true. A character who already wears armour is left as is (Fill armour tops it up).

EVIDENCE FROM THE SAVES (15 game-written saves, 30 character states)
  * attributes has 37 ints in every save. Slots 9, 10, 13, 15, 19, 20 and 35 are 50 in every state and slot 14 is 40
    (60 once): no game-written state has more than 60 in any of them. Slot 24 is 50 or 100 (100 twice). Slots 17 and
    23 rise and fall between saves like running meters, 0-3 are core values and 30-33 repeat them; those are never
    changed here. The names come from other editors (GarlicSaves, from a NinjaSaves before/after): skills, and the
    special ability meter for slot 24. GarlicSaves writes 99 to the skills and reports it tested in the game. The
    game's own names for the slots aren't known.
  * The criminal profile runs from -100 (Lucia late in one playthrough) to +0.25; a new playthrough starts Lucia at
    exactly -25. The game's text calls it the criminal profile, a temperament with the profiles Professional,
    Hardened, Violent, Psycho and Irredeemable, shown in the Jason & Lucia menu. Which value gives which profile isn't
    known.
  * The relationship is 52 to 100. relationshipScriptCap is 69 (lower cap 22) early in each playthrough and 100 (0)
    later; relationshipLocked turns true later in the story; relationshipDisabled is always false.
  * Armour: part 1 is the vest, with a maximum of 150 whenever armour is worn; the other parts are always 0/0 and
    $0x8034969a always false. bCachedArmourValues is true in exactly the 12 armoured states and false in all 18 bare
    ones. The vest is a wardrobe item: garment_s01_armortorsomilitary_fr1_000_001 in Lucia's inventory (InventoryId
    0xC0000002), ..._mr1_... in Jason's (0xC0000003), in every save of the first playthrough and none of the second.

REFUSED (FeatureError, nothing written): attributes_layout (not exactly one attribute set per character, or not 37
  ints), relationship_locked, relationship_disabled, no_vest (no vest garment to put on), out_of_range, bad_value,
  bad_request, layout_changed, verify_failed.

RISK: the special meter caution; skills, criminal profile, relationship and vest experimental. None tested on a PS5 yet.
"""
import json
import math
import re

import featurelib as fl
import jsonedit as je
import money

FEATURE = 'player'
CHAR, LOOKS = 0x22a87829, 0x9653b39d
K_SETS, K_NAME, K_ATTRS, K_PROFILE = '$0xdad204f6', '$0xacec22be', '$0x749dbb9e', '$0x177caa16'
K_REL, K_REL_CAP, K_REL_LOW, K_REL_LEVEL = '$0xab1347a3', '$0x41319109', '$0xe32a3fbf', '$0x650b110b'
K_REL_OFF, K_REL_LOCKED = '$0xa166f47a', '$0x5a51aa09'
K_OUTFITS, K_PARTS, K_ARMOUR, K_MAX, K_PART_FLAG, K_CACHED = ('$0x32fe6867', '$0x5e8a4ee1', '$0x45b925e3', '$0x9f8e2fa0',
                                                              '$0x8034969a', '$0x65be54f8')
K_INVENTORIES, K_INVENTORY_ID, K_WARDROBE = '$0x789bdd41', '$0x3e226822', money.K_SUBLISTS[2]
CHARACTERS = (('lucia', 'Lucia'), ('jason', 'Jason'))
NAME = dict(CHARACTERS)
SET_NAME = {'lucia': fl.joaat('lucia'), 'jason': fl.joaat('jason')}                     # attributeSet Name
OUTFIT_KEY = {'lucia': fl.joaat('player_lucia'), 'jason': fl.joaat('player_jason')}     # PlayerSavedOutfits $key
INVENTORY_ID = {'lucia': 0xc0000002, 'jason': 0xc0000003}
VEST = {'lucia': fl.joaat('garment_s01_armortorsomilitary_fr1_000_001'),
        'jason': fl.joaat('garment_s01_armortorsomilitary_mr1_000_001')}
N_ATTRS = 37
METER_SLOT, METER_FULL = 24, 100
SKILL_SLOTS = (9, 10, 13, 14, 15, 19, 20, 35)
SKILL_MIN, SKILL_MAX = 1, 99
SKILL_CHOICES = (60, 99)         # the most the game wrote in any save checked; what GarlicSaves writes
NEVER = (0, 1, 2, 3, 17, 23, 30, 31, 32, 33)                   # core values and the two running meters
PROFILE_MIN, PROFILE_MAX, PROFILE_NEW_GAME = -100.0, 0.25, -25.0
N_PARTS, VEST_PART, VEST_ARMOUR = 6, 1, 150.0
KEYS = ('lucia', 'jason', 'relationship')                      # the World tab's edits handled here
CHAR_KEYS = ('meter', 'skills', 'profile', 'vest')
# why the Save data browser keeps the relationship's own fields read-only (see raw_rules)
STORY_LIMIT = 'set by the story to limit the relationship'
# Local saves have (15,0), (25,1), (69,2), (72,2) and (81,2).
# Estimate transitions halfway across the unsampled gaps, using 100 as the
# endpoint for the fourth tier. These are editor estimates, not game constants.
REL_LEVEL_STARTS = (0, 20, 47, 91)
REL_MAX = 100
REL_LOCKED = 'the story has locked the relationship at this point'
REL_OFF = 'the story has switched the relationship off at this point'

_INT = re.compile(rb'-?(?:0|[1-9][0-9]*)')
_FLOAT = re.compile(rb'-?[0-9]+\.[0-9]+')
_HASH = re.compile(rb'"0x([0-9a-fA-F]{8})"')


# ---------------------------------------------------------------- finding the values
def _spans(t, s):
    """{key: (start, end)} of the object at s. A repeated key is a layout this module doesn't know."""
    m = fl.members(t, s)
    d = {k: (vs, ve) for k, vs, ve in m}
    if len(d) != len(m):
        raise fl.FeatureError('layout_changed')
    return d


def _hash_of(t, span):
    """A typed hash {"$data":"0x2fe5af54"} or a "0x…" string -> int, else None."""
    vs, ve = span
    if t[vs] == ord('{'):
        m = _spans(t, vs)
        if set(m) != {'$data'}:
            return None
        vs, ve = m['$data']
    g = _HASH.fullmatch(t[vs:ve])
    return int(g.group(1), 16) if g else None


def _root(t):
    s, _ = fl.walk(t, fl.CODE, fl.key(CHAR))
    return _spans(t, s)


def _sets(t, root):
    """{character: spans of its attribute set}. Exactly one set per character, or attributes_layout."""
    if K_SETS not in root or t[root[K_SETS][0]] != ord('['):
        raise fl.FeatureError('attributes_layout')
    who_of = {h: who for who, h in SET_NAME.items()}
    out = {}
    for es, _ in fl.elements(t, root[K_SETS][0]):
        if t[es] != ord('{'):
            raise fl.FeatureError('attributes_layout')
        m = _spans(t, es)
        who = who_of.get(_hash_of(t, m[K_NAME])) if K_NAME in m else None
        if who is None:
            continue                                   # a set for someone else is left alone
        if who in out:
            raise fl.FeatureError('attributes_layout')
        out[who] = m
    if set(out) != set(SET_NAME):
        raise fl.FeatureError('attributes_layout')
    return out


def _attributes(t, m):
    """(start of the int_array object, its 37 tokens), or attributes_layout."""
    if K_ATTRS not in m or t[m[K_ATTRS][0]] != ord('{'):
        raise fl.FeatureError('attributes_layout')
    obj = m[K_ATTRS][0]
    om = _spans(t, obj)
    if t[slice(*om.get('$content', (0, 0)))] != b'"int_array"':
        raise fl.FeatureError('attributes_layout')
    _, toks = fl.typed_values(t, obj)
    if len(toks) != N_ATTRS or not all(_INT.fullmatch(x) for x in toks):
        raise fl.FeatureError('attributes_layout')
    return obj, toks


def _profile(t, m):
    """((start, end), token) of the criminal profile, or layout_changed."""
    if K_PROFILE not in m or not _FLOAT.fullmatch(t[slice(*m[K_PROFILE])]):
        raise fl.FeatureError('layout_changed')
    return m[K_PROFILE], t[slice(*m[K_PROFILE])]


def _relationship(t, root):
    """({value, lowerCap, cap, level, locked, disabled}, span of the value), or layout_changed."""
    out = {}
    for k, name in ((K_REL, 'value'), (K_REL_LOW, 'lowerCap'), (K_REL_CAP, 'cap'), (K_REL_LEVEL, 'level')):
        tok = t[slice(*root[k])] if k in root else b''
        if not _INT.fullmatch(tok):
            raise fl.FeatureError('layout_changed')
        out[name] = int(tok)
    for k, name in ((K_REL_LOCKED, 'locked'), (K_REL_OFF, 'disabled')):
        tok = t[slice(*root[k])] if k in root else b''
        if tok not in (b'true', b'false'):
            raise fl.FeatureError('layout_changed')
        out[name] = tok == b'true'
    return out, root[K_REL]


def _rel_problem(r):
    return 'relationship_disabled' if r['disabled'] else 'relationship_locked' if r['locked'] else None


def _outfits(t):
    """{character: {'parts': [spans of each armour part], 'cached': span of bCachedArmourValues}}, or layout_changed."""
    s, _ = fl.walk(t, fl.CODE, fl.key(LOOKS), K_OUTFITS)
    if t[s] != ord('['):
        raise fl.FeatureError('layout_changed')
    who_of = {h: who for who, h in OUTFIT_KEY.items()}
    out = {}
    for es, _ in fl.elements(t, s):
        if t[es] != ord('{'):
            raise fl.FeatureError('layout_changed')
        m = _spans(t, es)
        who = who_of.get(_hash_of(t, m['$key'])) if '$key' in m else None
        if who is None:
            continue
        if who in out or K_PARTS not in m or K_CACHED not in m or t[m[K_PARTS][0]] != ord('['):
            raise fl.FeatureError('layout_changed')
        parts = []
        for ps, _ in fl.elements(t, m[K_PARTS][0]):
            if t[ps] != ord('{'):
                raise fl.FeatureError('layout_changed')
            pm = _spans(t, ps)
            if set(pm) != {K_ARMOUR, K_MAX, K_PART_FLAG}:
                raise fl.FeatureError('layout_changed')
            parts.append(pm)
        out[who] = {'parts': parts, 'cached': m[K_CACHED]}
    return out


def _vest_state(t, o, owns):
    """('can_add' | 'worn' | 'no_vest' | 'unknown', armour now, its maximum) for one character's saved outfit."""
    if not o or len(o['parts']) != N_PARTS:
        return 'unknown', None, None
    vals = []
    for pm in o['parts']:
        a, mx, flag = (t[slice(*pm[k])] for k in (K_ARMOUR, K_MAX, K_PART_FLAG))
        if not (_FLOAT.fullmatch(a) and _FLOAT.fullmatch(mx)) or flag not in (b'true', b'false'):
            return 'unknown', None, None
        vals.append((float(a), float(mx), flag == b'true'))
    cached = t[slice(*o['cached'])]
    armour, top = sum(v[0] for v in vals), sum(v[1] for v in vals)
    if cached not in (b'true', b'false'):
        return 'unknown', armour, top
    if any(v[0] or v[1] for v in vals):
        return 'worn', armour, top
    if cached == b'true' or any(v[2] for v in vals):      # bare but flagged: a state no save has shown
        return 'unknown', armour, top
    return ('can_add' if owns else 'no_vest'), armour, top


def _owns_vest(inv_txt):
    """{character: whether its wardrobe holds its vest garment}, by InventoryId."""
    invs = json.loads(inv_txt)[fl.CODE][fl.key(money.SEC_INV)][K_INVENTORIES]
    out = dict.fromkeys(INVENTORY_ID, False)
    for inv in invs:
        iid = inv.get(K_INVENTORY_ID)
        who = next((w for w, i in INVENTORY_ID.items() if isinstance(iid, int) and iid & fl.M32 == i), None)
        if who:
            items = money._data((inv.get(K_WARDROBE) or {}).get(money.K_ITEM))
            out[who] = any(isinstance(x, int) and x & fl.M32 == VEST[who] for x in items)
    return out


# ---------------------------------------------------------------- read
def read(b):
    s = fl.Save(b)
    t, lt = s.text(CHAR), s.text(LOOKS)
    root, sets, set_problem = None, None, 'attributes_layout'
    try:
        root = _root(t)
        sets, set_problem = _sets(t, root), None
    except fl.FeatureError as e:
        set_problem = str(e)
    try:
        outfits = _outfits(lt)
    except fl.FeatureError:
        outfits = {}
    try:
        owns = _owns_vest(s.text(money.SEC_INV))
    except (KeyError, ValueError, TypeError, IndexError, AttributeError):
        owns = {}
    chars = []
    for who, name in CHARACTERS:
        c = {'key': who, 'name': name, 'meter': None, 'skills': None, 'profile': None, 'attributesProblem': set_problem}
        if sets:
            try:
                _, toks = _attributes(t, sets[who])
                c['meter'] = int(toks[METER_SLOT])
                c['skills'] = [int(toks[i]) for i in SKILL_SLOTS]
            except fl.FeatureError as e:
                c['attributesProblem'] = str(e)
            try:
                c['profile'] = float(_profile(t, sets[who])[1])
            except fl.FeatureError:
                pass
        state, armour, top = _vest_state(lt, outfits.get(who), owns.get(who, False))
        c['vest'] = {'state': state, 'armour': armour, 'max': top, 'owned': owns.get(who)}
        chars.append(c)
    rel = {'problem': 'layout_changed'}
    if root is not None:
        try:
            rel, _ = _relationship(t, root)
            rel['problem'] = _rel_problem(rel)
            rel.update(scoreMin=0, scoreMax=REL_MAX, levelStarts=list(REL_LEVEL_STARTS))
        except fl.FeatureError as e:
            rel = {'problem': str(e)}
    return {'feature': FEATURE, 'characters': chars, 'relationship': rel,
            'meterSlot': METER_SLOT, 'meterFull': METER_FULL, 'skillSlots': list(SKILL_SLOTS), 'skillMin': SKILL_MIN,
            'skillMax': SKILL_MAX, 'skillChoices': list(SKILL_CHOICES), 'profileMin': PROFILE_MIN,
            'profileMax': PROFILE_MAX, 'profileNewGame': PROFILE_NEW_GAME, 'vestArmour': VEST_ARMOUR,
            'risk': {'meter': 'caution', 'skills': 'experimental', 'profile': 'experimental', 'relationship': 'experimental',
                     'vest': 'experimental'}}


# ---------------------------------------------------------------- apply
def _number(v, whole):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise fl.FeatureError('bad_value')
    if whole:
        if isinstance(v, float) and not v.is_integer():
            raise fl.FeatureError('bad_value')
        return int(v)
    return float(v)


def _checked(edit):
    """Check requested field types and editor ranges."""
    if not isinstance(edit, dict) or set(edit) - set(KEYS):
        raise fl.FeatureError('bad_request')
    out = {}
    for who in SET_NAME:
        c = edit.get(who)
        if c is None:
            continue
        if not isinstance(c, dict) or set(c) - set(CHAR_KEYS):
            raise fl.FeatureError('bad_request')
        cc = {}
        if c.get('meter') is not None:
            if c['meter'] != 'full':
                raise fl.FeatureError('bad_request')
            cc['meter'] = METER_FULL
        if c.get('skills') is not None:
            cc['skills'] = _number(c['skills'], True)
            if not SKILL_MIN <= cc['skills'] <= SKILL_MAX:
                raise fl.FeatureError('out_of_range')
        if c.get('profile') is not None:
            cc['profile'] = _number(c['profile'], False)
            if not PROFILE_MIN <= cc['profile'] <= PROFILE_MAX:
                raise fl.FeatureError('out_of_range')
        if c.get('vest') is not None:
            if c['vest'] is not True:
                raise fl.FeatureError('bad_request')
            cc['vest'] = True
        out[who] = cc
    if edit.get('relationship') is not None:
        target = edit['relationship']
        if isinstance(target, dict):  # presets saved by earlier builds
            if set(target) != {'value', 'level'}:
                raise fl.FeatureError('bad_request')
            level = _number(target['level'], True)
            if not 0 <= level < len(REL_LEVEL_STARTS):
                raise fl.FeatureError('out_of_range')
            target = target['value']
        out['relationship'] = _number(target, True)
    return out


def _zero(tok):
    return bool(_FLOAT.fullmatch(tok)) and float(tok) == 0.0


def profile_token(v):
    """The criminal profile as the game writes it: the float32 value with six decimals ('-45.450001')."""
    v = fl.f32(v)
    return b'%.6f' % (v if v else 0.0)


def edit_relationship(text, score):
    """Apply the same score-to-level rule for the player, research and raw editors."""
    score = _number(score, True)
    if not 0 <= score <= REL_MAX:
        raise fl.FeatureError('out_of_range')
    root = _root(text)
    rel, _ = _relationship(text, root)
    problem = _rel_problem(rel)
    if problem:
        raise fl.FeatureError(problem)
    level = sum(score >= start for start in REL_LEVEL_STARTS) - 1
    updates = [(root[K_REL], rel['value'], score, 'Relationship'),
               (root[K_REL_LEVEL], rel['level'], level, 'Relationship level')]
    log = []
    for (start, end), old, new, label in sorted(updates, reverse=True):
        if old != new:
            text = text[:start] + str(new).encode() + text[end:]
            log.append({'what': 'world', 'label': label, 'from': old, 'to': new})
    return text, log


def apply(b, edit):
    """edit: {'lucia': {'meter': 'full', 'skills': 99, 'profile': -25.0, 'vest': True}, 'jason': {...},
    'relationship': 69}; any key may be missing -> (new bytes, log). Applying the result again changes nothing."""
    edit = _checked(edit)
    s = fl.Save(b)
    t = s.text(CHAR)
    log = []
    for who, name in CHARACTERS:
        c = edit.get(who) or {}
        want = {}
        if c.get('meter'):
            want[METER_SLOT] = c['meter']
        if c.get('skills') is not None:
            want.update((i, c['skills']) for i in SKILL_SLOTS)
        if want:
            obj, toks = _attributes(t, _sets(t, _root(t))[who])
            raised = [(i, int(toks[i]), v) for i, v in sorted(want.items()) if v > int(toks[i])]     # raise only
            for i, old, v in raised:
                t = fl.typed_set(t, obj, i, toks[i], b'%d' % v)                              # old token checked
            if any(i == METER_SLOT for i, _, _ in raised):
                old = next(o for i, o, _ in raised if i == METER_SLOT)
                log.append({'what': 'world', 'label': 'Special meter (%s)' % name, 'from': old, 'to': METER_FULL})
            skills = [(i, o, v) for i, o, v in raised if i in SKILL_SLOTS]
            if skills:
                log.append({'what': 'world', 'label': 'Skills (%s)' % name, 'from': min(o for _, o, _ in skills),
                            'to': c['skills'], 'slots': [i for i, _, _ in skills]})
        if c.get('profile') is not None:
            (vs, ve), tok = _profile(t, _sets(t, _root(t))[who])
            new = profile_token(c['profile'])
            if new != tok:
                t = t[:vs] + new + t[ve:]
                log.append({'what': 'world', 'label': 'Criminal profile (%s)' % name, 'from': float(tok), 'to': float(new)})
    if edit.get('relationship') is not None:
        t, changes = edit_relationship(t, edit['relationship'])
        log.extend(changes)
    if t != s.text(CHAR):
        s.set_text(CHAR, t)
    vests = [who for who, _ in CHARACTERS if (edit.get(who) or {}).get('vest')]
    if vests:
        lt = s.text(LOOKS)
        outfits, owns = _outfits(lt), _owns_vest(s.text(money.SEC_INV))
        swaps = []
        for who in vests:
            state, _, _ = _vest_state(lt, outfits.get(who), owns[who])
            if state == 'worn':                  # armour on already (a second run, too): nothing to do
                continue
            if state != 'can_add':
                raise fl.FeatureError('no_vest' if state == 'no_vest' else 'layout_changed')
            part = outfits[who]['parts'][VEST_PART]
            swaps += [(part[K_ARMOUR], _zero, b'%.6f' % VEST_ARMOUR), (part[K_MAX], _zero, b'%.6f' % VEST_ARMOUR),
                      (outfits[who]['cached'], lambda tok: tok == b'false', b'true')]
            log.append({'what': 'world', 'label': 'Vest (%s)' % NAME[who], 'from': 0.0, 'to': VEST_ARMOUR})
        for (vs, ve), was, new in sorted(swaps, key=lambda x: -x[0][0]):     # the last span first keeps the others valid
            if not was(lt[vs:ve]):                                           # the old token is still the bare value
                raise fl.FeatureError('verify_failed')
            lt = lt[:vs] + new + lt[ve:]
        if swaps:
            s.set_text(LOOKS, lt)
    if not log:
        return b, []
    return s.build(), log


# ---------------------------------------------------------------- the Save data browser's rules for the same fields
def relationship_rule(txt, path):
    """The relationship value: from 0 to 100, read-only while the story has it locked or switched off."""
    try:
        rel, _ = _relationship(txt, _root(txt))
    except (fl.FeatureError, KeyError, IndexError, ValueError):
        return STORY_LIMIT
    if rel['disabled']:
        return REL_OFF
    if rel['locked']:
        return REL_LOCKED
    return (0, REL_MAX)


def attribute_rule(txt, path):
    """One element of a character's attributes: the special meter up to 100 and the skills up to 99, as on the World tab."""
    if len(path) < 2 or path[-2] != '$data' or not isinstance(path[-1], int):
        return None
    if path[-1] == METER_SLOT:
        return (0, METER_FULL)
    if path[-1] in SKILL_SLOTS:
        return (0, SKILL_MAX)
    return None


def armour_rule(txt, path):
    """fArmour of one armour part: up to that part's fMaxArmour, as the World tab fills it."""
    try:
        return (0.0, float(je.get(txt, list(path[:-1]) + [K_MAX])))
    except (je.PathError, ValueError, IndexError):
        return None


def raw_rules():
    """{(section, key): rule} for savebrowse.FIELD_RULES."""
    return {(CHAR, K_PROFILE): (PROFILE_MIN, PROFILE_MAX), (CHAR, K_REL): relationship_rule, (CHAR, K_ATTRS): attribute_rule,
            (CHAR, K_REL_CAP): STORY_LIMIT, (CHAR, K_REL_LOW): STORY_LIMIT, (CHAR, K_REL_LOCKED): STORY_LIMIT,
            (CHAR, K_REL_OFF): STORY_LIMIT, (LOOKS, K_ARMOUR): armour_rule, (LOOKS, K_MAX): (0.0, VEST_ARMOUR)}
