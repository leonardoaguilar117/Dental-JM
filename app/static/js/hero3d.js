// Escena del tablero: molar flotante + anillo orbital (ShaderMaterial) + destellos (Points con shader).
import * as THREE from "three";
import { createStage, enamelMaterial, detailedMolarGeometry, contactShadow, css, reduceMotion, hasWebGL } from "./dental3d.js";

const isDark = () => ["arrecife", "grafito"].includes(document.documentElement.dataset.theme);

function mountHero(el) {
  if (!hasWebGL()) { el.classList.add("ready"); return; }
  const stage = createStage(el, { fov: 30 });
  const { scene, camera } = stage;
  camera.position.set(0, 0.6, 8.5);
  camera.lookAt(0, 0.2, 0);

  // ---------- molar ----------
  const tooth = new THREE.Group();
  // molar anatómico: 4 cúspides con surcos, cuello cervical y 3 raíces
  const mat = enamelMaterial({ color: "#f5f1e8", rim: css("--scene-a"), rimStrength: 0.22 });
  mat.roughness = 0.28;
  const molar = new THREE.Mesh(detailedMolarGeometry(), mat);
  molar.castShadow = true;
  molar.scale.setScalar(1.05);
  molar.position.y = 0.25;
  tooth.add(molar);
  scene.add(tooth);

  const floor = contactShadow(3.0, 0.28);
  floor.position.y = -1.6;
  scene.add(floor);

  // ---------- anillo orbital: trazos que recorren el anillo ----------
  const ringMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { uTime: { value: 0 }, uColor: { value: new THREE.Color(css("--scene-a")) }, uColor2: { value: new THREE.Color(css("--scene-b")) } },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */ `
      uniform float uTime; uniform vec3 uColor; uniform vec3 uColor2; varying vec2 vUv;
      void main() {
        float dash = step(0.55, fract(vUv.x * 36.0 - uTime * 0.6));
        float glow = 0.5 + 0.5 * sin(vUv.x * 6.2831 * 2.0 + uTime);
        vec3 col = mix(uColor, uColor2, glow);
        gl_FragColor = vec4(col, dash * 0.85);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(1.75, 0.018, 8, 220), ringMat);
  ring.rotation.set(Math.PI / 2.35, 0.25, 0);
  scene.add(ring);
  const ring2 = new THREE.Mesh(new THREE.TorusGeometry(2.15, 0.01, 6, 220), ringMat);
  ring2.rotation.set(Math.PI / 1.85, -0.4, 0.3);
  scene.add(ring2);

  // ---------- destellos que titilan ----------
  const N = 60;
  const pos = new Float32Array(N * 3), seed = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const r = 1.8 + Math.random() * 1.4, a = Math.random() * Math.PI * 2, y = (Math.random() - 0.5) * 2.6;
    pos.set([Math.cos(a) * r, y, Math.sin(a) * r * 0.6], i * 3);
    seed[i] = Math.random() * 10;
  }
  const pgeo = new THREE.BufferGeometry();
  pgeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  pgeo.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
  const pmat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: isDark() ? THREE.AdditiveBlending : THREE.NormalBlending,
    uniforms: { uTime: { value: 0 }, uColor: { value: new THREE.Color(isDark() ? css("--scene-c") : css("--scene-a")) }, uPixel: { value: Math.min(window.devicePixelRatio, 2) } },
    vertexShader: /* glsl */ `
      attribute float aSeed; uniform float uTime; uniform float uPixel; varying float vA;
      void main() {
        vec3 p = position; p.y += sin(uTime * 0.6 + aSeed) * 0.12;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vA = 0.35 + 0.65 * (0.5 + 0.5 * sin(uTime * 2.0 + aSeed * 3.0));
        gl_PointSize = (10.0 + 8.0 * fract(aSeed)) * uPixel / -mv.z;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor; varying float vA;
      void main() {
        vec2 c = gl_PointCoord - 0.5; float d = length(c);
        float star = smoothstep(0.5, 0.0, d) + smoothstep(0.06, 0.0, abs(c.x)) * smoothstep(0.5, 0.1, abs(c.y)) * 0.6
                   + smoothstep(0.06, 0.0, abs(c.y)) * smoothstep(0.5, 0.1, abs(c.x)) * 0.6;
        gl_FragColor = vec4(uColor, star * vA);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const sparkles = new THREE.Points(pgeo, pmat);
  scene.add(sparkles);

  // ---------- puntero: inclinación con amortiguación ----------
  const goal = { x: 0, y: 0 }, cur = { x: 0, y: 0 };
  el.addEventListener("pointermove", (e) => {
    const r = el.getBoundingClientRect();
    goal.x = ((e.clientX - r.left) / r.width - 0.5) * 0.9;
    goal.y = ((e.clientY - r.top) / r.height - 0.5) * 0.6;
  });
  el.addEventListener("pointerleave", () => { goal.x = goal.y = 0; });

  window.addEventListener("themechange", () => {
    stage.applyTheme();
    mat.userData.uniforms.uRim.value.set(css("--scene-a"));
    ringMat.uniforms.uColor.value.set(css("--scene-a"));
    ringMat.uniforms.uColor2.value.set(css("--scene-b"));
    pmat.uniforms.uColor.value.set(isDark() ? css("--scene-c") : css("--scene-a"));
    pmat.blending = isDark() ? THREE.AdditiveBlending : THREE.NormalBlending;
    pmat.needsUpdate = true;
  });

  stage.loop((dt, t) => {
    cur.x += (goal.x - cur.x) * Math.min(1, dt * 4);
    cur.y += (goal.y - cur.y) * Math.min(1, dt * 4);
    const spin = reduceMotion ? 0.5 : t * 0.3;
    tooth.rotation.set(0.32 + cur.y, spin + cur.x, 0.08);
    tooth.position.y = reduceMotion ? 0.2 : 0.2 + Math.sin(t * 1.1) * 0.07;
    floor.scale.setScalar(1 - (tooth.position.y - 0.2) * 0.8);
    ring.rotation.z = reduceMotion ? 0 : t * 0.25;
    ring2.rotation.z = reduceMotion ? 0 : -t * 0.18;
    ringMat.uniforms.uTime.value = reduceMotion ? 0 : t;
    pmat.uniforms.uTime.value = reduceMotion ? 0 : t;
  });
  stage.ready.then(() => el.classList.add("ready"));
}

document.querySelectorAll("[data-hero3d]").forEach(mountHero);
