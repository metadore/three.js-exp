/**
 * React Three Fiber (R3F) Production Component
 * Target: React 18/19 with @react-three/fiber and @react-three/drei.
 * Rules: Never instantiate WebGLRenderer directly; use declarative scene graph.
 */
import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Float, MeshDistortMaterial } from '@react-three/drei';

function AnimatedSphere() {
  const meshRef = useRef();

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * 0.2;
      meshRef.current.rotation.y += delta * 0.3;
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
      <mesh ref={meshRef} castShadow>
        <sphereGeometry args={[1, 64, 64]} />
        <MeshDistortMaterial
          color="#38bdf8"
          roughness={0.2}
          metalness={0.8}
          distort={0.4}
          speed={2}
        />
      </mesh>
    </Float>
  );
}

export default function R3FScene() {
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#090d16' }}>
      <Canvas
        dpr={[1, 2]} // Automatic DPR clamping to [min, max]
        camera={{ position: [0, 0, 4.5], fov: 45 }}
        gl={{ antialias: true, powerPreference: 'high-performance' }}
      >
        <color attach="background" args={['#090d16']} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 8, 5]} intensity={2.0} castShadow />

        <AnimatedSphere />

        <OrbitControls enableDamping dampingFactor={0.05} />
      </Canvas>
    </div>
  );
}
