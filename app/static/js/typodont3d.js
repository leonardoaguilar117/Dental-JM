// Tipodonto 3D generado desde el odontograma del paciente.
// - Modelo tipo laboratorio: encía esculpida en herradura (no un tubo), coronas de esmalte, brackets redondeados.
// - Extracciones: "Por extraer" lleva una X roja y collar; "Extraído" deja el alvéolo vacío con su silueta punteada.
// - Encía: se enrojece si la historia clínica marca gingivitis, periodontitis u otra inflamación.
// - Legibilidad: número FDI sobre cada pieza con hallazgo (o sobre todas con "Números"), collar de color en el
//   cuello de la pieza afectada y ficha de la pieza seleccionada.
// - Navegación: girar (arrastrar), desplazar (clic derecho / dos dedos / Mayús+arrastrar), acercar (rueda o pellizco,
//   hacia el cursor), vistas rápidas, control de apertura de la boca y atajos de teclado.
// Uso: <div class="scene" data-typodont data-view="cerrada|abierta" data-odonto='{...}' data-states='{...}'>
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { createStage, enamelMaterial, toothGeometry, toothKind, QUADRANT, css, reduceMotion, hasWebGL } from "./dental3d.js";

const ORDER = [1, 2, 3, 4, 5, 6, 7, 8];
const WIDTH = { 1: 0.86, 2: 0.74, 3: 0.8, 4: 0.76, 5: 0.76, 6: 1.08, 7: 1.02, 8: 0.96 };
const KIND_NAME = { 1: "Incisivo central", 2: "Incisivo lateral", 3: "Canino", 4: "1er premolar", 5: "2º premolar", 6: "1er molar", 7: "2º molar", 8: "3er molar" };
const FACE_Z = { incisivo: 0.25, canino: 0.36, premolar: 0.46, molar: 0.55 };
const OCCLUSAL_Y = { premolar: 0.84, molar: 0.75 };  // altura del centro de la cara oclusal (perfil × escala)
const ARCH = { up: { A: 2.75, B: 2.35, y: 0.92 }, low: { A: 2.55, B: 2.15, y: -0.92 } };
const PHI0 = 0.04, PHI_SPAN = 1.5;          // reparto de las piezas a lo largo de la arcada
const MAX_OPEN = { up: -0.62, low: 0.3 };   // apertura máxima de cada arcada (rad)

const TARGET = [0, 0.1, 0.6];
// vistas rápidas: posición de cámara, punto observado y apertura de la boca (0 = cerrada, 1 = abierta)
const PRESETS = {
  cerrada: { cam: [-4.2, 1.6, 10.6], target: TARGET, open: 0 },
  abierta: { cam: [0, 0.6, 12.4], target: [0, 0.35, 0.9], open: 1 },
  frente: { cam: [0, 0.5, 11], target: TARGET },
  superior: { cam: [0, -9.4, 4.2], target: [0, 0.9, 0.3], open: 1, only: "up" },   // caras oclusales de arriba
  inferior: { cam: [0, 9.4, 4.6], target: [0, -0.9, 0.3], open: 1, only: "low" },  // caras oclusales de abajo
  izq: { cam: [10.8, 0.9, 1.8], target: [0, 0, 0.3] },                  // lado izquierdo del paciente
  der: { cam: [-10.8, 0.9, 1.8], target: [0, 0, 0.3] },
};
const INFLAMED = ["Gingivitis", "Periodontitis", "Hiperplasia gingival", "Absceso periodontal", "Pericoronitis", "Sangrado al sondeo"];
const PRESET_BUTTONS = [["frente", "Frente"], ["superior", "Arriba"], ["inferior", "Abajo"], ["der", "Der."], ["izq", "Izq."]];

