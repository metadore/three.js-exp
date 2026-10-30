/**
 * Production-Quality Three.js Scene Template
 * Standard: Responsive, capped DPR, ACESFilmic tone mapping, PCFShadowMap,
 * OrbitControls with damping, and complete disposal lifecycle.
 * Three.js >= r186 (PCFShadowMap, SRGBColorSpace, HDRLoader).
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export function createProductionScene(container) {
  // 1. Renderer Setup
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    powerPreference: 'high-performance'
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  container.appendChild(renderer.domElement);

  // 2. Scene & Camera
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f172a); // Deep slate background

  const camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    0.1,
    100
  );
  camera.position.set(3, 3, 6);

  // 3. OrbitControls with Damping
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.maxPolarAngle = Math.PI / 2 + 0.1; // Prevent going beneath floor

  // 4. Lighting & Environment
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 2.0);
  dirLight.position.set(5, 8, 4);
  dirLight.castShadow = true;
  dirLight.shadow.mapSize.set(2048, 2048);
  dirLight.shadow.bias = -0.0005;
  dirLight.shadow.normalBias = 0.02;
  dirLight.shadow.camera.near = 0.5;
  dirLight.shadow.camera.far = 25;
  scene.add(dirLight);

  // 5. Test Mesh & Shadow Receiver Floor
  const floorGeo = new THREE.PlaneGeometry(20, 20);
  const floorMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.8 });
  const floor = new THREE.Mesh(floorGeo, floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  const sphereGeo = new THREE.SphereGeometry(0.8, 64, 32);
  const sphereMat = new THREE.MeshStandardMaterial({
    color: 0x38bdf8,
    roughness: 0.2,
    metalness: 0.8
  });
  const sphere = new THREE.Mesh(sphereGeo, sphereMat);
  sphere.position.set(0, 1, 0);
  sphere.castShadow = true;
  scene.add(sphere);

  // 6. Resize Observer
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

  // 7. Animation Loop
  renderer.setAnimationLoop(() => {
    controls.update();
    sphere.rotation.y += 0.005;
    renderer.render(scene, camera);
  });

  // 8. Disposal Method
  return {
    destroy() {
      renderer.setAnimationLoop(null);
      resizeObserver.disconnect();
      controls.dispose();

      floorGeo.dispose();
      floorMat.dispose();
      sphereGeo.dispose();
      sphereMat.dispose();

      renderer.dispose();
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    }
  };
}
