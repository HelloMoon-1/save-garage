'use strict';
// Save Garage: redesigned UI for the local save editor service (same /api as the original UI, plus /api/slot and /api/stats).
(() => {
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const nf = new Intl.NumberFormat('en-US');
  const nf2 = new Intl.NumberFormat('en-US', {maximumFractionDigits: 2});
  const main = $('#main'), routeEl = $('#route'), statusEl = $('#status'), pendingEl = $('#pending'), toastEl = $('#toast');

  const STEPS = [['connect', 'Connect'], ['pair', 'Pair'], ['download', 'Download'], ['edit', 'Edit'], ['send', 'Send back']];
  const OWNER = {0: 'Total', 1: 'Lucia', 2: 'Jason'};
  const MONEY_GROUP = '$0x97232209';
  const PS5_TRANSFER = 'Settings, then System, then System Software, then Data Transfer';
  const PS5_DELETE = 'Settings, then Saved Data and Game/App Settings, then Saved Data (PS5), then Console Storage, then Delete';
  const AMMO = {pistol: 'Pistol', revolver: 'Revolver', smg: 'SMG', rifle: 'Rifle', shotgun: 'Shotgun', sniper: 'Sniper', marksman: 'Marksman',
                mg: 'Machine gun', minigun: 'Minigun', sporting: 'Sporting', thrown_grenade: 'Grenades'};
  const CATS = [
    ['progress', 'Progress', 'Percentages and counters from the stats screen.'],
    ['fitness', 'Fitness', 'Health and stamina for each character. The total updates itself to Lucia plus Jason.'],
    ['time', 'Time and distance', 'Play time and how you got around. Times are in hours.'],
    ['earnings', 'Money earned', 'Records of money you earned. Changing these does not add money. Use the Money tab for that.'],
    ['wanted', 'Wanted levels', 'How often and how long the police were after you. Times are in hours.'],
    ['records', 'Records', 'Combat, vehicle and other counters.'],
    ['trophies', 'Trophy counters', 'Counters behind some of the trophies. Raising one may make the game award the trophy the next time the counter goes up, and trophy sites such as PSNProfiles may flag that. The things a counter counts are not changed, so the numbers can stop matching.'],
    ['gadgets', 'Gadgets', 'Flags for gadgets you picked up.']];
  const TYPE_MAX = {int32: 2147483647, u32: 4294967295, int64: 9007199254740991, int16: 32767, u8: 127, float: 1e12};
  const STAGE = {
    pair_waiting_console: 'Waiting for the PS5', pair_reading: 'Reading the pairing request', paired: 'Paired',
    connecting: 'Connecting to your PS5', need_power: 'Press the PS5 power button', reading_list: 'Reading the save list',
    downloading: 'Downloading your save', decrypting: 'Decrypting your save', ready: 'Your save is ready to edit',
    patching: 'Applying your edits', encrypting: 'Encrypting the edited save', importing: 'Getting the save ready to send',
    ready_to_upload: 'Edits saved and ready to send', preparing: 'Preparing the transfer', waiting_console: 'Waiting for Data Transfer on the PS5',
    console_connected: 'PS5 connected. Keep this page open.', transferring: 'Sending your save', uploaded: 'Your save is back on the PS5', starting: 'Starting'};
  const ERR = {
    garlic_unreachable: 'The decryption service (garlicsaves.com) can’t be reached. Check your internet connection, then try again.',
    not_paired: 'This PS5 isn’t paired yet. Pair it first.',
    power_timeout: 'The power-button wait timed out, or the key service was too slow. Go back to the PS5 home screen and try again.',
    console_rejected: 'The PS5 refused the request. Sign in with the account you paired with, or pair again.',
    no_gta_save: 'No GTA VI save was found on the PS5. Save once in the game, then try again.',
    no_story_slot: 'No story save was found. Save once in story mode, then try again.',
    pair_failed: 'Pairing failed or timed out. Start pairing again.',
    save_layout_changed: 'The save layout is different from what this editor knows. Download again. If it still fails, the editor needs an update.',
    save_verify_failed: 'A value in the save didn’t match what was expected. Download again and redo the edit.',
    save_stale_item: 'Some values changed since this page loaded them. Reload the page and redo the edit.',
    save_protected_stat: 'That stat is kept in sync by the Money tab and can’t be edited directly.',
    save_bad_value: 'One of the new values isn’t valid for its field.',
    save_out_of_range: 'One of the new values is outside the allowed range.',
    save_bad_request: 'The edit didn’t match this save. Reload the page and try again.',
    no_change: 'Nothing changed. Edit a value first.',
    port_in_use: 'Ports 1004 to 1006 are already in use. Close any other save-transfer tool or another copy of Save Garage.',
    upload_failed: 'Sending failed. Check the PS5 and the network, then try again.',
    download_failed: 'The download failed. Go back to the PS5 home screen and try again.',
    tool_failed: 'Save processing failed. Open the details below.',
    internal: 'Something went wrong. Open the details below.',
    busy: 'Another task is running. Wait for it to finish.',
    no_console: 'No PS5 selected. Connect first.',
    no_session: 'No save downloaded yet.',
    nothing_to_upload: 'There are no saved edits to send.',
    console_not_found: 'No PS5 answered at that address. Check the IP address and that the PS5 is on.',
    request_failed: 'Save Garage didn’t answer. Check that it is still running.'};

  const S = {
    state: null, failures: 0, offline: false, manualView: null, consoles: null, searching: false, mainKey: '',
    slot: null, tab: 'money', detail: {}, stats: {}, drafts: {}, sig: '', deleted: false, reviewOpen: false,
    find: {q: '', varies: true, named: false, limit: 150}, lastJob: '', localError: null};

  // ------------------------------------------------------------ api
  async function api(path, body) {
    const post = body !== undefined;
    const r = await fetch(path, post
      ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal: AbortSignal.timeout(90000)}
      : {cache: 'no-store', signal: AbortSignal.timeout(30000)});
    let data = null;
    try { data = await r.json(); } catch { /* empty body */ }
    if (!r.ok) {
      const e = new Error((data && data.error) || 'request_failed');
      e.code = (data && data.error) || 'request_failed';
      e.detail = data && data.detail;
      throw e;
    }
    return data;
  }

  async function act(path, body, after) {
    S.localError = null;
    try {
      const out = await api(path, body ?? {});
      if (after) after(out);
    } catch (e) {
      S.localError = {code: e.code || 'request_failed', detail: e.detail || ''};
      renderJob();
    }
  }

  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toast.t);
    toast.t = setTimeout(() => toastEl.classList.remove('show'), 4200);
  }

  // ------------------------------------------------------------ state
  const slotsSig = st => (st.slots || []).map(s => s.file + ':' + s.revision).join('|') + '|' + st.entryId;
  const slotOf = file => (S.state?.slots || []).find(s => s.file === file);
  const running = () => S.state?.job?.status === 'running';
  const label = s => s.file === 'sdimg_sce_sdmemory' ? 'Autosave' : 'Manual save';
  const missionName = s => String(s.subtitle || s.file).replace(/^\(Autosave\)\s*/, '');

  function viewFor(st) {
    const job = st.job || {};
    if (job.status === 'running') return {pair: 'pair', download: 'download', patch: 'edit', restore: 'send', upload: 'send'}[job.kind] || 'edit';
    const ok = id => available(id, st);
    if (S.manualView && ok(S.manualView)) return S.manualView;
    if (!st.console) return 'connect';
    if (!st.paired) return 'pair';
    if (!st.hasSession) return 'download';
    if (job.kind === 'upload' && job.stage === 'uploaded') return 'send';
    return 'edit';
  }

  function available(id, st) {
    return {connect: true, pair: !!st.console, download: !!(st.console && st.paired), edit: !!st.hasSession, send: !!st.hasSession}[id];
  }

  function onState(st) {
    const prevJob = S.lastJob;
    const job = st.job || {};
    const jobKey = job.id + ':' + job.status;
    const sig = slotsSig(st);
    if (sig !== S.sig) {                         // new download: forget per-save data
      S.sig = sig; S.detail = {}; S.stats = {}; S.drafts = {};
      const slots = sortedSlots(st);
      S.slot = slots.length ? slots[0].file : null;
    }
    S.state = st;
    if (prevJob && prevJob !== jobKey && job.status === 'done') jobDone(job);
    if (prevJob && prevJob !== jobKey && job.status === 'error') S.localError = null;
    S.lastJob = jobKey;
    for (const s of st.slots || []) seedDraft(s);
    renderStatus();
    renderFoot();
    renderRoute();
    renderMain();
    renderJob();
    renderPending();
  }

  function jobDone(job) {
    const s = slotOf(S.slot);
    const msg = {pair: 'PS5 paired. Next: download your save.', download: 'Save downloaded. Pick what to change.',
                 patch: 'Edits saved' + (s ? ' to ' + missionName(s) : '') + '. Send the save back when you’re done.',
                 restore: 'Originals are back in place. Send them to the PS5 to undo your edits.', upload: 'Save sent to the PS5.'}[job.kind];
    if (job.kind === 'patch') passed('Edits saved', 'Ready to send back to your PS5');
    else if (job.kind === 'upload') passed('Save delivered', 'Load it in GTA VI to check your changes');
    else if (msg) toast(msg);
    if (job.kind === 'pair' || job.kind === 'download') S.manualView = null;
    if (job.kind === 'upload') S.deleted = false;
  }

  async function poll() {
    try {
      const st = await api('/api/state');
      S.failures = 0; S.offline = false;
      onState(st);
    } catch {
      if (++S.failures >= 3) { S.offline = true; renderStatus(); }
    } finally {
      setTimeout(poll, 1000);
    }
  }

  // ------------------------------------------------------------ header and route
  function renderFoot() {
    const st = S.state || {};
    $('#version').textContent = st.version ? 'Version ' + st.version : '';
    $('#quit').hidden = !st.canQuit;
  }

  function passed(big, small) {
    const el = $('#passed');
    el.innerHTML = `<div class="band"><div class="big">${esc(big)}</div><div class="small">${esc(small)}</div></div>`;
    el.hidden = false;
    clearTimeout(passed.t);
    passed.t = setTimeout(() => { el.hidden = true; }, 2600);
  }

  function renderStatus() {
    const st = S.state || {};
    const c = st.console;
    const net = st.network;
    statusEl.innerHTML = [
      S.offline ? '<span class="pill"><span class="dot bad"></span><b>Editor service not answering</b></span>' : '',
      c ? `<span class="pill"><span class="dot ${st.paired ? 'ok' : 'wait'}"></span><b>${esc(c.name)}</b>${st.paired ? 'paired' : 'not paired'}</span>` : '<span class="pill"><span class="dot"></span>No PS5 selected</span>',
      `<span class="pill"><span class="dot ${net ? (net.ok ? 'ok' : 'bad') : 'wait'}"></span>Decryption service ${net ? (net.ok ? 'online' : 'offline') : 'checking'}</span>`
    ].join('');
  }

  function renderRoute() {
    const st = S.state;
    if (!st) return;
    const view = viewFor(st);
    const idx = STEPS.findIndex(x => x[0] === view);
    routeEl.innerHTML = STEPS.map(([id, name], i) => {
      const done = i < idx || (id === 'pair' && st.paired) || (id === 'connect' && st.console) || (id === 'download' && st.hasSession);
      return `<button class="step ${id === view ? 'current' : done ? 'done' : ''}" data-act="go" data-view="${id}" ${available(id, st) && !running() ? '' : 'disabled'} aria-current="${id === view ? 'step' : 'false'}"><span class="n">${i + 1}</span>${name}</button>`;
    }).join('');
  }

  // ------------------------------------------------------------ main views
  function renderMain() {
    const st = S.state;
    const view = viewFor(st);
    const job = st.job || {};
    const s = slotOf(S.slot);
    const key = [view, st.console?.host, st.paired, st.hasSession, S.sig, st.readyToUpload,
      view === 'edit' ? [S.slot, S.tab, S.detail[S.slot] ? 1 : 0, S.stats[S.slot] ? 1 : 0, s?.modified, JSON.stringify(s?.applied || null)].join(',') : '',
      view === 'connect' ? [S.searching, JSON.stringify(S.consoles)].join(',') : '',
      view === 'send' ? [job.kind === 'upload' && job.stage === 'uploaded', (st.slots || []).map(x => x.modified).join('')].join(',') : ''].join('|');
    if (key === S.mainKey) return;
    S.mainKey = key;
    const scroll = window.scrollY;
    main.innerHTML = ({connect: viewConnect, pair: viewPair, download: viewDownload, edit: viewEdit, send: viewSend})[view]();
    if (view === 'edit') { afterEdit(); window.scrollTo(0, scroll); }
  }

  const jobBox = kinds => `<div data-job="${kinds}"></div>`;

  function viewConnect() {
    const list = S.consoles;
    return `
      <section class="title-card"><span class="chip">Step 1</span><h1>Find your PS5</h1>
        <p>Turn the PS5 on and leave it on the home screen. It has to be on the same home network as this computer.</p></section>
      <div class="stack">
        <div class="row">
          <button class="btn primary" data-act="discover" ${S.searching ? 'disabled' : ''}>${S.searching ? 'Searching…' : 'Find my PS5'}</button>
          <form class="row" data-form="ip"><label class="note" for="ip">Or type its IP address</label>
            <input id="ip" class="ip" inputmode="decimal" autocomplete="off" placeholder="192.168.1.50">
            <button class="btn" type="submit">Use this address</button></form>
        </div>
        ${list ? (list.length ? `<div class="fields">${list.map(c => `
          <div class="field"><div class="name">${esc(c.name)}<span class="help">${esc(c.host)}, system software ${esc(fw(c.firmware))}</span></div>
          <div class="inputs"><button class="btn primary small" data-act="pick" data-host="${esc(c.host)}">Use this PS5</button></div></div>`).join('')}</div>`
          : '<div class="empty">No PS5 answered. Check it is on and on the same network, or type its IP address.</div>') : ''}
        ${jobBox('connect')}
      </div>`;
  }

  const fw = f => /^[0-9a-f]{8}$/i.test(f || '') ? `${Number(f.slice(0, 2))}.${f.slice(2, 4)}` : (f || 'unknown');

  function viewPair() {
    return `
      <section class="title-card"><span class="chip">Step 2</span><h1>Pair your PS5</h1>
        <p>You only do this once for each PS5. Pairing waits up to 5 minutes for you.</p></section>
      <div class="stack">
        <ol class="how">
          <li><strong>Click Start pairing below.</strong></li>
          <li><strong>On the PS5, open Data Transfer.</strong><span class="path">${PS5_TRANSFER}.</span></li>
          <li><strong>Pick “Save Garage Pairing” from the list.</strong><span class="path">The PS5 then says it can’t transfer data. That’s expected: the pairing has already happened.</span></li>
        </ol>
        <div class="row"><button class="btn primary" data-act="pair" ${running() ? 'disabled' : ''}>Start pairing</button></div>
        ${jobBox('pair')}
      </div>`;
  }

  function viewDownload() {
    const again = S.state.hasSession;
    return `
      <section class="title-card"><span class="chip">Step 3</span><h1>Download your save</h1>
        <p>The PS5 restarts into transfer mode during the download and restarts again when it’s done.</p></section>
      <div class="stack">
        ${again ? '<div class="callout">You already have a save downloaded. Downloading again replaces it here, and edits you haven’t sent are lost.</div>' : ''}
        <ol class="how">
          <li><strong>In GTA VI, save your game, then go back to the PS5 home screen.</strong></li>
          <li><strong>Click Download save.</strong></li>
          <li><strong>When this page asks, press the PS5 power button once and let go at the beep.</strong></li>
        </ol>
        <div class="row"><button class="btn primary" data-act="download" ${running() ? 'disabled' : ''}>Download save</button></div>
        ${jobBox('download')}
      </div>`;
  }

  function sortedSlots(st) {
    return [...(st.slots || [])].sort((a, b) => (b.file === 'sdimg_sce_sdmemory') - (a.file === 'sdimg_sce_sdmemory') || b.file.localeCompare(a.file));
  }

  function moneySummary(s) {
    const get = k => (s.items || []).filter(x => x.kind === k).reduce((a, x) => a + x.value, 0);
    const parts = [['bank', 'Bank'], ['savings', 'Family Savings'], ['cash', 'Cash']].filter(([k]) => (s.items || []).some(x => x.kind === k))
      .map(([k, n]) => `${n} <span class="cash">$${nf.format(get(k))}</span>`);
    return parts.join(', ');
  }

  function viewEdit() {
    const st = S.state;
    const s = slotOf(S.slot);
    if (!s) return '<div class="empty">No story saves were found in this download.</div>';
    const tabs = [['money', 'Money'], ['ammo', 'Ammo'], ['stats', 'Stats'], ['all', 'All stats'], ['trophies', 'Trophies']];
    return `
      <section class="title-card"><span class="chip">${label(s)}</span><h1>${esc(missionName(s))}</h1>
        <p>${moneySummary(s) || 'No money balances in this save'}.${s.file === 'sdimg_sce_sdmemory' ? ' Continue in the game loads this save.' : ''}${s.modified ? ' This save has edits waiting to be sent.' : ''}</p></section>
      <div class="saves" role="group" aria-label="Choose a save">${sortedSlots(st).map(x => `
        <button class="save" data-act="slot" data-file="${esc(x.file)}" aria-pressed="${x.file === s.file}">
          <span class="k">${label(x)}</span><span class="t">${esc(missionName(x))}</span>${x.modified ? '<span class="m">Edited</span>' : ''}</button>`).join('')}</div>
      <div class="editor">
        <div class="tabs" role="tablist" aria-label="What to edit">${tabs.map(([id, name]) => `
          <button role="tab" aria-selected="${S.tab === id}" data-act="tab" data-tab="${id}">${name}<span class="count" data-count="${id}"></span></button>`).join('')}</div>
        <section role="tabpanel" id="panel">${panel(s)}</section>
      </div>`;
  }

  function panel(s) {
    if (S.tab === 'trophies') return panelTrophies();
    if (S.tab === 'money') return panelMoney(s);
    const d = S.detail[s.file];
    if (!d) return '<div class="empty">Reading this save…</div>';
    if (d.failed) return `<div class="callout danger">${esc(ERR[d.failed] || ERR.internal)} <button class="btn small" data-act="reload">Try again</button></div>`;
    if (S.tab === 'all' && S.stats[s.file]?.failed) return `<div class="callout danger">${esc(ERR[S.stats[s.file].failed] || ERR.internal)} <button class="btn small" data-act="reload">Try again</button></div>`;
    if (S.tab === 'ammo') return panelAmmo(s, d);
    if (S.tab === 'stats') return panelStats(s, d);
    if (S.tab === 'all') return S.stats[s.file] ? panelAll(s) : '<div class="empty">Loading every stat in this save…</div>';
    return '';
  }

  const riskTag = r => ({tested: '<span class="risk tested">Tested on PS5</span>', caution: '<span class="risk caution">Not tested yet</span>',
                         danger: '<span class="risk danger">Can break your save</span>'})[r] || '';

  // ---- drafts: what the user wants each save to look like, always relative to the original save
  function seedDraft(s) {
    if (S.drafts[s.file]) return;
    const d = {money: {}, ammo: {}, stats: {}};
    const a = s.applied || {};
    for (const c of a.money || []) d.money[`${c.inv}:${c.idx}`] = c;
    for (const c of a.ammo || []) d.ammo[`${c.inv}:${c.idx}`] = c;
    for (const c of a.stats || []) d.stats[`${c.group}:${c.row}`] = c;
    S.drafts[s.file] = d;
  }

  const draftOf = file => S.drafts[file] || (S.drafts[file] = {money: {}, ammo: {}, stats: {}});
  const draftList = d => ({money: Object.values(d.money), ammo: Object.values(d.ammo), stats: Object.values(d.stats)});
  const editCount = d => Object.keys(d.money).length + Object.keys(d.ammo).length + Object.keys(d.stats).length;
  const norm = e => JSON.stringify(['money', 'ammo', 'stats'].map(k => (e?.[k] || []).map(c => [c.inv, c.idx, c.group, c.row, c.newValue]).sort()));
  const dirty = s => norm(draftList(draftOf(s.file))) !== norm(s.applied);

  // a numeric input cell. kind: money|ammo|stat; init = value shown in the field
  function cell(o) {
    const {kind, key, label, value, display, unit, type, step, max, attrs = '', wide, narrow, money, extra = ''} = o;
    const wasText = ['money', 'count'].includes(unit) && Number.isInteger(value) ? nf.format(value) : display;
    const dr = draftOf(S.slot)[kind === 'stat' ? 'stats' : kind][key];
    const shown = dr ? toDisplay(dr.newValue, unit) : display;
    const changed = dr && true;
    if (type === 'bool') {
      const on = dr ? !!dr.newValue : !!value;
      return `<div class="cell ${changed ? 'changed' : ''}"><span class="lbl">${esc(label)}</span>
        <label class="toggle"><input type="checkbox" data-edit="${kind}" data-key="${esc(key)}" data-unit="flag" data-type="bool" data-orig="${value ? 1 : 0}" ${attrs} ${on ? 'checked' : ''}> ${on ? 'Yes' : 'No'}</label>
        <span class="was">${changed ? 'was ' + (value ? 'yes' : 'no') : ''}</span></div>`;
    }
    const id = 'f' + Math.random().toString(36).slice(2, 9);
    return `<div class="cell ${wide ? 'wide' : ''} ${narrow ? 'narrow' : ''} ${money ? 'money' : ''} ${changed ? 'changed' : ''}"><label for="${id}">${esc(label)}</label>
      <span class="with-unit"><input id="${id}" type="number" min="${o.min ?? 0}" ${max != null ? `max="${max}"` : ''} step="${step || 1}" value="${esc(shown)}"
        data-edit="${kind}" data-key="${esc(key)}" data-unit="${unit}" data-type="${type}" data-init="${esc(display)}" data-was="${esc(wasText)}" data-orig="${esc(JSON.stringify(value))}" ${attrs}>
        ${extra}</span>
      <span class="was">${changed ? 'was ' + esc(wasText) : ''}</span></div>`;
  }

  function toDisplay(raw, unit) {
    if (unit === 'ms') return (raw / 3600000).toFixed(2);
    if (unit === 'distance') return (raw / 1000).toFixed(3);
    if (unit === 'percent') return Number(raw).toFixed(2);
    if (unit === 'raw-float') return String(Number(raw));
    return String(raw);
  }

  function fromDisplay(str, unit, type) {
    const v = Number(str);
    if (str === '' || !Number.isFinite(v)) return null;
    if (unit === 'ms') return Math.round(v * 3600000);
    if (unit === 'distance') return v * 1000;
    if (type === 'float') return v;
    return Number.isInteger(v) ? v : null;
  }

  // ---- money
  function panelMoney(s) {
    const items = (s.items || []).filter(x => x.kind !== 'other');
    const name = x => ({bank: 'Bank account', savings: 'Family Savings', cash: 'Cash, ' + (x.inv === 0 ? 'Lucia' : 'Jason')})[x.kind];
    const help = x => ({bank: `Up to $${nf.format(x.max)}. Above your current limit the editor adds extra money boxes, the same way the game does for Family Savings goals.`,
                        savings: `Up to $${nf.format(x.max)}.`, cash: `Up to $${nf.format(x.max)}, the size of the wallet.`})[x.kind];
    return `
      <div class="group"><div class="section-head"><h2>Money</h2>${riskTag('tested')}
        <p>Balances of 0 aren’t stored in the save, so they don’t show here. Get a little money in the game, save, and download again to edit them.</p></div>
      ${items.length ? `<div class="fields">${items.map(x => `
        <div class="field"><div class="name">${esc(name(x))}<span class="help">${esc(help(x))}</span></div>
          <div class="inputs">${cell({kind: 'money', key: `${x.inv}:${x.idx}`, label: 'Amount in dollars', value: x.value, display: String(x.value), unit: 'money', type: 'int', max: x.max, wide: true, money: true,
            attrs: `data-inv="${x.inv}" data-idx="${x.idx}" data-label="${esc(name(x))}"`, extra: `<button class="btn small" data-act="fill" data-to="${x.max}">Max</button>`})}</div></div>`).join('')}</div>`
        : '<div class="empty">This save has no money balances to edit.</div>'}</div>`;
  }

  // ---- ammo
  function panelAmmo(s, d) {
    const seen = d.seen?.ammo || {};
    const by = inv => d.ammo.filter(a => a.inv === inv);
    const block = (inv, who) => {
      const rows = by(inv);
      if (!rows.length) return '';
      const guns = (d.weapons || []).filter(w => w.inv === inv).map(w => `<li>${esc(w.label)}</li>`).join('');
      return `<div class="group"><div class="section-head"><h3>${who}</h3><button class="btn small" data-act="fillall" data-scope="ammo-${inv}">Fill all to the highest seen</button></div>
        ${guns ? `<p class="note">Weapons carried</p><ul class="weapons">${guns}</ul>` : ''}
        <div class="fields">${rows.map(a => {
          const top = seen[a.type] || a.value;
          return `<div class="field"><div class="name">${esc(AMMO[a.type] || a.type)}<span class="help">Highest seen in a real save: ${nf.format(top)}.</span></div>
            <div class="inputs" data-scope="ammo-${inv}">${cell({kind: 'ammo', key: `${a.inv}:${a.idx}`, label: 'Rounds', value: a.value, display: String(a.value), unit: 'count', type: 'int', min: 1, max: 9999,
              attrs: `data-inv="${a.inv}" data-idx="${a.idx}" data-label="${esc((AMMO[a.type] || a.type) + ' ammo, ' + who)}" data-top="${top}"`,
              extra: `<button class="btn small" data-act="fill" data-to="${top}">Fill</button>`})}</div></div>`;
        }).join('')}</div></div>`;
    };
    return `<div class="section-head"><h2>Ammo</h2>${riskTag('tested')}
        <p>Only ammo a character is carrying is listed. To add a new type, pick some up in the game first. Edited amounts up to the highest seen are kept by the game.</p></div>
      ${d.ammo.length ? block(0, 'Lucia') + block(1, 'Jason') : '<div class="empty">Neither character is carrying ammo in this save.</div>'}`;
  }

  // ---- featured stats
  function panelStats(s, d) {
    const seen = d.seen?.stats || {};
    const unitOf = f => ({percent: ['percent', 'float', 0.01, '%'], ms: ['ms', null, 0.01, 'hours'], distance: ['distance', 'float', 0.001, 'km'],
                          money: ['count', null, 1, '$'], count: ['count', null, 1, ''], level: ['count', null, 1, ''], flag: ['flag', 'bool', 1, '']})[f.unit] || ['count', null, 1, ''];
    const rows = f => {
      const [unit, forced, step, unitLabel] = unitOf(f);
      const allSame = list => list.every(x => x.risk === f.risk);
      const own = f.risk === 'danger' && f.category !== 'trophies' ? riskTag('danger') : f.risk === 'tested' && !allSame(d.featured.filter(x => x.category === f.category)) ? riskTag('tested') : '';
      return `<div class="field"><div class="name">${esc(f.label)} ${own}<span class="help">${esc(f.help)}</span></div>
        <div class="inputs" data-spec="${esc(f.id)}">${f.entries.filter(e => !(f.autoTotal && e.owner === 0)).map(e => {
          const type = forced || e.type;
          const top = seen[`${f.id}:${e.owner}`];
          return cell({kind: 'stat', key: `${e.group}:${e.row}`, narrow: true, label: OWNER[e.owner] + (unitLabel ? `, ${unitLabel}` : '') + (top != null && f.unit === 'level' ? `, highest seen ${top}` : ''),
            value: e.value, display: type === 'bool' ? '' : toDisplay(e.value, unit), unit, type: type === 'bool' ? 'bool' : (e.type === 'float' ? 'float' : 'int'),
            step: e.type === 'float' || unit === 'ms' ? step : 1, max: TYPE_MAX[e.type],
            attrs: `data-group="${esc(e.group)}" data-row="${e.row}" data-base="${e.base}" data-qual="${e.qual}" data-owner="${e.owner}" data-label="${esc(f.label + ' (' + OWNER[e.owner] + ')')}"`});
        }).join('')}${f.autoTotal ? (() => { const t = f.entries.find(e => e.owner === 0); return `<div class="cell auto narrow"><span class="lbl">Total, updates itself</span>
          <span class="with-unit"><input type="number" disabled value="${esc(toDisplay(t.value, unit))}" data-total="${esc(f.id)}" data-orig="${t.value}"></span><span class="was"></span></div>`; })() : ''}
        </div></div>`;
    };
    const cats = CATS.map(([id, name, help]) => {
      const list = d.featured.filter(f => f.category === id);
      if (!list.length) return '';
      const worst = list.every(f => f.risk === 'danger') ? 'danger' : list.every(f => f.risk === 'tested') ? 'tested' : 'caution';
      return `<div class="group"><div class="section-head"><h2>${name}</h2>${riskTag(worst)}<p>${esc(help)}</p></div><div class="fields">${list.map(rows).join('')}</div></div>`;
    }).join('');
    return `<div class="callout" style="margin-bottom:24px">Fitness levels, money-earned records and the headphones flag have been tested on a PS5 and are kept by the game. The others haven’t been tried yet: change a few, send the save, and check it loads before changing more.</div>${cats}`;
  }

  // ---- all stats browser
  function statIndex(file) {
    const t = S.stats[file];
    if (t.index) return t.index;
    const n = t.names;
    const bn = i => n.base[i] || `#${i}`, qn = i => (i === 0 ? '' : (n.qual[i] || `#${i}`)), on = i => n.owner[i] || `#${i}`;
    const prot = new Set((t.protected[MONEY_GROUP] || []).map(String));
    const rows = [];
    for (const g of t.groups) {
      const vary = new Set(g.varies);
      for (let r = 0; r < g.value.length; r++) {
        const name = bn(g.base[r]) + (qn(g.qual[r]) ? '.' + qn(g.qual[r]) : '');
        rows.push({g: g.key, type: g.type, r, b: g.base[r], q: g.qual[r], o: g.owner[r], v: g.value[r], vary: vary.has(r),
          named: !!(n.base[g.base[r]] || n.qual[g.qual[r]]), name, owner: on(g.owner[r]),
          locked: g.key === MONEY_GROUP && prot.has(String(g.base[r])), text: (name + ' ' + on(g.owner[r]) + ` #${g.base[r]} #${g.qual[r]}`).toLowerCase()});
      }
    }
    rows.sort((a, b) => (b.named - a.named) || (a.named ? a.name.localeCompare(b.name) : a.b - b.b || a.q - b.q) || a.o - b.o);
    return (t.index = rows);
  }

  function filteredStats(file) {
    const f = S.find;
    const words = f.q.toLowerCase().split(/\s+/).filter(Boolean);
    return statIndex(file).filter(x => (!f.varies || x.vary) && (!f.named || x.named) && words.every(w => x.text.includes(w)));
  }

  function panelAll(s) {
    const f = S.find;
    return `<div class="section-head"><h2>All stats</h2>${riskTag('danger')}
        <p>Every stat in this save, ${nf.format(statIndex(s.file).length)} in all. Most names are unknown and shown as numbers. Names in the list were matched by their hash and are very likely right.
        Stats the game uses usually change between your saves, so that filter is on by default. Change one thing at a time.</p></div>
      <div class="finder"><input type="search" placeholder="Search, for example kills, time running, or #103" value="${esc(f.q)}" data-find="q" aria-label="Search stats">
        <label><input type="checkbox" data-find="varies" ${f.varies ? 'checked' : ''}> Only stats that change between my saves</label>
        <label><input type="checkbox" data-find="named" ${f.named ? 'checked' : ''}> Only named stats</label></div>
      <div id="allrows">${allRows(s)}</div>`;
  }

  function allRows(s) {
    const list = filteredStats(s.file);
    const shown = list.slice(0, S.find.limit);
    if (!list.length) return '<div class="empty">No stats match. Clear the search or turn off a filter.</div>';
    return `<table class="raw"><thead><tr><th>Stat</th><th>Whose</th><th>Type</th><th>Value</th></tr></thead><tbody>${shown.map(x => {
      const dr = draftOf(s.file).stats[`${x.g}:${x.r}`];
      const attrs = `data-edit="stat" data-key="${esc(x.g)}:${x.r}" data-group="${esc(x.g)}" data-row="${x.r}" data-base="${x.b}" data-qual="${x.q}" data-owner="${x.o}" data-label="${esc(x.name + ' (' + x.owner + ')')}"`;
      let input;
      if (x.locked) input = `<span class="lock">${esc(fmtRaw(x.v, x.type))}, managed by the Money tab</span>`;
      else if (x.type === 'bool') input = `<label class="toggle"><input type="checkbox" ${attrs} data-type="bool" data-unit="flag" data-orig="${x.v ? 1 : 0}" ${(dr ? dr.newValue : x.v) ? 'checked' : ''}> ${(dr ? dr.newValue : x.v) ? 'true' : 'false'}</label>`;
      else input = `<input type="number" ${attrs} data-type="${x.type === 'float' ? 'float' : 'int'}" data-unit="${x.type === 'float' ? 'raw-float' : 'count'}" min="0" max="${TYPE_MAX[x.type]}" step="${x.type === 'float' ? 'any' : 1}"
        data-init="${esc(String(x.v))}" data-orig="${esc(JSON.stringify(x.v))}" value="${esc(String(dr ? dr.newValue : x.v))}">`;
      return `<tr class="${dr ? 'changed' : ''}"><td class="key">${esc(x.name)}<small>#${x.b}${x.q ? ' / #' + x.q : ''}</small></td><td>${esc(x.owner)}</td><td>${esc(x.type)}</td><td>${input}</td></tr>`;
    }).join('')}</tbody></table>${list.length > shown.length ? `<div class="more"><button class="btn small" data-act="more">Show more (${nf.format(list.length - shown.length)} left)</button></div>` : ''}`;
  }

  const fmtRaw = (v, t) => t === 'float' ? nf2.format(v) : nf.format(v);

  // ---- trophies
  function panelTrophies() {
    return `<div class="section-head"><h2>Trophies</h2><p>What a save edit can and can’t do for trophies on a PS5 without a jailbreak.</p></div>
      <div class="facts">
        <div class="fact no"><span class="mark" aria-hidden="true"></span><div><h3>Trophies can’t be edited directly</h3><p>The PS5 keeps trophies outside the game save and syncs them to PSN. No public tool can write them on system software 14.23, and any “no jailbreak trophy unlocker” is a scam or malware.</p></div></div>
        <div class="fact yes"><span class="mark" aria-hidden="true"></span><div><h3>Money can help with two trophies the normal way</h3><p>Treat Yo Self needs $100,000 spent, and Little Boxes needs all eight garages, about $160,000. Add money in the Money tab, send the save back, then spend it in the game. The game awards these itself.</p></div></div>
        <div class="fact maybe"><span class="mark" aria-hidden="true"></span><div><h3>Counter trophies might pop after an edit</h3><p>About 16 trophies count things like collectibles, stunts, challenges and vehicles. If GTA VI re-checks its counters, one pushed past its target could unlock the next time it goes up. Nobody has tested this on GTA VI, and the counters behind most of these trophies haven’t been identified yet.</p></div></div>
        <div class="fact maybe"><span class="mark" aria-hidden="true"></span><div><h3>Story trophies need missions, and the Platinum needs play</h3><p>Mission progress is spread across many unnamed values, and getting them wrong can lock a mission later. About 18 trophies are one-off moments you have to play, so editing can’t finish the Platinum.</p></div></div>
        <div class="fact no"><span class="mark" aria-hidden="true"></span><div><h3>Trophy sites can flag save edits</h3><p>PSNProfiles’ rules list save editors as a reason to flag a trophy list, even when the game itself awarded the trophy. Sony’s terms forbid modifying game data, though no ban for single-player save edits has been reported. Never give your PSN login to a trophy service.</p></div></div>
      </div>`;
  }

  // ---- after the edit view renders: load what it needs
  async function afterEdit() {
    const s = slotOf(S.slot);
    if (!s) return;
    const file = s.file;
    if (S.tab !== 'money' && S.tab !== 'trophies' && !S.detail[file]) {
      try { S.detail[file] = await api('/api/slot?file=' + encodeURIComponent(file)); } catch (e) { S.detail[file] = {failed: e.code || 'request_failed', featured: [], ammo: [], seen: {}}; }
      S.mainKey = ''; renderMain(); return;
    }
    if (S.tab === 'all' && !S.stats[file]) {
      try { S.stats[file] = await api('/api/stats?file=' + encodeURIComponent(file)); } catch (e) { S.stats[file] = {failed: e.code || 'request_failed'}; }
      S.mainKey = ''; renderMain(); return;
    }
    renderCounts();
  }

  function renderCounts() {
    const d = draftOf(S.slot);
    const n = {money: Object.keys(d.money).length, ammo: Object.keys(d.ammo).length, stats: 0, all: 0};
    const feat = new Set((S.detail[S.slot]?.featured || []).flatMap(f => f.entries.map(e => `${e.group}:${e.row}`)));
    for (const k of Object.keys(d.stats)) n[feat.has(k) ? 'stats' : 'all']++;
    for (const el of $$('[data-count]')) el.textContent = n[el.dataset.count] || '';
  }

  // ------------------------------------------------------------ send back
  function viewSend() {
    const st = S.state;
    const job = st.job || {};
    const done = job.kind === 'upload' && job.stage === 'uploaded';
    const edited = (st.slots || []).filter(x => x.modified);
    const summary = edited.length ? `<div class="panel"><h3>What’s being sent</h3><ul class="review" style="max-height:none;margin-top:8px">${edited.map(x =>
      (x.changes || []).map(c => `<li><span>${esc(missionName(x))}: ${esc(changeLabel(c))}</span><span>${esc(fmtChange(c.from))} to ${esc(fmtChange(c.to))}</span></li>`).join('') ||
      `<li><span>${esc(missionName(x))}</span><span>edited</span></li>`).join('')}</ul></div>` : '';
    if (done) {
      return `<section class="title-card"><span class="chip">Done</span><h1>Your save is back on the PS5</h1>
          <p>Start GTA VI and load the save you edited. Check the values in the game before you play on.</p></section>
        <div class="stack">
          <div class="panel stack"><h3>If the save won’t load</h3>
            <ol class="how"><li><strong>Delete the GTA VI save on the PS5 again.</strong><span class="path">${PS5_DELETE}.</span></li>
              <li><strong>Click Put the originals back.</strong><span class="path">This swaps your untouched saves back in.</span></li>
              <li><strong>Send the save to the PS5 again from this page.</strong></li></ol>
            <div class="row"><button class="btn danger" data-act="restore" ${running() ? 'disabled' : ''}>Put the originals back</button>
              <button class="btn" data-act="go" data-view="edit">Edit more</button></div></div>
          ${jobBox('restore')}
        </div>`;
    }
    if (!st.readyToUpload) {
      return `<section class="title-card"><span class="chip">Step 5</span><h1>Nothing to send yet</h1><p>Save some edits first. They’ll wait here until you send them.</p></section>
        <div class="row"><button class="btn primary" data-act="go" data-view="edit">Edit a save</button></div>${jobBox('restore')}`;
    }
    return `
      <section class="title-card"><span class="chip">Step 5</span><h1>Send your save back</h1>
        <p>Your edits are encrypted and waiting. The PS5 won’t overwrite a save, so the old one has to be deleted first. The originals stay backed up on this computer.</p></section>
      <div class="stack">
        ${summary}
        <ol class="how">
          <li><strong>Optional: upload your GTA VI save to PS Plus cloud storage.</strong><span class="path">That gives you a second backup. Turn off auto-sync for GTA VI until you know the edited save works.</span></li>
          <li><strong>Delete the GTA VI save on the PS5.</strong><span class="path">${PS5_DELETE}, then pick Grand Theft Auto VI.</span>
            <label class="check" style="margin-top:10px"><input type="checkbox" data-act="deleted" ${S.deleted ? 'checked' : ''}><span>I deleted the GTA VI save on my PS5</span></label></li>
          <li><strong>Click Send save to PS5, then start the transfer on the PS5.</strong><span class="path">${PS5_TRANSFER}, then pick “Save Garage” and choose Start Transfer.</span></li>
        </ol>
        <div class="row"><button class="btn primary" data-act="upload" ${S.deleted && !running() ? '' : 'disabled'}>Send save to PS5</button>
          <button class="btn danger" data-act="restore" ${running() ? 'disabled' : ''}>Undo all edits</button></div>
        ${jobBox('upload restore')}
      </div>`;
  }

  const changeLabel = c => c.label || ({bank: 'Bank account', savings: 'Family Savings', cash: 'Cash'})[c.kind] || c.kind;
  const fmtChange = v => typeof v === 'boolean' ? (v ? 'yes' : 'no') : typeof v === 'number' ? (Number.isInteger(v) ? nf.format(v) : nf2.format(v)) : String(v);

  // ------------------------------------------------------------ job box
  function renderJob() {
    const st = S.state;
    if (!st) return;
    const job = st.job || {};
    for (const box of $$('[data-job]')) {
      const kinds = box.dataset.job.split(' ');
      const err = S.localError;
      let html = '';
      if (err) {
        html = `<div class="job err"><div class="stage">${esc(ERR[err.code] || ERR.internal)}</div>${err.detail ? `<div class="detail">${esc(err.detail)}</div>` : ''}</div>`;
      } else if (kinds.includes(job.kind) && job.status !== 'idle') {
        const stage = STAGE[job.stage] || job.stage || '';
        if (job.status === 'running') {
          const p = job.progress;
          const pct = p && p.total ? Math.round(100 * p.files / p.total) : null;
          html = `<div class="job"><div class="stage">${esc(stage)}</div>
            ${p ? `<div class="detail">${p.total ? `File ${p.files} of ${p.total}` : `${p.files} files so far`}</div>` : ''}
            <div class="bar ${pct != null ? 'fixed' : ''}"><span ${pct != null ? `style="width:${pct}%"` : ''}></span></div>
            ${job.needPower ? `<div class="power"><svg viewBox="0 0 48 48" aria-hidden="true"><path d="M15 12a16 16 0 1 0 18 0"/><line x1="24" y1="5" x2="24" y2="22"/></svg>
              <div><strong>Press the PS5 power button once</strong>Let go when it beeps. The PS5 restarts into transfer mode. You have about 5 minutes.</div></div>` : ''}
            ${job.hint === 'console_has_save' ? '<div class="callout" style="margin-top:12px">The PS5 still has a GTA VI save, so it has nothing to receive. Delete the save on the PS5, then open Data Transfer again.</div>' : ''}
            ${['waiting_console', 'pair_waiting_console', 'connecting', 'need_power'].includes(job.stage) ? '<div class="row" style="margin-top:10px"><button class="link" data-act="cancel">Cancel</button></div>' : ''}
            ${logBlock(job)}</div>`;
        } else if (job.status === 'error') {
          const code = job.error?.code || 'internal';
          const detail = job.error?.detail || '';
          const perm = /PermissionError/.test(detail);
          html = `<div class="job err"><div class="stage">${esc(ERR[code] || ERR.internal)}</div>
            ${perm ? '<div class="detail">This computer isn’t allowed to use ports 1004 to 1006. On Linux, run sudo sysctl -w net.ipv4.ip_unprivileged_port_start=1004 in a terminal, then try again.</div>' : ''}
            ${detail && !perm ? `<div class="detail">${esc(detail)}</div>` : ''}${logBlock(job)}</div>`;
        } else if (job.status === 'done') {
          html = `<div class="job ok"><div class="stage">${esc(stage)}</div></div>`;
        }
      }
      if (box.innerHTML !== html) {
        const open = box.querySelector('details')?.open;
        box.innerHTML = html;
        if (open && box.querySelector('details')) box.querySelector('details').open = true;
      }
    }
  }

  const logBlock = job => (job.log || []).length ? `<details class="log"><summary>Show details</summary><pre>${esc(job.log.map(l => l.m).join('\n'))}</pre></details>` : '';

  // ------------------------------------------------------------ pending bar
  function renderPending() {
    const st = S.state;
    const s = slotOf(S.slot);
    if (!st || viewFor(st) !== 'edit' || !s) { pendingEl.hidden = true; return; }
    const d = draftOf(s.file);
    const n = editCount(d);
    const isDirty = dirty(s);
    const busy = running();
    if (!n && !s.modified) { pendingEl.hidden = true; return; }
    const list = [...Object.values(d.money), ...Object.values(d.ammo), ...Object.values(d.stats)];
    const html = !n && s.modified && !isDirty
      ? `<div class="sum">${esc(missionName(s))} already has edits waiting<small>They were saved earlier. Send them to the PS5, or undo them on the Send back step.</small></div>
         <div class="row"><button class="btn primary" data-act="go" data-view="send">Go to send back</button></div>`
      : isDirty
      ? `<div class="sum">${n} change${n === 1 ? '' : 's'} to ${esc(missionName(s))}<small>Not saved yet. Saving encrypts the save through GarlicSaves and gets it ready to send.</small></div>
         <div class="row"><button class="btn small" data-act="review">${S.reviewOpen ? 'Hide list' : 'Review'}</button>
           <button class="btn small" data-act="discard">Discard</button>
           <button class="btn primary" data-act="save" ${busy ? 'disabled' : ''}>${busy && st.job.kind === 'patch' ? 'Saving…' : 'Save edits to this save'}</button></div>`
      : `<div class="sum">Edits saved to ${esc(missionName(s))}<small>${n} change${n === 1 ? '' : 's'}. Edit another save, or send them back to the PS5.</small></div>
         <div class="row"><button class="btn small" data-act="review">${S.reviewOpen ? 'Hide list' : 'Review'}</button>
           <button class="btn primary" data-act="go" data-view="send">Go to send back</button></div>`;
    const review = S.reviewOpen ? `<ul class="review">${list.map(c => `<li><span>${esc(c.label || 'Change')}</span><span>${esc(fmtChange(c.value))} to ${esc(fmtChange(c.newValue))}</span></li>`).join('')}</ul>` : '';
    const job = st.job || {};
    const jobLine = job.kind === 'patch' && job.status !== 'idle' && !(job.status === 'done' && !isDirty)
      ? `<div style="flex-basis:100%">${job.status === 'error' ? `<span class="risk danger">${esc(ERR[job.error?.code] || ERR.internal)}</span>` : `<span class="risk caution">${esc(STAGE[job.stage] || job.stage)}</span>`}</div>` : '';
    const full = html + jobLine + review;
    if (pendingEl.dataset.html !== full) { pendingEl.innerHTML = full; pendingEl.dataset.html = full; }
    pendingEl.hidden = false;
  }

  // ------------------------------------------------------------ input handling
  function onEdit(el) {
    const s = slotOf(S.slot);
    if (!s) return;
    const kind = el.dataset.edit;
    const bucket = kind === 'stat' ? 'stats' : kind;
    const key = el.dataset.key;
    const d = draftOf(s.file);
    const cellEl = el.closest('.cell') || el.closest('tr');
    let newValue, orig = JSON.parse(el.dataset.orig ?? 'null'), same;
    if (el.type === 'checkbox') {
      newValue = el.checked;
      orig = el.dataset.orig === '1';
      same = newValue === orig;
      const lab = el.closest('label');
      if (lab && lab.lastChild && lab.lastChild.nodeType === 3) lab.lastChild.textContent = ' ' + (el.closest('table') ? String(newValue) : (newValue ? 'Yes' : 'No'));
    } else {
      newValue = fromDisplay(el.value, el.dataset.unit, el.dataset.type);
      same = el.value.trim() === el.dataset.init;
      const max = Number(el.max), min = Number(el.min);
      const bad = !same && (newValue === null || (el.max !== '' && newValue > max * (el.dataset.unit === 'ms' ? 3600000 : el.dataset.unit === 'distance' ? 1000 : 1)) || newValue < (Number.isFinite(min) ? min : 0));
      el.setAttribute('aria-invalid', bad ? 'true' : 'false');
      if (bad) { delete d[bucket][key]; mark(cellEl, false, el); renderPending(); renderCounts(); return; }
    }
    if (same) delete d[bucket][key];
    else {
      const base = {value: orig, newValue, label: el.dataset.label || ''};
      d[bucket][key] = kind === 'stat'
        ? {group: el.dataset.group, row: +el.dataset.row, base: +el.dataset.base, qual: +el.dataset.qual, owner: +el.dataset.owner, ...base}
        : {inv: +el.dataset.inv, idx: +el.dataset.idx, ...base};
    }
    mark(cellEl, !same, el);
    if (kind === 'stat') updateTotal(el);
    renderPending();
    renderCounts();
  }

  function mark(cellEl, changed, el) {
    if (!cellEl) return;
    cellEl.classList.toggle('changed', changed);
    const was = cellEl.querySelector('.was');
    if (was) was.textContent = changed ? (el.type === 'checkbox' ? 'was ' + (el.dataset.orig === '1' ? 'yes' : 'no') : 'was ' + (el.dataset.was || el.dataset.init)) : '';
  }

  function updateTotal(el) {
    const wrap = el.closest('[data-spec]');
    const total = wrap && wrap.querySelector('[data-total]');
    if (!total) return;
    const ins = $$('input[data-edit]', wrap);
    const unit = ins[0]?.dataset.unit;
    const sum = ins.reduce((a, x) => a + (fromDisplay(x.value, x.dataset.unit, x.dataset.type) ?? JSON.parse(x.dataset.orig)), 0);
    total.value = toDisplay(sum, unit);
  }

  // ------------------------------------------------------------ events
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-act]');
    if (!b || b.disabled) return;
    const a = b.dataset.act;
    if (a === 'deleted') { S.deleted = b.checked; const up = $('[data-act="upload"]'); if (up) up.disabled = !(S.deleted && !running()); return; }
    if (b.tagName === 'A') return;
    e.preventDefault();
    if (a === 'go') { S.localError = null; S.manualView = b.dataset.view; S.mainKey = ''; renderRoute(); renderMain(); renderJob(); renderPending(); main.focus(); return; }
    if (a === 'discover') {
      S.searching = true; S.consoles = null; renderMain();
      act('/api/discover', {}, out => { S.consoles = out.consoles || []; }).finally(() => { S.searching = false; S.mainKey = ''; renderMain(); renderJob(); });
      return;
    }
    if (a === 'pick') { act('/api/console', {host: b.dataset.host}, st => { S.manualView = null; onState(st); }); return; }
    if (a === 'pair') { act('/api/pair'); return; }
    if (a === 'download') { act('/api/download'); return; }
    if (a === 'cancel') { act('/api/cancel'); return; }
    if (a === 'upload') { act('/api/upload'); return; }
    if (a === 'restore') {
      if (confirm('Put the original saves back? Every edit you saved here is undone. You still need to send the save to the PS5 afterwards.')) act('/api/restore', {}, () => { S.drafts = {}; });
      return;
    }
    if (a === 'slot') { S.slot = b.dataset.file; S.reviewOpen = false; S.mainKey = ''; renderMain(); renderPending(); return; }
    if (a === 'tab') { S.tab = b.dataset.tab; S.mainKey = ''; renderMain(); return; }
    if (a === 'fill') {
      const input = b.parentElement.querySelector('input[type="number"]');
      if (input) { input.value = b.dataset.to; onEdit(input); }
      return;
    }
    if (a === 'fillall') {
      for (const w of $$(`[data-scope="${b.dataset.scope}"]`)) {
        const input = w.querySelector('input[type="number"]');
        if (input && input.dataset.top) { input.value = input.dataset.top; onEdit(input); }
      }
      return;
    }
    if (a === 'reload') { const f = S.slot; delete S.detail[f]; delete S.stats[f]; S.mainKey = ''; renderMain(); return; }
    if (a === 'more') { S.find.limit += 300; $('#allrows').innerHTML = allRows(slotOf(S.slot)); return; }
    if (a === 'review') { S.reviewOpen = !S.reviewOpen; renderPending(); return; }
    if (a === 'discard') {
      const s = slotOf(S.slot);
      delete S.drafts[s.file]; seedDraft(s); S.mainKey = ''; renderMain(); renderPending(); return;
    }
    if (a === 'save') {
      const s = slotOf(S.slot);
      const d = draftList(draftOf(s.file));
      if (!d.money.length && !d.ammo.length && !d.stats.length && !s.modified) return;
      if (!d.money.length && !d.ammo.length && !d.stats.length) {
        if (confirm('You removed every edit for this save. Put its original back instead?')) act('/api/restore', {}, () => { S.drafts = {}; });
        return;
      }
      const risky = d.stats.some(c => !(S.detail[s.file]?.featured || []).some(f => f.entries.some(e => e.group === c.group && e.row === c.row)));
      if (risky && !confirm('Some of these edits come from All stats, where most values have unknown meanings and can break the save. Keep the originals backed up and check the save loads. Continue?')) return;
      act('/api/patch', {slot: s.file, ...d});
    }
  });

  $('#passed').addEventListener('click', () => { $('#passed').hidden = true; });
  $('#quit').addEventListener('click', () => {
    if (!confirm('Quit Save Garage? Edits you haven\u2019t saved here are lost.')) return;
    api('/api/quit', {}).then(() => { document.body.innerHTML = '<main id="main"><section class="title-card"><h1>Save Garage has closed</h1><p>You can close this tab.</p></section></main>'; })
      .catch(e => toast(ERR[e.code] || ERR.internal));
  });

  document.addEventListener('input', e => {
    const el = e.target;
    if (el.dataset.edit && el.type !== 'checkbox') onEdit(el);
    if (el.dataset.find === 'q') {
      S.find.q = el.value; S.find.limit = 150;
      clearTimeout(S.findT);
      S.findT = setTimeout(() => { const box = $('#allrows'); if (box) box.innerHTML = allRows(slotOf(S.slot)); }, 160);
    }
  });

  document.addEventListener('change', e => {
    const el = e.target;
    if (el.dataset.edit && el.type === 'checkbox') onEdit(el);
    if (el.dataset.find === 'varies' || el.dataset.find === 'named') {
      S.find[el.dataset.find] = el.checked; S.find.limit = 150;
      const box = $('#allrows'); if (box) box.innerHTML = allRows(slotOf(S.slot));
    }
  });

  document.addEventListener('submit', e => {
    const f = e.target;
    if (f.dataset.form !== 'ip') return;
    e.preventDefault();
    const host = $('#ip').value.trim();
    if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) { S.localError = {code: 'console_not_found', detail: ''}; renderJob(); return; }
    act('/api/console', {host}, st => { S.manualView = null; onState(st); });
  });

  window.addEventListener('beforeunload', e => {
    const s = S.state?.slots?.find(x => editCount(draftOf(x.file)) && dirty(x));
    if (s) { e.preventDefault(); e.returnValue = ''; }
  });

  // ------------------------------------------------------------ start
  api('/api/network', {}).catch(() => {});
  poll();
})();
