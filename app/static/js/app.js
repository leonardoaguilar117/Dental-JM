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
  // por defecto, la primera pestaña de la barra (no un enlace a pestaña que esté antes en la página)
  if (!initial || !show(initial)) show((bar.querySelector("[data-tab]") || tabs[0]).dataset.tab);
  requestAnimationFrame(() => (ink.style.transition = ""));
  window.addEventListener("resize", () => moveInk(bar.querySelector("[data-tab].active")));
}

// ---- Odontograma interactivo ----
const DARK_STATES = ["caries", "endodoncia", "extraer", "extraido", "bracket", "obturado"];
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

// ---- Móvil: hoja "Más" con las secciones que no caben en la barra ----
function setMore(open) {
  document.body.classList.toggle("more-open", open);
  document.querySelectorAll("[data-more]").forEach((b) => b.setAttribute("aria-expanded", open));
}
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-more]")) { setMore(!document.body.classList.contains("more-open")); return; }
  if (document.body.classList.contains("more-open") && (e.target.matches("[data-more-sheet]") || e.target.closest(".more-item, .more-user"))) setMore(false);
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") setMore(false); });

// ---- Hoja de cobro: elegir qué paga, cuánto y cómo; muestra lo que quedará a deber ----
function initCharge() {
  const dlg = document.querySelector("[data-charge]");
  if (!dlg) return;
  const fmt = (n) => n.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
  const form = dlg.querySelector("[data-charge-form]");
  const amount = form.querySelector("[data-amount]");
  const after = form.querySelector("[data-after]");
  const submit = form.querySelector("[data-charge-submit] span");
  const concept = form.querySelector("[data-concept]");
  const quick = form.querySelector("[data-quick]");
  const picked = () => form.querySelector('input[name="treatment_id"]:checked');
  const balance = () => { const r = picked(); return r && r.dataset.balance ? Number(r.dataset.balance) : null; };

  const update = () => {
    const b = balance(), a = Number(amount.value) || 0;
    concept.hidden = b !== null;
    concept.querySelector("input").required = b === null;
    if (b !== null) amount.max = b; else amount.removeAttribute("max");
    quick.querySelectorAll("button").forEach((q) => {
      const v = q.dataset.q;
      q.hidden = b === null ? (v === "all" || v === "half") : (Number(v) >= b);
      const val = v === "all" ? b : v === "half" ? (b === null ? null : Math.round(b / 2 * 100) / 100) : Number(v);
      q.classList.toggle("active", a > 0 && val === a);
    });
    submit.textContent = a ? `Cobrar ${fmt(a)}` : "Cobrar";
    after.className = "charge-after";
    if (b === null) { after.textContent = a ? "Se registra como pagado en el expediente." : ""; return; }
    const rest = Math.round((b - a) * 100) / 100;
    if (!a) { after.textContent = `Debe ${fmt(b)}`; }
    else if (rest < 0) { after.textContent = `Excede lo que debe por ${fmt(-rest)}`; after.classList.add("over"); }
    else if (rest === 0) { after.textContent = "Queda liquidado"; after.classList.add("ok"); }
    else { after.textContent = `Después de este pago quedará a deber ${fmt(rest)}`; after.classList.add("owe"); }
  };

  const open = (tid, fill) => {
    if (tid) { const r = form.querySelector(`input[name="treatment_id"][value="${tid}"]`); if (r) r.checked = true; }
    amount.value = fill === "all" && balance() !== null ? balance() : "";
    update();
    dlg.showModal();
    if (!amount.value) amount.focus();
  };

  form.addEventListener("change", (e) => { if (e.target.name === "treatment_id") amount.value = ""; update(); });
  amount.addEventListener("input", update);
  quick.addEventListener("click", (e) => {
    const q = e.target.closest("button"); if (!q) return;
    const b = balance();
    amount.value = q.dataset.q === "all" ? b : q.dataset.q === "half" ? Math.round(b / 2 * 100) / 100 : q.dataset.q;
    update();
  });
  form.addEventListener("submit", (e) => {
    const b = balance(), a = Number(amount.value) || 0;
    if (b !== null && a > b + 0.01) { e.preventDefault(); amount.focus(); return; }
    form.querySelector("[data-charge-submit]").disabled = true;
  });
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-charge-open]");
    if (b) { e.preventDefault(); open(b.dataset.tid, b.dataset.fill); }
    if (e.target.closest("[data-charge-close]") || e.target === dlg) dlg.close();
  });

  // ?cobrar=1 abre la hoja; ?cobrar=<id> la abre con ese tratamiento y su saldo
  const url = new URL(location.href), c = url.searchParams.get("cobrar");
  const clean = (k) => { url.searchParams.delete(k); history.replaceState(null, "", url.pathname + url.search + url.hash); };
  if (c) { clean("cobrar"); open(c !== "1" ? c : null, c !== "1" ? "all" : null); }
  else if (url.searchParams.has("recibo")) clean("recibo");
}

