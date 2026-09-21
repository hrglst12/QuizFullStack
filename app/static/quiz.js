"use strict";

// The quiz: pick a category -> answer questions -> see the score and the leaderboard.
// Talks to the FastAPI endpoints under /api; everything is drawn from `state` by render().

const root = document.getElementById("app");

const state = {
  view: "loading", // loading | categories | question | result | board
  categories: [],
  category: null,
  questions: [],
  pos: 0,
  score: 0,
  answers: [], // [{ question_id, choice }] sent to the server when the score is saved
  picked: null,
  result: null, // { correct, answer_index } once the current question is answered
  busy: false,
  board: [],
  player: stored.get("player"),
  saved: false,
  savedId: null,
  error: "",
};

async function api(path, options = {}) {
  const res = await send("/api" + path, { headers: { "Content-Type": "application/json" }, ...options });
  return res.json();
}

// ---------- actions ----------

async function home() {
  Object.assign(state, { view: "loading", error: "" });
  render();
  try {
    state.categories = await api("/categories");
  } catch (e) {
    state.error = e.message;
  }
  state.view = "categories";
  render();
}

async function start(category) {
  state.error = "";
  try {
    const questions = await api(`/categories/${category.id}/questions`);
    if (!questions.length) throw new Error("Bu kategoride henüz soru yok.");
    Object.assign(state, {
      view: "question", category, questions, pos: 0, score: 0, answers: [], picked: null, result: null,
      busy: false, board: [], saved: false, savedId: null,
    });
  } catch (e) {
    state.error = e.message;
  }
  render();
}

async function choose(index) {
  if (state.busy || state.result) return;
  const question = state.questions[state.pos];
  Object.assign(state, { busy: true, picked: index, error: "" });
  render();
  try {
    const result = await api(`/questions/${question.id}/answer`, { method: "POST", body: JSON.stringify({ choice: index }) });
    state.answers.push({ question_id: question.id, choice: index });
    if (result.correct) state.score++;
    state.result = result;
  } catch (e) {
    state.picked = null;
    state.error = e.message;
  }
  state.busy = false;
  render();
}

async function next() {
  if (!state.result || state.busy) return;
  if (state.pos + 1 < state.questions.length) {
    Object.assign(state, { pos: state.pos + 1, picked: null, result: null });
    render();
    return;
  }
  // Last question: fetch the leaderboard first so the result screen appears complete, in one go.
  state.busy = true;
  render();
  try {
    state.board = await api(`/categories/${state.category.id}/scores`);
  } catch (e) {
    state.board = [];
    state.error = e.message;
  }
  Object.assign(state, { busy: false, view: "result" });
  render();
}

async function saveScore(event) {
  event.preventDefault();
  const name = state.player.trim();
  if (!name || state.busy) return;
  Object.assign(state, { busy: true, error: "" });
  render();
  try {
    const entry = await api(`/categories/${state.category.id}/scores`, {
      method: "POST",
      body: JSON.stringify({ player_name: name, answers: state.answers }),
    });
    stored.set("player", name);
    state.savedId = entry.id;
    state.saved = true;
    state.board = await api(`/categories/${state.category.id}/scores`);
  } catch (e) {
    state.error = e.message;
  }
  state.busy = false;
  render();
}

async function showBoard(category) {
  state.error = "";
  try {
    state.board = await api(`/categories/${category.id}/scores`);
    Object.assign(state, { category, saved: false, savedId: null, view: "board" });
  } catch (e) {
    state.error = e.message;
  }
  render();
}

function leave() {
  const midQuiz = state.view === "question" && state.answers.length > 0;
  if (!midQuiz || confirm("Quiz yarıda kalsın mı? İlerlemen kaybolur.")) home();
}

// ---------- views ----------

const errorBox = () => (state.error ? h("p", { class: "error", role: "alert" }, state.error) : null);

function categoriesView() {
  const cards = state.categories.map((category) =>
    h("div", { class: "card" },
      h("button", { class: "card-main", disabled: !category.question_count, onclick: () => start(category) },
        h("span", { class: "card-name" }, category.name),
        h("span", { class: "card-meta" }, category.question_count ? `${category.question_count} soru` : "Henüz soru yok")),
      h("button", { class: "card-link", onclick: () => showBoard(category) }, "Skor tablosu")));

  let body;
  if (cards.length) body = h("div", { class: "grid" }, cards);
  else if (state.error) body = h("button", { class: "btn ghost", onclick: home }, "Tekrar dene");
  else body = h("p", { class: "muted" }, "Henüz kategori yok. Yönetim panelinden bir tane ekleyebilirsin.");

  return h("section", {},
    h("h1", {}, "Bir kategori seç"),
    h("p", { class: "lead" }, "Bir konu seç, soruları cevapla ve skorunu skor tablosuna yaz."),
    errorBox(),
    body);
}

