import * as THREE from "three";
import { OrbitControls } from "./vendor/three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "./vendor/three/examples/jsm/loaders/GLTFLoader.js";
import { EffectComposer } from "./vendor/three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "./vendor/three/examples/jsm/postprocessing/RenderPass.js";
import { GTAOPass } from "./vendor/three/examples/jsm/postprocessing/GTAOPass.js";
import { OutputPass } from "./vendor/three/examples/jsm/postprocessing/OutputPass.js";

// ─── URL params ──────────────────────────────────────────────────────────────
const params            = new URLSearchParams(window.location.search);
const fallbackModel     = "../exports/glb/liver_test.glb";
const fallbackAnno      = "../exports/annotations/liver_test.annotations.json";
const modelUrl          = params.get("model")       || fallbackModel;
const annotationsUrl    = params.get("annotations") || fallbackAnno;

// ─── DOM refs ────────────────────────────────────────────────────────────────
const container      = document.getElementById("viewer-canvas");
const labelsLayer    = document.getElementById("labels-layer");
const annotationList = document.getElementById("annotation-list");
const partTitle      = document.getElementById("part-title");
const sidebarCopy    = document.querySelector(".sidebar__copy");
const labelsToggle   = document.getElementById("labels-toggle");

// ─── Annotation helpers ───────────────────────────────────────────────────────
function displayIndex(item, idx) {
  return item.index ?? item.display_index ?? idx + 1;
}
function annotationLabel(item) {
  return item.label || item.source_object || item.id || "Unlabeled";
}

// ─── Model framing & materials ────────────────────────────────────────────────
/** Ignore stray helper / degenerate meshes when fitting the camera. */
function computeModelBounds(root) {
  const box = new THREE.Box3();
  root.traverse(obj => {
    if (!obj.isMesh || !obj.visible) return;
    const name = String(obj.name || "").toLowerCase();
    if (/^(mcp_|helper|label|grid)/.test(name)) return;
    const b = new THREE.Box3().setFromObject(obj);
    if (b.isEmpty()) return;
    const s = b.getSize(new THREE.Vector3());
    if (s.x * s.y * s.z < 1e-12) return;
    box.union(b);
  });
  if (box.isEmpty()) box.setFromObject(root);
  return box;
}

/** Move the export so its geometric centre sits at the world origin. */
function centerModelAtOrigin(root, box) {
  const c = box.getCenter(new THREE.Vector3());
  if (c.lengthSq() < 1e-12) return;
  root.position.sub(c);
  root.updateMatrixWorld(true);
  box.translate(c.clone().negate());
}

/** Base tissue tint keyed off the exported part name. */
function partTint(partLabel) {
  const n = String(partLabel || "").toLowerCase();
  if (n.includes("heart")) return new THREE.Color(0.78, 0.48, 0.44);
  if (n.includes("liver")) return new THREE.Color(0.68, 0.42, 0.34);
  if (n.includes("kidney")) return new THREE.Color(0.62, 0.40, 0.36);
  if (n.includes("brain")) return new THREE.Color(0.76, 0.68, 0.66);
  if (n.includes("lung")) return new THREE.Color(0.74, 0.58, 0.56);
  if (n.includes("stomach")) return new THREE.Color(0.74, 0.54, 0.50);
  if (n.includes("skull") || n.includes("bone") || n.includes("femur") || n.includes("tibia")) {
    return new THREE.Color(0.86, 0.82, 0.76);
  }
  return new THREE.Color(0.76, 0.72, 0.68);
}

