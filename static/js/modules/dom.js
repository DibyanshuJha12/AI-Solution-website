export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

export function onReady(callback) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", callback, { once: true });
    return;
  }
  callback();
}

export function csrfToken() {
  return $('meta[name="csrf-token"]')?.content || "";
}

export function safeJsonParse(value, fallback) {
  try {
    return JSON.parse(value);
  } catch (error) {
    return fallback;
  }
}

export function setToneText(node, text, tone = "neutral") {
  if (!node) return;
  node.textContent = text;
  node.dataset.tone = tone;
}
