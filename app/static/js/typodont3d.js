// Tipodonto 3D generado desde el odontograma del paciente.
// Sencillo y quieto: sin pulsos ni giro automático. Las arcadas cuelgan de una bisagra
// para abrir la boca y ver las caras oclusales, donde se marcan caries y resinas.
// Uso: <div class="scene" data-typodont data-view="cerrada|abierta" data-odonto='{...}' data-states='{...}'>
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { createStage, enamelMaterial, toothGeometry, toothKind, QUADRANT, css, reduceMotion, hasWebGL } from "./dental3d.js";

const ORDER = [1, 2, 3, 4, 5, 6, 7, 8];
const WIDTH = { 1: 0.86, 2: 0.74, 3: 0.8, 4: 0.76, 5: 0.76, 6: 1.08, 7: 1.02, 8: 0.96 };
const KIND_NAME = { incisivo: "Incisivo", canino: "Canino", premolar: "Premolar", molar: "Molar" };
const FACE_Z = { incisivo: 0.25, canino: 0.36, premolar: 0.46, molar: 0.55 };
const OCCLUSAL_Y = { premolar: 0.84, molar: 0.75 };  // altura del centro de la cara oclusal (perfil × escala)

// vistas: ángulo de cada arcada (rad) y posición de cámara
const VIEWS = {
  cerrada: { up: 0, low: 0, cam: [-4.2, 1.6, 10.6], target: [0, 0, 0.5] },
  abierta: { up: -0.58, low: 0.28, cam: [0, 0.55, 12.6], target: [0, 0.35, 0.9] },
};

