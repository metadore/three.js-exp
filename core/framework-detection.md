# Framework Detection Heuristics & Architecture Guardrails

Before generating or modifying any 3D graphics code, the AI agent must systematically audit the host project to identify its rendering architecture. Generating incompatible code (e.g. mounting a raw WebGL canvas inside a React Three Fiber component) causes fatal crashes and architectural debt.

---

## 1. Automated Detection Protocol

Execute these 3 audit steps in sequence:

### Step 1: Inspect `package.json`
Examine `dependencies` and `devDependencies`:
- **React Three Fiber (R3F)**: Presence of `@react-three/fiber` or `@react-three/drei`.
- **Next.js**: Presence of `next`.
- **Vite**: Presence of `vite` without Next.js.
- **Astro / Nuxt / SvelteKit**: Presence of `astro`, `nuxt`, or `@sveltejs/kit`.
- **Vanilla Three.js**: Presence of `three` alone, or no package.json (HTML import map).
- **Three Version**: Check the exact `three` semver (e.g. `^0.186.0`, `^0.150.0`, `~0.128.0`).

### Step 2: Inspect Directory Structure
- Presence of `app/` or `pages/` with `.tsx`/`.jsx` files indicates Next.js.
- Presence of `public/` folder indicates static asset root for models and textures.
- Look for existing 3D components (e.g. `src/components/Canvas.tsx`, `src/scene.js`).

### Step 3: Inspect Host Component Context
- If editing a file ending in `.jsx` or `.tsx` that imports from `@react-three/fiber`: **Strict R3F Mode**.
- If editing a Next.js file: check for `'use client';` directive at the top. Three.js requires browser APIs (`window`, `HTMLCanvasElement`, `WebGLRenderingContext`).

---

## 2. Framework Separation & Architecture Rules

### Matrix of Compatibility

| Host Architecture | Canvas Paradigm | Animation Loop | Asset Pathing | Lifecycle / Disposal |
| :--- | :--- | :--- | :--- | :--- |
| **Vanilla ESM** | `document.createElement('canvas')` | `renderer.setAnimationLoop()` | Relative or CDN | Manual `dispose()` on unload |
| **Vite** | DOM ref `<canvas ref={canvasRef}>` | `renderer.setAnimationLoop()` | `/models/foo.glb` (from `public/`) | Component unmount hook (`useEffect`) |
| **Next.js (SSR)** | `'use client'` dynamic import (`ssr: false`) | `renderer.setAnimationLoop()` | `/models/foo.glb` (from `public/`) | Client mount lifecycle, avoid SSR leak |
| **React Three Fiber** | Declarative `<Canvas>` component | `useFrame((state, delta) => {})` | `useGLTF('/models/foo.glb')` | Managed automatically by R3F reconciler |

### Absolute Invariants
1. **NEVER mix R3F with Imperative Loops**: Do not call `new THREE.WebGLRenderer()`, `document.body.appendChild()`, or `requestAnimationFrame()` inside an R3F component.
2. **NEVER access `window` or `document` in Next.js Server Components**: Three.js must only be loaded in Client Components via dynamic imports with `ssr: false` or inside `useEffect`.
3. **Preserve Existing Architecture**: If a project has already established a custom render loop, camera controller, or canvas wrapper, build within that pattern rather than overwriting it with boilerplate.
