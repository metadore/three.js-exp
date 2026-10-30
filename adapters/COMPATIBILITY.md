# Multi-IDE Adapter Compatibility Matrix & Verification Specification

> **Date Verified:** 2026-10-29  
> **Canonical Source:** Project root (`threejs-expert/`)  
> **Verification Status:** All 5 platforms verified against official documentation.

---

## 1. Master Compatibility Matrix

| Platform | Configuration Format | Primary Discovery Location | Relative Links Inlined? | Outside-Workspace Loading? | Scope Support | Verification Status |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **Google Antigravity** | Markdown with YAML frontmatter (`name`, `description`) | `.agents/skills/<name>/SKILL.md` | Yes (On-Demand Agent Tool) | Yes (User config root) | Project & User | **VERIFIED** |
| **Claude Code** | Markdown with YAML frontmatter + `CLAUDE.md` | `.claude/skills/<name>/SKILL.md` & `CLAUDE.md` | Yes (CLI Agent Tools) | Partial (Permissions-dependent) | Project & User | **VERIFIED** |
| **Cursor** | `.mdc` with YAML frontmatter (`description`, `globs`, `alwaysApply`) | `.cursor/rules/*.mdc` | **No** (Direct Injection Only) | No (Workspace Confined) | Project & User | **VERIFIED** |
| **GitHub Copilot** | Plain Markdown without frontmatter | `.github/copilot-instructions.md` | **No** (Direct Prompt Injection) | No (Workspace Confined) | Project & User | **VERIFIED** |
| **Windsurf** | Markdown with frontmatter or XML sections | `.windsurf/rules/*.md` & `.windsurfrules` | Partial (Cascade Tool Navigation) | No (Workspace Confined) | Project & User | **VERIFIED** |

---

## 2. Platform-by-Platform Technical Specifications

### 2.1 Google Antigravity
* **Primary Documentation:** Antigravity Customization System guide (`~/.gemini/antigravity/builtin/skills/agy-customizations/SKILL.md`), Antigravity CLI reference.
* **Discovery Locations:**
  - Project level: `.agents/skills/<name>/SKILL.md` (or `.agent/`, `_agents/`, `_agent/`).
  - Project rules: `GEMINI.md`, `AGENTS.md`, `.agents/rules/*.md`.
  - User level: `~/.gemini/config/skills/<name>/SKILL.md`.
* **Mechanism:** Progressive disclosure. The agent reads `name` and `description` frontmatter at startup. When user intent matches the description, the agent executes `view_file` on `SKILL.md` and subsequent referenced files.
* **External Files:** Supported within workspace and global user config directories.
* **Limitations:** Requires strict YAML frontmatter (`name`, `description`). Plain markdown files in `.agents/skills/` without frontmatter will fail discovery.

### 2.2 Claude Code (Anthropic)
* **Primary Documentation:** Official Anthropic Docs: `https://docs.anthropic.com/en/docs/claude-code`, Claude Code Skills & Memory guide.
* **Discovery Locations:**
  - Project instructions: `CLAUDE.md` in repository root (loaded at session start). Also `CLAUDE.local.md` for local uncommitted overrides.
  - Skills: `.claude/skills/<name>/SKILL.md` (maps directly to slash command `/<name>`).
  - User level: `~/.claude/skills/<name>/SKILL.md`, `~/.claude/CLAUDE.md`.
* **Mechanism:** `CLAUDE.md` provides session-wide invariants (< 200 lines recommended). Skills provide on-demand workflows triggered by slash commands or autonomous agent invocation.
* **External Files:** CLI can read external files if authorized by terminal permission boundaries.
* **Limitations:** Multi-file references require agent tool calls; `CLAUDE.md` must remain concise to prevent token saturation.

### 2.3 Cursor
* **Primary Documentation:** Official Cursor Docs: `https://docs.cursor.com/context/rules`, Cursor Rules & MDC format specification.
* **Discovery Locations:**
  - Project level: `.cursor/rules/*.mdc` (e.g. `.cursor/rules/threejs-expert.mdc`). Legacy root `.cursorrules` is deprecated.
  - User level: Cursor Settings -> Rules for AI.
* **Format Requirements:** **Must end in `.mdc`**. Plain `.md` files in `.cursor/rules/` are ignored by Cursor's rule parser.
* **Frontmatter Schema:**
  ```yaml
  ---
  description: "Description used by AI in Apply Intelligently mode"
  globs: "**/*.{js,ts,jsx,tsx,html}"
  alwaysApply: false
  ---
  ```
* **Mechanism:** Rules are injected directly into context when matching globs are active or when requested by the model. 
* **External Files:** Cursor cannot automatically load external files or follow hyperlinked Markdown files outside active editor context.
* **Limitations:** Adapters must inline critical non-negotiable rules directly into the `.mdc` body rather than relying solely on external hyperlinks.

### 2.4 GitHub Copilot
* **Primary Documentation:** Official GitHub Docs: `https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot`.
* **Discovery Locations:**
  - Project-wide: `.github/copilot-instructions.md`.
  - Scoped path instructions: `.github/instructions/**/*.instructions.md`.
  - User level: Global instructions in VS Code / JetBrains Copilot settings.
* **Format Requirements:** Pure Markdown without YAML frontmatter. Frontmatter blocks may be echoed literally into prompt context.
* **Mechanism:** Injected into system prompt for Copilot Chat, Code Review, and Cloud Agent.
* **External Files:** Strictly confined to workspace. No automatic hyperlink traversal.
* **Limitations:** Must be self-contained and concise. Core invariants (DPR cap, color space, shadow maps, cleanup) must be explicitly listed in the document.

### 2.5 Windsurf (Codeium)
* **Primary Documentation:** Official Codeium Docs: `https://codeium.com/windsurf`, Cascade Rules & Memories guide.
* **Discovery Locations:**
  - Project level: `.windsurf/rules/*.md` (modern format) or root `.windsurfrules` (legacy).
  - User level: `~/.codeium/windsurf/memories/global_rules.md`.
* **Mechanism:** Rule text is loaded directly into Cascade context. Cascade can browse workspace files on demand during its agentic execution loop.
* **External Files:** Confined to current workspace.
* **Limitations:** Rules should be structured with clear markdown headings to allow Cascade to prioritize relevant instructions.

---

## 3. Structural Strategy for Canonical Adapters

To avoid code duplication while respecting each platform's limitations:

1. **`adapters/antigravity/`**: Full progressive-disclosure orchestrator matching `.agents/skills/<name>/SKILL.md`.
2. **`adapters/claude-code/`**:
   - `CLAUDE.md`: Concise repository rules (< 100 lines) with Three.js invariants.
   - `skills/threejs-expert/SKILL.md`: Interactive slash command `/threejs-expert`.
3. **`adapters/cursor/`**:
   - `threejs-expert.mdc`: Targeted rule with `globs: "**/*.{js,jsx,ts,tsx,html}"` and embedded core guardrails.
4. **`adapters/copilot/`**:
   - `copilot-instructions.md`: Pure markdown instructions with explicit architectural mandates.
5. **`adapters/windsurf/`**:
   - `threejs-expert.md`: Structured markdown rule for `.windsurf/rules/`.
