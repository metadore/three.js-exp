/**
 * Scroll-Driven 3D Animation Pattern
 * Features: Decoupled DOM scroll tracking, normalized [0, 1] progress,
 * and smooth lerping inside 60fps render loop.
 */
import * as THREE from 'three';

export function setupScrollAnimation({ camera, targetMesh, scrollContainer = window }) {
  let targetProgress = 0;
  let currentProgress = 0;

  // 1. Decoupled Scroll Listener (no heavy math or DOM queries inside render loop)
  const onScroll = () => {
    const scrollY = scrollContainer === window ? window.scrollY : scrollContainer.scrollTop;
    const maxScroll =
      (scrollContainer === window
        ? document.documentElement.scrollHeight - window.innerHeight
        : scrollContainer.scrollHeight - scrollContainer.clientHeight) || 1;

    targetProgress = Math.min(Math.max(scrollY / maxScroll, 0), 1);
  };

  scrollContainer.addEventListener('scroll', onScroll, { passive: true });

  // 2. Camera Keyframe Waypoints
  const waypoints = [
    { pos: new THREE.Vector3(0, 2, 5), rotY: 0 },
    { pos: new THREE.Vector3(3, 1, 3), rotY: Math.PI * 0.5 },
    { pos: new THREE.Vector3(0, 4, 1), rotY: Math.PI }
  ];

  // 3. Per-Frame Update (called inside renderer.setAnimationLoop)
  function update(delta) {
    // Smooth lerp damping towards scroll target
    currentProgress = THREE.MathUtils.lerp(currentProgress, targetProgress, 0.08);

    // Map progress across waypoints
    const segmentCount = waypoints.length - 1;
    const scaledProgress = currentProgress * segmentCount;
    const index = Math.min(Math.floor(scaledProgress), segmentCount - 1);
    const segmentAlpha = scaledProgress - index;

    const wpA = waypoints[index];
    const wpB = waypoints[index + 1];

    camera.position.lerpVectors(wpA.pos, wpB.pos, segmentAlpha);
    camera.lookAt(0, 0, 0);

    if (targetMesh) {
      targetMesh.rotation.y = THREE.MathUtils.lerp(wpA.rotY, wpB.rotY, segmentAlpha);
    }
  }

  return {
    update,
    destroy() {
      scrollContainer.removeEventListener('scroll', onScroll);
    }
  };
}
