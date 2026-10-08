import dictionaries from './translations.json?v=calendar-20261008' with { type: 'json' };

const languageCodes = ['en', 'vi', 'ko', 'ru', 'hi', 'tr', 'pt-BR', 'en-NG'];
const localeCodes = { en: 'en-US', vi: 'vi-VN', ko: 'ko-KR', ru: 'ru-RU', hi: 'hi-IN', tr: 'tr-TR', 'pt-BR': 'pt-BR', 'en-NG': 'en-NG' };
const textSources = new WeakMap();
const attributeSources = new WeakMap();
let activeLanguage = 'en';
const packLanguage = language => language === 'en-NG' ? 'en-NG' : language;
export const numberLocale = () => localeCodes[activeLanguage] ?? 'en-US';
export function relativeDaysAgo(days) {
  const count = days.toLocaleString(numberLocale());
  if (activeLanguage === 'vi') return `cách đây ${count} ngày`;
  if (activeLanguage === 'ko') return `${count}일 전`;
  if (activeLanguage === 'ru') return `${count} дн. назад`;
  if (activeLanguage === 'hi') return `${count} दिन पहले`;
  if (activeLanguage === 'tr') return `${count} gün önce`;
  if (activeLanguage === 'pt-BR') return `há ${count} ${days === 1 ? 'dia' : 'dias'}`;
  return `${count} ${days === 1 ? 'day' : 'days'} ago`;
}

function localize(source) {
  if (activeLanguage === 'vi') return source === 'day' ? 'ngày' : (dictionaries.vi[source] ?? source);
  if (!source) return source;
  const dictionary = dictionaries[packLanguage(activeLanguage)] ?? dictionaries.en;
  if (dictionary[source] !== undefined) return dictionary[source];
  const phrases = Object.keys(dictionary).filter(phrase => phrase.length >= 3 && source.includes(phrase)).sort((a, b) => b.length - a.length);
  let result = source;
  for (const phrase of phrases) {
    const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const startsWithWord = /^[\p{L}\p{N}_]/u.test(phrase);
    const endsWithWord = /[\p{L}\p{N}_]$/u.test(phrase);
    const pattern = new RegExp(`${startsWithWord ? '(?<![\\p{L}\\p{N}_])' : ''}${escaped}${endsWithWord ? '(?![\\p{L}\\p{N}_])' : ''}`, 'gu');
    result = result.replace(pattern, dictionary[phrase]);
  }
  return result;
}
export const translate = localize;

function visit(root) {
  if (root.nodeType === Node.TEXT_NODE) {
    if (root.parentElement?.closest('script,style,code,select option')) return;
    if (!textSources.has(root)) textSources.set(root, root.nodeValue);
    root.nodeValue = localize(textSources.get(root));
    return;
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (!node.parentElement || node.parentElement.closest('script,style,code,select option')) continue;
    if (!textSources.has(node)) textSources.set(node, node.nodeValue);
    node.nodeValue = localize(textSources.get(node));
  }
  const elements = root.nodeType === Node.ELEMENT_NODE ? [root, ...root.querySelectorAll('*')] : [...document.querySelectorAll('html [aria-label], html [title], html [placeholder]')];
  for (const element of elements) {
    if (element.matches('script,style,code,select option')) continue;
    for (const attribute of ['aria-label', 'title', 'placeholder']) {
      if (!element.hasAttribute(attribute)) continue;
      let sources = attributeSources.get(element);
      if (!sources) { sources = new Map(); attributeSources.set(element, sources); }
      if (!sources.has(attribute)) sources.set(attribute, element.getAttribute(attribute));
      element.setAttribute(attribute, localize(sources.get(attribute)));
    }
  }
}

function applyLanguage(language) {
  activeLanguage = languageCodes.includes(language) ? language : 'en';
  document.documentElement.lang = activeLanguage;
  const picker = document.getElementById('language-picker');
  if (picker) picker.value = activeLanguage;
  visit(document.body);
  try { localStorage.setItem('eco-language', activeLanguage); } catch { /* Language selection still works in private browsing. */ }
  document.dispatchEvent(new CustomEvent('eco-language-changed', { detail: { language: activeLanguage } }));
}

export function initLanguage() {
  let saved = 'en';
  try { saved = localStorage.getItem('eco-language') ?? 'en'; } catch { /* English is the first-visit default. */ }
  const picker = document.getElementById('language-picker');
  picker?.addEventListener('change', () => applyLanguage(picker.value));
  applyLanguage(saved);
  const observer = new MutationObserver(records => {
    for (const record of records) for (const node of record.addedNodes) if (node.nodeType === Node.ELEMENT_NODE || node.nodeType === Node.TEXT_NODE) visit(node);
  });
  observer.observe(document.body, { childList: true, subtree: true });
}
