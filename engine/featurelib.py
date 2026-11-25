"""Shared helpers for the Save Garage story-save feature modules (compendium, discovery, challenges, hoops, gyms).

Nothing here re-serialises JSON. Every change is a splice into the section's original text, so all other bytes stay
as the game wrote them:
  * stats go through savedit._apply_stats (old value checked, floats '%.6f', bools true/false);
  * other sections are edited with the small scanner below, which finds the exact span of one value and replaces it;
  * the container is rebuilt with money._rebuild, which re-checks that every section parses and fixes offsets.

Keys are written as "$0x<joaat of the exact-case name>"; key() builds them from readable names.
"""
import json
import os
import struct
import sys

try:                                   # inside the app the engine modules are importable directly
    import money
    import savedit
except ImportError:                    # standalone: research_scratch/features -> ../../save-garage/engine
    sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'save-garage', 'engine')))
    import money
    import savedit

M32 = 0xffffffff
joaat = money.joaat
CODE = '$0x7a47cb05'                   # CodeSaveBlock wrapper
STATS = 0x0635cbd9
INVENTORY = 0xd3f59a5e
STORY = 'story000'                     # stats owner 0, the game-wide row


class FeatureError(savedit.SaveError):
    """Raised with a short machine code (stale_item, layout_changed, not_allowed, ...) like the rest of the engine."""


def key(name):
    """'NameHashes' -> '$0x872289a1' (exact-case joaat), or a hash int -> '$0x%08x'."""
    return '$0x%08x' % (joaat(name) if isinstance(name, str) else name & M32)


def h(x):
    """Name or int -> 32-bit hash (lower-case names are hashed as given)."""
    if isinstance(x, str):
        if x.startswith('0x'):
            return int(x, 16) & M32
        return joaat(x)
    return x & M32


def hexid(x):
    return '%08x' % (x & M32)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def pct32(count, total):
    """The game's cached percentage: float32((count / total)) * 100 in float32, capped at 100.
    Matches every cached value checked (60.000004 = 30/50, 18.571428 = 13/70, 1.111111 = 1/90, 81.5 = 163/200)."""
    if not total:
        return 0.0
    return f32(f32(min(count, total) / total) * 100.0)


# ---------------------------------------------------------------- container
class Save:
    """A decrypted JSAV file split into sections; edit .secs[i] (bytes) and call .build()."""

    def __init__(self, b):
        self.orig = b
        self.ents, self.secs, self.gaps, self.head, self.tail = money._load(b)

    def index(self, sec_hash):
        return money._sec(self.ents, sec_hash)

    def text(self, sec_hash):
        return self.secs[self.index(sec_hash)]

    def set_text(self, sec_hash, txt):
        self.secs[self.index(sec_hash)] = txt

    def build(self):
        return money._rebuild(self.head, [list(e) for e in self.ents], list(self.secs), self.gaps, self.tail, len(self.orig))


def payload(sec_txt, sec_hash):
    """Parsed section payload with the code wrapper removed."""
    return json.loads(sec_txt)[CODE][key(sec_hash)]


# ---------------------------------------------------------------- in-place JSON scanner (compact JSON as the game writes it)
_Q, _BS = 0x22, 0x5c
_OPEN, _CLOSE = b'{[', b'}]'


def _string_end(t, i):
    i += 1
    while True:
        c = t[i]
        if c == _BS:
            i += 2
        elif c == _Q:
            return i + 1
        else:
            i += 1


def value_end(t, i):
    """Index just past the JSON value starting at i."""
    c = t[i]
    if c == _Q:
        return _string_end(t, i)
    if c in _OPEN:
        depth = 0
        while True:
            c = t[i]
            if c == _Q:
                i = _string_end(t, i)
                continue
            if c in _OPEN:
                depth += 1
            elif c in _CLOSE:
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
    j = i
    while t[j] not in b',}]':
        j += 1
    if j == i:
        raise FeatureError('layout_changed')
    return j


def members(t, i):
    """[(key, value_start, value_end)] of the object starting at t[i] == '{'."""
    if t[i] != ord('{'):
        raise FeatureError('layout_changed')
    out = []
    i += 1
    if t[i] == ord('}'):
        return out
    while True:
        if t[i] != _Q:
            raise FeatureError('layout_changed')
        ke = _string_end(t, i)
        if t[ke] != ord(':'):
            raise FeatureError('layout_changed')
        vs = ke + 1
        ve = value_end(t, vs)
        out.append((t[i + 1:ke - 1].decode(), vs, ve))
        if t[ve] == ord(','):
            i = ve + 1
        elif t[ve] == ord('}'):
            return out
        else:
            raise FeatureError('layout_changed')


