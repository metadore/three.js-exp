# Three.js Expert Rules (Windsurf Cascade)

Apply these rules when designing, modifying, or troubleshooting 3D web applications using Three.js (target version: 0.186.0 / rev 187dev).

---

## 1. Mandatory Pre-Flight Audit
Before generating or modifying any 3D graphics code:
1. **Audit `package.json`**:
   - Check if project uses React Three Fiber (`@react-three/fiber`), Next.js (`next`), Vite (`vite`), or Vanilla Three.js.
   - Check installed `three` version. Verify APIs against the installed version.
2. **Strict Paradigm Isolation**:
   - Never write imperative DOM loops (`new THREE.WebGLRenderer()`, bare `rAF`) inside R3F declarative components.
   - For Next.js, always isolate Three.js in Client Components with dynamic imports (`ssr: false`).
3. **Preserve Existing Architecture**: Re-use existing canvas wrappers, resize listeners, camera setups, and loaders.

---

## 2. Verified Three.js r186+ Standards
- **Shadows**: Use `THREE.PCFShadowMap` (`PCFSoftShadowMap` is deprecated in r186+).
- **HDR Environment**: Use `HDRLoader` from `'three/addons/loaders/HDRLoader.js'` (`RGBELoader` is deprecated in r180+).
- **WebGPU Post-Processing**: Use `new THREE.RenderPipeline()`.
- **WebGPU Initialization**: Always `await renderer.init()` before the first render call.
- **Color Spaces**: Set `texture.colorSpace = THREE.SRGBColorSpace` for color maps; keep data maps linear.
- **Pixel Ratio**: Always clamp DPR: `renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))`.
- **Tone Mapping**: Use `THREE.ACESFilmicToneMapping` with exposure `1.0`.

---

## 3. Resource Disposal & Lifecycle
- Reclaim GPU memory by recursively traversing meshes and disposing geometries, materials, and textures on unmount.
- Prevent `CONTEXT_LOST_WEBGL` by cleaning up event listeners and stopping render loops cleanly.
- Do NOT call `renderer.forceContextLoss()` in production code.

---

## 4. Performance, Accessibility & Verification
- Use container-based `ResizeObserver` with zero-dimension guards (`width === 0 || height === 0`).
- Provide keyboard controls, canvas fallback descriptions, and honor `prefers-reduced-motion`.
- Test code when practical. State honestly if code has not been executed in a live runtime environment.

---

## 5. Reference Implementations
Consult the canonical Three.js knowledge base for complete templates:
- Patterns: `threejs-expert/core/implementation-patterns.md`
- Decisions: `threejs-expert/references/decision-guide.md`
- GLTF Loading: `threejs-expert/examples/gltf-loader-safe.js`
- Disposal Guide: `threejs-expert/references/disposal-guide.md`
- Diagnostics: `threejs-expert/references/troubleshooting-matrix.md`
