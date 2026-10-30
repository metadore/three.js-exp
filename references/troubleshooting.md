# Three.js Troubleshooting & Diagnostic Procedures

Use this systematic guide to isolate and resolve common 3D rendering failures.

---

## 1. Black Screen / Blank Canvas

A blank canvas is the most frequent issue. Work through these checks in order:

### Step 1: Canvas Geometry & DOM
- Verify container dimensions in DevTools: Is `container.clientWidth === 0` or `container.clientHeight === 0`?
- Check CSS styling: Ensure the canvas or its parent has `width: 100%`, `height: 100%`, or fixed pixel dimensions.
- Verify `renderer.setSize(width, height, false)` was called.

### Step 2: Camera Position & Clipping Planes
- **Camera inside mesh**: If camera is at `(0, 0, 0)` and an imported model is centered at `(0, 0, 0)`, the camera may be inside the mesh with backface culling active.
  - *Fix*: Move camera back: `camera.position.set(0, 2, 5); camera.lookAt(0, 0, 0);`.
- **Near/Far clipping**:
  - If `camera.near = 10` and object is at `z = 5`, it is clipped.
  - If `camera.far = 10` and object is at `z = 50`, it is clipped.
  - *Standard*: `new THREE.PerspectiveCamera(50, aspect, 0.1, 1000)`.

### Step 3: Missing Lights with PBR Materials
- `MeshStandardMaterial` and `MeshPhysicalMaterial` require light to reflect. Without lights, they render completely black.
- *Quick Diagnostic*: Temporarily add `scene.add(new THREE.AmbientLight(0xffffff, 2.0));` or swap material to `MeshBasicMaterial({ wireframe: true, color: 0x00ff00 })`. If the wireframe appears, the issue is lighting.

### Step 4: WebGPURenderer Initialization
- If using `WebGPURenderer`, forgetting `await renderer.init()` before the first render call will prevent pipeline compilation and result in an empty screen.

---

## 2. GLTF/GLB Asset Loading Failures

### 404 Not Found / Incorrect URL
- In Vite: Assets in `public/models/robot.glb` should be referenced as `/models/robot.glb` (root-relative), NOT `./public/...` or relative paths that break when routes change.
- In Next.js: Assets in `public/` are served at the root URL.

### Model Invisible or Displaced
- Model may have arbitrary coordinate offsets from Blender/Maya:
  ```javascript
  const box = new THREE.Box3().setFromObject(gltf.scene);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  console.log('Model Bounding Size:', size);
  console.log('Model Bounding Center:', center);
  ```
- If size is `0.0001`, the model is microscopic. If size is `50000`, the model engulfs the camera. Normalize size to 2 units as shown in `examples/gltf-loader-safe.js`.

### DRACO Compression Errors
- Symptom: `No DRACOLoader instance provided` or decoder 404 errors.
- Fix: Provide the Google CDN or local public path to decoder files:
  ```javascript
  dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.7/');
  ```

---

## 3. Lighting & Shadow Glitches

### Shadow Acne (Stripes across surfaces)
- Cause: Self-shadowing precision artifacts on surface polygons.
- Fix:
  ```javascript
  light.shadow.bias = -0.0005;
  light.shadow.normalBias = 0.02;
  ```

### Peter-Panning (Shadows disconnected from base)
- Cause: `shadow.bias` is set too negative.
- Fix: Reduce absolute bias value, rely on `normalBias = 0.01` to `0.03`.

### Shadows Cut Off Abruptly
- Cause: DirectionalLight shadow camera frustum is too small for the scene.
- Fix:
  ```javascript
  const d = 10;
  light.shadow.camera.left = -d;
  light.shadow.camera.right = d;
  light.shadow.camera.top = d;
  light.shadow.camera.bottom = -d;
  light.shadow.camera.updateProjectionMatrix();
  ```

---

## 4. Animation & Interaction Failures

### GLTF Animations Not Playing
- Did you instantiate `AnimationMixer`?
  ```javascript
  const mixer = new THREE.AnimationMixer(gltf.scene);
  const action = mixer.clipAction(gltf.animations[0]);
  action.play();
  ```
- Is the mixer being updated in the render loop with delta time?
  ```javascript
  // Inside setAnimationLoop:
  const delta = clock.getDelta();
  if (mixer) mixer.update(delta);
  ```

### Raycaster Not Selecting Objects
- Pointer coordinates must be normalized device coordinates (NDC) in range `[-1, 1]`:
  ```javascript
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const intersects = raycaster.intersectObjects(selectableObjects, true);
  ```

---

## 5. Performance Bottlenecks & Low Framerate

| Diagnosis | Metric / Tool | Recommended Resolution |
| :--- | :--- | :--- |
| **Too many draw calls** | Check `renderer.info.render.calls` > 200 | Use `InstancedMesh` for repeated objects; use `BatchedMesh` or merge static geometries. |
| **Excessive triangle count** | Check `renderer.info.render.triangles` > 1M | Decimate geometry, use LOD (`THREE.LOD`), or normal maps instead of high-poly geometry. |
| **GPU Fill-Rate Throttling** | High GPU usage on mobile/4K | Clamp pixel ratio: `Math.min(window.devicePixelRatio, 2)`. |
| **Expensive Post-Processing** | Framerate drops on bloom/SSAO | Downscale post-processing render targets; disable high-overhead passes on mobile. |
