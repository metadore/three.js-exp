# React Three Fiber (`@react-three/fiber`) Implementation Guide

React Three Fiber (R3F) is a declarative React reconciler for Three.js. It does not wrap Three.js in a separate engine; it compiles JSX directly into Three.js object instances.

---

## 1. Paradigm Differences

| Feature | Vanilla Three.js | React Three Fiber |
| :--- | :--- | :--- |
| **Object Instantiation** | `const mesh = new THREE.Mesh(...)` | `<mesh>` |
| **Render Loop** | `renderer.setAnimationLoop(callback)` | `useFrame((state, delta) => {})` |
| **Scene Graph** | `parent.add(child)` | Nesting JSX `<group><mesh /></group>` |
| **Resizing** | Container `ResizeObserver` | Automatic via `<Canvas>` wrapper |
| **Disposal** | Manual `.dispose()` traversal | Automatic upon unmount |
| **Loaders** | `new GLTFLoader().load(...)` | `useGLTF(url)` hook via `@react-three/drei` |

---

## 2. Production R3F Component Pattern

```jsx
import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Environment, useGLTF } from '@react-three/drei';

function Model({ url }) {
  const { scene } = useGLTF(url);
  const modelRef = useRef();

  useFrame((state, delta) => {
    if (modelRef.current) {
      modelRef.current.rotation.y += delta * 0.2;
    }
  });

  return <primitive ref={modelRef} object={scene} scale={1.5} />;
}

export default function Scene3D() {
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#0f172a' }}>
      <Canvas
        dpr={[1, 2]} // Automatic DPR clamping to [min, max]
        camera={{ position: [0, 2, 5], fov: 45 }}
        gl={{ antialias: true, powerPreference: 'high-performance' }}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 8, 4]} intensity={2.0} castShadow />

        <Model url="/models/robot.glb" />

        <OrbitControls enableDamping dampingFactor={0.05} />
        <Environment preset="city" />
      </Canvas>
    </div>
  );
}
```

---

## 3. Critical Rules for AI Agents Working in R3F

1. **NEVER call `new THREE.WebGLRenderer()`** inside an R3F project.
2. **NEVER use `useEffect` to start a `requestAnimationFrame` loop**. Use `useFrame`.
3. **Do NOT manually append `<canvas>` to the DOM**. `<Canvas>` handles DOM mounting.
4. If the user asks for post-processing in R3F, use `@react-three/postprocessing`, NOT vanilla `EffectComposer`.
