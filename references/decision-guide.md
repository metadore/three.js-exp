# Architecture Decision Guide: Three.js Ecosystem

When designing or contributing to a 3D web application, selecting the appropriate architecture and avoiding mixed paradigms is essential for maintainability and performance.

---

## 1. Paradigm Selection: Native Three.js vs. React Three Fiber (R3F)

### Native Three.js (Imperative)
**Use When:**
- Building vanilla JavaScript/TypeScript applications (Vite, vanilla Astro, vanilla Webpack).
- Building embedded canvas widgets inside non-React frameworks (Vue, Svelte, Angular) without framework wrappers.
- Fine-grained, micro-level control over render loops, custom WebGPU compute pipelines, or custom render targets is required.
- Migrating or integrating legacy Three.js codebases.

**Key Rule:**
- Control the DOM canvas directly. Lifecycle is handled via explicit `init()`, `animate()`, and `destroy()` functions.

### React Three Fiber (`@react-three/fiber` / R3F) (Declarative)
**Use When:**
- The host application is built in React 18/19 or Next.js.
- The 3D scene directly reflects React application state (props, context, Redux, Zustand).
- Leveraging the rich ecosystem: `@react-three/drei` (helpers, loaders, controls), `@react-three/postprocessing`, `@react-three/rapier` (physics).

**Critical Anti-Pattern (DO NOT MIX):**
- **NEVER** instantiate a `new THREE.WebGLRenderer()` and append its canvas to the DOM inside an R3F component. R3F's `<Canvas>` component already creates, configures, resizes, and manages the renderer lifecycle.
- **NEVER** use `requestAnimationFrame` inside R3F components. Use the `useFrame((state, delta) => { ... })` hook instead.

---

## 2. Rendering Backend: WebGLRenderer vs. WebGPURenderer

### WebGLRenderer
- **Engine**: WebGL 2.0 (WebGL 1.0 support was removed in r163).
- **Import**: `import * as THREE from 'three';`
- **Post-Processing**: `EffectComposer` from `'three/addons/postprocessing/EffectComposer.js'`.
- **Shaders**: Traditional GLSL shaders via `RawShaderMaterial` or `ShaderMaterial`.
- **Maturity**: Maximum browser compatibility across all current mobile and desktop devices.

### WebGPURenderer
- **Engine**: WebGPU with automatic fallback to WebGL 2.
- **Import**: `import * as THREE from 'three/webgpu';`
- **Post-Processing**: `RenderPipeline` (formerly `PostProcessing`) and `PassNode`.
- **Shaders**: TSL (Three.js Shading Language) imported from `'three/tsl'`. Compiles to WGSL for WebGPU and GLSL for WebGL2.
- **Initialization**: Requires asynchronous initialization before rendering:
  ```javascript
  const renderer = new THREE.WebGPURenderer({ antialias: true });
  await renderer.init();
  ```
- **Use When**: Building cutting-edge graphics, GPU compute simulations, node-based procedural materials, or future-proof WebGPU applications.

---

## 3. Pre-Flight Architecture Checklist

Before adding or modifying any 3D code:
1. Open `package.json`.
2. Inspect `dependencies` and `devDependencies` for:
   - `three`: version number.
   - `@react-three/fiber` or `@react-three/drei`: indicates R3F project.
   - `three-stdlib`: indicates legacy R3F utility imports.
3. Inspect the directory tree for existing canvas wrappers (e.g. `components/Canvas3D.jsx`, `src/scene.ts`).
4. Re-use existing lighting, camera, and asset loading infrastructure rather than creating competing instances.