const SVG = {
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
  minus: '<svg viewBox="0 0 24 24"><path d="M5 12h14"/></svg>',
  hash: '<svg viewBox="0 0 24 24"><path d="M5 9h14M5 15h14M10 4 8 20M16 4l-2 16"/></svg>',
  move: '<svg viewBox="0 0 24 24"><path d="M12 3v18M3 12h18M12 3l-3 3M12 3l3 3M12 21l-3-3M12 21l3-3M3 12l3-3M3 12l3 3M21 12l-3-3M21 12l-3 3"/></svg>',
};

// ---------- encía en herradura: forma 2D de la arcada extruida con bisel redondeado ----------
function gumGeometry({ A, B }) {
  const OUT = 0.5, IN = 0.72, END = PHI0 + PHI_SPAN + 0.12;
  const pt = (phi, d) => new THREE.Vector2((A + d) * Math.sin(phi), -(B + d) * Math.cos(phi));
  const shape = new THREE.Shape();
  const N = 64;
  shape.moveTo(...pt(-END, OUT).toArray());
  for (let i = 1; i <= N; i++) shape.lineTo(...pt(-END + (2 * END * i) / N, OUT).toArray());
  // remate trasero redondeado (detrás de los terceros molares)
  const capR = pt(END, (OUT - IN) / 2).add(new THREE.Vector2(0.05, 0.75));
  shape.quadraticCurveTo(capR.x, capR.y, ...pt(END, -IN).toArray());
  for (let i = N - 1; i >= 0; i--) shape.lineTo(...pt(-END + (2 * END * i) / N, -IN).toArray());
  const capL = pt(-END, (OUT - IN) / 2).add(new THREE.Vector2(-0.05, 0.75));
  shape.quadraticCurveTo(capL.x, capL.y, ...pt(-END, OUT).toArray());

  const geo = new THREE.ExtrudeGeometry(shape, {
    depth: 0.14, bevelEnabled: true, bevelThickness: 0.26, bevelSize: 0.24, bevelSegments: 10, curveSegments: 24, steps: 1,
  });
  geo.rotateX(-Math.PI / 2);          // forma en XZ, extrusión hacia +Y
  geo.translate(0, -(0.14 + 0.26), 0); // la cara superior (con bisel) queda en y = 0
  geo.computeVertexNormals();
  return geo;
}

