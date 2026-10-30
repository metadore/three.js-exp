# Three.js Expert Skill

A production-grade, multi-IDE AI coding assistant skill and canonical technical knowledge base for Three.js (verified against Three.js version `0.186.0` / revision `187dev`).

> [!IMPORTANT]
> **Independent Community Project Notice:**  
> This project is an independent open-source community initiative. It is **not** an official Three.js project and is **not** affiliated with, endorsed by, or sponsored by the Three.js project, mrdoob, or the Three.js maintainers.  
> In this project's development history, the upstream Three.js reference source was obtained by directly downloading a ZIP archive from GitHub and used strictly as an offline, read-only reference for API deprecation auditing. It was not forked, cloned as an upstream git repository, or modified.

---

## 1. Project Overview

Modern Three.js development moves quickly: lighting conventions shift, loaders migrate from addons, and WebGPU/TSL introduce new paradigms while legacy tutorials linger across the web.

The **Three.js Expert Skill** bridges this gap by providing AI coding agents (such as Google Antigravity, Claude Code, Cursor, GitHub Copilot, and Windsurf) with a **verified, canonical source of truth**. It prevents common AI hallucinations (such as using obsolete `Geometry`, deprecated `sRGBEncoding`, or legacy `PCFSoftShadowMap`) and enforces production patterns for DPR limits, memory disposal, framework isolation, and color management.

---

## 2. Key Features

- **Strict Modern Invariants (r186+ Standards):**
  - Universal enforcement of `THREE.PCFShadowMap` (`PCFSoftShadowMap` deprecated in r186+).
  - Modern HDR loading with `HDRLoader` (`RGBELoader` deprecated in r180+).
  - Modern WebGPU pass composition with `RenderPipeline` (`PostProcessing` deprecated in r183+).
  - Standardized sRGB color management with `THREE.SRGBColorSpace`.
- **Framework Isolation & Anti-Pattern Prevention:**
  - Dedicated architectural separation for Vanilla JS, Vite, Next.js (Client Component boundary + dynamic import), and React Three Fiber (declarative hooks without raw renderers).
- **GPU Resource Management:**
  - Complete recursive geometry, material, and texture disposal patterns preventing memory leaks and `CONTEXT_LOST_WEBGL` crashes.
- **Multi-IDE Adapter Parity:**
  - One canonical source generates configurations for 5 leading AI assistant environments.
- **Reversible Deployment Tool:**
  - CLI deployer with pre-flight dry-runs, collision detection, automated atomic backups, and SHA-256 manifest-driven rollbacks.
- **Read-Only Maintenance & Audit Subsystem:**
  - Strict manifest verification (`version.json`), token-bounded AST/pattern scanner, offline source auditor, deterministic reporting, and human-reviewed proposal workflow.

---

## 3. Architecture & Directory Structure

The project maintains a strict **4/10/10 canonical inventory**: exactly 4 core architecture guides, 10 deep-dive diagnostic references, and 10 production code examples.

