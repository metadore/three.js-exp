/**
 * Vite Responsive Scene with ResizeObserver & HDR Environment
 * Target: Vite bundler project with NPM dependencies.
 * Assumptions: Three.js >= r180 (HDRLoader), clamp DPR to 2.
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js'; // r180+ standard

export function initViteScene(container, hdrUrl = '/textures/studio.hdr') {
  // 1. Renderer
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  container.appendChild(renderer.domElement);

  // 2. Scene & Camera
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f172a);

  const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
  camera.position.set(2, 2, 4);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  // 3. Optional HDR Environment
  let envTexture = null;
  if (hdrUrl) {
    new HDRLoader().load(hdrUrl, (tex) => {
      tex.mapping = THREE.EquirectangularReflectionMapping;
      scene.environment = tex;
      envTexture = tex;
    });
  }

  // 4. Mesh
  const geo = new THREE.TorusKnotGeometry(0.7, 0.22, 128, 32);
  const mat = new THREE.MeshStandardMaterial({
    color: 0x818cf8,
    roughness: 0.15,
    metalness: 0.85
  });
  const torus = new THREE.Mesh(geo, mat);
  scene.add(torus);

  // 5. Container-based ResizeObserver
  const resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const { width, height } = entry.contentRect;
      if (width === 0 || height === 0) return;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    }
  });
  resizeObserver.observe(container);

  // 6. Loop
  renderer.setAnimationLoop(() => {
    controls.update();
    torus.rotation.x += 0.003;
    torus.rotation.y += 0.006;
    renderer.render(scene, camera);
  });

  return {
    destroy() {
      renderer.setAnimationLoop(null);
      resizeObserver.disconnect();
      controls.dispose();
      geo.dispose();
      mat.dispose();
      if (envTexture) envTexture.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    }
  };
}