export function mountTypodont(el) {
  if (!hasWebGL()) { el.classList.add("ready"); el.querySelector(".scene-skeleton").textContent = "Tu navegador no soporta 3D"; return null; }
  const data = JSON.parse(el.dataset.odonto || "{}");
  const states = JSON.parse(el.dataset.states || "{}");
  const encia = JSON.parse(el.dataset.encia || "[]");
  const inflamed = encia.filter((x) => INFLAMED.includes(x));
  const stage = createStage(el, { fov: 30 });
  const { scene, camera, renderer } = stage;
  scene.environmentIntensity = 0.42;

  // etiquetas HTML (texto nítido a cualquier zoom, con los colores del tema)
  const labels = new CSS2DRenderer();
  labels.domElement.className = "t3d-labels";
  el.appendChild(labels.domElement);
  const sizeLabels = () => labels.setSize(el.clientWidth || 1, el.clientHeight || 1);
  new ResizeObserver(sizeLabels).observe(el);
  sizeLabels();

  // ---------- controles de cámara ----------
  const controls = new OrbitControls(camera, renderer.domElement);
  Object.assign(controls, {
    enableDamping: true, dampingFactor: 0.09, rotateSpeed: 0.75, zoomSpeed: 0.9, panSpeed: 0.9,
    enablePan: true, screenSpacePanning: true, zoomToCursor: true,
    minDistance: 4.5, maxDistance: 19, minPolarAngle: 0.05, maxPolarAngle: Math.PI - 0.05,
  });
  controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
  controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
  // el desplazamiento no deja perder el modelo de vista
  const BOUNDS = new THREE.Box3(new THREE.Vector3(-3.2, -2.6, -2.2), new THREE.Vector3(3.2, 2.6, 3.2));
  controls.addEventListener("change", () => BOUNDS.clampPoint(controls.target, controls.target));
  renderer.domElement.addEventListener("contextmenu", (e) => e.preventDefault());
  renderer.domElement.tabIndex = 0;
  renderer.domElement.setAttribute("aria-label", "Tipodonto 3D. Flechas para girar, + y − para acercar, 0 para restablecer.");

  // bisagra detrás de los molares: cada arcada gira alrededor del eje X
  const HINGE_Z = -0.4;
  const pivots = { up: new THREE.Group(), low: new THREE.Group() };
  const arches = { up: new THREE.Group(), low: new THREE.Group() };
  for (const k of ["up", "low"]) {
    pivots[k].position.set(0, 0, HINGE_Z);
    arches[k].position.set(0, 0, -HINGE_Z);
    pivots[k].add(arches[k]);
    scene.add(pivots[k]);
  }

  const teeth = [];
  const brackets = { up: [], low: [] };
  const rimColor = css("--scene-a");
  const negative = css("--negative");
  const bracketGeo = new RoundedBoxGeometry(0.25, 0.21, 0.09, 2, 0.035);
  const bracketMat = new THREE.MeshStandardMaterial({ color: "#eef0f4", metalness: 0.55, roughness: 0.3 });
  const total = ORDER.reduce((s, n) => s + WIDTH[n], 0);

  for (const q of [1, 2, 3, 4]) {
    const upper = q <= 2;
    const key = upper ? "up" : "low";
    const side = q === 1 || q === 4 ? -1 : 1;
    const { A, B, y } = ARCH[key];
    let acc = 0;
    for (const n of ORDER) {
      const fdi = q * 10 + n;
      const mid = (acc + WIDTH[n] / 2) / total;
      acc += WIDTH[n];
      const phi = PHI0 + mid * PHI_SPAN;
      const x = side * A * Math.sin(phi), z = B * Math.cos(phi);
      const kind = toothKind(fdi);
      const state = data[String(fdi)] || "sano";
      const [stateName, stateColor] = states[state] || ["Sano", "#f3efe6"];

      const group = new THREE.Group();
      group.position.set(x, y, z);
      group.rotation.y = Math.atan2(side * Math.sin(phi) * B, Math.cos(phi) * A);
      if (upper) group.rotation.z = Math.PI;
      arches[key].add(group);

      const geo = toothGeometry(kind, { crownOnly: true });
      const half = { x: geo.boundingBox.max.x, z: geo.boundingBox.max.z };
      let mesh;
      if (state === "ausente" || state === "extraido") {
        // sin corona: silueta punteada para conservar el hueco legible (roja si fue extracción)
        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo, 30),
          new THREE.LineDashedMaterial({ color: state === "extraido" ? negative : css("--muted"), dashSize: 0.06, gapSize: 0.05,
                                         transparent: true, opacity: state === "extraido" ? 0.55 : 0.75 }));
        edges.computeLineDistances();
        group.add(edges);
        mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.04, depthWrite: false }));
        if (state === "extraido") {
          // alvéolo: hueco oscuro en la encía con un borde rojizo de cicatrización
          const socket = new THREE.Mesh(new THREE.CircleGeometry(1, 40),
            new THREE.MeshStandardMaterial({ color: "#5a1820", roughness: 0.7, polygonOffset: true, polygonOffsetFactor: -2 }));
          socket.rotation.x = -Math.PI / 2;
          socket.scale.set(half.x * 0.78, half.z * 0.78, 1);
          socket.position.y = 0.012;
          const rim = new THREE.Mesh(new THREE.TorusGeometry(1, 0.06, 10, 48),
            new THREE.MeshStandardMaterial({ color: "#b4505d", roughness: 0.55 }));
          rim.rotation.x = Math.PI / 2;
          rim.scale.set(half.x * 0.86, half.z * 0.86, 1);
          rim.position.y = 0.02;
          group.add(socket, rim);
        }
      } else {
        const color = { corona: stateColor, extraer: "#e7d6d3" }[state] || "#f4f0e8";
        const mat = enamelMaterial({ color, rim: rimColor, rimStrength: 0.06, clearcoat: 0.35,
                                     transmission: state === "endodoncia" ? 0.4 : 0 });
        mat.roughness = 0.38;
        if (state === "corona") { mat.metalness = 0.15; mat.roughness = 0.24; }
        mesh = new THREE.Mesh(geo, mat);
        mesh.castShadow = true;
      }
      group.add(mesh);

      // collar de color en el cuello: se lee el hallazgo desde cualquier ángulo
      if (!["sano", "bracket", "ausente", "extraido"].includes(state)) {
        const collar = new THREE.Mesh(new THREE.TorusGeometry(1, 0.055, 10, 48),
          new THREE.MeshStandardMaterial({ color: state === "extraer" ? negative : stateColor, roughness: 0.45,
                                           emissive: state === "extraer" ? negative : stateColor, emissiveIntensity: 0.18 }));
        collar.rotation.x = Math.PI / 2;
        collar.scale.set(half.x * 0.98, half.z * 0.98, 1);
        collar.position.y = 0.1;
        group.add(collar);
      }
      // marcas por afectación: oclusal en posteriores (visibles con la boca abierta), vestibular en anteriores
      if (state === "caries" || state === "obturado") {
        const posterior = kind === "molar" || kind === "premolar";
        const spot = new THREE.Mesh(new THREE.CircleGeometry(kind === "molar" ? 0.27 : 0.2, 32),
          new THREE.MeshStandardMaterial({ color: stateColor, roughness: state === "obturado" ? 0.3 : 0.85, side: THREE.DoubleSide,
                                           polygonOffset: true, polygonOffsetFactor: -2 }));
        if (posterior) { spot.rotation.x = -Math.PI / 2; spot.position.y = OCCLUSAL_Y[kind] + 0.015; }
        else { spot.position.set(0, 0.62, FACE_Z[kind] + 0.04); }
        group.add(spot);
      }
      if (state === "extraer") {
        // X roja en la cara vestibular: se distingue de lejos de una pieza sana
        const xMat = new THREE.MeshStandardMaterial({ color: negative, emissive: negative, emissiveIntensity: 0.25, roughness: 0.4 });
        for (const a of [Math.PI / 4, -Math.PI / 4]) {
          const bar = new THREE.Mesh(new RoundedBoxGeometry(0.62, 0.09, 0.05, 2, 0.02), xMat);
          bar.rotation.z = a;
          bar.position.set(0, 0.55, FACE_Z[kind] + 0.07);
          group.add(bar);
        }
      }
      if (state === "endodoncia") {
        const canal = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.035, 1.1, 12), new THREE.MeshStandardMaterial({ color: stateColor }));
        canal.position.y = 0.15;
        group.add(canal);
      }
      if (state === "bracket") {
        const b = new THREE.Mesh(bracketGeo, bracketMat);
        b.position.set(0, 0.5, FACE_Z[kind] + 0.02);
        b.castShadow = true;
        group.add(b);
        brackets[key].push({ obj: b, side, phi });
      }

      // etiqueta con el número FDI sobre la encía, frente a la pieza (en local -y queda hacia la raíz en ambas arcadas)
      const tag = document.createElement("span");
      tag.className = "t3d-tag" + (state !== "sano" && state !== "bracket" ? " finding" : "");
      tag.style.setProperty("--c", state === "extraer" ? negative : stateColor);
      tag.textContent = fdi;
      const label = new CSS2DObject(tag);
      label.position.set(0, -0.36, FACE_Z[kind] + 0.42);
      group.add(label);

      mesh.userData.fdi = fdi;
      teeth.push({ fdi, n, group, mesh, label, tag, state, stateName, stateColor, kind, upper,
                   outward: new THREE.Vector3(x, 0, z).normalize(), scale: 1, target: 1 });
    }
  }

  // encías: herradura esculpida por arcada, se mueve con su bisagra
  // con inflamación (gingivitis, periodontitis…) la encía se ve más roja
  const gumColor = () => new THREE.Color(css("--gum")).lerp(new THREE.Color("#c8374f"), inflamed.length ? 0.5 : 0);
  const gumMat = new THREE.MeshPhysicalMaterial({ color: gumColor(), roughness: 0.48, clearcoat: 0.35, clearcoatRoughness: 0.4,
                                                  sheen: 0.5, sheenColor: new THREE.Color("#ffd9de") });
  for (const key of ["up", "low"]) {
    const gum = new THREE.Mesh(gumGeometry(ARCH[key]), gumMat);
    gum.receiveShadow = true;
    // la cara superior de la encía cubre el cuello de las coronas (y = ±0.92 menos un margen)
    if (key === "up") { gum.scale.y = -1; gum.position.y = ARCH.up.y + 0.02; }
    else gum.position.y = ARCH.low.y - 0.02;
    arches[key].add(gum);
  }

  // alambre de ortodoncia en coordenadas de su arcada
  scene.updateMatrixWorld(true);
  for (const key of ["up", "low"]) {
    const list = brackets[key].sort((a, b) => a.side * a.phi - b.side * b.phi);
    if (list.length < 2) continue;
    const pts = list.map((b) => arches[key].worldToLocal(b.obj.getWorldPosition(new THREE.Vector3())));
    arches[key].add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 120, 0.018, 8, false),
      new THREE.MeshStandardMaterial({ color: "#e3e6ec", metalness: 1, roughness: 0.2 })));
  }

  // ---------- apertura y cámara (transiciones suaves) ----------
  let open = el.dataset.view === "abierta" ? 1 : 0;
  const applyOpen = (k) => {
    open = k;
    pivots.up.rotation.x = MAX_OPEN.up * k;
    pivots.low.rotation.x = MAX_OPEN.low * k;
  };
  const start = PRESETS[open ? "abierta" : "cerrada"];
  applyOpen(open);
  camera.position.set(...start.cam);
  controls.target.set(...start.target);
  const home = { cam: start.cam, target: start.target, open };

  const anim = { t: 1, from: null, to: null };
  const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  // si el usuario toma el control a mitad de una transición, la cámara se suelta (la apertura termina sola)
  controls.addEventListener("start", () => { if (anim.to) { anim.to.cam = null; anim.to.target = null; } });

  // mostrar solo una arcada (vistas oclusales y piezas posteriores) o ambas
  let only = null;
  function isolate(k) {
    only = k || null;
    pivots.up.visible = only !== "low";
    pivots.low.visible = only !== "up";
    bar?.querySelectorAll("[data-preset]").forEach((b) => b.classList.toggle("active", b.dataset.preset === activePreset));
  }
  let activePreset = null;

  function goTo({ cam = null, target = null, open: o = open, only: k = null }) {
    isolate(k);
    anim.from = { cam: camera.position.toArray(), target: controls.target.toArray(), open };
    anim.to = { cam, target, open: o };
    anim.t = 0;
    if (reduceMotion) finish();
    emitView(o);
  }
  function finish() {
    anim.t = 1;
    applyOpen(anim.to.open);
    if (anim.to.cam) camera.position.set(...anim.to.cam);
    if (anim.to.target) controls.target.set(...anim.to.target);
  }
  let lastView = null;
  function emitView(o) {
    const v = o >= 0.5 ? "abierta" : "cerrada";
    if (v !== lastView) { lastView = v; el.dispatchEvent(new CustomEvent("viewchange", { detail: v })); }
    if (slider && document.activeElement !== slider) slider.value = Math.round(o * 100);
  }
  function setView(next, moveCamera = true) {
    const p = PRESETS[next] || PRESETS.cerrada;
    activePreset = null;
    goTo(moveCamera ? p : { open: p.open });
  }
  function preset(name) {
    const p = PRESETS[name];
    activePreset = name;
    goTo({ cam: p.cam, target: p.target, open: p.open ?? open, only: p.only });
  }
  function zoom(factor) {
    const off = camera.position.clone().sub(controls.target);
    const len = THREE.MathUtils.clamp(off.length() * factor, controls.minDistance, controls.maxDistance);
    goTo({ cam: controls.target.clone().add(off.setLength(len)).toArray(), target: controls.target.toArray(), only });
  }
  function orbit(dTheta, dPhi) {
    const off = camera.position.clone().sub(controls.target);
    const s = new THREE.Spherical().setFromVector3(off);
    s.theta += dTheta;
    s.phi = THREE.MathUtils.clamp(s.phi + dPhi, controls.minPolarAngle, controls.maxPolarAngle);
    goTo({ cam: controls.target.clone().add(new THREE.Vector3().setFromSpherical(s)).toArray(), target: controls.target.toArray(), only });
  }

  // ---------- barra de navegación sobre la escena ----------
  const bar = document.createElement("div");
  bar.className = "t3d-bar";
  bar.innerHTML = `
    <div class="t3d-group" role="group" aria-label="Vistas rápidas">
      ${PRESET_BUTTONS.map(([k, l]) => `<button type="button" data-preset="${k}" title="Vista ${l.toLowerCase()}">${l}</button>`).join("")}
    </div>
    <label class="t3d-open" title="Apertura de la boca">Apertura
      <input type="range" min="0" max="100" step="1" value="${Math.round(open * 100)}" aria-label="Apertura de la boca"></label>
    <div class="t3d-group" role="group" aria-label="Acercar o alejar">
      <button type="button" data-zoom="0.8" title="Acercar (+)" aria-label="Acercar">${SVG.plus}</button>
      <button type="button" data-zoom="1.25" title="Alejar (−)" aria-label="Alejar">${SVG.minus}</button>
    </div>
    <button type="button" class="t3d-toggle" data-numbers aria-pressed="false" title="Mostrar el número de todas las piezas">${SVG.hash}<span>Números</span></button>
    ${inflamed.length ? `<span class="t3d-flag" title="Registrado en Historia clínica → Lengua y encía">Encía: ${inflamed.join(", ").toLowerCase()}</span>` : ""}`;
  el.appendChild(bar);
  const slider = bar.querySelector('input[type="range"]');
  bar.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.preset) preset(b.dataset.preset);
    if (b.dataset.zoom) zoom(Number(b.dataset.zoom));
    if ("numbers" in b.dataset) {
      const on = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", on);
      el.classList.toggle("t3d-all-numbers", on);
    }
  });
  slider.addEventListener("input", () => { anim.t = 1; applyOpen(slider.value / 100); emitView(open); });
  bar.querySelector('[data-preset="frente"]').title = "Vista de frente (ambas arcadas)";

  // ficha de la pieza seleccionada (lectura clara del hallazgo)
  const card = document.createElement("div");
  card.className = "t3d-card";
  card.setAttribute("aria-live", "polite");
  el.appendChild(card);

  // teclado: flechas giran, +/− acercan, 0 restablece
  renderer.domElement.addEventListener("keydown", (e) => {
    const step = 0.35;
    const act = { ArrowLeft: () => orbit(-step, 0), ArrowRight: () => orbit(step, 0), ArrowUp: () => orbit(0, -step * 0.6),
                  ArrowDown: () => orbit(0, step * 0.6), "+": () => zoom(0.8), "=": () => zoom(0.8), "-": () => zoom(1.25),
                  0: () => reset(), Escape: () => reset() }[e.key];
    if (act) { e.preventDefault(); act(); }
  });

  // ---------- interacción: tooltip, resaltado y selección ----------
  const tip = document.createElement("div");
  tip.className = "tip3d";
  el.appendChild(tip);
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let hovered = null, selected = null, downAt = null;
  const meshes = teeth.map((t) => t.mesh);
  const byFdi = new Map(teeth.map((t) => [t.fdi, t]));
  const where = (t) => `${KIND_NAME[t.n]} ${QUADRANT[Math.floor(t.fdi / 10)].toLowerCase()}`;
  const setTargets = () => teeth.forEach((t) => {
    t.target = t === selected ? 1.12 : t === hovered ? 1.05 : 1;
    const u = t.mesh.material.userData?.uniforms;
    if (u) u.uRimStrength.value = t === selected ? 0.55 : t === hovered ? 0.3 : 0.06;
    t.tag.classList.toggle("on", t === selected || t === hovered);
  });

  const pick = (e) => {
    const r = renderer.domElement.getBoundingClientRect();
    pointer.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(meshes, false)[0];
    return hit ? byFdi.get(hit.object.userData.fdi) : null;
  };
  renderer.domElement.addEventListener("pointermove", (e) => {
    if (e.buttons) { tip.classList.remove("on"); return; }   // arrastrando: sin tooltip
    hovered = pick(e);
    renderer.domElement.style.cursor = hovered ? "pointer" : "grab";
    if (hovered) {
      const r = renderer.domElement.getBoundingClientRect();
      tip.innerHTML = `<b>${hovered.fdi}</b> · ${where(hovered)} · ${hovered.stateName}`;
      tip.style.left = `${e.clientX - r.left}px`;
      tip.style.top = `${e.clientY - r.top}px`;
      tip.classList.add("on");
    } else tip.classList.remove("on");
    setTargets();
  });
  renderer.domElement.addEventListener("pointerdown", (e) => {
    downAt = { x: e.clientX, y: e.clientY };
    renderer.domElement.style.cursor = e.button === 2 || e.shiftKey ? "move" : "grabbing";
  });
  renderer.domElement.addEventListener("pointerup", (e) => {
    renderer.domElement.style.cursor = hovered ? "pointer" : "grab";
    // un clic (sin arrastre) sobre una pieza la selecciona
    if (downAt && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) < 5 && e.button === 0) {
      const t = pick(e);
      if (t) select(t.fdi, true);
    }
    downAt = null;
  });
  renderer.domElement.addEventListener("dblclick", (e) => { if (!pick(e)) reset(); });
  renderer.domElement.addEventListener("pointerleave", () => { hovered = null; tip.classList.remove("on"); setTargets(); });

  // seleccionar una pieza: abre la boca si hace falta y la cámara se acerca a ella
  function select(fdi, fromCanvas) {
    const t = byFdi.get(Number(fdi));
    if (!t) return;
    selected = t;
    setTargets();
    const o = Math.max(open, t.kind === "molar" || t.kind === "premolar" ? 1 : 0.6);
    // posición de la pieza con la apertura final
    const pivot = t.upper ? pivots.up : pivots.low;
    const saved = pivot.rotation.x;
    pivot.rotation.x = (t.upper ? MAX_OPEN.up : MAX_OPEN.low) * o;
    scene.updateMatrixWorld(true);
    const local = t.group.getWorldPosition(new THREE.Vector3());
    pivot.rotation.x = saved;
    scene.updateMatrixWorld(true);
    const dir = local.clone().setY(0).normalize();
    const posterior = t.kind === "molar" || t.kind === "premolar";
    activePreset = null;
    goTo({
      only: posterior ? (t.upper ? "up" : "low") : null,
      // se mira la cara oclusal: desde abajo para las superiores, desde arriba para las inferiores
      // posteriores: vista oclusal de su arcada centrada hacia la pieza; anteriores: de frente
      cam: posterior
        ? [local.x * 0.55, t.upper ? -8.6 : 8.6, local.z * 0.55 + 3.6]
        : local.clone().add(dir.multiplyScalar(6.6)).add(new THREE.Vector3(0, 0.8, 0)).toArray(),
      target: local.clone().lerp(new THREE.Vector3(0, local.y, 0.4), 0.45).toArray(),
      open: o,
    });
    card.innerHTML = `<span class="sw" style="background:${t.state === "extraer" ? negative : t.stateColor}"></span>
      <div><b>Pieza ${t.fdi}</b><small>${where(t)}</small></div><em>${t.stateName}</em>
      <button type="button" aria-label="Cerrar ficha">×</button>`;
    card.classList.add("on");
    el.dispatchEvent(new CustomEvent("toothselect", { detail: { fdi: t.fdi, fromCanvas } }));
  }
  card.addEventListener("click", (e) => { if (e.target.closest("button")) reset(); });

  function reset() {
    selected = null;
    activePreset = null;
    setTargets();
    card.classList.remove("on");
    goTo(home);
  }

  window.addEventListener("themechange", () => {
    stage.applyTheme();
    gumMat.color.copy(gumColor());
    teeth.forEach((t) => { const u = t.mesh.material.userData?.uniforms; if (u) u.uRim.value.set(css("--scene-a")); });
  });

  // ---------- ciclo de render ----------
  const camDir = new THREE.Vector3(), out = new THREE.Vector3();
  stage.loop((dt) => {
    if (anim.t < 1 && anim.to) {
      anim.t = Math.min(1, anim.t + dt / 0.7);
      const k = easeInOut(anim.t);
      const lerp = (a, b) => a + (b - a) * k;
      applyOpen(lerp(anim.from.open, anim.to.open));
      if (anim.to.cam) camera.position.set(...anim.from.cam.map((v, i) => lerp(v, anim.to.cam[i])));
      if (anim.to.target) controls.target.set(...anim.from.target.map((v, i) => lerp(v, anim.to.target[i])));
    }
    for (const t of teeth) {
      t.scale += (t.target - t.scale) * Math.min(1, dt * 10);
      t.group.scale.setScalar(t.scale);
    }
    controls.update(dt);
    // se ocultan los números de las piezas que dan la espalda a la cámara (evita lecturas encimadas)
    camDir.copy(camera.position).sub(controls.target).normalize();
    const fromTop = Math.abs(camDir.y) > 0.62;
    camDir.y = 0; camDir.normalize();
    for (const t of teeth) {
      out.copy(t.outward);
      const facing = fromTop || out.dot(camDir) > 0.32;
      t.label.visible = facing && (t.upper ? pivots.up.visible : pivots.low.visible);
    }
    labels.render(scene, camera);
  });
  stage.ready.then(() => el.classList.add("ready"));

  return { select, setView, preset, reset };
}

