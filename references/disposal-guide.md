# Three.js Memory Management & Resource Disposal Guide

JavaScript garbage collection only reclaims CPU memory. WebGL and WebGPU allocate buffers, textures, and pipelines directly in GPU memory, which **must be explicitly freed**.

Failing to dispose of resources leads to memory leaks, browser tab crashes, and `CONTEXT_LOST_WEBGL` errors during Single-Page App (SPA) route changes or component unmounts.

---

## 1. The Complete Object Disposal Utility

Use this recursive cleanup function when destroying a scene, removing a model, or unmounting a 3D component:

```javascript
import * as THREE from 'three';

export function disposeHierarchy(rootObject) {
  if (!rootObject) return;

  rootObject.traverse((node) => {
    // 1. Dispose Geometry
    if (node.geometry) {
      node.geometry.dispose();
    }

    // 2. Dispose Materials & Attached Textures
    if (node.material) {
      cleanMaterial(node.material);
    }
  });

  // Remove from parent if attached
  if (rootObject.parent) {
    rootObject.parent.remove(rootObject);
  }
}

export function cleanMaterial(material) {
  if (Array.isArray(material)) {
    material.forEach(cleanMaterial);
    return;
  }

  // Iterate over all material properties to find and dispose textures
  for (const key of Object.keys(material)) {
    const value = material[key];
    if (value && typeof value === 'object' && 'isTexture' in value && value.isTexture) {
      value.dispose();
    }
  }

  material.dispose();
}
```

---

## 2. Full Application Teardown Procedure

When cleaning up an entire Three.js application or component:

```javascript
export function teardownThreeApp({
  renderer,
  scene,
  controls,
  animationLoopId,
  resizeObserver,
  renderTargets = []
}) {
  // 1. Stop Render Loop
  if (renderer) {
    renderer.setAnimationLoop(null);
  }

  // 2. Disconnect Observers & Controls
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  if (controls && controls.dispose) {
    controls.dispose();
  }

  // 3. Dispose Scene Objects & Materials
  if (scene) {
    disposeHierarchy(scene);
    if (scene.environment && scene.environment.dispose) {
      scene.environment.dispose();
    }
    if (scene.background && scene.background.dispose) {
      scene.background.dispose();
    }
  }

  // 4. Dispose Extra Render Targets & Composers
  for (const target of renderTargets) {
    if (target && target.dispose) target.dispose();
  }

  // 5. Dispose Renderer & Release WebGL Context
  if (renderer) {
    renderer.dispose();
    if (renderer.forceContextLoss) {
      renderer.forceContextLoss();
    }
    if (renderer.domElement && renderer.domElement.parentNode) {
      renderer.domElement.parentNode.removeChild(renderer.domElement);
    }
  }
}
```

---

## 3. React Three Fiber Component Unmount

In R3F, unmounting `<Canvas>` automatically handles renderer and standard geometry disposal. However, if you load external textures or custom render targets outside the declarative tree, always wrap them in `useMemo` or clean them inside `useEffect` cleanup return:

```javascript
useEffect(() => {
  const customTexture = loadMyTexture();
  return () => {
    customTexture.dispose();
  };
}, []);
```
