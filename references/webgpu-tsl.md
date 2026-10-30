# WebGPURenderer & Three.js Shading Language (TSL)

In Three.js r150+, WebGPU support has evolved into a production-ready rendering pipeline. Shaders are written in **TSL (Three.js Shading Language)**, an expressive node-based language that cross-compiles to WGSL (WebGPU) and GLSL (WebGL2 fallback).

---

## 1. WebGPURenderer Initialization Standard

```javascript
import * as THREE from 'three/webgpu';

// 1. Instantiate renderer
const renderer = new THREE.WebGPURenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

// 2. MANDATORY: Await asynchronous GPU pipeline initialization
await renderer.init();
```

---

## 2. TSL Shader Composition

TSL replaces raw GLSL string templates with type-safe, composable JavaScript functions.

```javascript
import * as THREE from 'three/webgpu';
import { color, texture, uv, time, sin, positionLocal, vec3, Fn } from 'three/tsl';

// Define custom vertex displacement using Fn
const vertexDisplacement = Fn(() => {
  const t = time.mul(2.0);
  const displacement = sin(positionLocal.y.mul(4.0).add(t)).mul(0.15);
  return positionLocal.add(vec3(0, displacement, 0));
});

// Create node-based standard material
const material = new THREE.MeshStandardNodeMaterial();

// Assign procedural node logic to material slots
material.positionNode = vertexDisplacement();
material.colorNode = color(0x38bdf8).mul(sin(time).add(1.5).mul(0.5));
material.roughnessNode = sin(uv().x.mul(10.0)).mul(0.5).add(0.5);

const mesh = new THREE.Mesh(new THREE.TorusKnotGeometry(0.7, 0.2, 128, 32), material);
scene.add(mesh);
```

---

## 3. WebGPU Post-Processing via `RenderPipeline` (r183+)

In WebGPU, `EffectComposer` is NOT used. Use `RenderPipeline` and `pass`:

```javascript
import * as THREE from 'three/webgpu';
import { pass } from 'three/tsl';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';

const renderPipeline = new THREE.RenderPipeline(renderer);
const scenePass = pass(scene, camera);

// Apply bloom node to scene pass output
const scenePassColor = scenePass.getTextureNode();
const bloomEffect = bloom(scenePassColor, 0.7, 0.4, 0.85);

renderPipeline.outputNode = scenePassColor.add(bloomEffect);

renderer.setAnimationLoop(() => {
  renderPipeline.render();
});
```
