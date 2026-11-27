// Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
'use strict';
// Save Garage translations. The page is written in English; this swaps the text people read for the chosen language,
// as it appears (the page re-renders often), sentence by sentence where a whole text has no translation. Game names
// (missions, vehicles, places, stats) stay as the game writes them. Translations live in i18n/<code>.json as
// {"English text": "translation"}; numbers in a text are {0}, {1}, ... in both.
(() => {
  const LANGS = [['en', 'English'], ['de', 'Deutsch'], ['nl', 'Nederlands'], ['fr', 'Français'], ['es', 'Español'],
    ['pt-BR', 'Português (Brasil)'], ['it', 'Italiano'], ['pl', 'Polski'], ['ru', 'Русский'], ['ar', 'العربية'],
    ['ja', '日本語'], ['ko', '한국어'], ['zh-CN', '中文（简体）']];
  const RTL = new Set(['ar']);
  const NO_SPACE = new Set(['ja', 'zh-CN']);           // sentences are joined without a space
  const KEY = 'save-garage-language';
  // parts of the page that hold names from the game or the save, never translated
  const SKIP = 'script, style, input, textarea, select, option, [data-no-i18n], .weapons, #allrows, .crumbs, .review, .ck td.key small, .means, #version';
  const ATTRS = ['placeholder', 'aria-label', 'title', 'alt'];
  const NUM = /(?<![A-Za-z0-9.])[-+]?\$?\d(?:[\d,]*\d)?(?:\.\d+)?%?(?![A-Za-z0-9])/g;   // numbers, not the 5 in PS5
  const SPLIT = /(?<=[.!?…:])\s+(?=[A-Z0-9"“'‘$(¡¿])/;

  const norm = s => String(s).replace(/\s+/g, ' ').trim();
  // a text's translation key: numbers become {0}, {1}, ...
  function templateOf(s) {
    let k = 0;
    const t = norm(s).split(/(\{\d+\})/).map(p => /^\{\d+\}$/.test(p) ? '\u0000' : p.replace(NUM, '\u0000')).join('');
    return t.replace(/\u0000/g, () => `{${k++}}`);
  }
  // the units a text is translated in: the whole text, and each sentence of it
  function units(s) {
    const t = norm(s);
    if (!/[A-Za-z]{2}/.test(t)) return [];
    const parts = t.split(SPLIT).filter(p => /[A-Za-z]{2}/.test(p));
    const out = new Set([renumber(templateOf(t))]);
    if (parts.length > 1) for (const p of parts) out.add(renumber(templateOf(p)));
    return [...out];
  }
  // placeholders numbered in order of appearance
  function renumber(t) { let k = 0; const map = {}; return t.replace(/\{(\d+)\}/g, (_, d) => `{${map[d] ??= k++}}`); }

  let lang = 'en', exact = new Map(), tpls = [];
  function compile(dict) {
    exact = new Map(); tpls = [];
    for (const [src, dst] of Object.entries(dict || {})) {
      if (!dst) continue;
      if (!/\{\d+\}/.test(src)) { exact.set(src, dst); continue; }
      const letters = src.replace(/\{\d+\}/g, '').replace(/[^A-Za-z]/g, '').length;
      const ph = letters < 8 ? '([-+]?\\$?\\d[\\d,]*(?:\\.\\d+)?%?)' : '((?:(?![.!?…:]\\s+[A-Z0-9"“\'‘$(¡¿]).)+?)';
      const order = [];
      const re = '^' + src.split(/(\{\d+\})/).map(p => { const m = /^\{(\d+)\}$/.exec(p); if (m) { order.push(+m[1]); return ph; } return p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('') + '$';
      tpls.push({re: new RegExp(re), order, dst, weight: letters});
    }
    tpls.sort((a, b) => b.weight - a.weight);
  }
  function one(t) {
    if (exact.has(t)) return exact.get(t);
    for (const p of tpls) {
      const m = p.re.exec(t);
      if (!m) continue;
      const val = {};
      p.order.forEach((idx, i) => { val[idx] = exact.get(m[i + 1]) ?? m[i + 1]; });   // a piece that is a text of its own (a menu path) is translated too
      return p.dst.replace(/\{(\d+)\}/g, (_, d) => val[d] ?? '');
    }
    return null;
  }
  // the translation of a text, or null to leave it in English
  function tr(s) {
    const t = norm(s);
    if (!t || lang === 'en') return null;
    const whole = one(t);
    if (whole != null) return whole;
    const parts = t.split(SPLIT);
    if (parts.length < 2) return null;
    let any = false;
    const out = parts.map(p => { const x = one(p); if (x != null) any = true; return x ?? p; });
    return any ? out.join(NO_SPACE.has(lang) ? '' : ' ') : null;
  }

  // ------------------------------------------------------------ applying it to the page
  const seen = new WeakMap();                          // text node -> {en, out}
  const seenAttr = new WeakMap();                      // element -> {attr: {en, out}}
  const skipped = el => !!(el && el.closest && el.closest(SKIP));
  function doText(node) {
    const rec = seen.get(node);
    let en = node.data;
    if (rec && node.data === rec.out) en = rec.en;     // our own earlier write
    const lead = en.match(/^\s*/)[0], trail = en.match(/\s*$/)[0];
    const x = tr(en);
    const out = x == null ? en : lead + x + trail;
    seen.set(node, {en, out});
    if (node.data !== out) node.data = out;
  }
  function doAttrs(el) {
    let rec = seenAttr.get(el);
    for (const a of ATTRS) {
      if (!el.hasAttribute(a)) continue;
      const cur = el.getAttribute(a);
      rec ??= {};
      const r = rec[a];
      const en = r && cur === r.out ? r.en : cur;
      const x = tr(en), out = x == null ? en : x;
      rec[a] = {en, out};
      if (cur !== out) el.setAttribute(a, out);
    }
    if (rec) seenAttr.set(el, rec);
  }
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { if (!skipped(root.parentElement)) doText(root); return; }
    if (root.nodeType !== 1 || skipped(root)) return;
    doAttrs(root);
    const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: n => n.nodeType === 1 ? (skipped(n) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) : NodeFilter.FILTER_ACCEPT});
    for (let n = w.nextNode(); n; n = w.nextNode()) { if (n.nodeType === 3) { if (/\S/.test(n.data)) doText(n); } else doAttrs(n); }
  }
  let busy = false;
  const obs = new MutationObserver(list => {
    if (busy) return;
    busy = true;
    try {
      for (const m of list) {
        if (m.type === 'characterData') { if (!skipped(m.target.parentElement)) doText(m.target); }
        else if (m.type === 'attributes') { if (!skipped(m.target)) doAttrs(m.target); }
        else for (const n of m.addedNodes) walk(n);
      }
    } finally { obs.takeRecords(); busy = false; }
  });

  async function setLang(code, save) {
    if (!LANGS.some(([c]) => c === code)) code = 'en';
    let dict = {};
    if (code !== 'en') {
      try { dict = await (await fetch(`i18n/${code}.json`, {cache: 'no-cache'})).json(); } catch { code = 'en'; }
    }
    lang = code; compile(dict);
    if (save) try { localStorage.setItem(KEY, code); } catch { /* private mode */ }
    document.documentElement.lang = code;
    document.documentElement.dir = RTL.has(code) ? 'rtl' : 'ltr';
    const sel = document.getElementById('lang');
    if (sel && sel.value !== code) sel.value = code;
    busy = true; try { walk(document.body); document.title = document.querySelector('.brand-name').textContent; } finally { obs.takeRecords(); busy = false; }
  }

  function start() {
    const sel = document.getElementById('lang');
    if (sel) {
      sel.innerHTML = LANGS.map(([c, n]) => `<option value="${c}" lang="${c}">${n}</option>`).join('');
      sel.addEventListener('change', () => setLang(sel.value, true));
    }
    let saved = navigator.language?.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en';
    try { saved = localStorage.getItem(KEY) || saved; } catch { /* private mode */ }
    obs.observe(document.body, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS});
    setLang(saved, false);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();

  // used by the build script that collects the English text to translate
  window.SGI18N = {units, templateOf, renumber, tr, setLang, LANGS,
    // texts on the page left in English (for the coverage check)
    untranslated() {
      const out = new Set();
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {acceptNode: n => skipped(n.parentElement) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT});
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        const r = seen.get(n);
        if (r && r.out === r.en && /[A-Za-z]{3}/.test(r.en)) out.add(norm(r.en));
      }
      return [...out];
    },
    collect() {
      const out = new Set();
      const add = s => { for (const u of units(s)) out.add(u); };
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
        acceptNode: n => n.nodeType === 1 ? (skipped(n) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) : NodeFilter.FILTER_ACCEPT});
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        if (n.nodeType === 3) { const r = seen.get(n); add(r && n.data === r.out ? r.en : n.data); }
        else for (const a of ATTRS) if (n.hasAttribute(a)) add(n.getAttribute(a));
      }
      return [...out];
    }};
})();
