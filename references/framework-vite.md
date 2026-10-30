# Three.js in Vite Applications

Vite provides first-class support for ES modules, fast hot module replacement (HMR), and automated asset bundling.

---

## 1. Package Installation & Imports

```bash
npm install three
```

In Vite, addons are imported using the standard `three/addons/*` export map:
```javascript
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js'; // r180+
```

---

## 2. Static Asset Handling in Vite

- Place 3D models (`.glb`, `.gltf`), textures (`.hdr`, `.png`, `.jpg`), and Draco decoders in the `public/` directory:
  ```
  my-vite-project/
  ├── public/
  │   ├── models/
  │   │   └── helmet.glb
  │   └── textures/
  │       └── studio.hdr
  ├── src/
  │   └── scene.js
  ```
- **Referencing in Code**: Use absolute root-relative paths:
  ```javascript
  loader.load('/models/helmet.glb', (gltf) => { ... });
  ```
  Do NOT write `./public/models/...` or relative paths that break when bundled.

---

## 3. Vite HMR (Hot Module Replacement) Teardown

When Vite hot-reloads a module, old WebGL canvases and animation loops must be cleanly disposed to avoid context leaks:

```javascript
let app = initScene();

if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    if (app && app.destroy) {
      app.destroy();
    }
  });
}
```
