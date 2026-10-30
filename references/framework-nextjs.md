# Three.js in Next.js (App Router & Pages Router)

Next.js executes React components on the Node.js server during SSR (Server-Side Rendering) and SSG (Static Site Generation). Three.js accesses `window`, `document`, and `WebGLRenderingContext`, which do not exist in Node.js.

---

## 1. The Golden Rule of Next.js 3D Components

**NEVER import or execute Three.js code in a Server Component.**

Always encapsulate Three.js inside a dedicated Client Component with:
1. `'use client';` at the top of the file.
2. Dynamic import with `{ ssr: false }` when rendering from a page.

---

## 2. Implementation Pattern (App Router)

### Step 1: Create Client Canvas Component (`components/Canvas3D.tsx`)
```tsx
'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export default function Canvas3D() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;

    // 1. Renderer Setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);

    // 2. Scene & Camera
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
    camera.position.set(0, 2, 5);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    // 3. Geometry & Light
    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(2, 4, 3);
    scene.add(light);
    scene.add(new THREE.AmbientLight(0xffffff, 0.5));

    const geo = new THREE.TorusKnotGeometry(0.8, 0.25, 100, 16);
    const mat = new THREE.MeshStandardMaterial({ color: 0x6366f1, roughness: 0.3 });
    const mesh = new THREE.Mesh(geo, mat);
    scene.add(mesh);

    // 4. Resize Observer
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

    // 5. Loop
    renderer.setAnimationLoop(() => {
      controls.update();
      mesh.rotation.y += 0.005;
      renderer.render(scene, camera);
    });

    // 6. Mandatory Cleanup on Unmount
    return () => {
      renderer.setAnimationLoop(null);
      resizeObserver.disconnect();
      controls.dispose();
      geo.dispose();
      mat.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    };
  }, []);

  return <div ref={containerRef} className="w-full h-full min-h-[400px]" />;
}
```

### Step 2: Dynamic Import in Page (`app/page.tsx`)
```tsx
import dynamic from 'next/dynamic';

const Canvas3D = dynamic(() => import('@/components/Canvas3D'), {
  ssr: false,
  loading: () => <div className="w-full h-full bg-slate-900 flex items-center justify-center text-white">Loading 3D...</div>
});

export default function Page() {
  return (
    <main className="w-screen h-screen">
      <Canvas3D />
    </main>
  );
}
```