function hashUnit(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

/**
 * Replace washed-out / unlit GLB materials with readable PBR tissue colours.
 * Multi-mesh organs get subtle per-part hue/lightness variation so crevices
 * and separate structures remain distinguishable.
 */
function applyAnatomicalMaterials(root, partLabel, multiPart) {
  const base = partTint(partLabel);
  root.traverse(obj => {
    if (!obj.isMesh) return;
    const prev = Array.isArray(obj.material) ? obj.material : [obj.material];
    const next = prev.map((mat, idx) => {
      const key = obj.name || String(idx);
      const h = hashUnit(key);
      const color = base.clone();
      if (multiPart) {
        color.offsetHSL((h - 0.5) * 0.06, 0.04, (hashUnit(key + "l") - 0.5) * 0.08);
      }
      const std = new THREE.MeshStandardMaterial({
        color,
        roughness: 0.58,
        metalness: 0.04,
        envMapIntensity: 0.9,
        flatShading: false,
      });
      if (mat) {
        if (mat.map) std.map = mat.map;
        if (mat.normalMap) std.normalMap = mat.normalMap;
        if (mat.aoMap) std.aoMap = mat.aoMap;
      }
      return std;
    });
    obj.material = Array.isArray(obj.material) ? next : next[0];
  });
}

/**
 * Default anterior 3/4 view with the whole organ inside the frustum.
 * Returns the saved home pose used by "Reset view".
 */
function fitCameraToBounds(camera, controls, box, frame, aspect) {
  const center = box.getCenter(new THREE.Vector3());
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const radius = Math.max(sphere.radius, 0.05);

  const dir = frame.ant.clone().normalize();
  const up = frame.up.clone().normalize();
  const vFov = THREE.MathUtils.degToRad(camera.fov);
  const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
  const dist = Math.max(
    radius / Math.sin(vFov / 2),
    radius / Math.sin(hFov / 2),
  ) * 1.28;

  camera.up.copy(up);
  camera.position.copy(center)
    .addScaledVector(dir, dist)
    .addScaledVector(up, dist * 0.22);
  controls.target.copy(center);
  controls.minDistance = radius * 0.35;
  controls.maxDistance = radius * 12;
  camera.near = Math.max(radius * 0.008, 0.01);
  camera.far = radius * 200;
  camera.updateProjectionMatrix();
  camera.lookAt(center);
  controls.update();

  return {
    center,
    radius,
    homePos: camera.position.clone(),
    homeUp: camera.up.clone(),
  };
}

/** Anatomical frame: +Y superior, +Z anterior, ±X left/right (auto-calibrated). */
function buildAnatomicalFrame(root) {
  const up = new THREE.Vector3(0, 1, 0);
  const ant = new THREE.Vector3(0, 0, 1);
  let lx = 0, ln = 0, rx = 0, rn = 0;
  root.traverse(o => {
    if (!o.isMesh) return;
    const n = String(o.name || "").toLowerCase();
    const isL = /\.l(\.\d+)?$/.test(n) || /\bleft\b/.test(n);
    const isR = /\.r(\.\d+)?$/.test(n) || /\bright\b/.test(n);
    if (isL === isR) return;
    const b = new THREE.Box3().setFromObject(o);
    if (b.isEmpty()) return;
    const cc = b.getCenter(new THREE.Vector3());
    if (isL) { lx += cc.x; ln++; } else { rx += cc.x; rn++; }
  });
  const leftSign = (ln && rn) ? (((lx / ln) >= (rx / rn)) ? 1 : -1) : 1;
  return { up, ant, left: new THREE.Vector3(leftSign, 0, 0) };
}

// ─── Surface sampling ─────────────────────────────────────────────────────────
/**
 * Sample up to `limit` vertex positions from a mesh in world space.
 */
function sampleMeshSurface(mesh, limit) {
  const pos = mesh.geometry.attributes.position;
  if (!pos) return [];
  const total = pos.count;
  const step  = Math.max(1, Math.floor(total / limit));
  const out   = [];
  const v     = new THREE.Vector3();
  for (let i = 0; i < total && out.length < limit; i += step) {
    v.set(pos.getX(i), pos.getY(i), pos.getZ(i)).applyMatrix4(mesh.matrixWorld);
    out.push(v.clone());
  }
  return out;
}

/**
 * Farthest-Point Sampling — picks `count` maximally-spread points from a
 * candidate pool so labels never pile up in one area.
 */
function farthestPointSample(candidates, count) {
  if (candidates.length === 0 || count === 0) return [];
  // seed at the centroid-farthest point
  let seed = candidates[0];
  let maxD = -1;
  const centroid = candidates
    .reduce((acc, p) => acc.add(p), new THREE.Vector3())
    .divideScalar(candidates.length);
  for (const c of candidates) {
    const d = c.distanceTo(centroid);
    if (d > maxD) { maxD = d; seed = c; }
  }

  const selected = [seed];
  // distances from each candidate to its nearest selected point
  const dist = candidates.map(c => c.distanceTo(seed));

  while (selected.length < count) {
    let best = null, bestD = -1;
    for (let i = 0; i < candidates.length; i++) {
      if (dist[i] > bestD) { bestD = dist[i]; best = i; }
    }
    if (best === null) break;
    const chosen = candidates[best];
    selected.push(chosen);
    // update distances
    for (let i = 0; i < candidates.length; i++) {
      const d = candidates[i].distanceTo(chosen);
      if (d < dist[i]) dist[i] = d;
    }
  }
  return selected;
}

/**
 * Build `count` world-space anchor points spread across all meshes in the scene.
 */
function buildSurfaceAnchors(sceneRoot, count, box, center) {
  if (count === 0) return [];

  // collect surface candidates from every mesh
  const candidates = [];
  const perMesh = Math.max(50, count * 15);
  sceneRoot.traverse(obj => {
    if (obj.isMesh) candidates.push(...sampleMeshSurface(obj, perMesh));
  });

  if (candidates.length >= count) {
    return farthestPointSample(candidates, count);
  }

  // geometric fallback — spread around the bounding box surface
  const size = box.getSize(new THREE.Vector3());
  return Array.from({ length: count }, (_, i) => {
    const t     = i / Math.max(1, count - 1);
    const angle = t * Math.PI * 2;
    return center.clone().add(new THREE.Vector3(
      Math.cos(angle) * size.x * 0.42,
      (t - 0.5) * size.y * 0.9,
      Math.sin(angle) * size.z * 0.42,
    ));
  });
}

// ─── Image-based lighting ──────────────────────────────────────────────────────
/**
 * Build a prefiltered environment map from a procedural studio gradient.
 *
 * Uses only three.js core (PMREMGenerator) so the viewer stays dependency-free
 * and works offline — no RoomEnvironment addon or external HDRI required. The
 * vertical gradient (bright cool sky → neutral horizon → dark floor) yields soft
 * directional ambient light and gentle reflections on the PBR bone materials.
 */
function buildEnvironmentTexture(renderer) {
  const width = 512;
  const height = 256;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");

  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0.0, "#e6ecf3"); // sky top
  gradient.addColorStop(0.45, "#c2c9d1"); // upper horizon
  gradient.addColorStop(0.55, "#a3a9b0"); // horizon
  gradient.addColorStop(1.0, "#33363b"); // floor (darker → downward occlusion feel)
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  const equirect = new THREE.CanvasTexture(canvas);
  equirect.mapping = THREE.EquirectangularReflectionMapping;
  equirect.colorSpace = THREE.SRGBColorSpace;

  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();
  const envTarget = pmrem.fromEquirectangular(equirect);

  equirect.dispose();
  pmrem.dispose();
  return envTarget.texture;
}