```text
threejs-expert/
├── README.md                          # Master documentation & catalog
├── CONTRIBUTING.md                    # Contributor guide & governance invariants
├── CHANGELOG.md                       # Version history and release notes
├── LICENSE                            # MIT License & attribution notice
├── RELEASE_CHECKLIST.md               # Step-by-step pre-release verification
├── requirements-dev.txt               # Testing dependencies (pytest)
├── version.json                       # Version manifest & audited compatibility claims
│
├── core/                              # [CANONICAL 4 FILES] Universal architectural rules
│   ├── api-version-compatibility.md   # Revision shifts from r125 to r186+
│   ├── engineering-principles.md      # DPR clamping, tone mapping, color space rules
│   ├── framework-detection.md         # 3-step project audit & anti-patterns
│   └── implementation-patterns.md     # Verified scene boilerplate & resize observers
│
├── references/                        # [CANONICAL 10 FILES] Diagnostic guides & matrices
│   ├── accessibility.md               # ARIA labels, focus canvas, reduced motion
│   ├── decision-guide.md              # WebGL vs WebGPU, Vanilla vs R3F
│   ├── disposal-guide.md              # Recursive GPU memory disposal
│   ├── framework-nextjs.md            # Next.js App/Pages router & SSR safety
│   ├── framework-r3f.md               # React Three Fiber declarative rules
│   ├── framework-vanilla.md           # Vanilla JS ES modules & import maps
│   ├── framework-vite.md              # Vite configuration & asset handling
│   ├── troubleshooting-matrix.md      # Master symptom → cause → fix quick reference
│   ├── troubleshooting.md             # Narrative diagnostic workflows
│   └── webgpu-tsl.md                  # WebGPURenderer, TSL shaders & RenderPipeline
│
├── examples/                          # [CANONICAL 10 FILES] Production code templates
│   ├── animation-cleanup.js           # AnimationMixer & bounded loop cleanup
│   ├── basic-vanilla-scene.js         # Minimal boilerplate with resize handling
│   ├── gltf-loader-safe.js            # Safe GLTF loading with Box3 auto-scaling
│   ├── nextjs-client-canvas.tsx       # Next.js 'use client' SSR-safe canvas
│   ├── pointer-raycasting.js          # Canvas-relative NDC coordinate calculation
│   ├── postprocessing-webgl.js        # EffectComposer post-processing pipeline
│   ├── production-scene.js            # Full scene with ACESFilmic & PCFShadowMap
│   ├── r3f-standard-component.jsx     # Declarative Canvas & useFrame hook
│   ├── scroll-animation.js            # Smooth scroll progress animation
│   └── vite-responsive-scene.js       # Vite responsive layout with ResizeObserver
│
├── adapters/                          # Thin bridge configs for AI coding environments
│   ├── antigravity/                   # Google Antigravity skill (SKILL.md)
│   ├── claude-code/                   # Claude Code instructions (CLAUDE.md & skill)
│   ├── cursor/                        # Cursor rules (.cursor/rules/*.mdc)
│   ├── copilot/                       # GitHub Copilot (.github/copilot-instructions.md)
│   └── windsurf/                      # Windsurf rules (.windsurf/rules/*.md)
│
├── scripts/                           # Tooling, build, deployment & maintenance engine
│   ├── build.py                       # Adapter and knowledge packager
│   ├── deploy.py                      # Reversible deployment manager with rollback
│   ├── maintain.py                    # Read-only version auditor, scanner & reporter
│   └── registry.py                    # Canonical file registry & adapter definitions
│
├── tests/                             # Automated test suite (134 test items)
└── reports/                           # Generated audit reports & patch proposals
```

---

## 4. Supported IDE Adapters

| Environment | Target Adapter | Output Location | Discovery Mechanism |
| :--- | :--- | :--- | :--- |
| **Google Antigravity** | `antigravity` | `.agents/skills/threejs-expert/SKILL.md` | Progressive disclosure on agent task match |
| **Claude Code** | `claude-code` | `CLAUDE.md` + `.claude/skills/threejs-expert/` | Session startup instructions + slash command |
| **Cursor** | `cursor` | `.cursor/rules/threejs-expert.mdc` | Prompt rule injection via MDC glob matcher |
| **GitHub Copilot** | `copilot` | `.github/copilot-instructions.md` | Workspace system prompt instructions |
| **Windsurf** | `windsurf` | `.windsurf/rules/threejs-expert.md` | Cascade rules configuration |

---

## 5. Installation Instructions

### Option A: Install Directly into an Existing Project

Use `scripts/deploy.py` to deploy the skill into your target project:

```bash
# Preview what files will be created in your project (dry-run):
python scripts/deploy.py --adapter cursor --project-root /path/to/my-webgl-app --dry-run

# Deploy the adapter:
python scripts/deploy.py --adapter cursor --project-root /path/to/my-webgl-app

# Deploy all adapters simultaneously:
python scripts/deploy.py --adapter all --project-root /path/to/my-webgl-app
```

### Option B: Local Development & Contribution

```bash
git clone https://github.com/your-username/threejs-expert.git
cd threejs-expert
python -m venv .venv
# Activate virtual environment:
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
```

---

## 6. Build Instructions

The builder (`scripts/build.py`) packages canonical knowledge and generates adapter-specific distributions:

```bash
# Build standalone distribution for a specific adapter:
python scripts/build.py --adapter cursor --output-dir dist/cursor

# Build full distribution with all adapters:
python scripts/build.py --adapter all --output-dir dist/full

# Build adapter configuration only (excluding knowledge files):
python scripts/build.py --adapter claude-code --output-dir dist/claude --no-knowledge

# Calculate build actions without writing to disk:
python scripts/build.py --adapter all --output-dir dist/test --dry-run
```

