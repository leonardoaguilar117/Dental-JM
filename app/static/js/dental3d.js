// Consultorio Dental JM · motor 3D compartido (three.js r186, WebGLRenderer)
// - Geometría: dientes por tipo con LatheGeometry + cúspides esculpidas, encías con TubeGeometry.
// - Sombreado: MeshPhysicalMaterial extendido con onBeforeCompile (textura de ruido en el esmalte,
//   brillo de borde por fresnel y pulso emisivo para piezas con afectación).
// - Carga: LoadingManager + TextureLoader (textura de ruido) + RoomEnvironment para reflejos PBR.
// - Iluminación: hemisférica con colores del tema, luz principal con sombra y luz de contorno.
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

export const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
export const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888888";

// ---------- tipos de pieza (numeración FDI) ----------
export function toothKind(fdi) {
  const n = fdi % 10;
  if (n <= 2) return "incisivo";
  if (n === 3) return "canino";
  if (n <= 5) return "premolar";
  return "molar";
}
const KIND_SCALE = {
  incisivo: [0.78, 1.0, 0.46],
  canino: [0.72, 1.12, 0.66],
  premolar: [0.78, 0.9, 0.86],
  molar: [1.08, 0.82, 1.02],
};
export const QUADRANT = { 1: "Superior derecho", 2: "Superior izquierdo", 3: "Inferior izquierdo", 4: "Inferior derecho" };

// ---------- geometría de un diente ----------
const geometryCache = new Map();
export function toothGeometry(kind, { crownOnly = false } = {}) {
  const cacheKey = kind + (crownOnly ? ":crown" : "");
  if (geometryCache.has(cacheKey)) return geometryCache.get(cacheKey);
  // Perfil (radio, altura): raíz abajo (y<0), corona arriba (y>0). Se gira alrededor del eje Y.
  const profile = {
    incisivo: [[0, -1.7], [0.16, -1.5], [0.27, -0.9], [0.36, -0.25], [0.4, 0], [0.5, 0.35], [0.52, 0.72], [0.44, 1.02], [0.2, 1.12], [0, 1.13]],
    canino: [[0, -2.0], [0.16, -1.7], [0.3, -0.9], [0.4, -0.2], [0.44, 0], [0.52, 0.35], [0.5, 0.75], [0.32, 1.05], [0.1, 1.26], [0, 1.28]],
    premolar: [[0, -1.5], [0.2, -1.3], [0.32, -0.7], [0.4, -0.15], [0.44, 0], [0.54, 0.28], [0.56, 0.6], [0.48, 0.84], [0.24, 0.92], [0, 0.86]],
    molar: [[0, -1.25], [0.3, -1.12], [0.44, -0.6], [0.48, -0.1], [0.5, 0], [0.6, 0.25], [0.62, 0.58], [0.54, 0.82], [0.3, 0.9], [0, 0.82]],
  }[kind].map(([r, y]) => new THREE.Vector2(r, y));
  // corona sola (para el tipodonto): se corta la raíz bajo la encía y se cierra la base
  const pts = crownOnly ? [new THREE.Vector2(0, -0.35), ...profile.filter((p) => p.y >= -0.3)] : profile;

  let geo = new THREE.LatheGeometry(pts, 40);
  const pos = geo.attributes.position;
  const v = new THREE.Vector3();
  const [sx, sy, sz] = KIND_SCALE[kind];
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    const a = Math.atan2(v.z, v.x);
    // cúspides: ondulación en la cara oclusal (4 en molares, 2 en premolares)
    if (v.y > 0.55 && (kind === "molar" || kind === "premolar")) {
      const lobes = kind === "molar" ? 4 : 2;
      const t = (v.y - 0.55) / 0.4;
      v.y += Math.cos(a * lobes) * 0.07 * t;
    }
    // raíces de molar: dos lóbulos en lugar de un cono
    if (v.y < -0.2 && kind === "molar") {
      const k = Math.min(1, (-0.2 - v.y) / 0.9);
      v.x *= 1 - 0.25 * k * (1 - Math.abs(Math.cos(a)));
    }
    pos.setXYZ(i, v.x * sx, v.y * sy, v.z * sz);
  }
  geo.computeVertexNormals();
  geo.computeBoundingBox();
  geometryCache.set(cacheKey, geo);
  return geo;
}

