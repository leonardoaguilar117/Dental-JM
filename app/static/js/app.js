// Consultorio Dental JM · interacciones
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---- Menú móvil (cajón) ----
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-menu]")) { document.body.classList.toggle("nav-open"); return; }
  if (document.body.classList.contains("nav-open") && !e.target.closest(".sidebar")) document.body.classList.remove("nav-open");
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") document.body.classList.remove("nav-open"); });

// ---- Toasts: se cierran solos a los 6 s (pausa al pasar el cursor) ----
function initToasts() {
  document.querySelectorAll(".flash").forEach((t) => {
    let left = 6000, start = Date.now(), timer;
    const close = () => { t.classList.add("hide"); setTimeout(() => t.remove(), 320); };
    const run = () => { start = Date.now(); timer = setTimeout(close, left); };
    t.addEventListener("mouseenter", () => { clearTimeout(timer); left -= Date.now() - start; });
    t.addEventListener("mouseleave", run);
    t.querySelector("[data-dismiss]")?.addEventListener("click", close);
    run();
  });
}

// ---- Pestañas con subrayado que se desliza ----
function initTabs() {
  const bar = document.querySelector(".tabs");
  const tabs = document.querySelectorAll("[data-tab]");
  if (!bar || !tabs.length) return;
  const ink = document.createElement("span");
  ink.className = "ink";
  bar.appendChild(ink);
  const moveInk = (el) => {
    if (!el || !bar.contains(el)) return;
    ink.style.transform = `translateX(${el.offsetLeft}px) scaleX(${el.offsetWidth})`;
  };
  const show = (id) => {
    let found = null;
    tabs.forEach((t) => {
      const on = t.dataset.tab === id;
      t.classList.toggle("active", on);
      if (on && bar.contains(t)) found = t;
    });
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + id));
    if (found) { moveInk(found); found.scrollIntoView({ block: "nearest", inline: "nearest" }); }
    return !!found;
  };
  tabs.forEach((t) => t.addEventListener("click", (e) => {
    e.preventDefault(); show(t.dataset.tab); history.replaceState(null, "", "#" + t.dataset.tab);
  }));
  ink.style.transition = "none";
  const initial = location.hash.slice(1);
  if (!initial || !show(initial)) show(tabs[0].dataset.tab);
  requestAnimationFrame(() => (ink.style.transition = ""));
  window.addEventListener("resize", () => moveInk(bar.querySelector("[data-tab].active")));
}

// ---- Odontograma interactivo ----
const DARK_STATES = ["caries", "endodoncia", "extraer", "bracket", "obturado"];
function initOdontogram() { document.querySelectorAll("[data-odonto]").forEach(setupOdontogram); }
function setupOdontogram(root) {
  const readonly = root.classList.contains("readonly");
  const input = readonly ? null : document.getElementById("odontograma_json");
  const states = JSON.parse(root.dataset.states);
  let data = {};
  try { data = JSON.parse(input ? input.value : root.dataset.value || "{}"); } catch (_) {}
  let current = "caries";
  const palette = root.nextElementSibling;
  const paint = (el) => {
    const st = data[el.dataset.tooth] || "sano";
    const [label, color] = states[st];
    el.style.background = color;
    el.title = `${el.dataset.tooth}: ${label}`;
    el.setAttribute("aria-label", `Pieza ${el.dataset.tooth}: ${label}`);
    el.classList.toggle("dark", DARK_STATES.includes(st));
  };
  root.querySelectorAll(".tooth").forEach((el) => {
    paint(el);
    if (readonly) return;
    el.tabIndex = 0;
    el.setAttribute("role", "button");
    const toggle = () => {
      const k = el.dataset.tooth;
      if (data[k] === current || current === "sano") delete data[k]; else data[k] = current;
      paint(el);
      el.classList.remove("pop"); void el.offsetWidth; el.classList.add("pop");
      if (input) input.value = JSON.stringify(data);
    };
    el.addEventListener("click", toggle);
    el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
  });
  if (readonly || !palette) return;
  palette.querySelectorAll("button").forEach((b) => {
    if (b.dataset.state === current) b.classList.add("active");
    b.addEventListener("click", (e) => {
      e.preventDefault();
      current = b.dataset.state;
      palette.querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
    });
  });
}

