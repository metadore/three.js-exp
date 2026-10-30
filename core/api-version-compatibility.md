# Three.js API Version Compatibility Matrix

Three.js releases updates every month. APIs shift frequently, and applying obsolete code patterns causes runtime errors or silent rendering flaws. This matrix maps critical API evolutions from version 0.125 to 0.186.0 (dev revision 187dev).

---

## 1. Master API Evolution Table

| Revision / Range | Feature / API Area | Deprecated / Obsolete Pattern | Current Verified Standard | Source / Migration Note |
| :--- | :--- | :--- | :--- | :--- |
| **r186+** | Shadows | `THREE.PCFSoftShadowMap` | **`THREE.PCFShadowMap`** | `PCFSoftShadowMap` is deprecated in `constants.js:73`. Use `PCFShadowMap`. |
| **r183+** | WebGPU Post-Processing | `new THREE.PostProcessing()` | **`new THREE.RenderPipeline()`** | Renamed to `RenderPipeline`. `PostProcessing` is an alias emitting `warnOnce()`. |
| **r181+** | WebGPU Pipeline Render | `pipeline.renderAsync()` | **`pipeline.render()`** + **`await renderer.init()`** | Synchronous render calls are now standard after awaiting renderer initialization. |
| **r180+** | HDR Environment Loader | `RGBELoader` from `three/addons/...` | **`HDRLoader`** from `three/addons/...` | `RGBELoader` now extends `HDRLoader` and logs a deprecation warning. |
| **r163+** | Rendering Backend | WebGL 1.0 context fallback | **WebGL 2.0 only** | WebGL 1.0 is completely removed from `WebGLRenderer`. Browsers must support WebGL 2. |
| **r160+** | Tone Mapping | `ACESFilmicToneMapping` | `ACESFilmicToneMapping` or **`AgXToneMapping`** | `AgXToneMapping` added for improved color preservation in highlights. |
| **r152+** | Color Management | `renderer.outputEncoding = sRGBEncoding`<br>`texture.encoding = sRGBEncoding` | **`renderer.outputColorSpace = THREE.SRGBColorSpace`**<br>**`texture.colorSpace = THREE.SRGBColorSpace`** | Old `*Encoding` properties are removed. Use `ColorSpace`. Data textures use `NoColorSpace`. |
| **r150+** | Shading & Nodes | Raw GLSL string templates / `onBeforeCompile` | **TSL (Three.js Shading Language)** | Node-based materials (`MeshStandardNodeMaterial`) cross-compile to WGSL & GLSL. |
| **r125+** | Geometry System | `new THREE.Geometry()` | **`new THREE.BufferGeometry()`** | `Geometry` is deleted. All meshes must use `BufferGeometry`. |

---

## 2. Import Conventions Across Ecosystems

### Modern Module Imports (Vite / Rollup / Next.js / Webpack)
```javascript
// Core Three.js classes
import * as THREE from 'three';

// Addons and extensions (registered in package.json exports map)
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js'; // r180+
```

### Modern Browser Import Map (Zero Build Step / CDN)
```html
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.186.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.186.0/examples/jsm/",
    "three/webgpu": "https://cdn.jsdelivr.net/npm/three@0.186.0/build/three.webgpu.js",
    "three/tsl": "https://cdn.jsdelivr.net/npm/three@0.186.0/build/three.tsl.js"
  }
}
</script>
```

### WebGPU & TSL Imports
```javascript
// WebGPU Renderer and Node Materials
import * as THREE from 'three/webgpu';

// Three.js Shading Language built-ins
import { color, texture, uv, time, sin, positionLocal, vec3, Fn } from 'three/tsl';
```

---

## 3. Version Verification Heuristic for Agents

When inspecting a project:
1. Check `three` version in `package.json`.
2. If version `< 0.152.0`: Use `sRGBEncoding`.
3. If version `>= 0.152.0` and `< 0.180.0`: Use `SRGBColorSpace` and `RGBELoader`.
4. If version `>= 0.180.0` and `< 0.186.0`: Use `HDRLoader` and `PCFShadowMap` or `PCFSoftShadowMap`.
5. If version `>= 0.186.0`: Use `HDRLoader`, `RenderPipeline` (for WebGPU), and strictly `PCFShadowMap`.
