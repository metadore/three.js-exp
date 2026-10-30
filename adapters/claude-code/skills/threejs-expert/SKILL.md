---
name: threejs-expert
description: Expert guidance for architecting, optimizing, and debugging Three.js 3D web experiences, GLTF loading, WebGL/WebGPU shaders, and GPU memory disposal.
---

# /threejs-expert — Three.js Engineering Workflow

Follow this procedure when creating or debugging 3D scenes:

1. **Audit Project Framework**:
   - Check `package.json` for React Three Fiber, Next.js, or Vite.
   - Check `three` version. Never mix imperative Three.js DOM code into declarative R3F `<Canvas>`.

2. **Apply Standards (Three.js r186+)**:
   - ShadowMap: `THREE.PCFShadowMap`.
   - HDR: `HDRLoader` from `'three/addons/loaders/HDRLoader.js'`.
   - WebGPU: `await renderer.init()` before rendering; use `RenderPipeline`.
   - Texture color spaces: `THREE.SRGBColorSpace` for `map`/`emissiveMap`.
   - Clamp DPR: `Math.min(window.devicePixelRatio, 2)`.

3. **Consult Reference Implementations**:
   - Framework detection: `threejs-expert/core/framework-detection.md`
   - Decision guide: `threejs-expert/references/decision-guide.md`
   - Safe GLTF loading: `threejs-expert/examples/gltf-loader-safe.js`
   - Memory cleanup: `threejs-expert/references/disposal-guide.md`
   - Diagnostics: `threejs-expert/references/troubleshooting.md`

4. **Verify Implementation**:
   - Ensure animation loops are bounded and cancellable.
   - Ensure complete recursive cleanup on component unmount.
   - Clearly report test status; state honestly if runtime rendering was not verified.
