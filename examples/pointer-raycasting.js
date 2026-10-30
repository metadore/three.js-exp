/**
 * Pointer-Based Raycasting Interaction
 * Features: Strict container-relative Normalized Device Coordinates (NDC),
 * hover highlights, and click selection.
 */
import * as THREE from 'three';

export function setupRaycasting({
  canvas,
  camera,
  interactiveObjects,
  onHover,
  onClick
}) {
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let currentHovered = null;

  function updatePointerCoords(event) {
    const rect = canvas.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  }

  const handlePointerMove = (event) => {
    updatePointerCoords(event);
    raycaster.setFromCamera(pointer, camera);
    const intersects = raycaster.intersectObjects(interactiveObjects, true);

    const hit = intersects.length > 0 ? intersects[0] : null;

    if (hit !== currentHovered) {
      currentHovered = hit;
      if (onHover) onHover(currentHovered);
    }
  };

  const handlePointerDown = (event) => {
    updatePointerCoords(event);
    raycaster.setFromCamera(pointer, camera);
    const intersects = raycaster.intersectObjects(interactiveObjects, true);

    if (intersects.length > 0 && onClick) {
      onClick(intersects[0]);
    }
  };

  canvas.addEventListener('pointermove', handlePointerMove, { passive: true });
  canvas.addEventListener('pointerdown', handlePointerDown);

  return {
    destroy() {
      canvas.removeEventListener('pointermove', handlePointerMove);
      canvas.removeEventListener('pointerdown', handlePointerDown);
    }
  };
}
