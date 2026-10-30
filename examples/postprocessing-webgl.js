/**
 * Production WebGL Post-Processing Pipeline
 * Features: EffectComposer, RenderPass, UnrealBloomPass, OutputPass.
 */
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

export function setupPostProcessing(renderer, scene, camera, width, height) {
  // 1. Create Effect Composer
  const composer = new EffectComposer(renderer);
  composer.setSize(width, height);

  // 2. Base Scene Render Pass
  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);

  // 3. Unreal Bloom Pass
  const bloomPass = new UnrealBloomPass(
    new THREE.Vector2(width, height),
    0.7, // Strength
    0.4, // Radius
    0.85 // Threshold (only objects with high luminance glow)
  );
  composer.addPass(bloomPass);

  // 4. Output Pass (Handles tone mapping & color space conversion)
  const outputPass = new OutputPass();
  composer.addPass(outputPass);

  return {
    composer,
    bloomPass,
    resize(newWidth, newHeight) {
      composer.setSize(newWidth, newHeight);
      bloomPass.resolution.set(newWidth, newHeight);
    },
    render() {
      composer.render();
    },
    destroy() {
      composer.dispose();
    }
  };
}
