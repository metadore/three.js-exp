# GitHub Copilot Custom Instructions: Three.js Standards

These instructions govern all Three.js and 3D web development in this workspace (target version: Three.js 0.186.0 / rev 187dev).

---

## 1. Pre-Flight Architecture Audit
Before writing or modifying 3D code:
- **Inspect `package.json`**: Determine the framework (React Three Fiber, Next.js, Vite, or Vanilla) and installed `three` version.
- **Never mix paradigms**: Never instantiate `new THREE.WebGLRenderer()` or bare `requestAnimationFrame` loops inside React Three Fiber declarative components. For Next.js, isolate Three.js in Client Components with dynamic imports (`ssr: false`).
- **Preserve existing structure**: Re-use existing canvas elements, camera setups, and controls.

---

## 2. Mandatory Three.js Standards (r186+)
- **Shadow Maps**: Use `THREE.PCFShadowMap`. `THREE.PCFSoftShadowMap` is deprecated in r186+.
- **HDR Environment**: Use `HDRLoader` from `'three/addons/loaders/HDRLoader.js'`. `RGBELoader` is deprecated in r180+.
- **WebGPU Post-Processing**: Use `new THREE.RenderPipeline()`.
- **WebGPU Initialization**: Always `await renderer.init()` before the first render call.
- **Color Space**: Set `texture.colorSpace = THREE.SRGBColorSpace` for color maps; keep data textures (normals, roughness, metalness) linear.
- **Device Pixel Ratio**: Always clamp pixel ratio: `renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))`.
- **Tone Mapping**: Use `THREE.ACESFilmicToneMapping` with exposure `1.0`.

---

## 3. GPU Memory Disposal & Cleanup
Reclaim GPU memory on component unmount or route change to prevent `CONTEXT_LOST_WEBGL`:
- Traverse scene objects recursively: dispose geometries, materials, and attached textures.
- Cancel animation frame loops and remove event listeners (window resize, pointermove).
- Remove renderer DOM element cleanly.

---

## 4. Performance, Accessibility & Verification
- Use container-based `ResizeObserver` with zero-dimension guards (`width === 0 || height === 0`).
- Provide keyboard controls, canvas fallback descriptions, and honor `prefers-reduced-motion`.
- Test code when practical. State honestly if code has not been executed in a live runtime environment.

---

## 5. Knowledge Base Reference Paths
For full implementations, consult:
- `threejs-expert/core/implementation-patterns.md`
- `threejs-expert/references/decision-guide.md`
- `threejs-expert/examples/gltf-loader-safe.js`
- `threejs-expert/references/disposal-guide.md`
- `threejs-expert/references/troubleshooting-matrix.md`
