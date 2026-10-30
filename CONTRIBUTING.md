# Contributing to Three.js Expert Skill

Thank you for your interest in contributing to the **Three.js Expert Skill**!

This project is an independent community open-source technical skill and knowledge base. It is **not** an official Three.js project and is not maintained by the upstream Three.js core team.

---

## 1. Architectural Invariants & Governance

To maintain cross-platform stability across all AI coding assistants (Google Antigravity, Claude Code, Cursor, GitHub Copilot, Windsurf), every contribution must adhere to these non-negotiable rules:

1. **Strict 4/10/10 Canonical Inventory:**
   - `core/` contains exactly **4** universal architectural guides.
   - `references/` contains exactly **10** deep-dive diagnostic guides.
   - `examples/` contains exactly **10** verified runnable code patterns.
   - Do **not** add, remove, or rename files in these folders without an approved architectural RFC.
2. **Adapters as Thin Bridges:**
   - Environment adapters in `adapters/` must not duplicate core prose. They act as high-signal indexes that reference canonical files.
3. **Cross-Platform Text Formatting:**
   - All files must be saved with **UTF-8 encoding** and **LF (`\n`) line endings** (no Windows CRLF).
4. **Read-Only Maintenance & Safety:**
   - Automated tools in `scripts/maintain.py` are strictly read-only.
   - Automatic patch application is explicitly forbidden. All patches go through the review-first proposal workflow.

---

## 2. Development Setup

### Prerequisites
- Python 3.10 or higher.
- `pip` or virtual environment manager.

### Setting Up
```bash
# Clone the repository
git clone https://github.com/your-username/threejs-expert.git
cd threejs-expert

# Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### Optional: Local Three.js Source for API Auditing
The project does not require you to download Three.js source code to use or test the skill. However, if you wish to run local API claim audits (`scripts/maintain.py --audit-local`), you may point to a local directory:
```bash
# Via environment variable
export THREEJS_SOURCE_DIR=/path/to/downloaded/three.js

# Or via CLI flag
python scripts/maintain.py --audit-local --source-dir /path/to/downloaded/three.js
```
*(Note: In the project's development history, the reference source was downloaded directly as a read-only ZIP archive from GitHub, not forked or modified.)*

---

## 3. Running the Test Suite

Before submitting any changes, verify that the complete test suite passes:

```bash
# Run all tests
python -m pytest -p no:anyio tests/ -v
```

All 134 test items (or environment-appropriate subset) must pass.

---

## 4. Maintenance & Proposal Workflow

If you identify an outdated API reference or deprecated pattern:

1. **Scan and Audit:**
   ```bash
   python scripts/maintain.py --report
   ```
2. **Inspect the Findings:**
   Check `reports/latest.md` or `reports/latest.json`.
3. **Generate a Patch Proposal:**
   Only confirmed findings (`CONFIRMED_LOCAL_SOURCE` or `CONFIRMED_OFFICIAL_ONLINE`) are eligible:
   ```bash
   python scripts/maintain.py \
     --propose <FINDING_ID> \
     --target-file core/api-version-compatibility.md \
     --original "exact text in file" \
     --replacement "proposed new text" \
     --rationale "Explanation of change"
   ```
4. **Review the Proposal:**
   ```bash
   python scripts/maintain.py --show-proposal <PROPOSAL_ID>
   ```
   Proposals generate review documents under `reports/proposals/<PROPOSAL_ID>/review.md`.
5. **Approve or Reject:**
   ```bash
   python scripts/maintain.py --approve-proposal <PROPOSAL_ID>
   ```
   *Note: Approval changes metadata only. To finalize the change, manually update the file and submit a pull request.*

---

## 5. Pull Request Guidelines

1. **Focused Scope:** Keep PRs targeted to a specific documentation correction, adapter update, or bug fix.
2. **Integrity Verification:** Ensure canonical file counts remain exactly 4/10/10.
3. **No Automatic Commits of Personal Paths:** Verify that no machine-specific paths (e.g. `C:\Users\...`) appear in committed files.
4. **Commit Hygiene:** Write clear, concise commit messages adhering to standard conventions (e.g. `fix: update HDRLoader import path in vite example`).