def elements(t, i):
    """[(value_start, value_end)] of the array starting at t[i] == '['."""
    if t[i] != ord('['):
        raise FeatureError('layout_changed')
    out = []
    i += 1
    if t[i] == ord(']'):
        return out
    while True:
        ve = value_end(t, i)
        out.append((i, ve))
        if t[ve] == ord(','):
            i = ve + 1
        elif t[ve] == ord(']'):
            return out
        else:
            raise FeatureError('layout_changed')


def member(t, i, k):
    """(value_start, value_end) of key k in the object at i; k is a '$0x..' key string."""
    for kk, vs, ve in members(t, i):
        if kk == k:
            return vs, ve
    raise FeatureError('layout_changed')


def walk(t, *keys):
    """Follow object keys from the document root; returns (start, end) of the final value."""
    s, e = 0, len(t)
    for k in keys:
        s, e = member(t, s, k)
    return s, e


def splice(t, s, e, new):
    return t[:s] + new + t[e:]


# typed arrays: {"$content":"int_array","$data":[...]} or {"$content":"int_array"} when empty
def typed_values(t, obj_start):
    """(data_span or None, [token bytes]) of a typed array object."""
    for k, vs, ve in members(t, obj_start):
        if k == '$data':
            if t[vs] != ord('['):
                raise FeatureError('layout_changed')
            inner = t[vs + 1:ve - 1]
            return (vs + 1, ve - 1), (inner.split(b',') if inner else [])
    return None, []


def typed_append(t, obj_start, tokens):
    """Append tokens (bytes) to a typed array object, adding "$data" when the array is empty."""
    if not tokens:
        return t
    span, cur = typed_values(t, obj_start)
    if span is None:
        end = value_end(t, obj_start)            # just past '}'
        return t[:end - 1] + b',"$data":[' + b','.join(tokens) + b']' + t[end - 1:]
    s, e = span
    return t[:e] + (b',' if cur else b'') + b','.join(tokens) + t[e:]


def typed_set(t, obj_start, idx, old, new):
    """Replace element idx of a typed array, checking the old token."""
    span, cur = typed_values(t, obj_start)
    if span is None or not 0 <= idx < len(cur) or cur[idx] != old:
        raise FeatureError('verify_failed')
    cur[idx] = new
    return t[:span[0]] + b','.join(cur) + t[span[1]:]


# ---------------------------------------------------------------- stats
class Stats:
    """Lookup of stat rows by (base, qualifier, owner) names or hashes, and in-place edits through savedit."""

    def __init__(self, sec_txt):
        self.txt = sec_txt
        self.groups, self.tables = savedit.stat_rows(sec_txt)
        A, Q, O = self.tables['base'], self.tables['qual'], self.tables['owner']
        self.where = {}
        for g, G in self.groups.items():
            for r in range(len(G['value'])):
                self.where[(A[G['base'][r]], Q[G['qual'][r]], O[G['owner'][r]])] = (g, r)
        self.changes = {}

    def row(self, base, qual=0, owner=STORY):
        loc = self.where.get((h(base), h(qual) if qual else 0, h(owner)))
        if not loc:
            return None
        g, r = loc
        G = self.groups[g]
        return {'group': g, 'row': r, 'base': G['base'][r], 'qual': G['qual'][r], 'owner': G['owner'][r], 'type': G['type'],
                'value': self.changes[(g, r)]['newValue'] if (g, r) in self.changes else G['value'][r]}

    def value(self, base, qual=0, owner=STORY, default=None):
        r = self.row(base, qual, owner)
        return default if r is None else r['value']

    def set(self, base, qual, new, label, owner=STORY):
        """Queue a change; returns False when the row does not exist."""
        loc = self.where.get((h(base), h(qual) if qual else 0, h(owner)))
        if not loc:
            return False
        g, r = loc
        G = self.groups[g]
        old = G['value'][r]
        if G['type'] == 'float':
            new = f32(new)
        if savedit._same(G['type'], old, new):
            self.changes.pop((g, r), None)
            return True
        self.changes[(g, r)] = {'group': g, 'row': r, 'base': G['base'][r], 'qual': G['qual'][r], 'owner': G['owner'][r],
                                'value': old, 'newValue': new, 'label': label}
        return True

    def apply(self):
        """-> (new section text, log)."""
        if not self.changes:
            return self.txt, []
        return savedit._apply_stats(self.txt, list(self.changes.values()))
