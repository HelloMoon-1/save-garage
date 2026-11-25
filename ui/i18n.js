// SPDX-License-Identifier: GPL-3.0-only
'use strict';

const SaveGarageI18n = (() => {
  const preference = 'save-garage-language';
  const supported = ['en-US', 'zh-CN'];
  const chinese = window.saveGarageChinese || {};
  const catalog = new Map(Object.entries(chinese).map(([key, value]) => [key.toLowerCase(), value]));

  function browserLocale() {
    return /^zh(?:-(?:Hans(?:-.*)?|CN|SG))?$/i.test(navigator.language) ? 'zh-CN' : 'en-US';
  }

  let active = browserLocale();
  try {
    const saved = localStorage.getItem(preference);
    if (supported.includes(saved)) active = saved;
  } catch {
    // Some browser configurations block local storage.
  }

  function tr(message, ...args) {
    const template = active === 'zh-CN' && Object.hasOwn(chinese, message) ? chinese[message] : message;
    return template.replace(/\{(\d+)\}/g, (token, index) => Number(index) < args.length ? String(args[index]) : token);
  }

  function gameText(value) {
    if (active !== 'zh-CN' || !value) return value;
    const text = String(value);
    const label = catalog.get(text.toLowerCase());
    if (label) return label;
    const match = /^(.+) \((Lucia|Jason|Total)\)$/i.exec(text);
    if (match) {
      return gameText(match[1]) + (catalog.get((' (' + match[2] + ')').toLowerCase()) || ' (' + match[2] + ')');
    }
    const separator = text.lastIndexOf(': ');
    if (separator !== -1) {
      const operation = catalog.get(text.slice(separator + 2).toLowerCase());
      if (operation) return gameText(text.slice(0, separator)) + '：' + operation;
    }
    // Some recovered stat names have the form base.qualifier. Keep raw names in the secondary column.
    if (text.includes('.')) {
      const parts = text.split('.');
      const labels = parts.map(part => catalog.get(part.toLowerCase()) || part);
      if (labels.some((part, index) => part !== parts[index])) return labels.join(' · ');
    }
    return text;
  }

  function setLocale(value) {
    if (!supported.includes(value)) return;
    active = value;
    try { localStorage.setItem(preference, value); } catch { /* language still applies to this page */ }
  }

  function localizePage() {
    document.documentElement.lang = active;
    for (const element of document.querySelectorAll('[data-ui-text]')) element.textContent = tr(element.dataset.uiText);
    for (const element of document.querySelectorAll('[data-ui-label]')) element.setAttribute('aria-label', tr(element.dataset.uiLabel));
    document.querySelector('#language').value = active;
  }

  return {tr, gameText, setLocale, localizePage, locale: () => active};
})();