// ---- Cifras que cuentan hasta su valor (solo al cargar el tablero) ----
function initCounters() {
  const els = document.querySelectorAll("[data-count]");
  if (!els.length || reduceMotion) return;
  const fmt = (v, money) => (money ? (v < 0 ? "-$" : "$") : "") + Math.round(Math.abs(v)).toLocaleString("es-MX");
  els.forEach((el) => {
    const target = parseFloat(el.dataset.count);
    const money = el.dataset.money !== undefined;
    if (!isFinite(target)) return;
    const final = el.textContent;
    const t0 = performance.now(), dur = 650;
    const step = (now) => {
      const p = Math.min(1, (now - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(target * eased, money);
      if (p < 1) requestAnimationFrame(step); else el.textContent = final;
    };
    requestAnimationFrame(step);
  });
}

// ---- Copiar al portapapeles ----
document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-copy]");
  if (!b) return;
  const target = document.querySelector(b.dataset.copy);
  try { await navigator.clipboard.writeText(target.value || target.textContent); b.textContent = "¡Copiado!"; }
  catch (_) { target.select && target.select(); }
  setTimeout(() => (b.textContent = "Copiar"), 1600);
});

// ---- Confirmaciones ----
document.addEventListener("submit", (e) => {
  const msg = e.target.dataset.confirm;
  if (msg && !confirm(msg)) e.preventDefault();
});

// ---- Al abrir WhatsApp desde un aviso, marcarlo como enviado ----
document.addEventListener("click", (e) => {
  const a = e.target.closest("[data-mark-sent]");
  if (!a) return;
  const form = document.getElementById(a.dataset.markSent);
  if (form) setTimeout(() => form.submit(), 400);
});

// ---- Temas: crossfade de toda la página con View Transitions ----
function initThemePicker() {
  document.querySelectorAll("[data-theme-pick]").forEach((pick) => {
    const btn = pick.querySelector(".theme-btn");
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = pick.classList.toggle("open");
      btn.setAttribute("aria-expanded", open);
    });
    pick.querySelectorAll("[data-set-theme]").forEach((opt) => opt.addEventListener("click", () => {
      const key = opt.dataset.setTheme;
      pick.classList.remove("open");
      applyTheme(key, opt);
    }));
  });
  document.addEventListener("click", () => document.querySelectorAll("[data-theme-pick].open").forEach((p) => p.classList.remove("open")));
}
function applyTheme(key, opt) {
  document.cookie = `jm_theme=${key}; path=/; max-age=31536000; samesite=lax`;
  const swap = () => {
    document.documentElement.dataset.theme = key;
    document.querySelectorAll("[data-set-theme]").forEach((o) => o.setAttribute("aria-checked", o.dataset.setTheme === key));
    document.querySelectorAll(".theme-btn").forEach((b) => {
      const chips = opt.querySelectorAll(".chips i");
      b.querySelectorAll(".dots i").forEach((d, i) => (d.style.background = chips[i]?.style.background));
      const lbl = b.querySelector(".lbl"); if (lbl) lbl.textContent = opt.querySelector(".tname").firstChild.textContent.trim();
    });
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = getComputedStyle(document.documentElement).getPropertyValue("--frame").trim();
    window.dispatchEvent(new CustomEvent("themechange", { detail: key }));
  };
  if (document.startViewTransition && !reduceMotion) document.startViewTransition(swap);
  else swap();
}
// Lee un color del tema actual (para Chart.js y Three.js)
window.themeColor = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// ---- Dock con magnificación (estilo macOS) ----
function initDock() {
  const dock = document.querySelector("[data-dock]");
  if (!dock || reduceMotion || !matchMedia("(hover: hover) and (pointer: fine) and (min-width: 901px)").matches) return;
  const tiles = [...dock.querySelectorAll(".dock-item .tile")];
  const RANGE = 120, MAX = 0.32;
  let raf = 0, y = null;
  const update = () => {
    raf = 0;
    tiles.forEach((t) => {
      if (y === null) { t.style.setProperty("--mag", 1); return; }
      const r = t.getBoundingClientRect();
      const d = Math.abs(y - (r.top + r.height / 2));
      const k = Math.max(0, 1 - d / RANGE);
      t.style.setProperty("--mag", (1 + MAX * k * k).toFixed(3));
    });
  };
  dock.addEventListener("mousemove", (e) => { y = e.clientY; if (!raf) raf = requestAnimationFrame(update); });
  dock.addEventListener("mouseleave", () => { y = null; if (!raf) raf = requestAnimationFrame(update); });
}

document.addEventListener("DOMContentLoaded", () => { initToasts(); initTabs(); initOdontogram(); initCounters(); initThemePicker(); initDock(); });
