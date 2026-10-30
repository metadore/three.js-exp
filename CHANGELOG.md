# Changelog

All notable changes to the **Three.js Expert Skill** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-30

### Initial Open-Source Release

#### Canonical Knowledge Base
- **4 Universal Core Foundations (`core/`):**
  - `api-version-compatibility.md`: Historical and contemporary Three.js revision shifts from r125 to r186+.
  - `engineering-principles.md`: DPR clamps, tone mapping, sRGB color space invariants, recursive disposal rules.
  - `framework-detection.md`: Multi-step heuristic audit for Vanilla, Vite, Next.js, and React Three Fiber environments.
  - `implementation-patterns.md`: Standard boilerplate patterns, ResizeObserver bindings, and lighting topologies.
- **10 Diagnostic Reference Guides (`references/`):**
  - Accessibility standards, architectural decision guide, recursive disposal manual, framework-specific guides (Next.js, R3F, Vanilla, Vite), master troubleshooting matrix and diagnostic workflows, and WebGPU/TSL guide.
- **10 Production-Grade Code Examples (`examples/`):**
  - Vanilla scene, Vite setup, Next.js SSR canvas, React Three Fiber component, GLTF loader with Box3 scaling, animation mixer cleanup, post-processing pass chains, pointer raycasting, scroll progress animations, and full production scene setup.

#### Multi-IDE Adapter Ecosystem (`adapters/`)
- Native support for 5 major AI coding environments:
  - **Google Antigravity:** Progressive disclosure skill (`SKILL.md`).
  - **Claude Code:** System instruction bundle (`CLAUDE.md`) and slash command skill.
  - **Cursor:** MDC rules configuration (`.cursor/rules/threejs-expert.mdc`).
  - **GitHub Copilot:** Repository instructions (`.github/copilot-instructions.md`).
  - **Windsurf Cascade:** Cascade rules configuration (`.windsurf/rules/threejs-expert.md`).

#### Tooling & Deployment Engine (`scripts/`)
- `scripts/build.py`: Portable knowledge packager and adapter builder supporting dry-run previews and boundary containment.
- `scripts/deploy.py`: Reversible multi-IDE deployment tool featuring collision detection, automated atomic backups, SHA-256 manifest tracking, and verified rollbacks.
- `scripts/maintain.py`: Read-only maintenance subsystem with:
  - Strict version manifest verification (`version.json`).
  - Token-bounded AST/pattern scanner distinguishing code examples from explanatory prose.
  - Independent local-source symbol auditor with line and snippet extraction.
  - Deterministic JSON and Markdown maintenance reports.
  - Human-reviewed patch proposal workflow with staleness detection and metadata-only approval gates (automatic patching strictly forbidden).

#### Testing & Quality Assurance (`tests/`)
- 134-item comprehensive test suite verifying link integrity, schema validation, deployment safety, scanner precision, import categorization, and proposal invariants.

