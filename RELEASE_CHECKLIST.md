# Open-Source Release Checklist

Before tagging and publishing any release of `threejs-expert`:

- [ ] **1. Canonical Knowledge Integrity:**
  - Verify exactly 4 files in `core/`, 10 in `references/`, 10 in `examples/`.
  - Confirm all internal relative markdown links resolve.
  - Verify all text files have LF line endings (no CRLF).
- [ ] **2. Version Manifest Synchronization:**
  - Run `python scripts/maintain.py --check-manifest` and verify 0 cross-declaration discrepancies.
  - Check that target version, revision claim status, and evidence sources in `version.json` are up to date.
- [ ] **3. Quality & Regression Suite:**
  - Run `python -m pytest -p no:anyio tests/ -v` and verify 100% pass rate.
  - Run `python scripts/maintain.py --validate-examples` and confirm 10/10 examples pass.
- [ ] **4. Build & Deployment Sanity:**
  - Run `python scripts/build.py --dry-run --output-dir temp_build --adapter all` (Exit code 0).
  - Run `python scripts/deploy.py --list` and test dry-run deployments for client projects.
- [ ] **5. Portability & Hygiene:**
  - Confirm no personal paths (`C:\Users\...`) exist in committed files.
  - Ensure dynamic report files (`latest.json`, `latest.md`, `reports/proposals/`) are not committed.
  - Confirm `LICENSE` and attribution notices are present and accurate.
- [ ] **6. Documentation & Changelog:**
  - Update `CHANGELOG.md` with release version and date.
  - Verify `README.md` reflects current architecture, features, and setup instructions.
- [ ] **7. Git Publication:**
  - Review `git status` for clean staging area.
  - Commit with a clear release message (e.g., `release: v1.0.0`).
  - Create a signed/annotated git tag (e.g., `git tag -a v1.0.0 -m "Release v1.0.0"`).

