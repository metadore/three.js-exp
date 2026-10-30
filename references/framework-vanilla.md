# Vanilla Three.js Implementation Guide

Vanilla Three.js applications (HTML + pure JavaScript without bundlers) use ES Modules and Import Maps.

---

## 1. Import Map Architecture

Modern browsers support native ES modules via `<script type="importmap">`. Do NOT use old `three.min.js` script tags.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Three.js Vanilla Experience</title>
  <style>
    body { margin: 0; overflow: hidden; background: #0f172a; }
    #canvas-container { width: 100vw; height: 100vh; }
  </style>
  <script type="importmap">
  {
    "imports": {
      "three": "https://cdn.jsdelivr.net/npm/three@0.186.0/build/three.module.js",
      "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.186.0/examples/jsm/"
    }
  }
  </script>
</head>
<body>
  <div id="canvas-container"></div>
  <script type="module" src="./main.js"></script>
</body>
</html>
```

---

## 2. Main Entry Point (`main.js`)

```javascript
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const container = document.getElementById('canvas-container');

// 1. Renderer
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(container.clientWidth, container.clientHeight, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
container.appendChild(renderer.domElement);

// 2. Scene & Camera
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
camera.position.set(0, 2, 5);

// 3. Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

// 4. Lighting & Objects
const light = new THREE.DirectionalLight(0xffffff, 2);
light.position.set(3, 5, 2);
scene.add(light);
scene.add(new THREE.AmbientLight(0xffffff, 0.5));

const mesh = new THREE.Mesh(
  new THREE.BoxGeometry(1, 1, 1),
  new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.3 })
);
scene.add(mesh);

// 5. Responsive Resize
window.addEventListener('resize', () => {
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(container.clientWidth, container.clientHeight, false);
});

// 6. Animation Loop
renderer.setAnimationLoop(() => {
  controls.update();
  mesh.rotation.y += 0.01;
  renderer.render(scene, camera);
});
```
