# Three.js Engineering Principles & Standards Classification

Engineering recommendations must not be applied blindly. Every 3D scene balances a unique set of constraints: polygon budget, draw call limits, mobile battery impact, network bandwidth, and artistic direction.

---

## 1. Classification of Engineering Standards

### A. Mandatory Standards (Apply to Every Production Project)
- **Capped Device Pixel Ratio**: `renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))` (or `1.5` on low-power profiles). Prevents GPU thermal throttling on retina and 4K mobile displays.
- **Explicit Texture Color Space Management**: Color textures (`map`, `emissiveMap`) must use `THREE.SRGBColorSpace`. Data textures (`normalMap`, `roughnessMap`, `metalnessMap`, `displacementMap`) must remain linear (`NoColorSpace`).
- **Bounded Animation Loop**: Use `renderer.setAnimationLoop()` instead of recursive `requestAnimationFrame()` for proper WebXR synchronization and background tab sleep.
- **Explicit GPU Memory Teardown**: Always dispose geometries, materials, and textures when unmounting scenes to prevent memory leaks and `CONTEXT_LOST_WEBGL`.

### B. Recommended Defaults (Apply Unless Explicitly Overridden)
- **ACES Filmic Tone Mapping**: Provides realistic highlight rolloff for PBR materials. Can be swapped for `AgXToneMapping` (wider gamut) or `NoToneMapping` (flat 2D/stylized illustrations).
- **Container-Based `ResizeObserver`**: Strictly superior to window `resize` events for componentized layouts.
- **IBL Environment Reflection**: A subtle HDR environment map provides the roughness-dependent reflections required for physically plausible metal and dielectric surfaces.
- **OrbitControls Damping**: `controls.enableDamping = true` gives smooth, professional camera movement. Always call `controls.update()` in the animation loop.

### C. Context-Dependent Standards (Evaluate Based on Scene Scope)
- **Model Centering & Scaling (`Box3`)**:
  - *Appropriate for*: Isolated product viewers, single 3D character previewers, portfolio card thumbnails.
  - *Do NOT use on*: Multi-part architectural assemblies, level layouts, or environments where coordinate offsets established in 3D modeling tools are intentional.
- **Shadow Bias and Normal Bias**:
  - *Appropriate for*: Smooth, curved meshes with moderate polygon counts.
  - *Caution*: High bias causes peter-panning (shadows detaching from bases); low bias causes shadow acne. Tune based on light frustum size and scene dimensions.
- **DRACOLoader**:
  - *Appropriate for*: Large models (>5MB) compressed with Draco.
  - *Do NOT use on*: Uncompressed models or models using Meshopt compression, as it incurs extra HTTP requests for WASM decoders and decoding CPU overhead.

### D. Potentially Unsafe / Incorrect If Misused
- **`renderer.forceContextLoss()`**:
  - Only intended to simulate context loss for unit testing. Never use in regular production cleanup routines, as it can corrupt shared host WebGL contexts.
- **Disposing Shared Cached Assets**:
  - If multiple meshes share the same `BufferGeometry` or `Material`, calling `.dispose()` when removing one mesh will corrupt all remaining active meshes. Use reference counting or central cache tracking.
- **Hardcoding Canvas Dimensions (`window.innerWidth/Height`)**:
  - Breaks responsive embedding inside UI containers, modal dialogs, and split panes.

---

## 2. Accessibility & Reduced-Motion Preferences

Modern web experiences must respect user accessibility settings:

```javascript
export function setupReducedMotionObserver(onPreferenceChange) {
  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  onPreferenceChange(mediaQuery.matches);

  const handler = (e) => onPreferenceChange(e.matches);
  mediaQuery.addEventListener('change', handler);
  return () => mediaQuery.removeEventListener('change', handler);
}
```
**Application Rules:**
- If `prefers-reduced-motion: reduce` is active:
  - Disable automatic camera orbiting and continuous idle rotation.
  - Instantaneously snap camera positions on scroll rather than lerping.
  - Retain user-initiated interactive controls (drag to rotate).
