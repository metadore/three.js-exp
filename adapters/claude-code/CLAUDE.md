# Three.js Development Guidelines (Claude Code)

This repository incorporates the Three.js Expert Knowledge Base (target version: 0.186.0 / rev 187dev).

---

## 1. Pre-Flight Architecture Audit
Before writing or modifying 3D code:
1. **Inspect `package.json`**:
   - Determine framework: React Three Fiber (`@react-three/fiber`), Next.js (`next`), Vite (`vite`), or Vanilla Three.js.
   - Check installed `three` version. Verify APIs against the installed version.
2. **Never mix paradigms**:
   - Do NOT instantiate `new THREE.WebGLRenderer()` or bare `requestAnimationFrame` loops inside R3F components.
   - For Next.js, always isolate Three.js in Client Components with dynamic imports (`ssr: false`).
3. **Preserve existing infrastructure**: Reuse existing canvases, camera controls, resize listeners, and asset loaders.

---

## 2. Non-Negotiable Three.js Standards
- **Shadow Maps**: Use `THREE.PCFShadowMap` (`PCFSoftShadowMap` is deprecated in r186+).
- **HDR Environment**: Use `HDRLoader` from `'three/addons/loaders/HDRLoader.js'` (`RGBELoader` is deprecated in r180+).
- **WebGPU Post-Processing**: Use `RenderPipeline` (formerly `PostProcessing`).
- **WebGPU Initialization**: Always `await renderer.init()` before the first render call.
- **Color Spaces**: Set `texture.colorSpace = THREE.SRGBColorSpace` for color maps; leave data maps (normals/roughness) linear.
- **Device Pixel Ratio**: Always clamp DPR: `renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))`.
- **Tone Mapping**: Use `THREE.ACESFilmicToneMapping` with exposure `1.0`.
- **Resource Disposal**: Always recursively dispose geometries, materials, and textures on unmount.
- **Accessibility**: Provide keyboard controls and support `prefers-reduced-motion`.
- **Verification**: Always execute tests or state honestly when code has not been run in a live browser.

---

## 3. On-Demand Skill Workflow
For complete scene templates, GLTF loading patterns, and deep diagnostic procedures, run:
`/threejs-expert`
Or consult: `threejs-expert/core/`, `threejs-expert/references/`, `threejs-expert/examples/`.