// ---------- molar anatómico detallado (tablero) ----------
// Corona con 4 cúspides y surcos en cruz, cuello cervical y tres raíces divergentes.
export function detailedMolarGeometry() {
  if (geometryCache.has("molar:detail")) return geometryCache.get("molar:detail");
  const crownProfile = [[0, 0.02], [0.47, 0], [0.55, 0.12], [0.63, 0.32], [0.66, 0.52], [0.64, 0.7], [0.58, 0.82],
    [0.48, 0.9], [0.36, 0.95], [0.24, 0.97], [0.12, 0.96], [0, 0.95]].map(([r, y]) => new THREE.Vector2(r, y));
  const crown = new THREE.LatheGeometry(crownProfile, 96);
  const pos = crown.attributes.position;
  const v = new THREE.Vector3();
  const cusps = [[0.3, 0.27], [-0.3, 0.27], [0.3, -0.27], [-0.3, -0.27]];
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    // ligera forma rectangular redondeada (más ancho en sentido mesio-distal)
    v.x *= 1.1; v.z *= 0.96;
    if (v.y > 0.6) {
      const t = Math.min(1, (v.y - 0.6) / 0.35);
      let bump = 0;
      for (const [cx, cz] of cusps) bump += Math.exp(-((v.x - cx) ** 2 + (v.z - cz) ** 2) / 0.05);
      const groove = Math.exp(-(v.x * v.x) / 0.004) + Math.exp(-(v.z * v.z) / 0.004);    // surcos central y vestíbulo-lingual
      const fossa = Math.exp(-(v.x * v.x + v.z * v.z) / 0.02);                          // fosa central
      v.y += t * (0.11 * Math.min(bump, 1.2) - 0.05 * Math.min(groove, 1) - 0.06 * fossa - 0.04);
    }
    // contorno vestibular abombado
    if (v.y > 0.1 && v.y < 0.6) v.z *= 1 + 0.04 * Math.sin(((v.y - 0.1) / 0.5) * Math.PI);
    pos.setXYZ(i, v.x, v.y, v.z);
  }
  crown.computeVertexNormals();

  const neck = new THREE.LatheGeometry([[0, 0.02], [0.47, 0.0], [0.45, -0.1], [0.43, -0.22], [0.36, -0.3], [0, -0.3]]
    .map(([r, y]) => new THREE.Vector2(r, y)), 96);
  neck.scale(1.08, 1, 0.94);

  const root = (len, rTop, tilt, x, z) => {
    const g = new THREE.LatheGeometry([[0, 0], [rTop, 0], [rTop * 0.92, -len * 0.35], [rTop * 0.7, -len * 0.7], [rTop * 0.35, -len * 0.95], [0, -len]]
      .map(([r, y]) => new THREE.Vector2(r, y)), 32);
    g.rotateZ(tilt[0]); g.rotateX(tilt[1]);
    g.translate(x, -0.1, z);
    return g;
  };
  const roots = [
    root(1.2, 0.27, [0.12, -0.06], 0.22, 0.12),    // mesiovestibular
    root(1.1, 0.25, [-0.12, -0.06], -0.22, 0.12),  // distovestibular
    root(1.3, 0.3, [0, 0.13], 0, -0.16),           // palatina
  ];
  [neck, ...roots].forEach((g) => g.computeVertexNormals());
  const merged = mergeGeometries([crown, neck, ...roots], false);
  merged.computeBoundingBox();
  geometryCache.set("molar:detail", merged);
  return merged;
}

// ---------- material de esmalte (shader extendido) ----------
export const shared = { time: { value: 0 }, noise: { value: null } };

