/**
 * Production Safe GLTF/GLB Loader
 * Features: Optional Draco decoding, optional Box3 centering/scaling,
 * shadow casting propagation, and texture color space enforcement.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

export function loadGLTFSafe({
  url,
  scene,
  normalizeBounds = false, // Set true ONLY for standalone preview assets
  targetDim = 2.0,
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

      // Optional normalization
      if (normalizeBounds) {
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = targetDim / (maxDim || 1);

        model.scale.setScalar(scale);
        model.position.x = -center.x * scale;
        model.position.y = -box.min.y * scale; // align base on y = 0
        model.position.z = -center.z * scale;
      }

      // Traverse meshes to propagate shadow flags and verify color spaces
      model.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = true;
          child.receiveShadow = true;

          if (child.material) {
            const mats = Array.isArray(child.material) ? child.material : [child.material];
            mats.forEach((mat) => {
              if (mat.map) mat.map.colorSpace = THREE.SRGBColorSpace;
              if (mat.emissiveMap) mat.emissiveMap.colorSpace = THREE.SRGBColorSpace;
              // Crucial: do NOT touch normalMap, roughnessMap, metalnessMap (must be Linear)
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
    (error) => {
      console.error(`Failed to load GLTF asset from ${url}:`, error);
      if (onError) onError(error);
    }
  );
}
