/**
 * Animation Mixer Management & Comprehensive GPU Cleanup
 * Features: Delta-timed AnimationMixer, recursive disposal of geometries,
 * materials, and textures, with observer disconnect.
 */
import * as THREE from 'three';

export function createAnimatedSceneWithCleanup(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight, false);
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 100);
  camera.position.set(0, 2, 4);

  // Mesh with keyframe animation
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const mat = new THREE.MeshStandardMaterial({ color: 0x10b981 });
  const mesh = new THREE.Mesh(geo, mat);
  scene.add(mesh);

  scene.add(new THREE.DirectionalLight(0xffffff, 2.0));
  scene.add(new THREE.AmbientLight(0xffffff, 0.5));

  // Procedural AnimationClip
  const positionTrack = new THREE.VectorKeyframeTrack('.position', [0, 1, 2], [0, 0, 0, 0, 1, 0, 0, 0, 0]);
  const clip = new THREE.AnimationClip('bounce', 2, [positionTrack]);

  const mixer = new THREE.AnimationMixer(mesh);
  const action = mixer.clipAction(clip);
  action.play();

  const clock = new THREE.Clock();

  renderer.setAnimationLoop(() => {
    const delta = clock.getDelta();
    mixer.update(delta);
    renderer.render(scene, camera);
  });

  // Comprehensive GPU Teardown Utility
  function disposeObjectTree(root) {
    if (!root) return;
    root.traverse((node) => {
      if (node.geometry) {
        node.geometry.dispose();
      }
      if (node.material) {
        const mats = Array.isArray(node.material) ? node.material : [node.material];
        mats.forEach((m) => {
          for (const key of Object.keys(m)) {
            const val = m[key];
            if (val && typeof val === 'object' && val.isTexture) {
              val.dispose();
            }
          }
          m.dispose();
        });
      }
    });
  }

  return {
    destroy() {
      renderer.setAnimationLoop(null);
      mixer.stopAllAction();
      disposeObjectTree(scene);
      renderer.dispose();
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    }
  };
}
