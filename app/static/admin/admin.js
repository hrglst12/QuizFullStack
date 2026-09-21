"use strict";

// Admin panel: log in, then manage categories, questions and users through the /api/admin endpoints.

const root = document.getElementById("app");

const state = {
  token: stored.get("token"),
  tab: "categories", // categories | questions | users
  categories: [],
  questions: [],
  users: [],
  filter: "", // category id the question list is narrowed to
  editing: null, // the item currently loaded into the form of the active tab
  error: "",
  notice: "",
};

const TABS = { categories: "Kategoriler", questions: "Sorular", users: "Kullanıcılar" };

// Thrown after a 401 has already sent the user back to the login screen; nothing more to show.
class SessionEnded extends Error {}

async function api(path, { method = "GET", body } = {}) {
  try {
    const res = await send("/api" + path, {
      method,
      body: body === undefined ? undefined : JSON.stringify(body),
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${state.token}` },
    });
    return res.status === 204 ? null : await res.json();
  } catch (e) {
    if (e.status === 401) {
      logout("Oturum süresi doldu, lütfen tekrar giriş yap.");
      throw new SessionEnded();
    }
    throw e;
  }
}

// ---------- actions ----------

async function login(event) {
  event.preventDefault();
  const form = event.target.elements;
  state.error = "";
  try {
    const res = await send("/api/admin/login", {
      method: "POST",
      body: new URLSearchParams({ username: form.username.value, password: form.password.value }),
    });
    state.token = (await res.json()).access_token;
    stored.set("token", state.token);
    await loadAll();
  } catch (e) {
    if (!(e instanceof SessionEnded)) {
      state.error = e.message;
      showMessages(); // not render(): that would wipe what was typed into the form
    }
    return;
  }
  render();
}

function logout(message = "") {
  stored.remove("token");
  Object.assign(state, { token: "", editing: null, error: message, notice: "" });
  render();
}

async function loadAll() {
  const query = state.filter ? `?category_id=${state.filter}` : "";
  [state.categories, state.questions, state.users] = await Promise.all([
    api("/categories"), api(`/admin/questions${query}`), api("/admin/users"),
  ]);
}

// Runs a change, reloads the lists, and shows either the notice or the error the API gave.
async function run(action, notice = "") {
  Object.assign(state, { error: "", notice: "" });
  showMessages();
  try {
    await action();
    state.editing = null;
    await loadAll();
    state.notice = notice;
  } catch (e) {
    if (!(e instanceof SessionEnded)) {
      state.error = e.message;
      showMessages(); // the form keeps everything the user typed, so they can fix it and resubmit
    }
    return;
  }
  render();
}

function switchTab(tab) {
  Object.assign(state, { tab, editing: null, error: "", notice: "" });
  render();
}

function edit(item) {
  Object.assign(state, { editing: item, error: "", notice: "" });
  render();
  window.scrollTo(0, 0);
}

function remove(path, warning) {
  if (confirm(warning)) run(() => api(path, { method: "DELETE" }), "Silindi.");
}

// ---------- shared view pieces ----------

const banner = () => [
  state.error ? h("p", { class: "error", role: "alert" }, state.error) : null,
  state.notice ? h("p", { class: "notice", role: "status" }, state.notice) : null,
];

const messages = () => h("div", { id: "messages" }, banner());

// Updates only the message area, leaving forms (and whatever is typed in them) untouched.
const showMessages = () => document.getElementById("messages")?.replaceChildren(...banner().filter(Boolean));

const cancelButton = () =>
  state.editing ? h("button", { type: "button", class: "btn ghost", onclick: () => edit(null) }, "Vazgeç") : null;

const rowActions = (onEdit, onDelete) =>
  h("td", { class: "end" },
    h("button", { class: "link", onclick: onEdit }, "Düzenle"),
    h("button", { class: "link danger", onclick: onDelete }, "Sil"));

const table = (headers, rows) =>
  h("div", { class: "table-scroll" },
    h("table", {},
      h("thead", {}, h("tr", {}, headers.map((title, i) => h("th", { class: i === headers.length - 1 ? "end" : "" }, title)))),
      h("tbody", {}, rows)));

// ---------- categories ----------

function categoriesPanel() {
  const item = state.editing;
  const form = h("form", {
    class: "row",
    onsubmit: (e) => {
      e.preventDefault();
      const body = { name: e.target.elements.name.value };
      run(() => api(item ? `/admin/categories/${item.id}` : "/admin/categories", { method: item ? "PUT" : "POST", body }),
        item ? "Kategori güncellendi." : "Kategori eklendi.");
    },
  },
    h("input", { name: "name", type: "text", placeholder: "Kategori adı", maxlength: "100", required: true, value: item?.name ?? "", "aria-label": "Kategori adı" }),
    h("button", { class: "btn" }, item ? "Güncelle" : "Ekle"),
    cancelButton());

  const rows = state.categories.map((category) =>
    h("tr", {},
      h("td", {}, category.name),
      h("td", { class: "num muted" }, `${category.question_count} soru`),
      rowActions(() => edit(category),
        () => remove(`/admin/categories/${category.id}`, `"${category.name}" silinsin mi? Kategorideki sorular ve skorlar da silinir.`))));

  return [
    h("div", { class: "panel" }, h("h3", {}, item ? "Kategoriyi düzenle" : "Yeni kategori"), form),
    state.categories.length ? table(["Ad", "Sorular", ""], rows) : h("p", { class: "muted" }, "Henüz kategori yok."),
  ];
}

// ---------- questions ----------

function questionForm() {
  const item = state.editing;
  const draft = item ?? { category_id: state.filter, text: "", options: ["", "", "", ""], answer_index: 0 };

  const category = h("select", { name: "category", required: true, "aria-label": "Kategori" },
    h("option", { value: "", disabled: true, selected: !draft.category_id }, "Kategori seç"),
    state.categories.map((c) => h("option", { value: String(c.id), selected: c.id === Number(draft.category_id) }, c.name)));
  const text = h("input", { type: "text", placeholder: "Soru", required: true, value: draft.text, "aria-label": "Soru" });

  // Option rows are plain DOM; the correct answer is whichever row's radio is checked when the form is sent.
  const list = h("div", { class: "opts" });
  const addButton = h("button", { type: "button", class: "btn ghost", onclick: () => addRow() }, "+ Seçenek ekle");
  const refresh = () => { addButton.disabled = list.children.length >= 6; };
  const addRow = (value = "", checked = false) => {
    const row = h("div", { class: "opt-row" },
      h("input", { type: "radio", name: "correct", checked, "aria-label": "Doğru cevap", title: "Doğru cevap" }),
      h("input", { type: "text", placeholder: "Seçenek", required: true, value, "aria-label": "Seçenek" }),
      h("button", {
        type: "button", class: "icon", "aria-label": "Seçeneği kaldır",
        onclick: () => {
          if (list.children.length <= 2) return;
          const wasCorrect = row.querySelector("[type=radio]").checked;
          row.remove();
          if (wasCorrect) list.querySelector("[type=radio]").checked = true;
          refresh();
        },
      }, "×"));
    list.append(row);
    refresh();
  };
  draft.options.forEach((option, i) => addRow(option, i === draft.answer_index));

  return h("form", {
    class: "stack",
    onsubmit: (e) => {
      e.preventDefault();
      const rows = [...list.children];
      const body = {
        category_id: Number(category.value),
        text: text.value,
        options: rows.map((row) => row.querySelector("[type=text]").value),
        answer_index: rows.findIndex((row) => row.querySelector("[type=radio]").checked),
      };
      run(() => api(item ? `/admin/questions/${item.id}` : "/admin/questions", { method: item ? "PUT" : "POST", body }),
        item ? "Soru güncellendi." : "Soru eklendi.");
    },
  },
    category, text, list,
    h("p", { class: "muted small" }, "Doğru cevabı soldaki yuvarlak düğmeyle işaretle. En az 2, en fazla 6 seçenek olabilir."),
    h("div", { class: "row" }, addButton, h("button", { class: "btn" }, item ? "Güncelle" : "Ekle"), cancelButton()));
}

function questionsPanel() {
  const name = (id) => state.categories.find((c) => c.id === id)?.name ?? "—";
  const filter = h("select", {
    "aria-label": "Kategoriye göre filtrele",
    onchange: (e) => { state.filter = e.target.value; run(() => Promise.resolve()); },
  },
    h("option", { value: "" }, "Tüm kategoriler"),
    state.categories.map((c) => h("option", { value: String(c.id), selected: String(c.id) === state.filter }, c.name)));

  const rows = state.questions.map((question) =>
    h("tr", {},
      h("td", {},
        h("div", {}, question.text),
        h("div", { class: "muted small" }, `${name(question.category_id)} · Doğru: ${question.options[question.answer_index]}`)),
      rowActions(() => edit(question), () => remove(`/admin/questions/${question.id}`, "Bu soru silinsin mi?"))));

  return [
    h("div", { class: "panel" }, h("h3", {}, state.editing ? "Soruyu düzenle" : "Yeni soru"), questionForm()),
    h("div", { class: "toolbar" }, h("span", { class: "muted" }, `${state.questions.length} soru`), filter),
    state.questions.length ? table(["Soru", ""], rows) : h("p", { class: "muted" }, "Soru bulunamadı."),
  ];
}

// ---------- users ----------

function usersPanel() {
  const item = state.editing;
  const form = h("form", {
    class: "row",
    onsubmit: (e) => {
      e.preventDefault();
      const { username, password } = e.target.elements;
      const body = { username: username.value };
      if (password.value) body.password = password.value; // left out on edit = keep the current password
      run(() => api(item ? `/admin/users/${item.id}` : "/admin/users", { method: item ? "PUT" : "POST", body }),
        item ? "Kullanıcı güncellendi." : "Kullanıcı eklendi.");
    },
  },
    h("input", { name: "username", type: "text", placeholder: "Kullanıcı adı", maxlength: "50", required: true, value: item?.username ?? "", autocomplete: "off", "aria-label": "Kullanıcı adı" }),
    h("input", {
      name: "password", type: "password", minlength: "8", maxlength: "128", required: !item, autocomplete: "new-password",
      placeholder: item ? "Yeni şifre (boşsa değişmez)" : "Şifre (en az 8 karakter)", "aria-label": "Şifre",
    }),
    h("button", { class: "btn" }, item ? "Güncelle" : "Ekle"),
    cancelButton());

  const rows = state.users.map((user) =>
    h("tr", {},
      h("td", {}, user.username),
      h("td", { class: "muted" }, formatDate(user.created_at)),
      rowActions(() => edit(user), () => remove(`/admin/users/${user.id}`, `"${user.username}" kullanıcısı silinsin mi?`))));

  return [
    h("div", { class: "panel" }, h("h3", {}, item ? "Kullanıcıyı düzenle" : "Yeni kullanıcı"), form),
    table(["Kullanıcı", "Oluşturulma", ""], rows),
  ];
}

// ---------- screens ----------

function loginView() {
  return h("section", { class: "login" },
    h("h1", {}, "Yönetim"),
    messages(),
    h("form", { class: "stack", onsubmit: login },
      h("input", { name: "username", type: "text", placeholder: "Kullanıcı adı", required: true, autocomplete: "username", "aria-label": "Kullanıcı adı" }),
      h("input", { name: "password", type: "password", placeholder: "Şifre", required: true, autocomplete: "current-password", "aria-label": "Şifre" }),
      h("button", { class: "btn" }, "Giriş yap")));
}

function dashboardView() {
  const panels = { categories: categoriesPanel, questions: questionsPanel, users: usersPanel };
  return h("section", {},
    h("div", { class: "dash-head" },
      h("h1", {}, "Yönetim"),
      h("button", { class: "btn ghost", onclick: () => logout() }, "Çıkış yap")),
    h("div", { class: "tabs" },
      Object.entries(TABS).map(([id, title]) =>
        h("button", { class: "tab", "aria-current": state.tab === id ? "page" : null, onclick: () => switchTab(id) }, title))),
    messages(),
    panels[state.tab]());
}

let shown = null;

function render() {
  const view = state.token ? "dashboard" : "login";
  const el = view === "dashboard" ? dashboardView() : loginView();
  if (view !== shown) {
    el.classList.add("enter");
    shown = view;
  }
  root.replaceChildren(el);
}

async function init() {
  if (state.token) {
    try {
      await loadAll();
    } catch (e) {
      if (!(e instanceof SessionEnded)) state.error = e.message;
    }
  }
  render();
}

init();