// ─── Main ─────────────────────────────────────────────────────────────────────
async function init() {
  // Scene
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x18191d);

  // Camera
  const camera = new THREE.PerspectiveCamera(
    42, container.clientWidth / container.clientHeight, 0.01, 200,
  );

  // Renderer — tone-mapping is the key to correct material colour
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.toneMapping        = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;
  renderer.outputColorSpace   = THREE.SRGBColorSpace;
  // Per-material clipping planes (cross-section tool) clip only the model, not
  // the reference guides.
  renderer.localClippingEnabled = true;
  // Soft self-shadowing gives crevice/contact depth (an AO-like cue) so bones
  // read with volume instead of looking flat/chalky.
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type    = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  // Image-based lighting: a prefiltered procedural environment drives soft
  // ambient light + subtle specular reflections on the PBR materials. This is
  // the main lever that closes the "chalky" gap versus the Z-Anatomy renderer.
  scene.environment = buildEnvironmentTexture(renderer);

  // Controls
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping  = true;
  controls.dampingFactor  = 0.07;
  controls.minDistance    = 0.05;

  // ── Lighting ────────────────────────────────────────────────────────────────
  // IBL now supplies most of the ambient fill, so direct lights are dialled back
  // to avoid washing the materials out.
  scene.add(new THREE.HemisphereLight(0xffffff, 0x2a2d33, 0.35));

  // Key — broad frontal light to lift anatomical forms; casts the soft shadows
  // that give crevice depth. Shadow camera is fitted to the model after load.
  const key = new THREE.DirectionalLight(0xffffff, 2.0);
  key.position.set(3.0, 5.0, 4.0);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.02;
  scene.add(key);
  scene.add(key.target);

  // Fill — softer side light that keeps cavities readable.
  const fill = new THREE.DirectionalLight(0xf2f6ff, 0.45);
  fill.position.set(-4.0, 2.0, -3.0);
  scene.add(fill);

  // Rim — subtle separation from the dark stage background.
  const rim = new THREE.DirectionalLight(0xfff3e8, 0.35);
  rim.position.set(0.0, -2.5, -4.0);
  scene.add(rim);
  // ── End lighting ────────────────────────────────────────────────────────────

  // Load annotations
  const annoRes = await fetch(annotationsUrl);
  if (!annoRes.ok) throw new Error(`Cannot load annotations: ${annotationsUrl}`);
  const annotations    = await annoRes.json();
  partTitle.textContent = annotations.part_label ?? "Anatomy";

  // Load model
  const loader = new GLTFLoader();
  const gltf   = await loader.loadAsync(modelUrl);
  scene.add(gltf.scene);

  // Derive bounds from real mesh geometry only (stray helpers must not skew framing).
  const box = computeModelBounds(gltf.scene);
  const center = box.getCenter(new THREE.Vector3());
  const size   = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 0.1);

  let meshCount = 0;
  gltf.scene.traverse(o => { if (o.isMesh) meshCount++; });
  applyAnatomicalMaterials(gltf.scene, annotations.part_label, meshCount > 1);

  const frame = buildAnatomicalFrame(gltf.scene);
  const aspect = container.clientWidth / container.clientHeight;
  const viewHome = fitCameraToBounds(camera, controls, box, frame, aspect);

  // Self-shadowing gives contact/crevice depth between adjacent structures.
  gltf.scene.traverse(obj => {
    if (!obj.isMesh) return;
    obj.castShadow = true;
    obj.receiveShadow = true;
  });

  // Fit the key light's shadow frustum to the model so the shadow map resolves
  // fine crevices instead of covering empty space.
  key.position.copy(center).add(new THREE.Vector3(maxDim * 3, maxDim * 5, maxDim * 4));
  key.target.position.copy(center);
  key.target.updateMatrixWorld();
  const shadowCam = key.shadow.camera;
  shadowCam.near   = maxDim * 0.05;
  shadowCam.far    = maxDim * 12;
  shadowCam.left   = -maxDim * 1.2;
  shadowCam.right  =  maxDim * 1.2;
  shadowCam.top    =  maxDim * 1.2;
  shadowCam.bottom = -maxDim * 1.2;
  shadowCam.updateProjectionMatrix();

  // ── Post-processing: true screen-space ambient occlusion (GTAO) ───────────────
  // RenderPass (beauty) → GTAOPass (ambient occlusion in crevices/contacts) →
  // OutputPass (applies ACES tone mapping + sRGB once, at the end). Intermediate
  // composer targets are linear HDR, so tone mapping is not double-applied.
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));

  const gtaoPass = new GTAOPass(scene, camera, container.clientWidth, container.clientHeight);
  gtaoPass.output = GTAOPass.OUTPUT.Default;
  // World-space AO radius scaled to the part so contact darkening looks the same
  // whether the export is a tiny ossicle or a full limb.
  gtaoPass.updateGtaoMaterial({
    radius: maxDim * 0.05,
    distanceExponent: 1.0,
    thickness: maxDim * 0.1,
    scale: 1.35,
    samples: 16,
    screenSpaceRadius: false,
  });
  gtaoPass.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 4, rings: 2, samples: 16 });
  composer.addPass(gtaoPass);

  composer.addPass(new OutputPass());
  // ── End post-processing ───────────────────────────────────────────────────────

  // ── Build annotation entries ────────────────────────────────────────────────
  const items = Array.isArray(annotations.annotations) ? annotations.annotations : [];
  annotationList.innerHTML = "";
  labelsLayer.innerHTML    = "";

  // SVG overlay carrying leader lines + surface dots so each label reads as
  // "attached" to a specific point on the bone.
  const svgNS = "http://www.w3.org/2000/svg";
  const leaderSvg = document.createElementNS(svgNS, "svg");
  leaderSvg.setAttribute("class", "leader-svg");
  container.parentElement.insertBefore(leaderSvg, labelsLayer);

  // Dense surface point cloud, used to snap each annotation onto the mesh.
  const surfacePoints = [];
  gltf.scene.traverse(obj => {
    if (obj.isMesh) surfacePoints.push(...sampleMeshSurface(obj, 4000));
  });

  function nearestSurface(p) {
    let best = null, bestSq = Infinity;
    for (const s of surfacePoints) {
      const d = p.distanceToSquared(s);
      if (d < bestSq) { bestSq = d; best = s; }
    }
    return { point: best, dist: best ? Math.sqrt(bestSq) : Infinity };
  }

  // Named-mesh index. Z-Anatomy exports each structure as a separately named
  // mesh, so matching an annotation to its mesh by name yields a reliable anchor
  // even when the JSON marker positions are degenerate (many Z-Anatomy ".i"
  // marker objects collapse onto the origin, which is why heart/femur labels
  // used to pile up at one point).
  function normalizeName(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/\.\d+$/, "")           // ".001" duplicate suffix
      .replace(/\.[a-z]{1,2}$/, "")    // Z-Anatomy suffixes (.l/.r/.i/.j/.t/.g/.s)
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  const meshIndex = [];
  gltf.scene.traverse(obj => {
    if (!obj.isMesh) return;
    obj.updateWorldMatrix(true, false);
    const b = new THREE.Box3().setFromObject(obj);
    if (b.isEmpty()) return;
    const c = b.getCenter(new THREE.Vector3());
    meshIndex.push({
      name: normalizeName(obj.name),
      obj,
      center: c.clone(),
      centerLocal: obj.worldToLocal(c.clone()),   // follows the mesh when exploded
    });
  });

  function matchMeshByName(item) {
    const queries = [item.source_object, item.label]
      .filter(Boolean).map(normalizeName).filter(Boolean);
    for (const q of queries) {
      const hit = meshIndex.find(m => m.name === q);
      if (hit) return hit;
    }
    // Substring matching only for multi-mesh models, and only for specific
    // (longer) names, so a landmark label never matches a generic parent mesh.
    if (meshIndex.length > 1) {
      for (const q of queries) {
        if (q.length < 4) continue;
        const hit = meshIndex.find(m => m.name && (m.name.includes(q) || q.includes(m.name)));
        if (hit) return hit;
      }
    }
    return null;
  }

  // Convert a JSON anchor (Blender Z-up, relative to the selection centre) into a
  // Three.js world position (Y-up). GLB export applies a -90° X rotation, so
  // Blender (x, y, z) → Three (x, z, -y).
  function anchorFromJson(item) {
    if (Array.isArray(item.anchor_relative)) {
      const [x, y, z] = item.anchor_relative;
      return center.clone().add(new THREE.Vector3(x, z, -y));
    }
    if (Array.isArray(item.anchor_world)) {
      const [x, y, z] = item.anchor_world;
      return new THREE.Vector3(x, z, -y);
    }
    return null;
  }

  const KEEP_DIST  = maxDim * 0.18;
  const MAX_LABELS = 24;

  // Resolve one world-space anchor per annotation. Priority:
  //   quality 2 — exact named-mesh match (robust for organs with many named
  //               sub-meshes, e.g. the heart's papillary muscles / valves);
  //   quality 1 — JSON marker snapped to the surface when it is genuinely close;
  //   quality 0 — could not be placed reliably; spread across the surface below.
  const resolved = items.map(item => {
    const mesh = matchMeshByName(item);
    if (mesh) {
      const samplesLocal = sampleMeshSurface(mesh.obj, 80).map(p =>
        mesh.obj.worldToLocal(p.clone()),
      );
      return {
        item, label: annotationLabel(item), anchor: mesh.center.clone(), dist: 0, quality: 2,
        meshObj: mesh.obj, centerLocal: mesh.centerLocal, meshSamplesLocal: samplesLocal,
      };
    }
    const a = anchorFromJson(item);
    if (a) {
      const snap = nearestSurface(a);
      if (snap.point && snap.dist <= KEEP_DIST) {
        return {
          item, label: annotationLabel(item), anchor: snap.point.clone(), dist: snap.dist, quality: 1,
          anchorLocal: gltf.scene.worldToLocal(snap.point.clone()),
        };
      }
    }
    return { item, label: annotationLabel(item), anchor: null, dist: Infinity, quality: 0 };
  });

  // Spread the unplaced ones across the surface so they never pile up at one
  // point (which is what caused the "all labels vanish when rotating" bug — a
  // single clustered anchor left the frustum together).
  const unplaced = resolved.filter(r => !r.anchor);
  if (unplaced.length) {
    const spread = buildSurfaceAnchors(gltf.scene, unplaced.length, box, center);
    unplaced.forEach((r, i) => {
      const pt = (spread[i] || center).clone();
      r.anchor = pt;
      r.anchorLocal = gltf.scene.worldToLocal(pt.clone());
    });
  }

  let kept = resolved
    .filter(r => r.anchor)
    .sort((a, b) => (b.quality - a.quality) || (a.dist - b.dist))
    .slice(0, MAX_LABELS);

  const labelEntries = kept.map((entry, i) => {
    const badge = i + 1;   // clean sequential numbering
    const label = entry.label;

    const chip = document.createElement("div");
    chip.className = "annotation-chip";
    chip.innerHTML = `
      <span class="annotation-chip__index">${badge}</span>
      <span class="annotation-chip__label">${label}</span>
    `;
    labelsLayer.appendChild(chip);

    const li = document.createElement("li");
    li.innerHTML = `
      <span class="annotation-index">${badge}</span>
      <span class="annotation-label">${label}</span>
    `;
    annotationList.appendChild(li);

    const line = document.createElementNS(svgNS, "line");
    line.setAttribute("class", "leader-line");
    leaderSvg.appendChild(line);

    const dot = document.createElementNS(svgNS, "circle");
    dot.setAttribute("class", "leader-dot");
    dot.setAttribute("r", "3.5");
    leaderSvg.appendChild(dot);

    return {
      badge, label, world: entry.anchor, element: chip, line, dot,
      meshObj: entry.meshObj || null,
      centerLocal: entry.centerLocal || null,
      meshSamplesLocal: entry.meshSamplesLocal || null,
      anchorLocal: entry.anchorLocal || null,
    };
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // Reference frame & orientation aids
  // Borrowed from how spacecraft / CAD assemblies are visualised: a body-fixed
  // frame (anatomical axes), a ground reference (grid + shadow), a bounding
  // envelope with real dimensions, a camera-facing backdrop, and a corner
  // orientation gizmo.
  // ═══════════════════════════════════════════════════════════════════════════

  // Canvas-textured sprite for axis / scale labels.
  function makeTextSprite(text, color = "#e6ecf3", bg = "rgba(20,22,26,0.72)") {
    const pad = 12, font = 44;
    const c = document.createElement("canvas");
    const g2 = c.getContext("2d");
    g2.font = `600 ${font}px system-ui, sans-serif`;
    const w = Math.ceil(g2.measureText(text).width) + pad * 2;
    const h = font + pad * 2;
    c.width = w; c.height = h;
    g2.font = `600 ${font}px system-ui, sans-serif`;
    g2.fillStyle = bg;
    if (g2.roundRect) { g2.beginPath(); g2.roundRect(0, 0, w, h, 12); g2.fill(); }
    else g2.fillRect(0, 0, w, h);
    g2.fillStyle = color;
    g2.textBaseline = "middle"; g2.textAlign = "center";
    g2.fillText(text, w / 2, h / 2);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    const spr = new THREE.Sprite(new THREE.SpriteMaterial({
      map: tex, transparent: true, depthTest: false, depthWrite: false,
    }));
    spr.scale.set(w / h, 1, 1);
    return spr;
  }

  // Anatomical frame (+Y superior, +Z anterior) — built earlier for camera fit.
  // frame variable is in outer init scope.

  const guides = new THREE.Group();
  guides.visible = false;
  scene.add(guides);
  const floorY = box.min.y;

  // Soft shadow only — no grid, bounding box, or scale bar (keeps focus on the organ).
  const shadowPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(maxDim * 8, maxDim * 8),
    new THREE.ShadowMaterial({ opacity: 0.22 }),
  );
  shadowPlane.rotation.x = -Math.PI / 2;
  shadowPlane.position.set(center.x, floorY, center.z);
  shadowPlane.receiveShadow = true;
  guides.add(shadowPlane);

  // — Camera-facing cyclorama backdrop (always sits behind the model) —
  const backdropTex = (() => {
    const cnv = document.createElement("canvas");
    cnv.width = 16; cnv.height = 256;
    const g = cnv.getContext("2d");
    const grad = g.createLinearGradient(0, 0, 0, 256);
    grad.addColorStop(0, "#2b2f36");
    grad.addColorStop(1, "#0f1013");
    g.fillStyle = grad;
    g.fillRect(0, 0, 16, 256);
    const t = new THREE.CanvasTexture(cnv);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  })();
  const backdrop = new THREE.Mesh(
    new THREE.PlaneGeometry(maxDim * 12, maxDim * 12),
    new THREE.MeshBasicMaterial({ map: backdropTex, depthWrite: false }),
  );
  backdrop.renderOrder = -1;
  guides.add(backdrop);
  function updateBackdrop() {
    const dir = camera.position.clone().sub(controls.target);
    if (dir.lengthSq() === 0) return;
    dir.normalize();
    backdrop.position.copy(controls.target).addScaledVector(dir, -maxDim * 4.5);
    backdrop.lookAt(camera.position);
  }
  updateBackdrop();

  const mm = v => Math.round(v * 1000);
  const dimText = `${mm(size.x)} × ${mm(size.y)} × ${mm(size.z)} mm (L×H×D)`;
  const gizmoScene = new THREE.Scene();
  const gizmoCam = new THREE.PerspectiveCamera(50, 1, 0.1, 10);
  const axisDefs = [
    { dir: frame.up,   pos: "S", neg: "I", color: 0x6fd3c7 },
    { dir: frame.ant,  pos: "A", neg: "P", color: 0xf0b357 },
    { dir: frame.left, pos: "L", neg: "R", color: 0xb98cff },
  ];
  for (const ax of axisDefs) {
    const d = ax.dir.clone().normalize();
    gizmoScene.add(new THREE.ArrowHelper(d, new THREE.Vector3(), 1, ax.color, 0.28, 0.16));
    gizmoScene.add(new THREE.ArrowHelper(d.clone().negate(), new THREE.Vector3(), 1, ax.color, 0.28, 0.16));
    const sp = makeTextSprite(ax.pos, "#0b0c0e", "rgba(230,236,243,0.95)");
    sp.position.copy(d).multiplyScalar(1.3); sp.scale.multiplyScalar(0.5); gizmoScene.add(sp);
    const sn = makeTextSprite(ax.neg, "#0b0c0e", "rgba(230,236,243,0.95)");
    sn.position.copy(d).multiplyScalar(-1.3); sn.scale.multiplyScalar(0.5); gizmoScene.add(sn);
  }
  function renderGizmo() {
    const dir = camera.position.clone().sub(controls.target);
    if (dir.lengthSq() === 0) return;
    gizmoCam.position.copy(dir.normalize().multiplyScalar(3.2));
    gizmoCam.up.copy(camera.up);
    gizmoCam.lookAt(0, 0, 0);
    const s = Math.round(Math.min(140, Math.min(container.clientWidth, container.clientHeight) * 0.22));
    const m = 12;
    const prevAutoClear = renderer.autoClear;
    // Draw over the composited frame: keep colour, only reset depth inside the
    // gizmo's scissor rect so the triad isn't occluded by the (already drawn)
    // scene. autoClear must be off or render() would wipe the whole image.
    renderer.autoClear = false;
    renderer.setScissorTest(true);
    renderer.setScissor(m, m, s, s);
    renderer.setViewport(m, m, s, s);
    renderer.clearDepth();
    renderer.render(gizmoScene, gizmoCam);
    renderer.setScissorTest(false);
    renderer.setViewport(0, 0, container.clientWidth, container.clientHeight);
    renderer.autoClear = prevAutoClear;
  }

  // ── Cross-section (clipping) & exploded view ────────────────────────────────
  const parts = [];
  gltf.scene.traverse(o => { if (o.isMesh) parts.push(o); });

  // Z-Anatomy per-mesh cross-section flags (present on newly exported JSON).
  const meshMeta = annotations.mesh_metadata || {};
  const homeVisible = new Map(parts.map(p => [p, p.visible]));

  // Cache rest transforms + outward explode direction (in each part's parent
  // local space) so the exploded view is fully reversible.
  for (const p of parts) {
    p.updateWorldMatrix(true, false);
    const b = new THREE.Box3().setFromObject(p);
    const cw = b.isEmpty() ? p.getWorldPosition(new THREE.Vector3()) : b.getCenter(new THREE.Vector3());
    const dirW = cw.clone().sub(center);
    if (dirW.lengthSq() < 1e-9) dirW.set(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5);
    const pInv = new THREE.Matrix4().copy(p.parent.matrixWorld).invert();
    p.userData._home = p.position.clone();
    p.userData._explodeDir = dirW.clone().transformDirection(pInv).normalize();
    p.userData._explodeUp = frame.up.clone().transformDirection(pInv).normalize();
    p.userData._explodeAnt = frame.ant.clone().transformDirection(pInv).normalize();
    p.userData._explodeLeft = frame.left.clone().transformDirection(pInv).normalize();
  }

  let explodeFactor = 0;
  let explodeMode = "radial";
  function setExplode(factor, mode = explodeMode) {
    explodeFactor = factor;
    explodeMode = mode;
    const spread = maxDim * 0.6 * factor;
    for (const p of parts) {
      if (!p.userData._home) continue;
      let dir = p.userData._explodeDir;
      if (mode === "superior") dir = p.userData._explodeUp;
      else if (mode === "anterior") dir = p.userData._explodeAnt;
      else if (mode === "lateral") dir = p.userData._explodeLeft;
      p.position.copy(p.userData._home).addScaledVector(dir, spread);
    }
  }

  // Project the model AABB onto an anatomical axis for plane sliding.
  function projectBoundsAlong(axis) {
    const n = axis.clone().normalize();
    const corners = [
      new THREE.Vector3(box.min.x, box.min.y, box.min.z),
      new THREE.Vector3(box.max.x, box.min.y, box.min.z),
      new THREE.Vector3(box.min.x, box.max.y, box.min.z),
      new THREE.Vector3(box.max.x, box.max.y, box.min.z),
      new THREE.Vector3(box.min.x, box.min.y, box.max.z),
      new THREE.Vector3(box.max.x, box.min.y, box.max.z),
      new THREE.Vector3(box.min.x, box.max.y, box.max.z),
      new THREE.Vector3(box.max.x, box.max.y, box.max.z),
    ];
    let mn = Infinity, mx = -Infinity;
    for (const c of corners) {
      const d = c.dot(n);
      mn = Math.min(mn, d);
      mx = Math.max(mx, d);
    }
    return { min: mn, max: mx, normal: n };
  }

  const anatomicalPlanes = {
    sagittal:   { label: "Sagittal",   axis: frame.left, crossKey: "Cross-section-X" },
    coronal:    { label: "Coronal",    axis: frame.ant,  crossKey: "Cross-section-Y" },
    transverse: { label: "Transverse", axis: frame.up,   crossKey: "Cross-section-Z" },
  };

  // Collect unique model materials (guides keep their own materials → unclipped).
  const modelMaterials = [];
  for (const p of parts) {
    const mats = Array.isArray(p.material) ? p.material : [p.material];
    for (const m of mats) {
      if (m && !modelMaterials.includes(m)) {
        m.userData._side = m.side;
        modelMaterials.push(m);
      }
    }
  }

  const clipPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);
  const clipHelper = new THREE.Mesh(
    new THREE.PlaneGeometry(maxDim * 3.2, maxDim * 3.2),
    new THREE.MeshBasicMaterial({
      color: 0x4a90d9,
      transparent: true,
      opacity: 0.14,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  clipHelper.visible = false;
  clipHelper.renderOrder = 2;
  guides.add(clipHelper);

  function applyMeshCrossSectionVisibility(planeKey) {
    if (!planeKey) {
      for (const p of parts) p.visible = homeVisible.get(p) ?? true;
      return;
    }
    const spec = anatomicalPlanes[planeKey];
    if (!spec) return;
    for (const p of parts) {
      const flags = meshMeta[p.name]?.cross_section;
      if (flags && spec.crossKey in flags && Number(flags[spec.crossKey]) === 0) {
        p.visible = false;
      } else {
        p.visible = homeVisible.get(p) ?? true;
      }
    }
  }

  function updateClipHelper(planeKey, t) {
    if (!planeKey || !guides.visible) {
      clipHelper.visible = false;
      return;
    }
    const spec = anatomicalPlanes[planeKey];
    const { min, max, normal } = projectBoundsAlong(spec.axis);
    const along = min + (max - min) * t;
    const point = normal.clone().multiplyScalar(along);
    clipHelper.position.copy(point);
    clipHelper.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    clipHelper.visible = true;
  }

  function applyClip(planeKey, t, flip) {
    if (!planeKey) {
      for (const m of modelMaterials) {
        m.clippingPlanes = [];
        m.side = m.userData._side;
        m.needsUpdate = true;
      }
      applyMeshCrossSectionVisibility(null);
      clipHelper.visible = false;
      return;
    }
    const spec = anatomicalPlanes[planeKey];
    const { min, max, normal } = projectBoundsAlong(spec.axis);
    const along = min + (max - min) * t;
    const point = normal.clone().multiplyScalar(along);
    const planeNormal = flip ? normal.clone() : normal.clone().negate();
    clipPlane.setFromNormalAndCoplanarPoint(planeNormal, point);
    for (const m of modelMaterials) {
      m.clippingPlanes = [clipPlane];
      m.side = THREE.DoubleSide;
      m.needsUpdate = true;
    }
    applyMeshCrossSectionVisibility(planeKey);
    updateClipHelper(planeKey, t);
  }

  // — Sidebar controls: guides toggle, dimensions, snap-view buttons —
  const controlsHost = document.querySelector(".sidebar__controls");
  let curPlane = null, curT = 0.5, curFlip = false;
  if (controlsHost) {
    const guideToggle = document.createElement("label");
    guideToggle.className = "toggle";
    guideToggle.innerHTML = `<input type="checkbox"><span>Show reference guides</span>`;
    guideToggle.querySelector("input").addEventListener("change", e => {
      guides.visible = e.target.checked;
      if (!e.target.checked) clipHelper.visible = false;
      else if (curPlane) updateClipHelper(curPlane, curT);
    });
    controlsHost.appendChild(guideToggle);

    const dimEl = document.createElement("p");
    dimEl.className = "dims-readout";
    dimEl.textContent = `Bounding box: ${dimText}`;
    controlsHost.appendChild(dimEl);

    const viewGrid = document.createElement("div");
    viewGrid.className = "view-grid";
    const homePos = viewHome.homePos;
    const homeUp = viewHome.homeUp;
    function setView(dir, upv) {
      const vFov = THREE.MathUtils.degToRad(camera.fov);
      const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
      const dist = Math.max(
        viewHome.radius / Math.sin(vFov / 2),
        viewHome.radius / Math.sin(hFov / 2),
      ) * 1.28;
      camera.up.copy(upv);
      camera.position.copy(controls.target).addScaledVector(dir.clone().normalize(), dist);
      camera.lookAt(controls.target);
      controls.update();
    }
    const views = [
      ["Anterior",  () => setView(frame.ant, frame.up)],
      ["Posterior", () => setView(frame.ant.clone().negate(), frame.up)],
      ["Left",      () => setView(frame.left, frame.up)],
      ["Right",     () => setView(frame.left.clone().negate(), frame.up)],
      ["Superior",  () => setView(frame.up, frame.ant)],
      ["Inferior",  () => setView(frame.up.clone().negate(), frame.ant)],
    ];
    for (const [name, fn] of views) {
      const b = document.createElement("button");
      b.className = "view-btn";
      b.textContent = name;
      b.addEventListener("click", fn);
      viewGrid.appendChild(b);
    }
    const resetBtn = document.createElement("button");
    resetBtn.className = "view-btn view-btn--reset";
    resetBtn.textContent = "Reset view";
    resetBtn.addEventListener("click", () => {
      camera.up.copy(homeUp);
      camera.position.copy(homePos);
      camera.lookAt(controls.target);
      controls.update();
    });
    viewGrid.appendChild(resetBtn);
    controlsHost.appendChild(viewGrid);

    // — Cross-section tool (anatomical planes) —
    const secWrap = document.createElement("div");
    secWrap.className = "tool-block";
    secWrap.innerHTML = `<p class="tool-title">Cross-section</p>`;
    const axisRow = document.createElement("div");
    axisRow.className = "view-grid";
    const planeBtns = {};
    const secSlider = document.createElement("input");
    const flipBtn = document.createElement("button");
    const planeOptions = [
      ["Off", null],
      ["Sagittal", "sagittal"],
      ["Coronal", "coronal"],
      ["Transverse", "transverse"],
    ];
    for (const [label, key] of planeOptions) {
      const b = document.createElement("button");
      b.className = "view-btn";
      b.textContent = label;
      b.addEventListener("click", () => {
        curPlane = key;
        applyClip(curPlane, curT, curFlip);
        for (const k in planeBtns) planeBtns[k].classList.toggle("is-active", k === label);
        secSlider.disabled = !curPlane;
        flipBtn.disabled = !curPlane;
      });
      planeBtns[label] = b;
      axisRow.appendChild(b);
    }
    planeBtns["Off"].classList.add("is-active");
    secWrap.appendChild(axisRow);

    secSlider.type = "range"; secSlider.min = "0"; secSlider.max = "1"; secSlider.step = "0.01"; secSlider.value = "0.5";
    secSlider.className = "tool-slider"; secSlider.disabled = true;
    secSlider.addEventListener("input", () => {
      curT = parseFloat(secSlider.value);
      if (curPlane) applyClip(curPlane, curT, curFlip);
    });
    secWrap.appendChild(secSlider);

    flipBtn.className = "view-btn"; flipBtn.textContent = "Flip cut side"; flipBtn.disabled = true;
    flipBtn.addEventListener("click", () => {
      curFlip = !curFlip;
      if (curPlane) applyClip(curPlane, curT, curFlip);
    });
    secWrap.appendChild(flipBtn);
    controlsHost.appendChild(secWrap);

    // — Exploded view (multi-part models only) —
    if (parts.length > 1) {
      const expWrap = document.createElement("div");
      expWrap.className = "tool-block";
      expWrap.innerHTML = `
        <p class="tool-title">Exploded view</p>
        <p class="tool-hint">${parts.length} parts — spread along an axis to reveal internals</p>
      `;
      const expModeRow = document.createElement("div");
      expModeRow.className = "view-grid";
      const expModes = [
        ["Radial", "radial"],
        ["Superior", "superior"],
        ["Anterior", "anterior"],
        ["Lateral", "lateral"],
      ];
      const expBtns = {};
      for (const [label, mode] of expModes) {
        const b = document.createElement("button");
        b.className = "view-btn";
        b.textContent = label;
        b.addEventListener("click", () => {
          explodeMode = mode;
          setExplode(explodeFactor, mode);
          for (const k in expBtns) expBtns[k].classList.toggle("is-active", k === label);
        });
        if (mode === "radial") b.classList.add("is-active");
        expBtns[label] = b;
        expModeRow.appendChild(b);
      }
      expWrap.appendChild(expModeRow);

      const expSlider = document.createElement("input");
      expSlider.type = "range"; expSlider.min = "0"; expSlider.max = "1"; expSlider.step = "0.01"; expSlider.value = "0";
      expSlider.className = "tool-slider";
      expSlider.addEventListener("input", () => setExplode(parseFloat(expSlider.value), explodeMode));
      expWrap.appendChild(expSlider);

      const expReset = document.createElement("button");
      expReset.className = "view-btn view-btn--reset";
      expReset.textContent = "Reset assembly";
      expReset.addEventListener("click", () => {
        expSlider.value = "0";
        setExplode(0, explodeMode);
      });
      expWrap.appendChild(expReset);
      controlsHost.appendChild(expWrap);
    }

    const styleEl = document.createElement("style");
    styleEl.textContent = `
      .dims-readout{margin:.55rem 0 .15rem;font-size:.72rem;color:#aab2bd;letter-spacing:.02em}
      .view-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:.4rem}
      .view-btn{background:#212429;color:#dce1e8;border:1px solid #313640;border-radius:8px;padding:6px 8px;font-size:.72rem;cursor:pointer;transition:background .12s,border-color .12s}
      .view-btn:hover{background:#2b2f36;border-color:#4a90d9}
      .view-btn.is-active{background:#2f4257;border-color:#4a90d9;color:#fff}
      .view-btn:disabled{opacity:.4;cursor:default}
      .view-btn--reset{grid-column:1 / -1;background:#26303a}
      .tool-block{margin-top:.7rem;padding-top:.6rem;border-top:1px solid #23262c}
      .tool-title{margin:0 0 .35rem;font-size:.72rem;color:#c7cdd6;font-weight:600;letter-spacing:.03em;text-transform:uppercase}
      .tool-hint{margin:0 0 .35rem;font-size:.68rem;color:#8b939e;line-height:1.35}
      .tool-slider{width:100%;margin-top:.45rem;accent-color:#4a90d9}
      .tool-slider:disabled{opacity:.4}
    `;
    document.head.appendChild(styleEl);
  }

  // ── Labels toggle ────────────────────────────────────────────────────────────
  labelsToggle.addEventListener("change", () => {
    const show = labelsToggle.checked;
    labelsLayer.style.display = show ? "block" : "none";
    leaderSvg.style.display   = show ? "block" : "none";
  });

  // ── Label layout ─────────────────────────────────────────────────────────────
  // Project each structure anchor onto the screen and place the chip directly on
  // that surface point so labels stay glued to the organ as the camera moves.
  function labelAnchorWorld(entry) {
    if (entry.meshObj) {
      entry.meshObj.updateWorldMatrix(true, false);
      const meshCenter = new THREE.Vector3();
      entry.meshObj.getWorldPosition(meshCenter);
      const toCam = camera.position.clone().sub(meshCenter);
      if (toCam.lengthSq() < 1e-9) toCam.set(0, 0, 1);
      toCam.normalize();

      if (entry.meshSamplesLocal?.length) {
        let best = null, bestScore = -Infinity;
        for (const local of entry.meshSamplesLocal) {
          const world = entry.meshObj.localToWorld(local.clone());
          const n = world.clone().sub(meshCenter);
          const nl = n.length();
          if (nl < 1e-6) continue;
          n.divideScalar(nl);
          const score = n.dot(toCam);
          if (score > bestScore) { bestScore = score; best = world; }
        }
        if (best) return best;
      }
      return entry.meshObj.localToWorld(entry.centerLocal.clone());
    }
    if (entry.anchorLocal) {
      return gltf.scene.localToWorld(entry.anchorLocal.clone());
    }
    return entry.world;
  }

  function layoutLabels() {
    const W = container.clientWidth;
    const H = container.clientHeight;
    leaderSvg.setAttribute("width", W);
    leaderSvg.setAttribute("height", H);
    camera.updateMatrixWorld();

    for (const e of labelEntries) {
      e.element.classList.add("is-hidden");
      e.line.style.display = "none";
      e.dot.style.display  = "none";
    }

    for (const entry of labelEntries) {
      const world = labelAnchorWorld(entry);
      const v = world.clone().project(camera);
      if (v.z <= -1 || v.z >= 1) continue;

      const x = (v.x * 0.5 + 0.5) * W;
      const y = (-v.y * 0.5 + 0.5) * H;
      if (x < -20 || x > W + 20 || y < -20 || y > H + 20) continue;

      const ch = entry.element.offsetHeight || 28;
      const lx = x;
      const ly = y - ch * 0.55 - 4;

      entry.element.style.left = `${lx}px`;
      entry.element.style.top  = `${ly}px`;
      entry.element.classList.remove("is-hidden");

      entry.dot.setAttribute("cx", x);
      entry.dot.setAttribute("cy", y);
      entry.dot.style.display = "block";

      entry.line.setAttribute("x1", x);
      entry.line.setAttribute("y1", y);
      entry.line.setAttribute("x2", lx);
      entry.line.setAttribute("y2", ly + ch * 0.35);
      entry.line.style.display = "block";
    }
  }

  // ── Resize ────────────────────────────────────────────────────────────────────
  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
    composer.setSize(container.clientWidth, container.clientHeight);
    gtaoPass.setSize(container.clientWidth, container.clientHeight);
  });

  // ── Render loop ───────────────────────────────────────────────────────────────
  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    if (guides.visible) updateBackdrop();
    composer.render();
    renderGizmo();
    if (labelsToggle.checked) layoutLabels();
  }
  animate();
}

function showError(err) {
  console.error(err);
  partTitle.textContent = "Viewer error";
  sidebarCopy.textContent = err instanceof Error ? err.message : String(err);
}

init().catch(showError);