---

## 7. Deployment & Rollback Instructions

The deployment manager (`scripts/deploy.py`) ensures safe, tracked, reversible installation into client repositories:

```bash
# 1. Inspect supported adapters:
python scripts/deploy.py --list

# 2. Deploy with automatic conflict protection and backups:
python scripts/deploy.py --adapter cursor --project-root /path/to/project --force

# 3. Verify a deployment against its manifest:
python scripts/deploy.py --verify --project-root /path/to/project --manifest /path/to/manifest.json

# 4. Safely rollback a deployment:
python scripts/deploy.py --rollback --manifest /path/to/manifest.json
```

---

## 8. Maintenance & Version Auditing

The maintenance tool (`scripts/maintain.py`) operates in a strictly read-only mode to scan for outdated patterns and cross-check version declarations:

```bash
# Check version manifest and declaration consistency:
python scripts/maintain.py --check-manifest

# Scan knowledge base for deprecated Three.js APIs:
python scripts/maintain.py --scan

# Audit claims against a local Three.js source repository:
python scripts/maintain.py --audit-local
# (Optional: specify custom path via --source-dir or THREEJS_SOURCE_DIR environment variable)

# Validate code examples for syntax, imports, and deprecated APIs:
python scripts/maintain.py --validate-examples

# Generate full deterministic JSON and Markdown reports:
python scripts/maintain.py --report
# (Outputs to reports/latest.json and reports/latest.md)
```

---

## 9. Patch Proposal & Review Workflow

Automated tools **never** modify canonical knowledge files directly. When an outdated API is confirmed by local source or official documentation:

1. **Generate a Proposal:**
   ```bash
   python scripts/maintain.py \
     --propose <FINDING_ID> \
     --target-file core/api-version-compatibility.md \
     --original "exact string to replace" \
     --replacement "proposed replacement string" \
     --rationale "Explanation of API change"
   ```
2. **Inspect the Proposal:**
   Review generated documents under `reports/proposals/<PROPOSAL_ID>/review.md`:
   ```bash
   python scripts/maintain.py --show-proposal <PROPOSAL_ID>
   ```
3. **Record Approval or Rejection:**
   ```bash
   python scripts/maintain.py --approve-proposal <PROPOSAL_ID>
   python scripts/maintain.py --reject-proposal <PROPOSAL_ID>
   ```
   *Note: Approving a proposal records a decision record only. Canonical file edits are executed manually and committed through peer review.*

---

## 10. Testing Instructions

Run the automated test suite with pytest:

```bash
python -m pytest -p no:anyio tests/ -v
```

The test suite covers:
- Canonical file manifests and 4/10/10 inventory.
- LF line endings and internal relative link validation.
- Deployment safety, path traversal rejection, and rollback fidelity.
- Scanner precision, token boundary isolation, and import parsing.
- Version manifest constraints and proposal staleness protection.

---

## 11. Known Limitations

1. **Offline Source Auditing:**  
   Auditing compatibility claims via `scripts/maintain.py --audit-local` requires pointing to a local Three.js repository. If unavailable, the tool transparently reports `source_available: False` rather than guessing or fabricating claims.
2. **Revision 187dev Tracking:**  
   Target version `0.186.0` is verified against local source `package.json`. The revision designation `187dev` reflects a recorded claim from repository setup and is documented as `RECORDED_CLAIM_NOT_INDEPENDENTLY_REVERIFIED`.
3. **Windows Symlink Elevation:**  
   Creating genuine filesystem symlinks on Windows requires administrator privileges. In non-elevated Windows shells, test suites use mock verification for symlink escape tests.
4. **No Automatic Patch Application:**  
   By architectural design, the system contains no `--apply` command to prevent unintended changes to canonical standards.

---

## 12. Contribution Guidelines

Contributions are welcome! Please review [CONTRIBUTING.md](CONTRIBUTING.md) for architectural invariants, coding guidelines, and pull request procedures.

---

## License

This project is licensed under the [MIT License](LICENSE).  
Copyright (c) 2026 Three.js Expert Skill Contributors.
