# Multi-IDE Adapter Deployment & Rollback Guide

This guide documents the controlled, reversible deployment system for installing the Three.js Expert Knowledge Base adapters into client projects across multiple AI coding assistants.

---

## 1. Adapter-to-Destination Mappings

When deploying to a target `--project-root <path>`, each adapter writes strictly to its officially verified project-level destination:

| Adapter Key | AI Assistant | Source File in Canonical Project | Destination in Target Project Root |
| :--- | :--- | :--- | :--- |
| **`antigravity`** | Google Antigravity | `adapters/antigravity/SKILL.md`<br>+ `core/`, `references/`, `examples/` | `.agents/skills/threejs-expert/SKILL.md`<br>+ `.agents/skills/threejs-expert/{core,references,examples}/` (25 files) |
| **`claude-code`** | Claude Code | `adapters/claude-code/CLAUDE.md`<br>`adapters/claude-code/skills/threejs-expert/SKILL.md` | `CLAUDE.md`<br>`.claude/skills/threejs-expert/SKILL.md` |
| **`cursor`** | Cursor | `adapters/cursor/threejs-expert.mdc` | `.cursor/rules/threejs-expert.mdc` |
| **`copilot`** | GitHub Copilot | `adapters/copilot/copilot-instructions.md` | `.github/copilot-instructions.md` |
| **`windsurf`** | Windsurf Cascade | `adapters/windsurf/threejs-expert.md` | `.windsurf/rules/threejs-expert.md` |

*(Note: Target key `all` deploys all 5 adapters in a single atomic transaction).*

---

## 2. CLI Command Reference

### A. List Supported Adapters
Inspect all supported adapters, their descriptions, and exact deployment mappings:
```bash
python scripts/deploy.py --list
```

### B. Dry-Run Planning (Safe Preview)
Calculate all planned file actions (`CREATE`, `REPLACE`, `SKIP_IDENTICAL`, `CONFLICT`) without modifying disk:
```bash
python scripts/deploy.py --adapter cursor --project-root <target-project> --dry-run
```

### C. Standard Deployment (Conflict-Safe)
Deploys the adapter. If any conflicting or differing file already exists, deployment aborts immediately without touching any files:
```bash
python scripts/deploy.py --adapter cursor --project-root <target-project>
```

### D. Force Deployment (With Automatic Backup)
Replaces existing files, but **only after** taking an exact byte-for-byte SHA-256 backup into a unique deployment backup directory:
```bash
python scripts/deploy.py --adapter cursor --project-root <target-project> --force
```

### E. Verification Mode
Validates live deployed files against the SHA-256 hashes recorded in the deployment manifest:
```bash
python scripts/deploy.py --verify --project-root <target-project> --manifest <path/to/manifest.json>
```

### F. Rollback Mode
Reverts a deployment safely:
- Files replaced by the deployment are restored to their exact pre-deployment bytes from backup.
- Files created by the deployment are safely deleted, **provided they have not been subsequently modified**.
- If a user modified a deployed file after installation, rollback halts and preserves the user's modifications.
```bash
python scripts/deploy.py --rollback --manifest <path/to/manifest.json>
```

---

## 3. Backup Architecture & Manifest Structure

### Backup Directory Layout
When a file is replaced during a `--force` deployment, backups are stored in a dedicated, timestamped folder under the target project root:
```text
<target-project>/
└── .threejs-expert-backups/
    └── deploy_YYYYMMDD_HHMMSS_<unique-id>/
        ├── manifest.json              # Atomic deployment manifest
        └── <relative/path/to/file>    # Exact original byte backup
```

### Manifest Schema (`manifest.json`)
```json
{
  "manifest_version": "1.0",
  "deployment_id": "deploy_20261029_220000_a1b2c3d4",
  "timestamp": "2026-10-29T22:00:00.000000Z",
  "adapter": "cursor",
  "project_root": "C:/projects/my-web-app",
  "backup_dir": "C:/projects/my-web-app/.threejs-expert-backups/deploy_20261029_220000_a1b2c3d4",
  "files": [
    {
      "dest_rel": ".cursor/rules/threejs-expert.mdc",
      "action": "REPLACE",
      "existed_before": true,
      "pre_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "deployed_hash": "f2d4e3b1...",
      "backup_rel": ".cursor/rules/threejs-expert.mdc"
    }
  ],
  "status": "SUCCESS"
}
```

---

## 4. Conflict Handling & Safety Boundaries

1. **Safety Boundary Checks**:
   - The deployment tool rejects filesystem root paths (`C:\`, `/`).
   - The deployment tool strictly rejects the Three.js source library (`three.js-dev/three.js-dev`).
   - Destination paths are checked for path traversal (`../`) and symlink escapes.
2. **Byte-Identical Skipping**:
   - If an existing target file already has the exact same SHA-256 hash as the adapter, it is marked `SKIP_IDENTICAL` and left untouched.
3. **Differing Files**:
   - If a target file exists and differs from the adapter, it is marked as a `CONFLICT`.
   - Without `--force`, the tool aborts with exit code 1 to protect existing user configurations.
   - With `--force`, the tool creates an immutable backup before overwriting.
4. **Post-Deployment Modification Protection**:
   - If a file created by deployment was subsequently edited by the user, `--rollback` will refuse to delete it, reporting a safety conflict.

---

## 5. Scope: Project-Level vs. User-Level Configuration

- **Project-Level (Supported by `deploy.py`)**:
  - Installs adapters directly into the project repository (`.agents/`, `.claude/`, `.cursor/`, `.github/`, `.windsurf/`).
  - Suitable for team collaboration and version control (committed via Git).
- **User-Level (Manual Setup Only)**:
  - Global user configurations (e.g. `~/.gemini/config/`, `~/.claude/CLAUDE.md`, Cursor IDE global settings, or `%USERPROFILE%/copilot-instructions.md`).
  - `deploy.py` deliberately operates on explicit project roots and does not modify user-level global system settings.
