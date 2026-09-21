"use strict";

// Tiny helpers shared by the quiz and the admin panel.

// h("button", { class: "btn", onclick: fn }, "Text") builds a DOM element. Text goes in as text nodes,
// never as HTML, so names and questions typed by users can't inject markup.
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (name.startsWith("on")) el.addEventListener(name.slice(2), value);
    else el.setAttribute(name, value === true ? "" : value);
  }
  el.append(...children.flat().filter((child) => child != null && child !== false));
  return el;
}

const stored = {
  get(key) {
    try { return localStorage.getItem(key) || ""; } catch { return ""; }
  },
  set(key, value) {
    try { localStorage.setItem(key, value); } catch { /* storage unavailable: nothing to remember */ }
  },
  remove(key) {
    try { localStorage.removeItem(key); } catch { /* same */ }
  },
};

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" });
}

// fetch() that turns a network failure or an API error into an Error carrying a readable message.
async function send(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new Error("Sunucuya ulaşılamadı. Bağlantını kontrol edip tekrar dene.");
  }
  if (!res.ok) {
    let message = `Bir hata oluştu (${res.status}).`;
    try {
      const { detail } = await res.json();
      message = typeof detail === "string" ? detail : detail.map((e) => e.msg).join("; ");
    } catch { /* keep the generic message */ }
    const error = new Error(message);
    error.status = res.status;
    throw error;
  }
  return res;
}