// ---- Entrada al depósito: muestra el egreso que se registrará ----
function initBuy() {
  const fmt = (n) => n.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
  document.querySelectorAll("[data-buy-form]").forEach((form) => {
    const chk = form.querySelector("[data-buy]"), out = form.querySelector("[data-buy-total]"), meth = form.querySelector("[data-buy-method]");
    const qty = form.querySelector('[name="quantity"], [name="initial_qty"]'), cost = form.querySelector('[name="unit_cost"], [name="cost_price"]');
    const upd = () => {
      const v = (Number(qty.value) || 0) * (Number(cost.value) || 0);
      out.textContent = chk.checked && v ? `(${fmt(v)})` : "";
      meth.hidden = !chk.checked;
    };
    form.addEventListener("input", upd); upd();
  });
}

// ---- Foto del doctor: se recorta en cuadro y se reduce antes de subirla ----
function initPhoto() {
  document.querySelectorAll("[data-photo]").forEach((form) => {
    const input = form.querySelector("[data-photo-input]");
    input?.addEventListener("change", () => {
      const file = input.files?.[0];
      if (!file) return;
      const img = new Image();
      img.onload = () => {
        const S = 320, side = Math.min(img.naturalWidth, img.naturalHeight);
        const c = document.createElement("canvas");
        c.width = c.height = S;
        const ctx = c.getContext("2d");
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(img, (img.naturalWidth - side) / 2, (img.naturalHeight - side) / 2, side, side, 0, 0, S, S);
        form.querySelector('input[name="foto"]').value = c.toDataURL("image/jpeg", 0.86);
        URL.revokeObjectURL(img.src);
        form.classList.add("busy");
        form.submit();
      };
      img.onerror = () => alert("No se pudo leer la imagen. Prueba con una foto JPG o PNG.");
      img.src = URL.createObjectURL(file);
    });
  });
  document.querySelectorAll("[data-show-pass]").forEach((cb) => cb.addEventListener("change", () => {
    cb.closest("form").querySelectorAll('input[type="password"], input[data-was-pass]').forEach((i) => {
      i.dataset.wasPass = "1";
      i.type = cb.checked ? "text" : "password";
    });
  }));
}

// ---- Firma en pantalla (consentimiento informado) ----
function initSignature() {
  document.querySelectorAll("[data-signature]").forEach((form) => {
    const canvas = form.querySelector("canvas");
    const ctx = canvas.getContext("2d");
    const save = form.querySelector("[data-sig-save]");
    let drawing = false, dirty = false, last = null;
    const ink = () => getComputedStyle(document.documentElement).getPropertyValue("--text").trim() || "#1c2030";
    function size() {
      // el lienzo se dimensiona a su caja real × densidad de pantalla (trazo nítido en móvil)
      const r = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
      if (!r.width) return;
      canvas.width = r.width * dpr; canvas.height = r.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.lineCap = ctx.lineJoin = "round"; ctx.lineWidth = 2.4; ctx.strokeStyle = ink();
      dirty = false; save.disabled = true;
    }
    const pos = (e) => { const r = canvas.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
    canvas.addEventListener("pointerdown", (e) => {
      drawing = true; last = pos(e); canvas.setPointerCapture(e.pointerId);
      ctx.beginPath(); ctx.arc(last.x, last.y, ctx.lineWidth / 2, 0, Math.PI * 2); ctx.fillStyle = ctx.strokeStyle; ctx.fill();
    });
    canvas.addEventListener("pointermove", (e) => {
      if (!drawing) return;
      const p = pos(e);
      ctx.beginPath(); ctx.moveTo(last.x, last.y); ctx.lineTo(p.x, p.y); ctx.stroke();
      last = p;
      if (!dirty) { dirty = true; save.disabled = false; form.classList.add("signed"); }
    });
    const stop = () => { drawing = false; };
    canvas.addEventListener("pointerup", stop);
    canvas.addEventListener("pointercancel", stop);
    form.querySelector("[data-sig-clear]").addEventListener("click", () => { size(); form.classList.remove("signed"); });
    form.addEventListener("submit", (e) => {
      if (!dirty) { e.preventDefault(); return; }
      // se guarda con trazo oscuro sobre fondo transparente: legible al imprimir con cualquier tema
      const out = document.createElement("canvas");
      out.width = canvas.width; out.height = canvas.height;
      const o = out.getContext("2d");
      o.drawImage(canvas, 0, 0);
      o.globalCompositeOperation = "source-in"; o.fillStyle = "#1c2030"; o.fillRect(0, 0, out.width, out.height);
      form.querySelector('input[name="firma"]').value = out.toDataURL("image/png");
    });
    // la pestaña puede estar oculta al cargar: se dimensiona cuando el recuadro se vuelve visible
    new ResizeObserver(() => { if (!dirty) size(); }).observe(canvas);
  });
}

// enlaces que abren una pestaña y bajan a una sección (p.ej. "Falta consentimiento")
document.addEventListener("click", (e) => {
  const a = e.target.closest("[data-scroll]");
  if (a) setTimeout(() => document.querySelector(a.dataset.scroll)?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
});

document.addEventListener("DOMContentLoaded", () => { initToasts(); initTabs(); initOdontogram(); initCounters(); initThemePicker(); initDock(); initSignature(); initCharge(); initBuy(); initPhoto(); });
