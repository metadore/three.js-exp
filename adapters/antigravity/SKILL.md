---
name: threejs-expert
description: >-
  Expert guidance for building, optimizing, and debugging production-grade
  Three.js 3D web experiences. Activates when creating 3D scenes, 3D websites,
  and portfolios, loading GLTF/GLB models, configuring PBR materials and shadows,
  implementing animations and raycasting interactions, building scroll-driven 3D
  experiences, writing WebGL/WebGPU shaders (TSL), optimizing rendering
  performance, or diagnosing black screens, rendering glitches, and GPU memory leaks.
---

# Three.js Expert Agent Skill

This skill guides you through architecting, implementing, optimizing, and debugging production-grade 3D graphics on the web using Three.js (based on source repository `three.js-dev`, version 0.186.0 / rev 187dev).

Follow this structured workflow to deliver resilient, high-performance, and visually stunning 3D applications.

---

## 1. Pre-Flight Architecture Audit (Mandatory Step 0)

Before generating or modifying any 3D code, execute the detection protocol:
1. **Inspect `package.json`**:
   - Check if the project uses **React Three Fiber** (`@react-three/fiber`), **Next.js** (`next`), **Vite** (`vite`), or **Vanilla Three.js**.
   - Check the installed `three` version (r186+, r180+, r163+, etc.). Verify APIs against the installed version.
2. **Never mix paradigms**:
   - Never write imperative DOM loops (`renderer.setAnimationLoop`, `new THREE.WebGLRenderer`) inside a declarative React Three Fiber component.
   - For Next.js, always isolate Three.js in Client Components with dynamic imports (`ssr: false`).
3. **Preserve existing architecture**: Re-use existing canvas wrappers, resize listeners, camera setups, and asset loaders rather than tearing down working code.

Refer to detailed rules in: [core/framework-detection.md](core/framework-detection.md) | [references/decision-guide.md](references/decision-guide.md)

---

## 2. API Version Standards

Three.js APIs evolve rapidly. Apply version-accurate standards verified from the live repository:
- **Shadows**: In r186+, `PCFSoftShadowMap` is deprecated; use **`THREE.PCFShadowMap`**.
- **HDR Environment**: In r180+, `RGBELoader` is deprecated; use **`HDRLoader`** from `'three/addons/loaders/HDRLoader.js'`.
- **WebGPU Post-Processing**: In r183+, `PostProcessing` was renamed to **`RenderPipeline`**.
- **WebGPU Initialization**: Always `await renderer.init()` before the first render call.
- **Color Space**: Always use `THREE.SRGBColorSpace` for color maps; keep data textures (normals, roughness) linear.
- **WebGL 2**: WebGL 1 is completely dropped since r163.

Full historical shift matrix: [core/api-version-compatibility.md](core/api-version-compatibility.md)

---

## 3. Engineering Standards & Performance Guardrails

Classify standards according to project needs:
- **Mandatory**: Capped DPR (`Math.min(window.devicePixelRatio, 2)`), explicit texture color space management, bounded animation loops, and recursive GPU memory cleanup.
- **Recommended**: ACES Filmic or AgX tone mapping, container-based `ResizeObserver`, IBL HDR reflections, and damped OrbitControls.
- **Context-Dependent**: Model centering via `Box3` (use only for single asset viewers, not full scenes), shadow bias (tune per scene volume), and `DRACOLoader` (use only when models actually have Draco compression).
- **Potentially Unsafe**: Do NOT call `renderer.forceContextLoss()` in production teardown (it is a unit-test simulation method). Do NOT dispose shared cached assets.
- **Accessibility**: Provide keyboard navigation, screen reader fallbacks, and support `prefers-reduced-motion`.

Detailed guidelines & accessibility: [core/engineering-principles.md](core/engineering-principles.md) and [references/accessibility.md](references/accessibility.md)

---

## 4. Implementation Pattern Blueprints

Use the verified implementation blueprints for your target environment:
- **Core Implementation Patterns**: [core/implementation-patterns.md](core/implementation-patterns.md)
- **Vanilla Three.js**: [references/framework-vanilla.md](references/framework-vanilla.md) | [examples/basic-vanilla-scene.js](examples/basic-vanilla-scene.js)
- **Vite (Responsive + HDR)**: [references/framework-vite.md](references/framework-vite.md) | [examples/vite-responsive-scene.js](examples/vite-responsive-scene.js)
- **React Three Fiber (R3F)**: [references/framework-r3f.md](references/framework-r3f.md) | [examples/r3f-standard-component.jsx](examples/r3f-standard-component.jsx)
- **Next.js (App / Pages Router)**: [references/framework-nextjs.md](references/framework-nextjs.md) | [examples/nextjs-client-canvas.tsx](examples/nextjs-client-canvas.tsx)
- **WebGPU & TSL (Three.js Shading Language)**: [references/webgpu-tsl.md](references/webgpu-tsl.md)
- **GLTF Safe Loading**: [examples/gltf-loader-safe.js](examples/gltf-loader-safe.js)
- **Pointer Raycasting**: [examples/pointer-raycasting.js](examples/pointer-raycasting.js)
- **Animation & GPU Disposal**: [examples/animation-cleanup.js](examples/animation-cleanup.js) | [references/disposal-guide.md](references/disposal-guide.md)

---

## 5. Diagnostic & Troubleshooting

When encountering rendering bugs, runtime exceptions, or performance issues, consult:
- **Quick-reference table** (symptoms → root cause → fix): [references/troubleshooting-matrix.md](references/troubleshooting-matrix.md)
- **Step-by-step diagnostic procedures** (black screen, GLTF failures, shadow glitches, animation, performance): [references/troubleshooting.md](references/troubleshooting.md)

Follow the diagnostic flow for:
- Blank canvas / black screen (container dimensions, camera clipping, unlit PBR materials).
- Missing, displaced, or microscopic models (`Box3` bounding check).
- 404 asset pathing (root-relative `/` URLs for `public/` assets).
- Shadow acne and peter-panning (tuning `bias` and `normalBias`).
- WebGL context loss and GPU memory leaks (recursive object/material/texture disposal).
- Next.js SSR crashes (`window is not defined`).

---

## 6. Pre-Completion Quality Checklist

Before completing any Three.js task:
- [ ] No uncaught console errors, 404s, or deprecation warnings in browser DevTools.
- [ ] DPR capped to `Math.min(window.devicePixelRatio, 2)`.
- [ ] Container resizing tested and aspect ratio maintained without distortion.
- [ ] Color spaces correct: sRGB for color maps, linear for data maps.
- [ ] Unmounting the component triggers complete GPU memory disposal without leaks.
- [ ] If code was not executed or visually verified, honestly state what was validated and what remains to be tested.
