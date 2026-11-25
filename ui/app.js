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
  const CATS = [
    ['progress', 'Progress', 'Percentages and counters from the stats screen.'],
    ['skills', 'Skills', 'Overpowers and buffs for health, stamina and focus, plus workouts and meditations. The total updates itself to Lucia plus Jason.'],
    ['time', 'Time and distance', 'Time played and how you got around. Times are in hours.'],
    ['earnings', 'Money earned', 'Records of money you earned. Changing these does not add money. Use the Money tab for that.'],
    ['wanted', 'Wanted levels', 'How often and how long the police were after you. Times are in hours.'],
    ['records', 'Records', 'Combat, vehicle and other counters.'],
    ['trophies', 'Trophy counters', 'Counters behind some of the trophies. A PS5 keeps edited values, even above the game\u2019s own totals. Raising one may make the game award the trophy the next time the counter goes up, and trophy sites such as PSNProfiles may flag that. The things a counter counts are not changed, so the numbers can stop matching.'],
    ['gadgets', 'Gadgets', 'Flags for gadgets you picked up.']];
  const TYPE_MAX = {int32: 2147483647, u32: 4294967295, int64: 9007199254740991, int16: 32767, u8: 127, float: 1e12};
  const STAGE = {
    pair_waiting_console: 'Waiting for the PS5', pair_reading: 'Reading the pairing request', paired: 'Paired',
    connecting: 'Connecting to your PS5', need_power: 'Press the PS5 power button', reading_list: 'Reading the save list',
    choose_account: 'Choose the PS5 account', downloading: 'Downloading your save', decrypting: 'Decrypting your save', ready: 'Your save is ready to edit',
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
    save_bad_time: 'The time of day needs an hour from 0 to 23 and a minute from 0 to 59.',
    save_read_only: 'That part of the save is read-only.',
    save_not_editable: 'Only numbers and true/false values can be changed.',
    save_bad_request: 'The edit didn’t match this save. Reload the page and try again.',
    no_change: 'Nothing changed. Edit a value first.',
    port_in_use: 'Ports 1004 to 1006 are already in use. Close any other save-transfer tool or another copy of Save Garage.',
    upload_failed: 'Sending failed. Check the PS5 and the network, then try again.',
    download_failed: 'The download failed. Go back to the PS5 home screen and try again.',
    tool_failed: 'Save processing failed. Open the details below.',
    internal: 'Something went wrong. Open the details below.',
    busy: 'Another task is running. Wait for it to finish.',
    bad_request: 'That choice is no longer available. Start the download again.',
    no_console: 'No PS5 selected. Connect first.',
    no_session: 'No save downloaded yet.',
    nothing_to_upload: 'There are no saved edits to send.',
    console_not_found: 'No PS5 answered at that address. Check the IP address and that the PS5 is on.',
    request_failed: 'Save Garage didn’t answer. Check that it is still running.'};

  const S = {
    state: null, failures: 0, offline: false, manualView: null, consoles: null, searching: false, mainKey: '',
    slot: null, tab: 'money', detail: {}, stats: {}, comp: {}, world: {}, sd: {}, stuntSel: {}, stuntKeys: {}, drafts: {}, sig: '', deleted: false, reviewOpen: false,
    find: {q: '', varies: true, named: false, game: false, limit: 150}, lastJob: '', localError: null};

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
      S.sig = sig; S.detail = {}; S.stats = {}; S.comp = {}; S.world = {}; S.sd = {}; S.stuntSel = {}; S.stuntKeys = {}; S.drafts = {};
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
    const tabs = [['money', 'Money'], ['ammo', 'Ammo'], ['stats', 'Stats'], ['completion', 'Completion'], ['world', 'World'], ['all', 'All stats'], ['data', 'Save data'], ['trophies', 'Trophies']];
    return `
      <section class="title-card"><span class="chip">${label(s)}</span><h1>${esc(missionName(s))}</h1>
        ${st.user?.name ? `<p>PS5 account: <strong>${esc(st.user.name)}</strong></p>` : ''}
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
    if (S.tab === 'data') return S.sd[s.file]?.failed ? `<div class="callout danger">${esc(ERR[S.sd[s.file].failed] || ERR.internal)} <button class="btn small" data-act="reload">Try again</button></div>`
      : S.sd[s.file] ? panelData(s) : '<div class="empty">Reading this save…</div>';
    if (S.tab === 'world') return S.world[s.file]?.failed ? `<div class="callout danger">${esc(ERR[S.world[s.file].failed] || ERR.internal)} <button class="btn small" data-act="reload">Try again</button></div>`
      : S.world[s.file] ? panelWorld(s) : '<div class="empty">Reading this save…</div>';
    if (S.tab === 'completion') return S.comp[s.file]?.failed ? `<div class="callout danger">${esc(ERR[S.comp[s.file].failed] || ERR.internal)} <button class="btn small" data-act="reload">Try again</button></div>`
      : S.comp[s.file] ? panelCompletion(s) : '<div class="empty">Reading this save…</div>';
    if (S.tab === 'all') return S.stats[s.file] ? panelAll(s) : '<div class="empty">Loading every stat in this save…</div>';
    return '';
  }

  const riskTag = r => ({tested: '<span class="risk tested">Tested on PS5</span>', caution: '<span class="risk caution">Not tested yet</span>',
                         danger: '<span class="risk danger">Can break your save</span>'})[r] || '';

  // ---- drafts: what the user wants each save to look like, always relative to the original save
  function seedDraft(s) {
    if (S.drafts[s.file]) return;
    const d = {money: {}, ammo: {}, stats: {}, world: {}, raw: {}, completion: {}};
    const a = s.applied || {};
    if (a.world) d.world = {...a.world};
    if (a.completion) d.completion = JSON.parse(JSON.stringify(a.completion));
    for (const c of a.raw || []) d.raw[rawKey(c.section, c.path)] = c;
    for (const c of a.money || []) d.money[`${c.inv}:${c.idx}`] = c;
    for (const c of a.ammo || []) d.ammo[`${c.inv}:${c.idx}`] = c;
    for (const c of a.stats || []) d.stats[`${c.group}:${c.row}`] = c;
    S.drafts[s.file] = d;
  }

  const rawKey = (sec, path) => sec + ':' + JSON.stringify(path);
  const draftOf = file => S.drafts[file] || (S.drafts[file] = {money: {}, ammo: {}, stats: {}, world: {}, raw: {}, completion: {}});
  const draftList = d => ({money: Object.values(d.money), ammo: Object.values(d.ammo), stats: Object.values(d.stats), world: {...(d.world || {})},
                           raw: Object.values(d.raw || {}), completion: JSON.parse(JSON.stringify(d.completion || {}))});
  const compCount = c => ['compendium', 'discovery', 'challenges', 'gyms', 'activities', 'robberies', 'fencing', 'activities2', 'hoops', 'vehicles', 'collectibles'].filter(k => c && c[k]).length;
  const editCount = d => Object.keys(d.money).length + Object.keys(d.ammo).length + Object.keys(d.stats).length + Object.keys(d.world || {}).length
                         + Object.keys(d.raw || {}).length + compCount(d.completion);
  const worldKey = w => JSON.stringify(Object.keys(w || {}).sort().map(k => [k, w[k]]));
  const norm = e => JSON.stringify(['money', 'ammo', 'stats'].map(k => (e?.[k] || []).map(c => [c.inv, c.idx, c.group, c.row, c.newValue]).sort())) + worldKey(e?.world)
    + JSON.stringify((e?.raw || []).map(c => [rawKey(c.section, c.path), c.newValue]).sort()) + worldKey(e?.completion);
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
    if (unit === 'distance') return (raw / 1000).toFixed(2);
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
    const by = inv => d.ammo.filter(a => a.inv === inv);
    const block = (inv, who) => {
      const rows = by(inv);
      if (!rows.length) return '';
      const carried = (d.weapons || []).filter(w => w.inv === inv), unnamed = carried.filter(w => !w.label).length;
      const guns = carried.filter(w => w.label).map(w => `<li>${esc(w.label)}${w.kind ? ` <span class="kind">${esc(w.kind)}</span>` : ''}</li>`).join('')
        + (unnamed ? `<li class="kind">${unnamed} more not identified yet</li>` : '');
      return `<div class="group"><div class="section-head"><h3>${who}</h3><div class="head-actions"><button class="btn small" data-act="fillall" data-scope="ammo-${inv}">Refill all</button><button class="btn small" data-act="maxall" data-scope="ammo-${inv}">Max all</button></div></div>
        ${guns ? `<p class="note">Weapons carried</p><ul class="weapons">${guns}</ul>` : ''}
        <div class="fields">${rows.map(a => {
          const help = a.full ? `A full load is ${nf.format(a.full)}. Can go up to ${nf.format(a.max)}.` : `Can go up to ${nf.format(a.max)}. The game’s full load for this isn’t known yet.`;
          return `<div class="field"><div class="name">${esc(a.label)}<span class="help">${help}</span></div>
            <div class="inputs" data-scope="ammo-${inv}">${cell({kind: 'ammo', key: `${a.inv}:${a.idx}`, label: a.type.startsWith('thrown') ? 'How many' : 'Rounds', value: a.value, display: String(a.value), unit: 'count', type: 'int', min: 1, max: a.max,
              attrs: `data-inv="${a.inv}" data-idx="${a.idx}" data-label="${esc(a.label + ', ' + who)}" data-full="${a.full || ''}" data-max="${a.max}"`,
              extra: (a.full ? `<button class="btn small" data-act="fill" data-to="${a.full}">Full</button>` : '') + `<button class="btn small" data-act="fill" data-to="${a.max}">Max</button>`})}</div></div>`;
        }).join('')}</div></div>`;
    };
    return `<div class="section-head"><h2>Ammo</h2>${riskTag('tested')}
        <p>Only ammo a character is carrying is listed. To add a new type, pick some up in the game first. Amounts up to a full load have been tested on a PS5 and the game keeps them. Larger amounts haven’t been tried yet: the game may cut them back to a full load when it loads the save.</p></div>
      ${d.ammo.length ? block(0, 'Lucia') + block(1, 'Jason') : '<div class="empty">Neither character is carrying ammo in this save.</div>'}`;
  }

  // ---- featured stats
  function panelStats(s, d) {
    const unitOf = f => ({percent: ['percent', 'float', 0.01, '%'], ms: ['ms', null, 0.01, 'hours'], distance: ['distance', 'float', 0.01, 'km'],
                          money: ['count', null, 1, '$'], count: ['count', null, 1, ''], level: ['count', null, 1, ''], flag: ['flag', 'bool', 1, '']})[f.unit] || ['count', null, 1, ''];
    const rows = f => {
      const [unit, forced, step, unitLabel] = unitOf(f);
      const allSame = list => list.every(x => x.risk === f.risk);
      const own = f.risk === 'danger' && f.category !== 'trophies' ? riskTag('danger') : f.risk === 'tested' && !allSame(d.featured.filter(x => x.category === f.category)) ? riskTag('tested') : '';
      const limit = maxText(f);
      return `<div class="field"><div class="name">${esc(f.label)} ${own}<span class="help">${esc(f.help)}${limit ? ' ' + esc(limit) : ''}</span></div>
        <div class="inputs" data-spec="${esc(f.id)}">${f.entries.filter(e => !(f.autoTotal && e.owner === 0)).map(e => {
          const type = forced || e.type;
          return cell({kind: 'stat', key: `${e.group}:${e.row}`, narrow: true, label: OWNER[e.owner] + (unitLabel ? `, ${unitLabel}` : ''),
            value: e.value, display: type === 'bool' ? '' : toDisplay(e.value, unit), unit, type: type === 'bool' ? 'bool' : (e.type === 'float' ? 'float' : 'int'),
            step: e.type === 'float' || unit === 'ms' ? step : 1, max: e.type === 'bool' || f.max == null ? null : maxShown(f),
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
    return `<div class="callout" style="margin-bottom:24px">Almost every stat here has been tested on a PS5: the game showed the edited values on its stats screens, kept them when it saved, and went on counting from them. Labels follow the game’s own stats screens. The times, distances, story and styles percentages and two gadget flags haven’t been tried yet: change a few, send the save, and check it loads before changing more.</div>${cats}`;
  }

  // ---- all stats browser
  function statIndex(file) {
    const t = S.stats[file];
    if (t.index) return t.index;
    const n = t.names;
    const ql = n.qual_labels || {}, ol = n.owner_labels || {};
    const bn = i => n.base[i] || `#${i}`, qn = i => (i === 0 ? '' : (n.qual[i] || (ql[i] ? (ql[i] === ql[i].toUpperCase() ? ql[i].toLowerCase() : ql[i]) : `#${i}`))), on = i => ol[i] || n.owner[i] || `#${i}`;
    // keys whose real name is unknown but whose meaning was worked out from the saves: shown as a description, marked
    const bm = n.base_meanings || {}, mq = new Set((n.meaning || {}).qual || []), mo = new Set((n.meaning || {}).owner || []);
    const labels = t.labels || {};
    const pretty = l => l ? (l.charAt(0) + l.slice(1).toLowerCase()).replace(/\b(lucia|jason)\b/g, w => w[0].toUpperCase() + w.slice(1)) : '';
    const prot = new Set((t.protected[MONEY_GROUP] || []).map(String));
    const rows = [];
    for (const g of t.groups) {
      const vary = new Set(g.varies);
      for (let r = 0; r < g.value.length; r++) {
        const b = g.base[r], q = g.qual[r], desc = !n.base[b] && bm[b];
        const name = desc ? bm[b] + (qn(q) ? ` (${qn(q)})` : '') : bn(b) + (qn(q) ? '.' + qn(q) : '');
        const meaning = !!desc || (!n.qual[q] && mq.has(q)) || mo.has(g.owner[r]);
        const game = pretty(labels[`${g.key}:${r}`]);
        rows.push({g: g.key, type: g.type, r, b: g.base[r], q: g.qual[r], o: g.owner[r], v: g.value[r], vary: vary.has(r),
          named: !!(n.base[b] || n.qual[q] || game || desc), meaning, game, name, owner: on(g.owner[r]), qlab: n.qual[g.qual[r]] ? ql[g.qual[r]] || '' : '',
          locked: g.key === MONEY_GROUP && prot.has(String(g.base[r])), text: (game + ' ' + name + ' ' + (ql[g.qual[r]] || '') + ' ' + on(g.owner[r]) + ' ' + (n.owner[g.owner[r]] || '') + ` #${g.base[r]} #${g.qual[r]}`).toLowerCase()});
      }
    }
    rows.sort((a, b) => (!!b.game - !!a.game) || (b.named - a.named) || (a.game || a.name).localeCompare(b.game || b.name) || a.b - b.b || a.q - b.q || a.o - b.o);
    return (t.index = rows);
  }

  function filteredStats(file) {
    const f = S.find;
    const words = f.q.toLowerCase().split(/\s+/).filter(Boolean);
    return statIndex(file).filter(x => (!f.varies || x.vary) && (!f.named || x.named) && (!f.game || x.game) && words.every(w => x.text.includes(w)));
  }

  function panelAll(s) {
    const f = S.find;
    return `<div class="section-head"><h2>All stats</h2>${riskTag('danger')}
        <p>Every stat in this save, ${nf.format(statIndex(s.file).length)} in all. Stats the game shows on its stats screens use the game’s own wording; other names were matched by their hash and are very likely right. Where the real name is still unknown but the saves show what a stat holds, it gets a plain description in italics. The rest are shown as numbers.
        Stats the game uses usually change between your saves, so that filter is on by default. Change one thing at a time.</p></div>
      <div class="finder"><input type="search" placeholder="Search, for example kills, time running, or #103" value="${esc(f.q)}" data-find="q" aria-label="Search stats">
        <label><input type="checkbox" data-find="varies" ${f.varies ? 'checked' : ''}> Only stats that change between my saves</label>
        <label><input type="checkbox" data-find="named" ${f.named ? 'checked' : ''}> Only named stats</label>
        <label><input type="checkbox" data-find="game" ${f.game ? 'checked' : ''}> Only stats the game shows</label></div>
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
      else input = `<input type="number" ${attrs} data-type="${x.type === 'float' ? 'float' : 'int'}" data-unit="${x.type === 'float' ? 'raw-float' : 'count'}" min="0" max="${capOf(x)}" step="${x.type === 'float' ? 'any' : 1}"
        data-init="${esc(String(x.v))}" data-orig="${esc(JSON.stringify(x.v))}" value="${esc(String(dr ? dr.newValue : x.v))}">`;
      return `<tr class="${dr ? 'changed' : ''}"><td class="key${x.meaning && !x.game ? ' described' : ''}">${esc(x.game || x.name)}<small>${x.game ? esc(x.name) + ', ' : x.qlab ? esc(x.qlab) + ', ' : ''}${x.meaning && !x.game ? 'real name unknown, described from how it behaves in saves, ' : ''}#${x.b}${x.q ? ' / #' + x.q : ''}</small></td><td>${esc(x.owner)}</td><td>${esc(x.type)}${x.type === 'bool' ? '' : `<small>up to ${esc(compact.format(capOf(x)))}</small>`}</td><td>${input}</td></tr>`;
    }).join('')}</tbody></table>${list.length > shown.length ? `<div class="more"><button class="btn small" data-act="more">Show more (${nf.format(list.length - shown.length)} left)</button></div>` : ''}`;
  }

  const fmtRaw = (v, t) => t === 'float' ? nf2.format(v) : nf.format(v);
  const compact = new Intl.NumberFormat('en', {notation: 'compact', maximumFractionDigits: 1});
  // All stats: a cap far below where a counter could overflow as the game keeps adding to it (the meaning of most of
  // these stats is unknown, so this guards against the worst breakage, not against every bad value)
  const SAFE_MAX = {int64: 999999999999, int32: 9999999, u32: 9999999, int16: 9999, u8: 99, float: 999999999};
  // a stat already holding more than the cap isn't a simple counter (often an id or a set of flags): keep the type's range
  const capOf = x => Math.abs(x.v) > (SAFE_MAX[x.type] ?? Infinity) ? TYPE_MAX[x.type] : (SAFE_MAX[x.type] ?? TYPE_MAX[x.type]);

  // featured stats: the reasonable max in the units the field shows, and in words
  const maxShown = f => f.unit === 'ms' ? Math.floor(f.max / 3600000) : f.unit === 'distance' ? Math.floor(f.max / 1000) : f.max;
  function maxText(f) {
    if (f.max == null) return '';
    const n = nf.format(maxShown(f));
    const shown = f.unit === 'percent' ? `${n}%` : f.unit === 'ms' ? `${n} hours` : f.unit === 'distance' ? `${n} km` : f.unit === 'money' ? `$${n}` : n;
    return `Max ${shown}${f.maxWhy ? ', ' + f.maxWhy : ''}.`;
  }

  // ---- trophies
  // ---- completion: whole groups of the 100% checklist at once
  function panelCompletion(s) {
    const c = S.comp[s.file].stunts;
    const sel = S.stuntSel[s.file] || new Set();
    const row = g => {
      const marked = sel.has(g.id), all = g.done >= g.count;
      return `<div class="field"><div class="name">${esc(g.label)}<span class="help">${nf.format(g.done)} of ${nf.format(g.count)} done in this save${g.gameTotal !== g.count ? ` (the game has ${nf.format(g.gameTotal)})` : ''}.</span></div>
        <div class="inputs">${marked ? `<span class="note">Marked done. Save edits to apply it.</span> <button class="btn small" data-act="stunts-undo" data-group="${g.id}">Undo</button>`
          : `<button class="btn small" data-act="stunts" data-group="${g.id}" ${all ? 'disabled' : ''}>${all ? 'All done' : 'Mark all done'}</button>`}</div></div>`;
    };
    const left = c.groups.filter(g => g.done < g.count && !sel.has(g.id)).length;
    return `<div class="section-head"><h2>Completion</h2>${riskTag('caution')}
        <p>Mark whole parts of the 100% checklist done. Each one is marked found and completed, the counters the game keeps are set to match, and the 100% figure is worked out again the way the game does it. Not tested on a PS5 yet: send the save and check it loads before relying on it.</p></div>
      ${checklistTable(s)}
      <div class="group"><div class="section-head"><h3>Stunts</h3>${left > 1 ? '<button class="btn small" data-act="stunts" data-group="all">Mark every stunt done</button>' : ''}
        <p>The 100% checklist needs any ${nf.format(c.for100)} of the game’s 397 stunts. Unique stunts done in this save: ${c.uniqueTotal == null ? 'unknown' : nf.format(c.uniqueTotal)}. Under-the-bridge flights and knife flights can’t be told apart in the save, so they’re marked together.</p></div>
        <div class="fields">${c.groups.map(row).join('')}</div></div>
      ${compParts(s)}`;
  }

  function compParts(s) {
    const C = S.comp[s.file], d = draftOf(s.file).completion;
    const pending = (k, text) => `<span class="note">${esc(text)} Save edits to apply it.</span> <button class="btn small" data-act="comp-undo" data-feature="${k}">Undo</button>`;
    // compendium: animals and weapons (vehicles aren't offered: the game's vehicle pages don't match the save's list)
    const types = (C.compendium.types || []).filter(t => t.group === 'animals' || t.group === 'weapons');
    const cg = new Set(d.compendium?.groups || []);
    const comp = `<div class="group"><div class="section-head"><h3>Compendium</h3><p>Marks animals and weapons as discovered in the game’s compendium, with the counters and the 100% checklist rows that go with them. Vehicles aren’t offered: the game’s vehicle pages don’t match the list in the save.</p></div>
      <div class="fields">${types.map(t => `<div class="field"><div class="name">${t.group === 'animals' ? 'Animals' : 'Weapons'}<span class="help">${nf.format(t.discovered)} of ${nf.format(t.candidates)} discovered in this save.</span></div>
        <div class="inputs">${cg.has(t.group) ? pending('compendium:' + t.group, 'Will be marked discovered.') : `<button class="btn small" data-act="comp-add" data-feature="compendium" data-value="${t.group}" ${t.discovered >= t.candidates ? 'disabled' : ''}>${t.discovered >= t.candidates ? 'All discovered' : 'Mark all discovered'}</button>`}</div></div>`).join('')}</div></div>`;
    // map discoveries: shop and place categories
    const places = (C.discovery.categories || []).filter(x => x.kind === 'place');
    const placeDone = places.filter(x => x.state === 'complete').length;
    const disc = `<div class="group"><div class="section-head"><h3>Map discoveries</h3><p>Shops and places on the map, by kind: ${nf.format(placeDone)} of ${nf.format(places.length)} kinds fully discovered. Completing a kind marks all its locations discovered, the way the game records a finished kind. Stunt and gang locations aren’t touched here.</p></div>
      <div class="fields"><div class="field"><div class="name">Every shop and place<span class="help">${places.filter(x => x.state !== 'complete').map(x => `${esc(x.label)} ${x.found}/${x.locations}`).join(', ') || 'All done.'}</span></div>
        <div class="inputs">${d.discovery ? pending('discovery', 'Will be discovered.') : `<button class="btn small" data-act="comp-add" data-feature="discovery" data-value="all" ${placeDone >= places.length ? 'disabled' : ''}>${placeDone >= places.length ? 'All discovered' : 'Discover all'}</button>`}</div></div></div></div>`;
    // challenges by category
    const cats = C.challenges.categories || [];
    const chosen = d.challenges ? (d.challenges.categories === 'all' ? new Set(cats.map(x => x.key)) : new Set(d.challenges.categories)) : new Set();
    const chal = `<div class="group"><div class="section-head"><h3>Challenges</h3>${cats.some(x => x.done < x.of && !chosen.has(x.key)) ? '<button class="btn small" data-act="comp-add" data-feature="challenges" data-value="all">Complete every challenge</button>' : ''}
        <p>The 100% checklist needs 70 of the game’s 80 challenges. Completed in this save: ${nf.format(C.challenges.done)}. Completing one sets it done and moves its counters; rewards the game hands out itself, such as vehicles, may not unlock.</p></div>
      <div class="fields">${cats.map(x => `<div class="field"><div class="name">${esc(x.label)}<span class="help">${x.done} of ${x.of} completed.</span></div>
        <div class="inputs">${chosen.has(x.key) ? pending('challenges:' + x.key, 'Will be completed.') : `<button class="btn small" data-act="comp-add" data-feature="challenges" data-value="${x.key}" ${x.done >= x.of ? 'disabled' : ''}>${x.done >= x.of ? 'All done' : 'Complete'}</button>`}</div></div>`).join('')}</div></div>`;
    // gym memberships
    const gyms = C.gyms.gyms || [];
    const owned = gyms.filter(g => g.owned).length;
    const gymBox = `<div class="group"><div class="section-head"><h3>Gym memberships</h3><p>The 100% checklist needs all 8. Owned in this save: ${owned}. A membership is added the way the game adds one; the gyms marked “not seen yet” have never been bought in a real save, so their item IDs come from the game’s text.</p></div>
      <div class="fields"><div class="field"><div class="name">All gym memberships<span class="help">${gyms.map(g => `${esc(g.label)}${g.owned ? ' (owned)' : g.grade !== 'confirmed' ? ' (not seen yet)' : ''}`).join(', ')}.</span></div>
        <div class="inputs">${d.gyms ? pending('gyms', 'Will be added.') : `<button class="btn small" data-act="comp-add" data-feature="gyms" data-value="all" ${owned >= gyms.length ? 'disabled' : ''}>${owned >= gyms.length ? 'All owned' : 'Add all'}</button>`}</div></div></div></div>`;
    // meditation spots
    const m = C.activities.meditation;
    const med = `<div class="group"><div class="section-head"><h3>Meditation spots</h3><p>The 100% checklist needs 15; the save has ${m.total} spots and ${m.done} are done. Completing them records a meditation at each spot, for Lucia, with the counters and the checklist row in step. Focus training rewards aren’t given.</p></div>
      <div class="fields"><div class="field"><div class="name">Every meditation spot<span class="help">${m.done} of ${m.total} done.</span></div>
        <div class="inputs">${d.activities ? pending('activities', 'Will be completed.') : `<button class="btn small" data-act="comp-add" data-feature="activities" data-value="all" ${m.done >= m.total ? 'disabled' : ''}>${m.done >= m.total ? 'All done' : 'Complete all'}</button>`}</div></div></div></div>`;
    return comp + disc + chal + gymBox + med + robberyParts(s) + activityParts(s) + collectibleParts(s) + leftToPlay(s);
  }

  // collectibles: the proven kinds, the experimental ones (no save has one to copy), and the ones that can't be written yet
  const COLL = {
    cards: ['Collectible cards', c => `All ${c.entries} cards in their 18 sets (the checklist needs 15); ${c.found} found in this save. The cards don’t appear in Lucia’s pocket.`],
    magazines: ['Magazines, books and comics', c => `The ${c.entries} identified so far; ${c.found} found. They count toward MAGAZINES, BOOKS & COMICS (${c.line?.value ?? '?'} of ${c.line?.of ?? 30}).`],
    watches: ['Luxury watches', c => `All ${c.entries} watches, which count as discovered styles (${c.line?.value ?? '?'} of ${c.line?.of ?? 70}); ${c.found} found. The watches themselves aren’t added to the wardrobe.`],
    bookswaps: ['Book swaps (experimental)', c => `${c.entries} library book swaps that count toward magazines, books and comics. No save has one yet, so how the game records it is a best guess.`],
    magazinestyles: ['Magazine styles (experimental)', c => `${c.entries} tattoos, make-up looks and hairstyles from magazines that count as discovered styles. No save has one yet, and the store unlock they give may be stored elsewhere.`],
    flamingos: ['Cocaine flamingos (experimental)', c => `All ${c.entries} are identified, but no save has had one destroyed, so how the game records it is a best guess.`]};
  function collectibleParts(s) {
    const C = S.comp[s.file], d = draftOf(s.file).completion;
    if (!C.collectibles) return '';
    const cats = (C.collectibles.categories || []).filter(c => COLL[c.key] && (c.state === 'proven' || c.state === 'experimental'));
    const chosen = new Set(d.collectibles?.categories || []);
    const rows = cats.map(c => `<div class="field"><div class="name">${esc(COLL[c.key][0])}<span class="help">${COLL[c.key][1](c)}</span></div>
      <div class="inputs">${chosen.has(c.key) ? `<span class="note">Will be marked found. Save edits to apply it.</span> <button class="btn small" data-act="coll-undo" data-value="${c.key}">Undo</button>`
        : `<button class="btn small" data-act="coll-add" data-value="${c.key}" ${c.found >= c.entries ? 'disabled' : ''}>${c.found >= c.entries ? 'All found' : 'Mark found'}</button>`}</div></div>`).join('');
    const refused = (C.collectibles.categories || []).filter(c => c.state === 'refused').map(c => esc((c.label || c.key).charAt(0) + (c.label || c.key).slice(1).toLowerCase().replace('waink', 'WAiNK')));
    return `<div class="group"><div class="section-head"><h3>Collectibles</h3><p>Marked found the way the game records a pickup. Marking one found may stop it appearing in the world, so keep your backup until the PS5 shows it counted.</p></div>
      <div class="fields">${rows}</div>${refused.length ? `<p class="note">Not possible yet, because the save doesn’t show which entries they are or how the game records them: ${refused.join(', ')}.</p>` : ''}</div>`;
  }

  // activities, hoops and the vehicle compendium
  function activityParts(s) {
    const C = S.comp[s.file], d = draftOf(s.file).completion;
    if (!C.activities2 || !C.hoops || !C.vehicles) return '';
    const label = t => t.charAt(0) + t.slice(1).toLowerCase().replace(/bret's/, 'Bret’s');
    const chosen = new Set(d.activities2?.lines || []);
    const lines = C.activities2.lines;
    const open = lines.filter(l => !l.done_line && l.counter < l.of && !chosen.has(l.key) && l.key !== 'bret');
    const help = l => l.confidence === 'verified' ? 'Marks each one played.' : l.key === 'bret' ? 'Sets the count only: deck progress isn’t in the save.' : 'Sets the checklist count; the individual results aren’t written, since no save has one played to copy.';
    const acts = `<div class="group"><div class="section-head"><h3>Activities</h3>${open.length > 1 ? '<button class="btn small" data-act="act-line" data-value="all">Complete all</button>' : ''}<p>Races, ranges, video games, pool, mini golf, drone trials and Bret’s target decks. Prize money, rewards and trophies for them aren’t given.</p></div>
      <div class="fields">${lines.map(l => `<div class="field"><div class="name">${esc(label(l.label))}<span class="help">${nf.format(l.counter)} of ${nf.format(l.of)}. ${help(l)}</span></div>
        <div class="inputs">${chosen.has(l.key) ? `<span class="note">Will be completed. Save edits to apply it.</span> <button class="btn small" data-act="act-line-undo" data-value="${l.key}">Undo</button>`
          : `<button class="btn small" data-act="act-line" data-value="${l.key}" ${l.counter >= l.of ? 'disabled' : ''}>${l.counter >= l.of ? 'Done' : 'Complete'}</button>`}</div></div>`).join('')}</div></div>`;
    const h = C.hoops, ht = h.countyTotals || {};
    const hoopBox = `<div class="group"><div class="section-head"><h3>Basketball hoops</h3><p>The 100% checklist needs 90 of the game’s 100 hoops. Found ${h.found}, scored ${h.scored}. Every hoop is marked found and scored, with each county’s count (${Object.entries(ht).map(([k, v]) => `${esc(k)} ${v}`).join(', ')}, from the game’s own hoop numbers on public maps).</p></div>
      <div class="fields"><div class="field"><div class="name">Every hoop<span class="help">${h.scored} of ${h.total} scored.</span></div>
        <div class="inputs">${d.hoops ? `<span class="note">Will be scored. Save edits to apply it.</span> <button class="btn small" data-act="comp-undo" data-feature="hoops">Undo</button>` : `<button class="btn small" data-act="comp-add" data-feature="hoops" data-value="all" ${h.scored >= h.total ? 'disabled' : ''}>${h.scored >= h.total ? 'All scored' : 'Score all'}</button>`}</div></div></div></div>`;
    const v = C.vehicles;
    const veh = `<div class="group"><div class="section-head"><h3>Vehicle compendium</h3><p>BASE MODEL VEHICLES on the 100% checklist: ${v.checklist.value} of ${v.checklist.of}. Adds the ${v.needed} cars and utility vehicles still needed to the compendium, each counted on its own page. Boats, aircraft and a few special cars aren’t added: their compendium IDs aren’t known.</p></div>
      <div class="fields"><div class="field"><div class="name">Discover ${v.needed} more vehicles<span class="help">${v.candidates} candidates on the car and utility pages.</span></div>
        <div class="inputs">${d.vehicles ? `<span class="note">Will be discovered. Save edits to apply it.</span> <button class="btn small" data-act="comp-undo" data-feature="vehicles">Undo</button>` : `<button class="btn small" data-act="comp-add" data-feature="vehicles" data-value="min" ${!v.needed || v.candidates < v.needed ? 'disabled' : ''}>${!v.needed ? 'Done' : v.candidates < v.needed ? 'Not enough candidates' : 'Discover'}</button>`}</div></div></div></div>`;
    return acts + hoopBox + veh;
  }

  // robberies and fencing: lines of the checklist, each marked as the game records it
  function robberyParts(s) {
    const C = S.comp[s.file], d = draftOf(s.file).completion;
    if (!C.robberies || !C.fencing) return '';
    const fmtv = l => l.of >= 1000 ? `$${nf.format(l.value)} of $${nf.format(l.of)}` : `${nf.format(l.value)} of ${nf.format(l.of)}`;
    const part = (feat, title, intro, lines) => {
      const chosen = new Set(d[feat]?.lines || []);
      const open = lines.filter(l => !l.done && !chosen.has(l.key));
      return `<div class="group"><div class="section-head"><h3>${title}</h3>${open.length > 1 ? `<button class="btn small" data-act="comp-line" data-feature="${feat}" data-value="all">Complete all</button>` : ''}<p>${intro}</p></div>
        <div class="fields">${lines.map(l => `<div class="field"><div class="name">${esc(l.label.charAt(0) + l.label.slice(1).toLowerCase())}<span class="help">${fmtv(l)}${l.missing ? `, $${nf.format(l.missing)} to go` : ''}.</span></div>
          <div class="inputs">${chosen.has(l.key) ? `<span class="note">Will be completed. Save edits to apply it.</span> <button class="btn small" data-act="comp-line-undo" data-feature="${feat}" data-value="${l.key}">Undo</button>`
            : `<button class="btn small" data-act="comp-line" data-feature="${feat}" data-value="${l.key}" ${l.done ? 'disabled' : ''}>${l.done ? 'Done' : 'Complete'}</button>`}</div></div>`).join('')}</div></div>`;
    };
    return part('robberies', 'Robberies', 'Marks robbery locations fully hit the way the game records it, with the per-type counters and the checklist rows. No cash, goods or robbery counts are added. Vaults: the save doesn’t say which 8 banks have one, so the vaults of all 12 large banks are marked.', C.robberies.lines)
      + part('fencing', 'Fencing', 'Records one sale per unfinished line, worth exactly what’s missing, to the fence the game uses most for it, as Lucia. The earnings totals that a real sale raises go up with it.', C.fencing.lines);
  }

  // optional tasks and gang operations can't be completed by editing the save: show what's left to play
  function leftToPlay(s) {
    const C = S.comp[s.file], t = C.tasks, g = C.gangs;
    if (!t || !g) return '';
    const np = t.notPassed || [], titled = np.filter(x => x.title), untitled = np.length - titled.length;
    const taskList = titled.length ? titled.map(x => esc(x.title)).join(', ') + (untitled ? `, and ${untitled} more without a title in the game’s text` : '') : '';
    const tasks = `<div class="group"><div class="section-head"><h3>Optional tasks</h3><p>${t.checklist.value} of ${t.checklist.of} done. These can’t be completed by editing the save: the game records a task only once it’s played, and recording one that wasn’t played would leave it still on offer in the world, without its rewards. ${t.missing} are left to play.${(t.knownMissing || []).length ? ` One of them was finished in your other playthrough.` : ''}</p></div>
      ${taskList ? `<p class="note">Side missions not passed in this save, a good place to look: ${taskList}.</p>` : ''}</div>`;
    const left = (g.locations || []).filter(x => !x.cleared);
    const byGang = Object.fromEntries((g.gangs || []).map(x => [x.key, x.name]));
    const gangs = `<div class="group"><div class="section-head"><h3>Gang operations</h3><p>${g.checklist.value} of ${g.checklist.of} cleared. These can’t be completed by editing the save either: a clear is written in three places, many operations have no record yet, and each one hands out its own weapons, vehicles and safes. Left to clear:</p></div>
      <table class="raw"><thead><tr><th>Operation</th><th>Gang</th><th>State</th></tr></thead><tbody>${left.map(x => `
        <tr><td class="key">${esc(x.label || x.owner || x.id)}${x.hint ? `<small>${esc(x.hint)}</small>` : ''}</td><td>${esc(byGang[x.gang] || x.gang || '')}</td><td>${esc(x.state || '')}</td></tr>`).join('')}</tbody></table></div>`;
    return tasks + gangs;
  }

  // the game's 100% checklist, line by line, with what this tab can do about each
  function checklistTable(s) {
    const c = S.comp[s.file].checklist;
    if (!c || !c.lines) return '';
    const here = l => l.grade === 'a' || l.grade === 'done' ? 'On this tab' : l.grade === 'partial' ? 'Partly, on this tab' : l.grade === 'b' ? 'Not yet: tied to missions, or not certain enough' : 'Can’t be done from the save';
    const fmtv = l => l.of == null ? (typeof l.value === 'number' ? nf2.format(l.value) + (l.label.includes('COMPLETION') ? '%' : '') : '') : `${nf.format(l.value)} / ${nf.format(l.of)}`;
    return `<details class="checklist"><summary>The game’s 100% checklist: ${nf2.format(c.overall?.stored ?? c.overall)}% in this save</summary>
      <table class="raw"><thead><tr><th>Line</th><th>In this save</th><th>Weight</th><th>Here</th></tr></thead><tbody>${c.lines.map(l => `
        <tr><td>${esc(l.label)}</td><td>${esc(fmtv(l))}</td><td>${l.weight}%</td><td>${esc(here(l))}</td></tr>`).join('')}</tbody></table></details>`;
  }

  // ---- world: time of day, health, armour
  const two = n => String(n).padStart(2, '0');
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  function panelWorld(s) {
    const w = S.world[s.file], d = draftOf(s.file).world, c = w.clock;
    const t = d.time || {hour: c.hour, minute: c.minute};
    const hp = d.health ?? w.health;
    return `<div class="section-head"><h2>World</h2>${riskTag('caution')}
        <p>The time of day, health and armour the save was made with. Not tested on a PS5 yet: send the save and check it loads before relying on it.</p></div>
      <div class="fields">
        <div class="field"><div class="name">Time of day<span class="help">Now ${two(c.hour)}:${two(c.minute)} on ${c.day} ${MONTHS[c.month - 1] || ''} ${c.year} in the game. The date stays the same.</span></div>
          <div class="inputs"><div class="cell narrow ${d.time ? 'changed' : ''}"><label for="w-hour">Hour</label><span class="with-unit"><input id="w-hour" type="number" min="0" max="23" step="1" value="${t.hour}" data-world="hour"></span></div>
            <div class="cell narrow ${d.time ? 'changed' : ''}"><label for="w-min">Minute</label><span class="with-unit"><input id="w-min" type="number" min="0" max="59" step="1" value="${two(t.minute)}" data-world="minute"></span></div></div></div>
        <div class="field"><div class="name">Health<span class="help">Now ${nf2.format(w.health)}. Up to ${nf.format(w.healthMax)}; above 100 is overpowered health.</span></div>
          <div class="inputs"><div class="cell ${d.health != null ? 'changed' : ''}"><label for="w-hp">Health</label><span class="with-unit"><input id="w-hp" type="number" min="1" max="${w.healthMax}" step="any" value="${hp}" data-world="health">
            <button class="btn small" data-act="world-fill" data-what="health">Max</button></span></div></div></div>
        <div class="field"><div class="name">Armour<span class="help">Now ${nf2.format(w.armour)} of ${nf2.format(w.armourMax)}, for both characters’ armour together.</span></div>
          <div class="inputs">${d.armour === 'full' ? '<span class="note">Will be filled. Save edits to apply it.</span> <button class="btn small" data-act="world-undo" data-what="armour">Undo</button>'
            : `<button class="btn small" data-act="world-fill" data-what="armour" ${w.armour >= w.armourMax ? 'disabled' : ''}>${w.armour >= w.armourMax ? 'Already full' : 'Fill armour'}</button>`}</div></div>
      </div>`;
  }

  function onWorld(el) {
    const s = slotOf(S.slot);
    if (!s || !S.world[s.file]) return;
    const w = S.world[s.file], d = draftOf(s.file).world, c = w.clock;
    const what = el.dataset.world, v = Number(el.value);
    if (what === 'hour' || what === 'minute') {
      const t = {hour: d.time?.hour ?? c.hour, minute: d.time?.minute ?? c.minute};
      t[what] = v;
      const ok = el.value !== '' && Number.isInteger(v) && v >= 0 && v <= (what === 'hour' ? 23 : 59);
      el.setAttribute('aria-invalid', ok ? 'false' : 'true');
      if (!ok) { delete d.time; }
      else if (t.hour === c.hour && t.minute === c.minute) delete d.time;
      else d.time = t;
    } else if (what === 'health') {
      const ok = el.value !== '' && v >= 1 && v <= w.healthMax;
      el.setAttribute('aria-invalid', ok ? 'false' : 'true');
      if (!ok || v === w.health) delete d.health; else d.health = v;
    }
    renderPending(); renderCounts();
  }

  // ---- save data: every section, one number or true/false at a time
  function panelData(s) {
    const sd = S.sd[s.file], d = draftOf(s.file).raw;
    const head = `<div class="section-head"><h2>Save data</h2>${riskTag('danger')}
        <p>Every section of the save, with names where they’re known. Numbers and true/false values can be changed one at a time; text, the story flow, heists, vehicle records and anything another tab handles stay read-only. Most of these values have unknown meanings, so change one thing, send the save and check it loads.</p></div>`;
    if (!sd.cur) {
      return head + `<table class="raw"><thead><tr><th>Section</th><th>Size</th><th></th></tr></thead><tbody>${sd.sections.map(x => `
        <tr><td class="key">${esc(x.name || '0x' + x.hash)}<small>0x${x.hash}${x.readOnly ? ', read-only: ' + esc(x.readOnly) : x.risky ? ', not recommended' : ''}</small></td>
          <td>${nf.format(x.bytes)} bytes</td><td><button class="btn small" data-act="sd-open" data-section="${x.hash}" data-path="[]">Open</button></td></tr>`).join('')}</tbody></table>`;
    }
    const n = sd.node, sec = sd.sections.find(x => x.hash === sd.cur.section);
    const crumbs = [`<button class="btn small" data-act="sd-home">Sections</button>`, `<button class="btn small" data-act="sd-open" data-section="${sd.cur.section}" data-path="[]">${esc(sec?.name || '0x' + sd.cur.section)}</button>`]
      .concat(sd.cur.path.map((p, i) => `<button class="btn small" data-act="sd-open" data-section="${sd.cur.section}" data-path='${esc(JSON.stringify(sd.cur.path.slice(0, i + 1)))}'>${esc(String(sd.cur.labels[i] ?? p))}</button>`));
    if (!n) return head + `<div class="crumbs">${crumbs.join(' ')}</div><div class="empty">Reading…</div>`;
    const ro = n.readOnly;
    const rows = n.items.map(x => {
      const path = [...n.path, x.key], k = rawKey(n.section, path), dr = d[k];
      let cell;
      if (x.kind === 'object' || x.kind === 'array') cell = `<button class="btn small" data-act="sd-open" data-section="${n.section}" data-path='${esc(JSON.stringify(path))}' data-label="${esc(String(x.label))}">Open, ${nf.format(x.count)} ${x.kind === 'array' ? 'items' : 'fields'}</button>`;
      else if (ro || !['int', 'float', 'bool'].includes(x.kind)) cell = `<span class="lock">${esc(x.raw)}</span>`;
      else if (x.kind === 'bool') { const on = dr ? dr.newValue : x.raw === 'true';
        cell = `<label class="toggle"><input type="checkbox" data-raw="1" data-section="${n.section}" data-path='${esc(JSON.stringify(path))}' data-orig="${esc(x.raw)}" data-label="${esc(String(x.label))}" ${on ? 'checked' : ''}> ${on ? 'true' : 'false'}</label>`; }
      else cell = `<input type="number" step="any" data-raw="1" data-kind="${x.kind}" data-section="${n.section}" data-path='${esc(JSON.stringify(path))}' data-orig="${esc(x.raw)}" data-label="${esc(String(x.label))}" value="${esc(dr ? String(dr.newValue) : x.raw)}">`;
      return `<tr class="${dr ? 'changed' : ''}"><td class="key">${esc(String(x.label))}${typeof x.key === 'string' && x.label !== x.key ? `<small>${esc(x.key)}</small>` : ''}</td><td>${esc(x.kind)}</td><td>${cell}</td></tr>`;
    }).join('');
    const more = n.total > n.offset + n.items.length ? `<div class="more"><button class="btn small" data-act="sd-more">Show more (${nf.format(n.total - n.offset - n.items.length)} left)</button></div>` : '';
    return head + `<div class="crumbs">${crumbs.join(' ')}</div>${ro ? `<div class="callout">Read-only: ${esc(ro)}.</div>` : n.risky ? '<div class="callout">Not recommended: this section is tied to the story or its meaning isn’t known.</div>' : ''}
      <table class="raw"><thead><tr><th>Field</th><th>Type</th><th>Value</th></tr></thead><tbody>${rows}</tbody></table>${more}`;
  }

  async function sdOpen(file, section, path, labelText, append) {
    const sd = S.sd[file];
    if (!append) {
      const same = sd.cur && sd.cur.section === section;
      const labels = same ? sd.cur.labels.slice(0, path.length) : [];
      if (labelText && path.length) labels[path.length - 1] = labelText;
      sd.cur = {section, path, labels};
      sd.node = null; S.mainKey = ''; renderMain();
    }
    const offset = append ? sd.node.offset + sd.node.items.length : 0;
    try {
      const n = await api('/api/savedata?file=' + encodeURIComponent(file) + '&section=' + section + '&path=' + encodeURIComponent(JSON.stringify(path)) + '&offset=' + offset);
      if (append) { n.items = sd.node.items.concat(n.items); n.offset = sd.node.offset; }
      sd.node = n;
    } catch (e) { toast(ERR[e.code] || ERR.internal); }
    S.mainKey = ''; renderMain();
  }

  function onRaw(el) {
    const s = slotOf(S.slot);
    if (!s) return;
    const d = draftOf(s.file).raw, path = JSON.parse(el.dataset.path), k = rawKey(el.dataset.section, path);
    let nv;
    if (el.type === 'checkbox') { nv = el.checked; const lab = el.closest('label'); if (lab && lab.lastChild?.nodeType === 3) lab.lastChild.textContent = ' ' + String(nv); }
    else {
      nv = Number(el.value);
      const ok = el.value.trim() !== '' && Number.isFinite(nv) && (el.dataset.kind !== 'int' || Number.isInteger(nv));
      el.setAttribute('aria-invalid', ok ? 'false' : 'true');
      if (!ok) { delete d[k]; renderPending(); renderCounts(); return; }
    }
    const orig = el.dataset.orig;
    const same = el.type === 'checkbox' ? String(nv) === orig : Number(orig) === nv;
    if (same) delete d[k];
    else d[k] = {section: el.dataset.section, path, value: orig, newValue: nv, label: el.dataset.label};
    el.closest('tr')?.classList.toggle('changed', !same);
    renderPending(); renderCounts();
  }

  async function setStunts(file, ids) {
    const d = draftOf(file);
    for (const k of S.stuntKeys[file] || []) delete d.stats[k];
    S.stuntKeys[file] = new Set();
    S.stuntSel[file] = new Set(ids);
    if (ids.length) d.completion.stuntDiscovery = [...ids]; else delete d.completion.stuntDiscovery;
    if (ids.length) {
      try {
        const r = await api('/api/stunt-edits', {file, groups: ids});
        for (const e of r.edits) { const k = `${e.group}:${e.row}`; d.stats[k] = e; S.stuntKeys[file].add(k); }
      } catch (e) { S.stuntSel[file] = new Set(); toast(ERR[e.code] || ERR.internal); }
    }
    S.mainKey = ''; renderMain(); renderPending(); renderCounts();
  }

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
      try { S.detail[file] = await api('/api/slot?file=' + encodeURIComponent(file)); } catch (e) { S.detail[file] = {failed: e.code || 'request_failed', featured: [], ammo: []}; }
      S.mainKey = ''; renderMain(); return;
    }
    if (S.tab === 'all' && !S.stats[file]) {
      try { S.stats[file] = await api('/api/stats?file=' + encodeURIComponent(file)); } catch (e) { S.stats[file] = {failed: e.code || 'request_failed'}; }
      S.mainKey = ''; renderMain(); return;
    }
    if (S.tab === 'data' && !S.sd[file]) {
      try { S.sd[file] = {sections: (await api('/api/savedata?file=' + encodeURIComponent(file))).sections, cur: null, node: null}; }
      catch (e) { S.sd[file] = {failed: e.code || 'request_failed'}; }
      S.mainKey = ''; renderMain(); return;
    }
    if (S.tab === 'world' && !S.world[file]) {
      try { S.world[file] = await api('/api/world?file=' + encodeURIComponent(file)); } catch (e) { S.world[file] = {failed: e.code || 'request_failed'}; }
      S.mainKey = ''; renderMain(); return;
    }
    if (S.tab === 'completion' && !S.comp[file]) {
      try { S.comp[file] = await api('/api/completion?file=' + encodeURIComponent(file)); } catch (e) { S.comp[file] = {failed: e.code || 'request_failed'}; }
      S.mainKey = ''; renderMain(); return;
    }
    renderCounts();
  }

  function renderCounts() {
    const d = draftOf(S.slot);
    const n = {money: Object.keys(d.money).length, ammo: Object.keys(d.ammo).length, stats: 0, all: 0};
    const feat = new Set((S.detail[S.slot]?.featured || []).flatMap(f => f.entries.map(e => `${e.group}:${e.row}`)));
    const stunt = S.stuntKeys[S.slot] || new Set();
    n.completion = compCount(d.completion); n.world = Object.keys(d.world || {}).length; n.data = Object.keys(d.raw || {}).length;
    for (const k of Object.keys(d.stats)) n[stunt.has(k) ? 'completion' : feat.has(k) ? 'stats' : 'all']++;
    for (const el of $$('[data-count]')) el.textContent = n[el.dataset.count] || '';
  }

  // ------------------------------------------------------------ send back
  function viewSend() {
    const st = S.state;
    const job = st.job || {};
    const done = job.kind === 'upload' && job.stage === 'uploaded';
    const edited = (st.slots || []).filter(x => x.modified);
    const summary = edited.length ? `<div class="panel"><h3>What’s being sent</h3><ul class="review" style="max-height:none;margin-top:8px">${edited.map(x =>
      (x.changes || []).slice(0, 60).map(c => `<li><span>${esc(missionName(x))}: ${esc(changeLabel(c))}</span><span>${c.count > 1 ? `${nf.format(c.count)} changes` : c.from === '' || c.from == null ? esc(fmtChange(c.to)) : `${esc(fmtChange(c.from))} to ${esc(fmtChange(c.to))}`}</span></li>`).join('')
      + ((x.changes || []).length > 60 ? `<li><span>${esc(missionName(x))}: and ${nf.format(x.changes.length - 60)} more changes</span><span></span></li>` : '') ||
      `<li><span>${esc(missionName(x))}</span><span>edited</span></li>`).join('')}</ul></div>` : '';
    const all = sortedSlots(st);
    const total = Math.max(st.fileCount || 0, all.length);
    const allList = all.length ? `<div class="panel"><h3>All ${total} saves are sent back</h3>
      <p class="detail" style="margin:6px 0 10px">Everything the PS5 had for ${esc(st.user?.name || 'this account')} in GTA VI goes back, not only the save you edited. Edited saves carry your changes. The others are sent exactly as downloaded.</p>
      <ul class="review" style="max-height:none;margin-top:8px">${all.map(x => `<li><span>${esc(label(x))}: ${esc(missionName(x))}</span><span>${x.modified ? 'edited' : 'unchanged'}</span></li>`).join('')}${total > all.length ? `<li><span>${total - all.length} other file${total - all.length > 1 ? 's' : ''}</span><span>unchanged</span></li>` : ''}</ul></div>` : '';
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
        <p>Your edits are encrypted and waiting. The PS5 won’t overwrite a save, so the old ones have to be deleted first. Every save of this account comes back, and the originals stay backed up on this computer.</p></section>
      <div class="stack">
        ${summary}
        ${allList}
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
            ${job.stage === 'choose_account' && job.accounts ? `<div class="accounts"><strong>Which account’s save do you want to edit?</strong>
              <div class="row">${job.accounts.map(a => `<button class="btn primary" data-act="choose-account" data-owner="${esc(a.id)}">${esc(a.name)}</button>`).join('')}</div>
              <div class="detail">These accounts each have a GTA VI save on this PS5.</div></div>` : ''}
            ${job.hint === 'console_has_save' ? '<div class="callout" style="margin-top:12px">The PS5 still has a GTA VI save, so it has nothing to receive. Delete the save on the PS5, then open Data Transfer again.</div>' : ''}
            ${['waiting_console', 'pair_waiting_console', 'connecting', 'need_power', 'choose_account'].includes(job.stage) ? '<div class="row" style="margin-top:10px"><button class="link" data-act="cancel">Cancel</button></div>' : ''}
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
    const w = d.world || {}, now = S.world[s.file];
    const worldList = [w.time && {label: 'Time of day', value: now ? `${two(now.clock.hour)}:${two(now.clock.minute)}` : '', newValue: `${two(w.time.hour)}:${two(w.time.minute)}`},
      w.health != null && {label: 'Health', value: now ? now.health : '', newValue: w.health},
      w.armour && {label: 'Armour', value: now ? now.armour : '', newValue: 'full'}].filter(Boolean);
    const cp = d.completion || {};
    const compList = [cp.compendium && {label: 'Compendium: ' + cp.compendium.groups.join(' and '), value: '', newValue: 'discovered'},
      cp.discovery && {label: 'Map: every shop and place', value: '', newValue: 'discovered'},
      cp.challenges && {label: 'Challenges: ' + (cp.challenges.categories === 'all' ? 'every category' : cp.challenges.categories.join(', ')), value: '', newValue: 'completed'},
      cp.gyms && {label: 'Gym memberships: ' + (cp.gyms.gyms === 'all' ? 'all' : cp.gyms.gyms.length), value: '', newValue: 'owned'},
      cp.activities && {label: 'Meditation spots: all, as ' + (cp.activities.character === 'jason' ? 'Jason' : 'Lucia'), value: '', newValue: 'completed'},
      cp.robberies && {label: 'Robberies: ' + cp.robberies.lines.join(', '), value: '', newValue: 'fully hit'},
      cp.fencing && {label: 'Fencing: ' + cp.fencing.lines.join(', '), value: '', newValue: 'completed'},
      cp.activities2 && {label: 'Activities: ' + cp.activities2.lines.join(', '), value: '', newValue: 'completed'},
      cp.hoops && {label: 'Basketball hoops: all', value: '', newValue: 'scored'},
      cp.vehicles && {label: 'Vehicle compendium: up to 200 base models', value: '', newValue: 'discovered'},
      cp.collectibles && {label: 'Collectibles: ' + cp.collectibles.categories.join(', '), value: '', newValue: 'found'}].filter(Boolean);
    const list = [...Object.values(d.money), ...Object.values(d.ammo), ...Object.values(d.stats), ...worldList, ...Object.values(d.raw || {}), ...compList];
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
    if (a === 'choose-account') { act('/api/choose-account', {owner: b.dataset.owner}); return; }
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
    if (a === 'coll-add' || a === 'coll-undo') {
      const s = slotOf(S.slot), d = draftOf(s.file).completion, v = b.dataset.value;
      const cur = new Set(d.collectibles?.categories || []);
      if (a === 'coll-add') cur.add(v); else cur.delete(v);
      const exp = [...cur].filter(k => ['bookswaps', 'magazinestyles', 'flamingos'].includes(k));
      if (cur.size) d.collectibles = {categories: [...cur], card_items: 'skip', watch_items: 'skip', ...(exp.length ? {experimental: exp} : {})};
      else delete d.collectibles;
      S.mainKey = ''; renderMain(); renderPending(); renderCounts();
      return;
    }
    if (a === 'act-line' || a === 'act-line-undo') {
      const s = slotOf(S.slot), d = draftOf(s.file).completion, C = S.comp[s.file];
      const lines = C.activities2.lines, v = b.dataset.value;
      const cur = new Set(d.activities2?.lines || []);
      if (a === 'act-line') { if (v === 'all') lines.filter(l => l.counter < l.of && l.key !== 'bret').forEach(l => cur.add(l.key)); else cur.add(v); } else cur.delete(v);
      if (cur.size) {
        const level = {};
        for (const k of cur) level[k] = (lines.find(l => l.key === k) || {}).confidence === 'verified' ? 'full' : 'counter';
        d.activities2 = {lines: [...cur], level, unverified_ok: cur.has('bret')};
      } else delete d.activities2;
      S.mainKey = ''; renderMain(); renderPending(); renderCounts();
      return;
    }
    if (a === 'comp-line' || a === 'comp-line-undo') {
      const s = slotOf(S.slot), d = draftOf(s.file).completion, C = S.comp[s.file];
      const feat = b.dataset.feature, v = b.dataset.value, all = C[feat].lines.filter(l => !l.done).map(l => l.key);
      const cur = new Set(d[feat]?.lines || []);
      if (a === 'comp-line') { if (v === 'all') all.forEach(k => cur.add(k)); else cur.add(v); } else cur.delete(v);
      if (cur.size) d[feat] = feat === 'robberies' ? {lines: [...cur], vaults: 'large'} : {lines: [...cur], character: 'lucia'}; else delete d[feat];
      S.mainKey = ''; renderMain(); renderPending(); renderCounts();
      return;
    }
    if (a === 'comp-add' || a === 'comp-undo') {
      const s = slotOf(S.slot), d = draftOf(s.file).completion, C = S.comp[s.file];
      const [feat, sub] = (a === 'comp-add' ? b.dataset.feature : b.dataset.feature).split(':');
      const v = b.dataset.value;
      if (a === 'comp-add') {
        if (feat === 'compendium') { const g = new Set(d.compendium?.groups || []); g.add(v); d.compendium = {groups: [...g]}; }
        if (feat === 'discovery') d.discovery = {categories: 'all'};
        if (feat === 'gyms') d.gyms = {gyms: 'all'};
        if (feat === 'activities') d.activities = {spots: 'all', character: 'lucia'};
        if (feat === 'hoops') d.hoops = {hoops: 'all', scored: true, county_counters: 'update'};
        if (feat === 'vehicles') d.vehicles = {count: 'min'};
        if (feat === 'challenges') {
          if (v === 'all') d.challenges = {categories: 'all'};
          else { const cur = d.challenges ? (d.challenges.categories === 'all' ? C.challenges.categories.map(x => x.key) : d.challenges.categories) : [];
                 d.challenges = {categories: [...new Set([...cur, v])]}; }
        }
      } else {
        if (feat === 'compendium') { const g = (d.compendium?.groups || []).filter(x => x !== sub); if (g.length) d.compendium = {groups: g}; else delete d.compendium; }
        else if (feat === 'challenges') {
          const cur = d.challenges ? (d.challenges.categories === 'all' ? C.challenges.categories.map(x => x.key) : d.challenges.categories) : [];
          const left = cur.filter(x => x !== sub);
          if (left.length) d.challenges = {categories: left}; else delete d.challenges;
        } else delete d[feat];
      }
      S.mainKey = ''; renderMain(); renderPending(); renderCounts();
      return;
    }
    if (a === 'sd-home') { S.sd[S.slot].cur = null; S.sd[S.slot].node = null; S.mainKey = ''; renderMain(); return; }
    if (a === 'sd-open') { sdOpen(S.slot, b.dataset.section, JSON.parse(b.dataset.path), b.dataset.label, false); return; }
    if (a === 'sd-more') { const c = S.sd[S.slot].cur; sdOpen(S.slot, c.section, c.path, null, true); return; }
    if (a === 'world-fill' || a === 'world-undo') {
      const s = slotOf(S.slot), w = S.world[s.file], d = draftOf(s.file).world;
      if (b.dataset.what === 'health') d.health = w.healthMax;
      else if (a === 'world-fill') d.armour = 'full';
      else delete d.armour;
      S.mainKey = ''; renderMain(); renderPending(); renderCounts();
      return;
    }
    if (a === 'stunts' || a === 'stunts-undo') {
      const file = S.slot, sel = new Set(S.stuntSel[file] || []);
      const g = b.dataset.group;
      if (a === 'stunts-undo') sel.delete(g);
      else if (g === 'all') for (const x of S.comp[file].stunts.groups) { if (x.done < x.count) sel.add(x.id); }
      else sel.add(g);
      setStunts(file, [...sel]);
      return;
    }
    if (a === 'fillall' || a === 'maxall') {
      for (const w of $$(`.inputs[data-scope="${b.dataset.scope}"]`)) {
        const input = w.querySelector('input[type="number"]');
        const to = input && (a === 'fillall' ? input.dataset.full : input.dataset.max);
        if (to) { input.value = to; onEdit(input); }
      }
      return;
    }
    if (a === 'reload') { const f = S.slot; delete S.detail[f]; delete S.stats[f]; delete S.comp[f]; delete S.world[f]; delete S.sd[f]; S.mainKey = ''; renderMain(); return; }
    if (a === 'more') { S.find.limit += 300; $('#allrows').innerHTML = allRows(slotOf(S.slot)); return; }
    if (a === 'review') { S.reviewOpen = !S.reviewOpen; renderPending(); return; }
    if (a === 'discard') {
      const s = slotOf(S.slot);
      delete S.drafts[s.file]; delete S.stuntSel[s.file]; delete S.stuntKeys[s.file]; seedDraft(s); S.mainKey = ''; renderMain(); renderPending(); return;
    }
    if (a === 'save') {
      const s = slotOf(S.slot);
      const d = draftList(draftOf(s.file));
      const none = !d.money.length && !d.ammo.length && !d.stats.length && !Object.keys(d.world).length && !d.raw.length && !compCount(d.completion);
      if (none && !s.modified) return;
      if (none) {
        if (confirm('You removed every edit for this save. Put its original back instead?')) act('/api/restore', {}, () => { S.drafts = {}; });
        return;
      }
      const stuntKeys = S.stuntKeys[s.file] || new Set();
      const risky = d.stats.some(c => !stuntKeys.has(`${c.group}:${c.row}`) && !(S.detail[s.file]?.featured || []).some(f => f.entries.some(e => e.group === c.group && e.row === c.row)));
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
    if (el.dataset.world) onWorld(el);
    if (el.dataset.raw && el.type !== 'checkbox') onRaw(el);
    if (el.dataset.find === 'q') {
      S.find.q = el.value; S.find.limit = 150;
      clearTimeout(S.findT);
      S.findT = setTimeout(() => { const box = $('#allrows'); if (box) box.innerHTML = allRows(slotOf(S.slot)); }, 160);
    }
  });

  document.addEventListener('change', e => {
    const el = e.target;
    if (el.dataset.edit && el.type === 'checkbox') onEdit(el);
    if (el.dataset.raw && el.type === 'checkbox') onRaw(el);
    if (el.dataset.find === 'varies' || el.dataset.find === 'named' || el.dataset.find === 'game') {
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
