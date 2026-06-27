import * as THREE from "three";
import { OrbitControls } from "./vendor/three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "./vendor/three/examples/jsm/loaders/GLTFLoader.js";

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
  renderer.toneMappingExposure = 1.0;
  renderer.outputColorSpace   = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  // Controls
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping  = true;
  controls.dampingFactor  = 0.07;
  controls.minDistance    = 0.05;

  // ── Lighting ────────────────────────────────────────────────────────────────
  scene.add(new THREE.HemisphereLight(0xffffff, 0x333333, 2.0));

  // Key — broad frontal light to lift anatomical forms.
  const key = new THREE.DirectionalLight(0xffffff, 2.5);
  key.position.set(3.0, 5.0, 4.0);
  scene.add(key);

  // Fill — softer side light that keeps cavities readable.
  const fill = new THREE.DirectionalLight(0xf2f6ff, 0.8);
  fill.position.set(-4.0, 2.0, -3.0);
  scene.add(fill);

  // Rim — subtle separation from the dark stage background.
  const rim = new THREE.DirectionalLight(0xfff3e8, 0.45);
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

  // Fit camera
  const box    = new THREE.Box3().setFromObject(gltf.scene);
  const center = box.getCenter(new THREE.Vector3());
  const size   = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 0.1);

  controls.target.copy(center);
  camera.near = maxDim * 0.005;
  camera.far  = maxDim * 60;
  camera.position.copy(center).add(
    new THREE.Vector3(maxDim * 1.6, maxDim * 0.9, maxDim * 2.0),
  );
  camera.updateProjectionMatrix();
  camera.lookAt(center);
  controls.update();

  // ── Build annotation entries ────────────────────────────────────────────────
  const items = Array.isArray(annotations.annotations) ? annotations.annotations : [];
  annotationList.innerHTML = "";
  labelsLayer.innerHTML    = "";

  // Spread anchors evenly across the mesh surface
  const anchors = buildSurfaceAnchors(gltf.scene, items.length, box, center);

  const labelEntries = items.map((item, idx) => {
    const badge = displayIndex(item, idx);
    const label = annotationLabel(item);

    // ── 3D chip element
    const chip = document.createElement("div");
    chip.className = "annotation-chip";
    chip.innerHTML = `
      <span class="annotation-chip__index">${badge}</span>
      <span class="annotation-chip__label">${label}</span>
    `;
    labelsLayer.appendChild(chip);

    // ── Sidebar list item
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="annotation-index">${badge}</span>
      <span class="annotation-label">${label}</span>
    `;
    annotationList.appendChild(li);

    // World position: prefer FPS surface anchor, then JSON anchor_relative, then fallback ring
    let world;
    if (anchors[idx]) {
      world = anchors[idx].clone();
    } else if (item.anchor_relative) {
      const [x, y, z] = item.anchor_relative;
      // GLB uses Y-up (Blender's -90° X rotation on export), so Blender Z → Three Y
      world = center.clone().add(new THREE.Vector3(x, z, -y));
    } else {
      const angle = (idx / Math.max(1, items.length)) * Math.PI * 2;
      world = center.clone().add(new THREE.Vector3(
        Math.cos(angle) * maxDim * 0.4,
        Math.sin(idx) * maxDim * 0.3,
        Math.sin(angle) * maxDim * 0.4,
      ));
    }

    return { badge, label, world, element: chip };
  });

  // ── Labels toggle ────────────────────────────────────────────────────────────
  labelsToggle.addEventListener("change", () => {
    labelsLayer.style.display = labelsToggle.checked ? "block" : "none";
  });

  // ── Label layout ─────────────────────────────────────────────────────────────
  // Project each anchor to screen, hide those that overlap already-placed chips.
  // Uses a simple rectangle-occupancy list (fast enough for <100 labels).
  function layoutLabels() {
    const W = container.clientWidth;
    const H = container.clientHeight;
    const PAD = 10; // px padding around each chip rect

    const visible = labelEntries
      .map(entry => {
        const v = entry.world.clone().project(camera);
        return {
          entry,
          x: (v.x * 0.5 + 0.5) * W,
          y: (-v.y * 0.5 + 0.5) * H,
          depth: v.z,
          inFrustum: v.z < 1.0,
        };
      })
      .filter(p => p.inFrustum)
      .sort((a, b) => a.depth - b.depth);   // front-to-back priority

    const occupied = [];

    for (const { entry, x, y } of visible) {
      entry.element.style.left = `${x}px`;
      entry.element.style.top  = `${y}px`;
      entry.element.classList.remove("is-hidden");

      const cw = entry.element.offsetWidth  || 150;
      const ch = entry.element.offsetHeight || 36;

      const r = {
        left:   x - cw / 2 - PAD,
        right:  x + cw / 2 + PAD,
        top:    y - ch / 2 - PAD,
        bottom: y + ch / 2 + PAD,
      };

      const clash = occupied.some(o =>
        !(r.right < o.left || r.left > o.right || r.bottom < o.top || r.top > o.bottom),
      );

      if (clash) {
        entry.element.classList.add("is-hidden");
      } else {
        occupied.push(r);
      }
    }

    // Labels not in frustum are always hidden
    labelEntries
      .filter((_, i) => !visible.find(p => p.entry === labelEntries[i]))
      .forEach(e => e.element.classList.add("is-hidden"));
  }

  // ── Resize ────────────────────────────────────────────────────────────────────
  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });

  // ── Render loop ───────────────────────────────────────────────────────────────
  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
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