function questionView() {
  const question = state.questions[state.pos];
  const total = state.questions.length;
  const { result } = state;
  const isLast = state.pos + 1 === total;

  const options = question.options.map((text, i) => {
    let mark = String.fromCharCode(65 + i);
    const classes = ["option"];
    if (result) {
      if (i === result.answer_index) { classes.push("correct"); mark = "✓"; }
      else if (i === state.picked) { classes.push("wrong"); mark = "✗"; }
      else classes.push("dim");
    } else if (i === state.picked) {
      classes.push("picked");
    }
    return h("button", { class: classes.join(" "), disabled: state.busy || Boolean(result), onclick: () => choose(i) },
      h("span", { class: "key" }, mark),
      h("span", {}, text));
  });

  return h("section", {},
    h("div", { class: "meta" },
      h("button", { class: "link", onclick: leave }, "← Kategoriler"),
      h("span", {}, `${state.category.name} · Soru ${state.pos + 1} / ${total}`)),
    h("div", { class: "track" }, h("div", { class: "fill", style: `width: ${(state.pos + (result ? 1 : 0)) / total * 100}%` })),
    h("h1", { class: "question" }, question.text),
    errorBox(),
    h("div", { class: "options" }, options),
    h("p", { class: `feedback ${result ? (result.correct ? "good" : "bad") : ""}`, role: "status" },
      result ? (result.correct ? "Doğru!" : "Yanlış.") : ""),
    result ? h("button", { class: "btn", id: "next", disabled: state.busy, onclick: next }, isLast ? "Sonucu gör" : "Sonraki soru") : null,
    result ? null : h("p", { class: "hint" }, "Klavye: A–D ile seç, Enter ile devam et."));
}

function resultView() {
  const total = state.questions.length;
  const percent = Math.round((state.score / total) * 100);
  const message = percent === 100 ? "Kusursuz." : percent >= 70 ? "Çok iyi." : percent >= 40 ? "Fena değil." : "Bir dahaki sefere.";
  const outsideTop = state.saved && !state.board.some((entry) => entry.id === state.savedId);

  const saveForm = h("form", { class: "row", onsubmit: saveScore },
    h("input", {
      type: "text", placeholder: "Adın", maxlength: "50", required: true, value: state.player,
      "aria-label": "Adın", autocomplete: "nickname", oninput: (e) => { state.player = e.target.value; },
    }),
    h("button", { class: "btn", disabled: state.busy }, "Skoru kaydet"));

  return h("section", {},
    h("p", { class: "eyebrow" }, state.category.name),
    h("p", { class: "score" }, String(state.score), h("small", {}, ` / ${total}`)),
    h("p", { class: "lead" }, message),
    errorBox(),
    state.saved
      ? h("p", { class: "notice" }, outsideTop ? "Skorun kaydedildi ama ilk 10'a girmedi." : "Skorun kaydedildi.")
      : saveForm,
    h("h2", {}, "Skor tablosu"),
    boardTable(),
    h("div", { class: "actions" },
      h("button", { class: "btn", onclick: () => start(state.category) }, "Tekrar oyna"),
      h("button", { class: "btn ghost", onclick: home }, "Kategoriler")));
}

function boardView() {
  return h("section", {},
    h("p", { class: "eyebrow" }, "Skor tablosu"),
    h("h1", {}, state.category.name),
    h("p", { class: "lead" }, "En yüksek yüzdeye sahip ilk 10 oyuncu."),
    errorBox(),
    boardTable(),
    h("div", { class: "actions" },
      h("button", { class: "btn", disabled: !state.category.question_count, onclick: () => start(state.category) }, "Oyna"),
      h("button", { class: "btn ghost", onclick: home }, "Kategoriler")));
}

function boardTable() {
  if (!state.board.length) return h("p", { class: "muted" }, "Bu kategoride henüz skor yok. İlk sen ol.");
  const rows = state.board.map((entry, i) =>
    h("tr", { class: entry.id === state.savedId ? "me" : "" },
      h("td", { class: "num" }, String(i + 1)),
      h("td", {}, entry.player_name),
      h("td", { class: "num" }, `${entry.score} / ${entry.total}`),
      h("td", { class: "num muted" }, `%${Math.round((entry.score / entry.total) * 100)}`),
      h("td", { class: "muted" }, formatDate(entry.created_at))));
  return h("div", { class: "table-scroll" },
    h("table", {},
      h("thead", {}, h("tr", {}, ["#", "Oyuncu", "Skor", "Oran", "Tarih"].map((title) => h("th", {}, title)))),
      h("tbody", {}, rows)));
}

const views = {
  loading: () => h("p", { class: "muted" }, "Yükleniyor…"),
  categories: categoriesView,
  question: questionView,
  result: resultView,
  board: boardView,
};

let shownKey = null;

function render() {
  const el = views[state.view]();
  // Fade in only when the screen actually changes, not on every click inside it.
  const key = state.view === "question" ? `question-${state.pos}` : state.view;
  if (key !== shownKey) {
    el.classList.add("enter");
    if (shownKey !== null) window.scrollTo(0, 0);
    shownKey = key;
  }
  root.replaceChildren(el);
  if (state.view === "question" && state.result) document.getElementById("next")?.focus({ preventScroll: true });
}

// A–D (or 1–4) pick an answer, Enter moves on.
document.addEventListener("keydown", (e) => {
  if (state.view !== "question" || e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.target.matches("input, textarea, select")) return;
  if (e.key.length === 1) {
    const index = /[1-9]/.test(e.key) ? Number(e.key) - 1 : e.key.toLowerCase().charCodeAt(0) - 97;
    if (index >= 0 && index < state.questions[state.pos].options.length) choose(index);
  } else if (e.key === "Enter" && state.result && e.target.tagName !== "BUTTON") {
    next();
  }
});

home();
