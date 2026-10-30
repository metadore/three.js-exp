# Accessibility & Reduced-Motion in 3D Web Experiences

3D web experiences can cause disorientation, nausea, or vestibular distress for users sensitive to motion.

---

## 1. Respecting User Motion Preferences

Always detect and observe the user's `prefers-reduced-motion` media query:

```javascript
export function setupMotionAccessibility(onMotionPreferenceChange) {
  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

  // Initial check
  onMotionPreferenceChange(mediaQuery.matches);

  // Listen for real-time OS preference changes
  const listener = (event) => onMotionPreferenceChange(event.matches);
  mediaQuery.addEventListener('change', listener);

  return () => mediaQuery.removeEventListener('change', listener);
}
```

### Motion Strategy Guidelines
| Behavior | Normal Motion (`prefers-reduced-motion: no-preference`) | Reduced Motion (`prefers-reduced-motion: reduce`) |
| :--- | :--- | :--- |
| **Idle Animation** | Slow continuous rotation or hovering | Static (zero automatic movement) |
| **Scroll Animations** | Continuous camera interpolation / lerp | Instantaneous waypoint snap on scroll stop |
| **Interactive Drag** | Smooth damping (`dampingFactor: 0.05`) | Immediate response without momentum drift |

---

## 2. Accessible DOM Overlays via `CSS2DRenderer`

Screen readers cannot read pixels rendered in a WebGL `<canvas>`. To make 3D annotations accessible, use `CSS2DRenderer` from `three/addons/renderers/CSS2DRenderer.js`:

```javascript
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

// Create accessible HTML element with proper ARIA attributes
const labelDiv = document.createElement('div');
labelDiv.className = 'label-accessible';
labelDiv.setAttribute('role', 'region');
labelDiv.setAttribute('aria-label', 'Interactive 3D Engine Component');
labelDiv.innerHTML = '<button aria-label="Inspect turbine rotor">Turbine Rotor</button>';

const labelObject = new CSS2DObject(labelDiv);
labelObject.position.set(0, 1.5, 0);
mesh.add(labelObject);
```