// ---------- auto-montaje y controles de la tarjeta ----------
document.querySelectorAll("[data-typodont]").forEach((el) => {
  const api = mountTypodont(el);
  if (!api) return;
  const card = el.closest(".card") || document;
  const list = document.querySelector(el.dataset.list || "#zone-list");
  const viewBtns = card.querySelectorAll("[data-typo-view]");
  viewBtns.forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); api.setView(b.dataset.typoView); }));
  el.addEventListener("viewchange", (e) => viewBtns.forEach((b) => b.classList.toggle("active", b.dataset.typoView === e.detail)));
  if (list) {
    list.addEventListener("click", (e) => {
      const b = e.target.closest("[data-fdi]");
      if (b) api.select(b.dataset.fdi, false);
    });
    el.addEventListener("toothselect", (e) => {
      list.querySelectorAll("[data-fdi]").forEach((b) => b.classList.toggle("on", Number(b.dataset.fdi) === e.detail.fdi));
      const on = list.querySelector(`[data-fdi="${e.detail.fdi}"]`);
      if (on && e.detail.fromCanvas) on.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    });
  }
  card.querySelectorAll("[data-typo-reset]").forEach((b) => b.addEventListener("click", () => {
    api.reset();
    list?.querySelectorAll(".on").forEach((x) => x.classList.remove("on"));
  }));
});
