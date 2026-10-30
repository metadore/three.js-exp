# Canonical Three.js Implementation Patterns

This document defines verified, production-grade patterns extracted directly from the Three.js library and official examples.

---

## 1. Scene, Camera, and Renderer Initialization

```javascript
import * as THREE from 'three';

export function initRenderer(canvas, container) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    powerPreference: 'high-performance',
    alpha: false
  });

  // Clamp DPR to avoid thermal throttling
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight, false);

  // Modern Color & Tone Mapping
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;

  // Shadow Map Configuration
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap; // r186+ standard

  return renderer;
}
```

---

## 2. Robust Responsive Resizing (ResizeObserver)

Window `resize` listeners fail when the 3D canvas is embedded inside dynamic layouts (flexboxes, CSS grids, drawer sidebars). Always use a `ResizeObserver` observing the parent container:

```javascript
export function attachResizeHandler(container, camera, renderer, onResizeCallback) {
  const observer = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const width = entry.contentRect.width;
      const height = entry.contentRect.height;
      if (width === 0 || height === 0) return;

      camera.aspect = width / height;
      camera.updateProjectionMatrix();

      renderer.setSize(width, height, false);
      if (onResizeCallback) onResizeCallback(width, height);
    }
  });

  observer.observe(container);
  return observer;
}
```

---

## 3. High-Fidelity PBR Lighting & HDR Environment

```javascript
import * as THREE from 'three';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js'; // r180+ standard

export function setupLighting(scene) {
  // Key directional light for crisp shadows
  const dirLight = new THREE.DirectionalLight(0xffffff, 2.0);
  dirLight.position.set(5, 10, 7);
  dirLight.castShadow = true;
  dirLight.shadow.mapSize.set(2048, 2048);
  dirLight.shadow.camera.near = 0.5;
  dirLight.shadow.camera.far = 30;

  // Tune shadow frustum bounds to fit the scene volume
  const d = 6;
  dirLight.shadow.camera.left = -d;
  dirLight.shadow.camera.right = d;
  dirLight.shadow.camera.top = d;
  dirLight.shadow.camera.bottom = -d;

  // Bias to eliminate shadow acne without detaching contact shadows
  dirLight.shadow.bias = -0.0005;
  dirLight.shadow.normalBias = 0.02;
  scene.add(dirLight);

  // Soft ambient fill
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
  scene.add(ambientLight);
}

export function loadHDREnvironment(scene, renderer, url) {
  new HDRLoader().load(url, (texture) => {
    texture.mapping = THREE.EquirectangularReflectionMapping;
    scene.environment = texture;
    // scene.background = texture; // optional: or leave background as solid color
  });
}
```

---

## 4. Safe GLTF/GLB Loading with Optional Normalization

```javascript
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

export function loadGLTFSafe({
  url,
  scene,
  normalizeBounds = false, // Never force normalization on pre-arranged game levels
  targetScale = 2.0,
  dracoPath = 'https://www.gstatic.com/draco/versioned/decoders/1.5.7/',
  onProgress,
  onSuccess,
  onError
}) {
  const gltfLoader = new GLTFLoader();

  if (dracoPath) {
    const dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath(dracoPath);
    gltfLoader.setDRACOLoader(dracoLoader);
  }

  gltfLoader.load(
    url,
    (gltf) => {
      const model = gltf.scene;

      // Optional normalization for isolated showcase assets
      if (normalizeBounds) {
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = targetScale / (maxDim || 1);

        model.scale.setScalar(scale);
        model.position.x = -center.x * scale;
        model.position.y = -box.min.y * scale; // align base with ground plane
        model.position.z = -center.z * scale;
      }

      // Ensure proper shadow casting and texture color spaces
      model.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = true;
          child.receiveShadow = true;
          if (child.material) {
            const mats = Array.isArray(child.material) ? child.material : [child.material];
            mats.forEach((m) => {
              if (m.map) m.map.colorSpace = THREE.SRGBColorSpace;
              if (m.emissiveMap) m.emissiveMap.colorSpace = THREE.SRGBColorSpace;
              // Data maps (normalMap, roughnessMap, metalnessMap) MUST remain linear!
            });
          }
        }
      });

      scene.add(model);
      if (onSuccess) onSuccess({ model, gltf });
    },
    (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(event.loaded / event.total);
      }
    },
    onError
  );
}
```

---

## 5. Normalized Pointer Raycasting

```javascript
import * as THREE from 'three';

export function setupPointerRaycaster(canvas, camera, targetObjects, onSelect) {
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  const handlePointerDown = (event) => {
    const rect = canvas.getBoundingClientRect();
    // Normalize coordinates strictly within the canvas bounds [-1, 1]
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(pointer, camera);
    const intersects = raycaster.intersectObjects(targetObjects, true);

    if (intersects.length > 0 && onSelect) {
      onSelect(intersects[0]);
    }
  };

  canvas.addEventListener('pointerdown', handlePointerDown);
  return () => canvas.removeEventListener('pointerdown', handlePointerDown);
}
```