export function enamelMaterial({ color = "#f3efe6", pulse = 0, pulseColor = "#c4242a", rim = "#0ea1d2", rimStrength = 0.35, transmission = 0, clearcoat = 0.6 } = {}) {
  const mat = new THREE.MeshPhysicalMaterial({
    color: new THREE.Color(color), roughness: 0.32, metalness: 0.0, clearcoat, clearcoatRoughness: 0.25,
    sheen: 0.4, sheenColor: new THREE.Color("#ffffff"), transmission, thickness: 0.6, ior: 1.52,
    transparent: transmission > 0, opacity: 1,
  });
  mat.userData.uniforms = {
    uTime: shared.time, uNoise: shared.noise,
    uPulse: { value: pulse }, uPulseColor: { value: new THREE.Color(pulseColor) },
    uRim: { value: new THREE.Color(rim) }, uRimStrength: { value: rimStrength },
  };
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, mat.userData.uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vToothPos;\nvarying vec3 vWNormal;\nvarying vec3 vWPos;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvToothPos = position;")
      .replace("#include <worldpos_vertex>", "#include <worldpos_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvWNormal = normalize(mat3(modelMatrix) * objectNormal);");
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>
        uniform float uTime; uniform sampler2D uNoise; uniform float uPulse; uniform vec3 uPulseColor; uniform vec3 uRim; uniform float uRimStrength;
        varying vec3 vToothPos; varying vec3 vWNormal; varying vec3 vWPos;`)
      .replace("#include <color_fragment>", `#include <color_fragment>
        float enamelNoise = texture(uNoise, vToothPos.xy * 0.55 + vToothPos.zx * 0.35).r;
        diffuseColor.rgb *= 0.9 + 0.12 * enamelNoise;                       // vetas del esmalte
        diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * vec3(1.0, 0.93, 0.82), smoothstep(0.1, -0.6, vToothPos.y)); // raíz más cálida`)
      .replace("#include <emissivemap_fragment>", `#include <emissivemap_fragment>
        vec3 viewDir = normalize(cameraPosition - vWPos);
        float fres = pow(1.0 - max(dot(viewDir, normalize(vWNormal)), 0.0), 3.0);
        totalEmissiveRadiance += uRim * fres * uRimStrength;              // contorno con el color del tema
        float beat = 0.5 + 0.5 * sin(uTime * 3.2);
        totalEmissiveRadiance += uPulseColor * uPulse * (0.18 + 0.32 * beat);  // pulso en piezas afectadas`);
  };
  mat.customProgramCacheKey = () => "enamel-v2";
  return mat;
}

// ---------- escena base ----------
export function createStage(container, { fov = 35, shadows = true } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = shadows;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(fov, 1, 0.1, 100);

  // carga coordinada: textura de ruido del esmalte + entorno de reflejos
  const manager = new THREE.LoadingManager();
  const ready = new Promise((resolve) => { manager.onLoad = resolve; manager.onError = () => resolve(); });
  if (!shared.noise.value) {
    const tex = new THREE.TextureLoader(manager).load("/static/img/noise.png");
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping; // dato escalar: NoColorSpace
    shared.noise.value = tex;
  } else {
    manager.itemStart("noop"); manager.itemEnd("noop");
  }
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  scene.environment = pmrem.fromScene(room, 0.04).texture;
  scene.environmentIntensity = 0.55;
  room.dispose(); pmrem.dispose();

  // luces: cielo/suelo con colores del tema, principal con sombra, contorno de color
  const hemi = new THREE.HemisphereLight(0xffffff, 0x888888, 1.1);
  const key = new THREE.DirectionalLight(0xffffff, 2.4);
  key.position.set(3, 6, 5);
  key.castShadow = shadows;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.normalBias = 0.02;
  Object.assign(key.shadow.camera, { left: -5, right: 5, top: 5, bottom: -5, near: 0.5, far: 20 });
  const rim = new THREE.DirectionalLight(0xffffff, 1.6);
  rim.position.set(-4, 2, -5);
  scene.add(hemi, key, rim);

  const lights = { hemi, key, rim };
  const applyTheme = () => {
    hemi.color.set(css("--scene-c"));
    hemi.groundColor.set(css("--scene-b"));
    rim.color.set(css("--scene-a"));
  };
  applyTheme();

  const resize = () => {
    const w = container.clientWidth || 1, h = container.clientHeight || 1;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(container);
  resize();

  // pausa cuando no está en pantalla
  let visible = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { threshold: 0.01 }).observe(container);

  const timer = new THREE.Timer();
  timer.connect(document);
  const loop = (fn) => renderer.setAnimationLoop(() => {
    if (!visible) return;
    timer.update();
    if (!reduceMotion) shared.time.value = timer.getElapsed();
    fn(timer.getDelta(), timer.getElapsed());
    renderer.render(scene, camera);
  });

  return { THREE, renderer, scene, camera, lights, ready, loop, applyTheme };
}

// sombra de contacto barata (plano con degradado radial)
export function contactShadow(size = 4, opacity = 0.35) {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, `rgba(0,0,0,${opacity})`);
  grd.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2;
  return m;
}

export function hasWebGL() {
  try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); }
  catch (_) { return false; }
}