export function mountTypodont(el) {
  if (!hasWebGL()) { el.classList.add("ready"); el.querySelector(".scene-skeleton").textContent = "Tu navegador no soporta 3D"; return null; }
  const data = JSON.parse(el.dataset.odonto || "{}");
  const states = JSON.parse(el.dataset.states || "{}");
  const stage = createStage(el, { fov: 30 });
  const { scene, camera, renderer } = stage;
  scene.environmentIntensity = 0.35;

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.enablePan = false;
  controls.minDistance = 6;
  controls.maxDistance = 16;

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
  const archPoints = { up: [], low: [] };
  const brackets = { up: [], low: [] };
  const rimColor = css("--scene-a");

  for (const q of [1, 2, 3, 4]) {
    const upper = q <= 2;
    const key = upper ? "up" : "low";
    const side = q === 1 || q === 4 ? -1 : 1;
    const A = upper ? 2.75 : 2.55, B = upper ? 2.35 : 2.15;
    const total = ORDER.reduce((s, n) => s + WIDTH[n], 0);
    let acc = 0;
    for (const n of ORDER) {
      const fdi = q * 10 + n;
      const mid = (acc + WIDTH[n] / 2) / total;
      acc += WIDTH[n];
      const phi = 0.04 + mid * 1.5;
      const x = side * A * Math.sin(phi), z = B * Math.cos(phi);
      const kind = toothKind(fdi);
      const state = data[String(fdi)] || "sano";
      const stateColor = (states[state] || ["", "#f3efe6"])[1];

      const group = new THREE.Group();
      group.position.set(x, upper ? 0.92 : -0.92, z);
      group.rotation.y = Math.atan2(side * Math.sin(phi) * B, Math.cos(phi) * A);
      if (upper) group.rotation.z = Math.PI;
      arches[key].add(group);

      const geo = toothGeometry(kind, { crownOnly: true });
      let mesh;
      if (state === "ausente") {
        group.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo, 25),
          new THREE.LineBasicMaterial({ color: css("--faint"), transparent: true, opacity: 0.5 })));
        mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.03, depthWrite: false }));
      } else {
        const color = { corona: stateColor, extraer: "#3a3f52" }[state] || "#f1ede4";
        const mat = enamelMaterial({ color, rim: rimColor, rimStrength: 0.08, clearcoat: 0.15,
                                     transmission: state === "endodoncia" ? 0.45 : 0 });
        mat.roughness = 0.45;
        if (state === "corona") { mat.metalness = 0.25; mat.roughness = 0.3; }
        mesh = new THREE.Mesh(geo, mat);
        mesh.castShadow = true;
      }
      group.add(mesh);

      // marcas por afectación: oclusal en posteriores (visibles con la boca abierta), vestibular en anteriores
      if (state === "caries" || state === "obturado") {
        const posterior = kind === "molar" || kind === "premolar";
        const spot = new THREE.Mesh(new THREE.CircleGeometry(kind === "molar" ? 0.24 : 0.17, 28),
          new THREE.MeshStandardMaterial({ color: stateColor, roughness: state === "obturado" ? 0.3 : 0.85, side: THREE.DoubleSide,
                                           polygonOffset: true, polygonOffsetFactor: -2 }));
        if (posterior) { spot.rotation.x = -Math.PI / 2; spot.position.y = OCCLUSAL_Y[kind] + 0.015; }
        else { spot.position.set(0, 0.62, FACE_Z[kind] + 0.04); }
        group.add(spot);
      }
      if (state === "endodoncia") {
        const canal = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.03, 1.1, 10), new THREE.MeshStandardMaterial({ color: stateColor }));
        canal.position.y = 0.15;
        group.add(canal);
      }
      if (state === "extraer") {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.035, 8, 40), new THREE.MeshBasicMaterial({ color: css("--negative") }));
        ring.rotation.x = Math.PI / 2;
        ring.position.y = 0.15;
        group.add(ring);
      }
      if (state === "bracket") {
        const b = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.2, 0.1), new THREE.MeshStandardMaterial({ color: "#c9ced8", metalness: 0.85, roughness: 0.3 }));
        b.position.set(0, 0.5, FACE_Z[kind]);
        group.add(b);
        brackets[key].push({ obj: b, side, phi });
      }

      mesh.userData.fdi = fdi;
      teeth.push({ fdi, group, mesh, state, kind, upper, scale: 1, target: 1 });
      archPoints[key].push({ side, phi, x, z });
    }
  }

  // encías: un tubo por arcada, dentro de su propio grupo (se mueve con la bisagra)
  const gumMat = new THREE.MeshStandardMaterial({ color: css("--gum"), roughness: 0.6 });
  for (const [key, y] of [["up", 1.42], ["low", -1.42]]) {
    const pts = archPoints[key].slice().sort((a, b) => a.side * a.phi - b.side * b.phi)
      .map((p) => new THREE.Vector3(p.x * 1.02, y, p.z * 1.02));
    const gum = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 120, 0.6, 18, false), gumMat);
    gum.scale.y = 0.8;
    arches[key].add(gum);
  }

  // alambre de ortodoncia en coordenadas de su arcada
  scene.updateMatrixWorld(true);
  for (const key of ["up", "low"]) {
    const list = brackets[key].sort((a, b) => a.side * a.phi - b.side * b.phi);
    if (list.length < 2) continue;
    const pts = list.map((b) => arches[key].worldToLocal(b.obj.getWorldPosition(new THREE.Vector3())));
    arches[key].add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 100, 0.022, 6, false),
      new THREE.MeshStandardMaterial({ color: "#d7dbe3", metalness: 1, roughness: 0.25 })));
  }

  // ---------- vista: cerrada / abierta (transición suave, ease-in-out) ----------
  let view = el.dataset.view === "abierta" ? "abierta" : "cerrada";
  const anim = { from: null, to: VIEWS[view], t: 1 };
  const applyPose = (p) => {
    pivots.up.rotation.x = p.up; pivots.low.rotation.x = p.low;
  };
  applyPose(VIEWS[view]);
  camera.position.set(...VIEWS[view].cam);
  controls.target.set(...VIEWS[view].target);
  const current = () => ({ up: pivots.up.rotation.x, low: pivots.low.rotation.x,
    cam: camera.position.toArray(), target: controls.target.toArray() });
  function setView(next, moveCamera = true) {
    view = next;
    anim.from = current();
    anim.to = { ...VIEWS[next], cam: moveCamera ? VIEWS[next].cam : anim.from.cam, target: moveCamera ? VIEWS[next].target : anim.from.target };
    anim.t = reduceMotion ? 1 : 0;
    if (reduceMotion) { applyPose(anim.to); camera.position.set(...anim.to.cam); controls.target.set(...anim.to.target); }
    el.dispatchEvent(new CustomEvent("viewchange", { detail: next }));
  }
  const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

  // ---------- interacción: tooltip + resaltado discreto ----------
  const tip = document.createElement("div");
  tip.className = "tip3d";
  el.appendChild(tip);
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let hovered = null, selected = null;
  const meshes = teeth.map((t) => t.mesh);
  const byFdi = new Map(teeth.map((t) => [t.fdi, t]));
  const label = (t) => `<b>${t.fdi}</b> · ${KIND_NAME[t.kind]} ${QUADRANT[Math.floor(t.fdi / 10)].toLowerCase()} · ${(states[t.state] || ["Sano"])[0]}`;
  const setTargets = () => teeth.forEach((t) => { t.target = t === selected ? 1.14 : t === hovered ? 1.06 : 1; });

  renderer.domElement.addEventListener("pointermove", (e) => {
    const r = renderer.domElement.getBoundingClientRect();
    pointer.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(meshes, false)[0];
    hovered = hit ? byFdi.get(hit.object.userData.fdi) : null;
    renderer.domElement.style.cursor = hovered ? "pointer" : "grab";
    if (hovered) {
      tip.innerHTML = label(hovered);
      tip.style.left = `${e.clientX - r.left}px`;
      tip.style.top = `${e.clientY - r.top}px`;
      tip.classList.add("on");
    } else tip.classList.remove("on");
    setTargets();
  });
  renderer.domElement.addEventListener("pointerleave", () => { hovered = null; tip.classList.remove("on"); setTargets(); });
  renderer.domElement.addEventListener("click", () => { if (hovered) select(hovered.fdi, true); });

  // seleccionar una pieza: abre la boca si hace falta y la cámara se acerca a ella
  function select(fdi, fromCanvas) {
    const t = byFdi.get(Number(fdi));
    if (!t) return;
    selected = t;
    setTargets();
    if (view !== "abierta") setView("abierta", false);
    const pose = VIEWS.abierta;
    const local = new THREE.Vector3();
    // posición de la pieza ya con la boca abierta
    const pivot = t.upper ? pivots.up : pivots.low;
    const saved = pivot.rotation.x;
    pivot.rotation.x = t.upper ? pose.up : pose.low;
    scene.updateMatrixWorld(true);
    t.group.getWorldPosition(local);
    pivot.rotation.x = saved;
    scene.updateMatrixWorld(true);
    const dir = local.clone().setY(0).normalize();
    anim.from = current();
    anim.to = { ...pose,
      // se mira la cara oclusal: desde abajo para las superiores, desde arriba para las inferiores
      cam: local.clone().add(dir.multiplyScalar(5.6)).add(new THREE.Vector3(0, t.upper ? -3.2 : 3.6, 0)).toArray(),
      target: local.clone().lerp(new THREE.Vector3(0, local.y, 0.9), 0.25).toArray() };
    anim.t = reduceMotion ? 1 : 0;
    if (reduceMotion) { applyPose(anim.to); camera.position.set(...anim.to.cam); controls.target.set(...anim.to.target); }
    el.dispatchEvent(new CustomEvent("toothselect", { detail: { fdi: t.fdi, fromCanvas } }));
  }

  window.addEventListener("themechange", () => {
    stage.applyTheme();
    gumMat.color.set(css("--gum"));
    teeth.forEach((t) => { const u = t.mesh.material.userData?.uniforms; if (u) u.uRim.value.set(css("--scene-a")); });
  });

  stage.loop((dt) => {
    if (anim.t < 1 && anim.from) {
      anim.t = Math.min(1, anim.t + dt / 0.75);
      const k = easeInOut(anim.t);
      const lerp = (a, b) => a + (b - a) * k;
      applyPose({ up: lerp(anim.from.up, anim.to.up), low: lerp(anim.from.low, anim.to.low) });
      camera.position.set(...anim.from.cam.map((v, i) => lerp(v, anim.to.cam[i])));
      controls.target.set(...anim.from.target.map((v, i) => lerp(v, anim.to.target[i])));
    }
    for (const t of teeth) {
      t.scale += (t.target - t.scale) * Math.min(1, dt * 10);
      t.group.scale.setScalar(t.scale);
    }
    controls.update(dt);
  });
  stage.ready.then(() => el.classList.add("ready"));

  return {
    select, setView,
    reset: () => { selected = null; setTargets(); setView(view); },
  };
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
