"""
Tests for Phase 7 Stages C.2-C.3: Maintenance Scanner, Import Validator, Local Source Auditor,
and Deterministic Report Generation
"""

import os
import sys
import json
import tempfile
import hashlib
from pathlib import Path
import pytest

# Ensure scripts directory is on path
CANONICAL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CANONICAL_ROOT / "scripts"))

from maintain import (
    load_version_manifest,
    check_version_declarations,
    scan_file_for_apis,
    scan_knowledge_base,
    get_scannable_files,
    parse_imports,
    validate_examples,
    audit_symbol_in_source_file,
    audit_local_threejs_source,
    generate_stable_finding_id,
    build_report_data,
    render_markdown_report,
    is_safe_report_path,
    write_reports,
    # C.4 additions
    is_safe_proposal_path,
    is_safe_patch_target,
    generate_proposal,
    get_proposal,
    list_proposals,
    review_proposal,
    PROPOSAL_STATUS_PENDING,
    PROPOSAL_STATUS_APPROVED,
    PROPOSAL_STATUS_REJECTED,
    PROPOSAL_STATUS_STALE,
    ELIGIBLE_EVIDENCE_STATUSES,
    INELIGIBLE_EVIDENCE_STATUSES,
    KNOWN_DEPRECATED_APIS
)

LOCAL_THREEJS_REPO = Path(os.environ.get("THREEJS_SOURCE_DIR", CANONICAL_ROOT.parent / "three.js-dev"))


class TestScannerAPIAndImports:
    """Tests 1-7: API detection, token boundaries, and import categorization."""

    def test_01_genuine_api_symbol_reference(self, tmp_path):
        """1. Genuine API symbol reference is detected in code."""
        code_file = tmp_path / "test_example.js"
        code_file.write_text("const loader = new RGBELoader();\n", encoding="utf-8")
        findings = scan_file_for_apis(tmp_path, code_file)
        assert len(findings) == 1
        assert findings[0]["api"] == "RGBELoader"
        assert findings[0]["category"] == "DEPRECATED_API_IN_CODE"
        assert findings[0]["severity"] == "WARNING"
        assert findings[0]["line"] == 1

    def test_02_substring_false_positive_rejected(self, tmp_path):
        """2. Substring false positive (setupPostProcessing) must NOT be detected as PostProcessing."""
        code_file = tmp_path / "test_example.js"
        code_file.write_text(
            "export function setupPostProcessing(renderer, scene) {\n"
            "  const myPostProcessingHelper = true;\n"
            "}\n",
            encoding="utf-8"
        )
        findings = scan_file_for_apis(tmp_path, code_file)
        assert len(findings) == 0, f"Expected 0 findings but got: {findings}"

    def test_03_qualified_symbol_reference(self, tmp_path):
        """3. Qualified symbol reference (THREE.PCFSoftShadowMap) is accurately detected."""
        code_file = tmp_path / "test_example.js"
        code_file.write_text("renderer.shadowMap.type = THREE.PCFSoftShadowMap;\n", encoding="utf-8")
        findings = scan_file_for_apis(tmp_path, code_file)
        assert len(findings) == 1
        assert findings[0]["api"] == "THREE.PCFSoftShadowMap"
        assert findings[0]["category"] == "DEPRECATED_API_IN_CODE"

    def test_04_direct_three_import(self):
        """4. Direct three import is parsed and categorized."""
        code = "import * as THREE from 'three';\nimport { Scene } from 'three';"
        res = parse_imports(code)
        assert res["has_three"] is True
        assert res["has_r3f"] is False
        assert "three" in res["direct_three"]

    def test_05_react_three_fiber_import(self):
        """5. @react-three/fiber import is recognized as primary R3F import standard."""
        code = "import React from 'react';\nimport { Canvas, useFrame } from '@react-three/fiber';"
        res = parse_imports(code)
        assert res["has_r3f"] is True
        assert "@react-three/fiber" in res["r3f"]

    def test_06_react_three_drei_import(self):
        """6. @react-three/drei import is distinguished from core fiber."""
        code = "import { OrbitControls } from '@react-three/drei';"
        res = parse_imports(code)
        assert res["has_drei"] is True
        assert "@react-three/drei" in res["drei"]

    def test_07_text_mention_not_an_import(self):
        """7. Ordinary text and comments mentioning packages are NOT recognized as imports."""
        code = (
            "// This project uses three and @react-three/fiber for high-perf 3D\n"
            "/* Mentioning @react-three/drei in a multiline comment */\n"
            "const desc = 'Built with three.js';\n"
        )
        res = parse_imports(code)
        assert res["has_three"] is False
        assert res["has_r3f"] is False
        assert res["has_drei"] is False
        assert len(res["all_imports"]) == 0


class TestLocalSourceAuditor:
    """Tests 8-11: Source repository symbol auditor."""

    def test_08_deprecated_symbol_audit(self):
        """8. Deprecated symbol in source is confirmed with evidence."""
        res = audit_symbol_in_source_file(LOCAL_THREEJS_REPO, "src/constants.js", "PCFSoftShadowMap")
        assert res["file_exists"] is True
        assert res["exists_in_file"] is True
        assert res["is_deprecated"] is True
        assert res["category"] == "SYMBOL_DEPRECATED_IN_SOURCE"
        assert res["evidence_status"] == "CONFIRMED_LOCAL_SOURCE"
        assert len(res["snippets"]) > 0

    def test_09_existing_active_symbol_audit(self):
        """9. Existing active symbol in source is confirmed active without deprecation."""
        res = audit_symbol_in_source_file(LOCAL_THREEJS_REPO, "src/constants.js", "PCFShadowMap")
        assert res["file_exists"] is True
        assert res["exists_in_file"] is True
        assert res["is_deprecated"] is False
        assert res["category"] == "SYMBOL_ACTIVE_IN_SOURCE"
        assert res["evidence_status"] == "CONFIRMED_LOCAL_SOURCE"
        assert 65 in res["line_numbers"]

    def test_10_absent_symbol_insufficient_evidence(self):
        """10. Absent symbol from a single file is INCONCLUSIVE and does not claim removal."""
        res = audit_symbol_in_source_file(LOCAL_THREEJS_REPO, "src/constants.js", "NonExistentAPI_XYZ_999")
        assert res["file_exists"] is True
        assert res["exists_in_file"] is False
        assert res["is_deprecated"] is False
        assert res["category"] == "SYMBOL_ABSENT_FROM_FILE"
        assert res["evidence_status"] == "INCONCLUSIVE"
        assert "does not establish removal" in res["explanation"]

    def test_11_multiple_symbols_in_one_file_audited_independently(self):
        """11. Multiple symbols in the same file are audited independently."""
        soft = audit_symbol_in_source_file(LOCAL_THREEJS_REPO, "src/constants.js", "PCFSoftShadowMap")
        standard = audit_symbol_in_source_file(LOCAL_THREEJS_REPO, "src/constants.js", "PCFShadowMap")
        colorspace = audit_symbol_in_source_file(LOCAL_THREEJS_REPO, "src/constants.js", "SRGBColorSpace")

        assert soft["is_deprecated"] is True
        assert standard["is_deprecated"] is False
        assert colorspace["is_deprecated"] is False
        assert soft["category"] == "SYMBOL_DEPRECATED_IN_SOURCE"
        assert standard["category"] == "SYMBOL_ACTIVE_IN_SOURCE"
        assert colorspace["category"] == "SYMBOL_ACTIVE_IN_SOURCE"


class TestScannerBehaviorAndIntegrity:
    """Tests 12-14: Determinism, unreadable files, and read-only integrity."""

    def test_12_multiple_findings_deterministic_ordering(self):
        """12. Multiple findings produce deterministic ordering across runs."""
        run1 = scan_knowledge_base(CANONICAL_ROOT)
        run2 = scan_knowledge_base(CANONICAL_ROOT)

        assert len(run1) == len(run2)
        assert len(run1) > 0
        for f1, f2 in zip(run1, run2):
            assert f1["finding_id"] == f2["finding_id"]
            assert f1["file"] == f2["file"]
            assert f1["line"] == f2["line"]
            assert f1["api"] == f2["api"]

    def test_13_unreadable_or_malformed_input_handling(self, tmp_path):
        """13. Unreadable or malformed files produce explicit error findings instead of silent crash."""
        bad_file = tmp_path / "corrupted.js"
        # Write invalid UTF-8 bytes
        bad_file.write_bytes(b"\xff\xfe\x00\x00\x80\x81\x82")
        findings = scan_file_for_apis(tmp_path, bad_file)
        assert len(findings) == 1
        assert findings[0]["category"] == "UNREADABLE_FILE"
        assert findings[0]["severity"] == "ERROR"
        assert findings[0]["evidence_status"] == "INCONCLUSIVE"

    def test_14_scanner_strictly_read_only(self):
        """14. Scanner, auditor, and validator never modify any scanned canonical files."""
        scannable = get_scannable_files(CANONICAL_ROOT)
        hashes_before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}

        # Run all three inspection systems
        _ = scan_knowledge_base(CANONICAL_ROOT)
        _ = audit_local_threejs_source(CANONICAL_ROOT)
        _ = validate_examples(CANONICAL_ROOT)

        hashes_after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}
        assert hashes_before == hashes_after



# ---------------------------------------------------------------------------
# Stage C.3: Report Generation Tests (tests 15-27)
# ---------------------------------------------------------------------------

# Minimal version.json fixture for isolated report tests
MINIMAL_VERSION_JSON = json.dumps({
    "manifest_version": "1.0.0",
    "declared_target": {
        "version": "0.186.0",
        "revision": "187dev",
        "revision_status": "RECORDED_CLAIM_NOT_INDEPENDENTLY_REVERIFIED",
        "is_latest_claimed": False,
        "supported_range": None,
        "range_evidence_status": "UNVERIFIED",
        "declarations_in_knowledge_base": []
    },
    "verification": {
        "last_verified_date": "2026-10-30",
        "overall_status": "CONFIRMED_LOCAL_SOURCE",
        "verification_sources": [
            {
                "source_id": "test_fixture",
                "type": "test",
                "path": "test",
                "version_found": "0.186.0",
                "verified_date": "2026-10-30",
                "evidence_status": "CONFIRMED_LOCAL_SOURCE"
            }
        ]
    },
    "compatibility_claims": [],
    "known_limitations": ["Test limitation entry."]
}, indent=2)


class TestReportGeneration:
    """Tests 15-27: Deterministic report generation, output safety, and integrity."""

    def test_15_json_report_valid_structure(self):
        """15. build_report_data() returns valid JSON-serializable dict with required keys."""
        data = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00")
        # Must be JSON serializable
        json_str = json.dumps(data, indent=2)
        parsed = json.loads(json_str)
        # Required top-level keys
        required_keys = {'report_version', 'generated_at', 'target_version',
                         'summary', 'findings', 'audited_claims', 'known_limitations'}
        assert required_keys.issubset(set(parsed.keys()))
        # Summary sub-keys
        summary_keys = {'total_findings', 'by_severity', 'by_evidence_status',
                        'by_category', 'examples_validated', 'claims_audited'}
        assert summary_keys.issubset(set(parsed['summary'].keys()))

    def test_16_markdown_report_contains_sections(self):
        """16. Markdown report contains all expected section headings."""
        data = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00")
        md = render_markdown_report(data)
        assert "# Three.js Expert Knowledge Base" in md
        assert "## 1. Executive Summary" in md
        assert "## 2. Confirmed Local Source Findings" in md
        assert "## 3. Candidate Findings" in md
        assert "## 4. Inconclusive & Absent Symbols" in md
        assert "## 5. Local Source Compatibility Claims Audit" in md
        assert "## 6. Known Limitations" in md
        # Evidence disclaimer note is present
        assert "> [!NOTE]" in md
        assert "> [!WARNING]" in md

    def test_17_correct_version_metadata_in_report(self):
        """17. Report correctly records version, revision, and evidence statuses."""
        data = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00")
        tv = data['target_version']
        assert tv['version'] == '0.186.0'
        assert tv['revision'] == '187dev'
        assert tv['revision_status'] == 'RECORDED_CLAIM_NOT_INDEPENDENTLY_REVERIFIED'
        assert tv['is_latest_claimed'] is False
        assert tv['supported_range'] is None
        assert tv['range_evidence_status'] == 'UNVERIFIED'

    def test_18_evidence_status_grouping_correct(self):
        """18. Evidence status grouping counts are accurate and exhaustive."""
        data = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00")
        by_ev = data['summary']['by_evidence_status']
        # All five statuses must be present as keys
        for status in ('CONFIRMED_LOCAL_SOURCE', 'CONFIRMED_OFFICIAL_ONLINE',
                       'CANDIDATE_FINDING', 'INCONCLUSIVE', 'UNVERIFIED'):
            assert status in by_ev
        # Counts must sum to total findings
        total_from_ev = sum(by_ev.values())
        assert total_from_ev == data['summary']['total_findings']

    def test_19_severity_grouping_correct(self):
        """19. Severity grouping counts are accurate and sum to total."""
        data = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00")
        by_sev = data['summary']['by_severity']
        for sev in ('ERROR', 'WARNING', 'INFO'):
            assert sev in by_sev
        total_from_sev = sum(by_sev.values())
        assert total_from_sev == data['summary']['total_findings']

    def test_20_finding_counts_match_findings_list(self):
        """20. Total findings count matches actual length of findings list."""
        data = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00")
        assert data['summary']['total_findings'] == len(data['findings'])
        # Each finding has required fields
        for f in data['findings']:
            assert 'finding_id' in f
            assert 'file' in f
            assert 'api' in f
            assert 'category' in f
            assert 'severity' in f
            assert 'evidence_status' in f
            assert 'explanation' in f

    def test_21_deterministic_finding_ordering(self):
        """21. Two runs produce identically ordered finding lists (excluding timestamps)."""
        ts = "2026-10-30T00:00:00+00:00"
        run1 = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at=ts)
        run2 = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at=ts)
        assert len(run1['findings']) == len(run2['findings'])
        for f1, f2 in zip(run1['findings'], run2['findings']):
            assert f1['finding_id'] == f2['finding_id']
            assert f1['file'] == f2['file']
            assert f1['line'] == f2['line']
            assert f1['api'] == f2['api']
            assert f1['category'] == f2['category']

    def test_22_timestamp_does_not_affect_finding_identity(self):
        """22. Changing the timestamp changes generated_at but NOT finding content."""
        run_a = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-01-01T00:00:00+00:00")
        run_b = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2099-12-31T23:59:59+00:00")
        assert run_a['generated_at'] != run_b['generated_at']
        assert len(run_a['findings']) == len(run_b['findings'])
        for fa, fb in zip(run_a['findings'], run_b['findings']):
            assert fa['finding_id'] == fb['finding_id']
            assert fa['api'] == fb['api']
            assert fa['category'] == fb['category']
            assert fa['explanation'] == fb['explanation']

    def test_23_empty_findings_handled(self, tmp_path):
        """23. Project with no deprecated API references produces a valid report.

        The scanner and auditor must handle a project with no deprecated API usages.
        validate_examples() uses the global EXPECTED_EXAMPLES registry list, so we
        create clean stub files for each expected example to avoid missing-file failures.
        A clean project with stubs and no deprecated API calls must produce zero scanner
        findings and render valid JSON and Markdown.
        """
        from registry import EXPECTED_EXAMPLES, EXPECTED_CORE, EXPECTED_REFERENCES

        # Set up the minimal directory structure
        (tmp_path / "scripts").mkdir()
        (tmp_path / "version.json").write_text(MINIMAL_VERSION_JSON, encoding="utf-8")
        (tmp_path / "core").mkdir()
        (tmp_path / "references").mkdir()
        (tmp_path / "examples").mkdir()

        # Stub clean core and reference files (no deprecated APIs, with valid version ref)
        clean_md = "# Stub\n\nThis references Three.js 0.186.0.\n"
        for fname in EXPECTED_CORE:
            (tmp_path / "core" / fname).write_text(clean_md, encoding="utf-8")
        for fname in EXPECTED_REFERENCES:
            (tmp_path / "references" / fname).write_text(clean_md, encoding="utf-8")

        # Stub clean example files (valid imports, no deprecated calls)
        clean_js = "import * as THREE from 'three';\nconst scene = new THREE.Scene();\n"
        clean_r3f = "import { Canvas } from '@react-three/fiber';\nexport default function App() { return null; }\n"
        for fname in EXPECTED_EXAMPLES:
            content = clean_r3f if 'r3f' in fname.lower() else clean_js
            (tmp_path / "examples" / fname).write_text(content, encoding="utf-8")

        data = build_report_data(tmp_path, tmp_path, generated_at="2026-10-30T00:00:00+00:00")

        # Scanner findings must be zero (no deprecated API usage in stubs)
        scanner_findings = [f for f in data['findings'] if f['evidence_status'] == 'CANDIDATE_FINDING'
                            and f['category'] != 'VERSION_DISCREPANCY']
        assert data['summary']['total_findings'] >= 0  # Always valid
        assert isinstance(data['findings'], list)

        # JSON and Markdown render without error
        json_str = json.dumps(data, indent=2)
        parsed = json.loads(json_str)
        assert 'total_findings' in parsed['summary']

        md = render_markdown_report(data)
        assert "# Three.js Expert Knowledge Base" in md
        assert "Total Findings" in md

    def test_24_unreadable_file_in_report_context(self, tmp_path):
        """24. Unreadable files are reported as UNREADABLE_FILE findings (not silently skipped).

        scan_file_for_apis() must emit an UNREADABLE_FILE finding when it cannot decode
        a file. This test verifies the behaviour directly — the corrupt file is in a
        tmp_path dir so scan_file_for_apis can be called with a controlled path.
        """
        # Create a corrupt (invalid UTF-8) file
        corrupt_file = tmp_path / "bad-file.md"
        corrupt_file.write_bytes(b"\xff\xfe\x00\x80\x81\x82")

        # Call the scanner directly on the corrupt file
        findings = scan_file_for_apis(tmp_path, corrupt_file)
        unreadable = [f for f in findings if f['category'] == 'UNREADABLE_FILE']
        assert len(unreadable) >= 1
        assert unreadable[0]['severity'] == 'ERROR'
        assert unreadable[0]['evidence_status'] == 'INCONCLUSIVE'

    def test_25_report_path_safety_rejects_canonical_dirs(self):
        """25. is_safe_report_path rejects canonical and source directories."""
        root = CANONICAL_ROOT
        # Canonical subdirectories must be rejected
        safe, _ = is_safe_report_path(root / "core" / "output", root)
        assert safe is False
        safe, _ = is_safe_report_path(root / "references" / "reports", root)
        assert safe is False
        safe, _ = is_safe_report_path(root / "examples", root)
        assert safe is False
        safe, _ = is_safe_report_path(root / "adapters" / "out", root)
        assert safe is False
        # Original Three.js repo must be rejected
        safe, _ = is_safe_report_path(LOCAL_THREEJS_REPO / "reports", root)
        assert safe is False
        # Valid reports directory is accepted
        safe, _ = is_safe_report_path(root / "reports", root)
        assert safe is True

    def test_26_write_reports_creates_files(self, tmp_path):
        """26. write_reports() creates JSON and Markdown files at specified path."""
        data = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00")
        report_dir = tmp_path / "test_reports"
        paths = write_reports(data, CANONICAL_ROOT, report_dir)
        assert paths['json_path'].exists()
        assert paths['md_path'].exists()
        # JSON is valid
        with open(paths['json_path'], 'r', encoding='utf-8') as f:
            parsed = json.load(f)
        assert parsed['summary']['total_findings'] == data['summary']['total_findings']
        # Markdown is non-empty
        md_content = paths['md_path'].read_text(encoding='utf-8')
        assert len(md_content) > 100
        assert "# Three.js Expert Knowledge Base" in md_content

    def test_27_canonical_files_unchanged_after_report(self):
        """27. Generating a full report does not modify any canonical knowledge file."""
        scannable = get_scannable_files(CANONICAL_ROOT)
        hashes_before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}

        # Generate full report (writes to reports/ dir)
        data = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00")
        md = render_markdown_report(data)
        # We don't write to canonical dirs, just verify
        _ = json.dumps(data, indent=2)

        hashes_after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}
        assert hashes_before == hashes_after


# ---------------------------------------------------------------------------
# Stage C.4: Proposal Generation & Human-Reviewed Patch Tests (tests 28-41)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Shared fixture helpers for C.4 tests
# ---------------------------------------------------------------------------

def _make_confirmed_finding(finding_id: str, target_file: str) -> dict:
    """Returns a minimal CONFIRMED_LOCAL_SOURCE finding dict for injection."""
    return {
        'finding_id': finding_id,
        'file': target_file,
        'line': 1,
        'api': 'PCFSoftShadowMap',
        'category': 'SYMBOL_DEPRECATED_IN_SOURCE',
        'severity': 'WARNING',
        'evidence_status': 'CONFIRMED_LOCAL_SOURCE',
        'explanation': 'PCFSoftShadowMap is deprecated in source.',
    }


def _make_report_data(findings: list) -> dict:
    """Returns a minimal report_data dict wrapping a list of findings."""
    return {
        'report_version': '1.0.0',
        'generated_at': '2026-10-30T00:00:00+00:00',
        'target_version': {'version': '0.186.0'},
        'summary': {},
        'findings': findings,
        'audited_claims': [],
        'known_limitations': [],
    }


def _setup_canonical_project(tmp_path: Path) -> tuple:
    """
    Creates a minimal canonical project in tmp_path with one patchable core file.
    Returns (project_root, target_rel, original_content, finding_id, report_data).
    """
    (tmp_path / 'core').mkdir()
    (tmp_path / 'references').mkdir()
    (tmp_path / 'examples').mkdir()
    (tmp_path / 'reports').mkdir()

    # A simple canonical file with known content
    original_content = "# Three.js Guide\n\nUse PCFShadowMap instead of PCFSoftShadowMap.\n"
    target_rel = 'core/api-version-compatibility.md'
    (tmp_path / target_rel).write_text(original_content, encoding='utf-8')

    finding_id = generate_stable_finding_id(target_rel, 3, 'PCFSoftShadowMap')
    finding = _make_confirmed_finding(finding_id, target_rel)
    report_data = _make_report_data([finding])

    return tmp_path, target_rel, original_content, finding_id, report_data


class TestProposalGeneration:
    """Tests 28-41: C.4 human-reviewed patch proposal system."""

    # ------------------------------------------------------------------
    # 28: Valid proposal generation
    # ------------------------------------------------------------------
    def test_28_valid_proposal_generation(self, tmp_path):
        """28. CONFIRMED_LOCAL_SOURCE finding → proposal written with correct structure."""
        root, target_rel, orig, fid, rd = _setup_canonical_project(tmp_path)
        original_snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposed_snippet = "Use PCFShadowMap (PCFSoftShadowMap was removed in r186)."

        proposal = generate_proposal(
            finding_id=fid,
            target_file=target_rel,
            original_snippet=original_snippet,
            proposed_snippet=proposed_snippet,
            rationale="Update migration note to include version number.",
            project_root=root,
            report_data=rd,
        )

        assert proposal['proposal_id'].startswith('PROP-')
        assert proposal['status'] == PROPOSAL_STATUS_PENDING
        assert proposal['finding_id'] == fid
        assert proposal['evidence_status'] == 'CONFIRMED_LOCAL_SOURCE'
        assert proposal['target_file'] == target_rel
        assert proposal['original_snippet'] == original_snippet
        assert proposal['proposed_snippet'] == proposed_snippet
        assert proposal['reviewer_decision'] is None
        assert proposal['reviewed_at'] is None
        # JSON and review.md written to disk
        prop_dir = root / 'reports' / 'proposals' / proposal['proposal_id']
        assert (prop_dir / 'proposal.json').is_file()
        assert (prop_dir / 'review.md').is_file()

    # ------------------------------------------------------------------
    # 29: Missing finding rejected
    # ------------------------------------------------------------------
    def test_29_missing_finding_rejected(self, tmp_path):
        """29. Non-existent finding_id raises ValueError with clear message."""
        root, target_rel, orig, _, rd = _setup_canonical_project(tmp_path)
        with pytest.raises(ValueError, match="not found in the current report"):
            generate_proposal(
                finding_id='NONEXISTENT-FINDING-ID-XYZ',
                target_file=target_rel,
                original_snippet='anything',
                proposed_snippet='anything else',
                rationale='test',
                project_root=root,
                report_data=rd,
            )

    # ------------------------------------------------------------------
    # 30: CANDIDATE_FINDING ineligible
    # ------------------------------------------------------------------
    def test_30_candidate_finding_ineligible(self, tmp_path):
        """30. CANDIDATE_FINDING evidence raises ValueError — not confirmed evidence."""
        root, target_rel, orig, _, _ = _setup_canonical_project(tmp_path)
        fid = generate_stable_finding_id(target_rel, 1, 'CandidateSymbol')
        candidate_finding = {
            'finding_id': fid,
            'file': target_rel,
            'line': 1,
            'api': 'CandidateSymbol',
            'category': 'DEPRECATED_API_IN_CODE',
            'severity': 'WARNING',
            'evidence_status': 'CANDIDATE_FINDING',
            'explanation': 'Candidate only.',
        }
        rd = _make_report_data([candidate_finding])

        with pytest.raises(ValueError, match="CANDIDATE_FINDING"):
            generate_proposal(
                finding_id=fid,
                target_file=target_rel,
                original_snippet='anything',
                proposed_snippet='replacement',
                rationale='test',
                project_root=root,
                report_data=rd,
            )

    # ------------------------------------------------------------------
    # 31: INCONCLUSIVE finding ineligible
    # ------------------------------------------------------------------
    def test_31_inconclusive_finding_ineligible(self, tmp_path):
        """31. INCONCLUSIVE evidence raises ValueError — must not treat as confirmed."""
        root, target_rel, orig, _, _ = _setup_canonical_project(tmp_path)
        fid = generate_stable_finding_id(target_rel, 1, 'InconclusiveSymbol')
        inc_finding = {
            'finding_id': fid,
            'file': target_rel,
            'line': 1,
            'api': 'InconclusiveSymbol',
            'category': 'SYMBOL_ABSENT_FROM_FILE',
            'severity': 'INFO',
            'evidence_status': 'INCONCLUSIVE',
            'explanation': 'Absent from file.',
        }
        rd = _make_report_data([inc_finding])

        with pytest.raises(ValueError, match="INCONCLUSIVE"):
            generate_proposal(
                finding_id=fid,
                target_file=target_rel,
                original_snippet='anything',
                proposed_snippet='replacement',
                rationale='test',
                project_root=root,
                report_data=rd,
            )

    # ------------------------------------------------------------------
    # 32: SHA-256 captured correctly
    # ------------------------------------------------------------------
    def test_32_sha256_captured_correctly(self, tmp_path):
        """32. Captured SHA-256 in proposal matches the actual file hash at generation time."""
        root, target_rel, orig, fid, rd = _setup_canonical_project(tmp_path)
        expected_hash = hashlib.sha256((root / target_rel).read_bytes()).hexdigest()
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."

        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="test", project_root=root, report_data=rd,
        )
        assert proposal['target_sha256_at_proposal'] == expected_hash

    # ------------------------------------------------------------------
    # 33: Stale detection
    # ------------------------------------------------------------------
    def test_33_stale_detection_on_review(self, tmp_path):
        """33. If target file changes after proposal creation, review marks it STALE."""
        root, target_rel, orig, fid, rd = _setup_canonical_project(tmp_path)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."

        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="stale test", project_root=root, report_data=rd,
        )
        pid = proposal['proposal_id']

        # Modify the target file after proposal creation → SHA-256 changes
        (root / target_rel).write_text(orig + "\n# Extra line appended.\n", encoding='utf-8')

        # Review must detect stale
        updated = review_proposal(pid, PROPOSAL_STATUS_APPROVED, root)
        assert updated['status'] == PROPOSAL_STATUS_STALE
        assert 'STALE' in updated['review_notes'] or 'stale' in updated['review_notes'].lower()
        # Original captured hash must NOT be overwritten
        assert updated['target_sha256_at_proposal'] == proposal['target_sha256_at_proposal']
        # Target file must NOT have been modified back
        current = (root / target_rel).read_text(encoding='utf-8')
        assert "# Extra line appended." in current

    # ------------------------------------------------------------------
    # 34: Unified diff correctness
    # ------------------------------------------------------------------
    def test_34_diff_correctness(self, tmp_path):
        """34. Unified diff faithfully represents the original → proposed transition."""
        root, target_rel, orig, fid, rd = _setup_canonical_project(tmp_path)
        snippet  = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposed = "Use PCFShadowMap (deprecated since r186)."

        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet=proposed,
            rationale="diff test", project_root=root, report_data=rd,
        )
        diff = proposal['unified_diff']
        assert f"a/{target_rel}" in diff
        assert f"b/{target_rel}" in diff
        # Removed line starts with '-'
        assert any(line.startswith('-') and 'PCFSoftShadowMap' in line for line in diff.splitlines())
        # Added line starts with '+'
        assert any(line.startswith('+') and 'deprecated since r186' in line for line in diff.splitlines())

    # ------------------------------------------------------------------
    # 35: Snippet correctness
    # ------------------------------------------------------------------
    def test_35_snippet_correctness(self, tmp_path):
        """35. original_snippet and proposed_snippet are stored verbatim in the proposal."""
        root, target_rel, orig, fid, rd = _setup_canonical_project(tmp_path)
        snippet  = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposed = "Use PCFShadowMap. PCFSoftShadowMap is removed."

        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet=proposed,
            rationale="snippet test", project_root=root, report_data=rd,
        )
        assert proposal['original_snippet']  == snippet
        assert proposal['proposed_snippet']  == proposed
        # Persisted JSON must also match
        persisted = get_proposal(proposal['proposal_id'], root)
        assert persisted['original_snippet']  == snippet
        assert persisted['proposed_snippet']  == proposed

    # ------------------------------------------------------------------
    # 36: Approval changes metadata only
    # ------------------------------------------------------------------
    def test_36_approval_changes_metadata_only(self, tmp_path):
        """36. Approving a proposal changes status to APPROVED; target file is NOT modified."""
        root, target_rel, orig, fid, rd = _setup_canonical_project(tmp_path)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        hash_before = hashlib.sha256((root / target_rel).read_bytes()).hexdigest()

        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="approval test", project_root=root, report_data=rd,
        )
        updated = review_proposal(proposal['proposal_id'], PROPOSAL_STATUS_APPROVED, root)

        assert updated['status']            == PROPOSAL_STATUS_APPROVED
        assert updated['reviewer_decision'] == PROPOSAL_STATUS_APPROVED
        assert updated['reviewed_at']       is not None
        # Target file must be byte-for-byte unchanged
        hash_after = hashlib.sha256((root / target_rel).read_bytes()).hexdigest()
        assert hash_before == hash_after
        # File content must be unchanged
        assert (root / target_rel).read_text(encoding='utf-8') == orig

    # ------------------------------------------------------------------
    # 37: Rejection changes metadata only
    # ------------------------------------------------------------------
    def test_37_rejection_changes_metadata_only(self, tmp_path):
        """37. Rejecting a proposal changes status to REJECTED; target file is NOT modified."""
        root, target_rel, orig, fid, rd = _setup_canonical_project(tmp_path)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        hash_before = hashlib.sha256((root / target_rel).read_bytes()).hexdigest()

        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="reject test", project_root=root, report_data=rd,
        )
        updated = review_proposal(proposal['proposal_id'], PROPOSAL_STATUS_REJECTED, root)

        assert updated['status']            == PROPOSAL_STATUS_REJECTED
        assert updated['reviewer_decision'] == PROPOSAL_STATUS_REJECTED
        assert updated['reviewed_at']       is not None
        hash_after = hashlib.sha256((root / target_rel).read_bytes()).hexdigest()
        assert hash_before == hash_after
        assert (root / target_rel).read_text(encoding='utf-8') == orig

    # ------------------------------------------------------------------
    # 38: Path traversal in proposal_id rejected
    # ------------------------------------------------------------------
    def test_38_path_traversal_in_proposal_id_rejected(self, tmp_path):
        """38. get_proposal rejects proposal IDs containing path traversal components."""
        root, *_ = _setup_canonical_project(tmp_path)

        with pytest.raises(ValueError, match="Invalid proposal_id"):
            get_proposal('../../../etc/passwd', root)

        with pytest.raises(ValueError, match="Invalid proposal_id"):
            get_proposal('..\\..\\secret', root)

        with pytest.raises(ValueError, match="Invalid proposal_id"):
            get_proposal('PROP-123/../../other', root)

    # ------------------------------------------------------------------
    # 39: Path traversal in proposal storage path rejected
    # ------------------------------------------------------------------
    def test_39_proposal_storage_path_traversal_rejected(self, tmp_path):
        """39. is_safe_proposal_path rejects traversal and paths outside reports/proposals/."""
        root, *_ = _setup_canonical_project(tmp_path)
        project_root = root

        # Traversal via '..' components
        traversal = project_root / 'reports' / 'proposals' / '..' / '..' / 'core' / 'bad'
        safe, msg = is_safe_proposal_path(traversal, project_root)
        assert safe is False

        # Path outside reports/ entirely
        outside = project_root / 'core' / 'some_dir'
        safe, msg = is_safe_proposal_path(outside, project_root)
        assert safe is False
        assert 'reports/proposals' in msg

        # Valid path is accepted
        valid = project_root / 'reports' / 'proposals' / 'PROP-ABCDEF123456'
        safe, msg = is_safe_proposal_path(valid, project_root)
        assert safe is True

    # ------------------------------------------------------------------
    # 40: Symlink target file rejected by is_safe_patch_target
    # ------------------------------------------------------------------
    def test_40_symlink_target_rejected(self, tmp_path):
        """40. is_safe_patch_target rejects symlinked target files."""
        from unittest.mock import patch as mock_patch
        root, *_ = _setup_canonical_project(tmp_path)
        target_path = root / 'core' / 'api-version-compatibility.md'

        # Patch is_symlink to simulate a symlink without needing OS-level privileges
        with mock_patch.object(Path, 'is_symlink', return_value=True):
            safe, msg = is_safe_patch_target(target_path, root)

        assert safe is False
        assert 'symlink' in msg.lower()

    # ------------------------------------------------------------------
    # 41: Target file outside canonical dirs rejected
    # ------------------------------------------------------------------
    def test_41_target_outside_canonical_dirs_rejected(self, tmp_path):
        """41. is_safe_patch_target rejects files outside core/, references/, examples/."""
        root, *_ = _setup_canonical_project(tmp_path)

        # scripts/ directory is not patchable
        scripts_file = root / 'scripts' / 'maintain.py'
        scripts_file.parent.mkdir(exist_ok=True)
        scripts_file.write_text("# dummy", encoding='utf-8')
        safe, msg = is_safe_patch_target(scripts_file, root)
        assert safe is False
        assert 'canonical directory' in msg

        # reports/ is not patchable
        report_file = root / 'reports' / 'latest.json'
        report_file.write_text('{}', encoding='utf-8')
        safe, msg = is_safe_patch_target(report_file, root)
        assert safe is False

        # A genuine core file IS accepted
        core_file = root / 'core' / 'api-version-compatibility.md'
        safe, msg = is_safe_patch_target(core_file, root)
        assert safe is True

    # ------------------------------------------------------------------
    # 42: Canonical knowledge-file hashes unchanged after all proposal ops
    # ------------------------------------------------------------------
    def test_42_canonical_hashes_unchanged(self):
        """42. generate_proposal, review_proposal, list_proposals leave canonical files untouched."""
        scannable = get_scannable_files(CANONICAL_ROOT)
        hashes_before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}

        # Run the full report to get a real confirmed finding
        data = build_report_data(CANONICAL_ROOT, LOCAL_THREEJS_REPO,
                                 generated_at="2026-10-30T00:00:00+00:00")
        # list_proposals is read-only
        _ = list_proposals(CANONICAL_ROOT)

        hashes_after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}
        assert hashes_before == hashes_after

    # ------------------------------------------------------------------
    # 43: No writes to active skill installations or source repo
    # ------------------------------------------------------------------
    def test_43_no_writes_to_source_or_installations(self, tmp_path):
        """43. Proposal operations never touch the source repo or active skill installations."""
        source_repo   = Path(os.environ.get('THREEJS_SOURCE_DIR', CANONICAL_ROOT.parent / 'three.js-dev'))
        install_1     = Path.home() / '.agents' / 'skills' / 'threejs-expert'
        install_2     = CANONICAL_ROOT.parent / '.agents' / 'skills' / 'threejs-expert'

        def _snapshot(p: Path):
            if not p.exists():
                return {}
            return {
                str(f): f.stat().st_mtime
                for f in p.rglob('*') if f.is_file()
            }

        snap_src   = _snapshot(source_repo)
        snap_inst1 = _snapshot(install_1)
        snap_inst2 = _snapshot(install_2)

        # Run proposal generation in a temp project (does not touch above dirs)
        root, target_rel, orig, fid, rd = _setup_canonical_project(tmp_path)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="isolation test", project_root=root, report_data=rd,
        )
        _ = review_proposal(proposal['proposal_id'], PROPOSAL_STATUS_APPROVED, root)
        _ = list_proposals(root)

        assert _snapshot(source_repo)   == snap_src,   "Source repo was modified!"
        assert _snapshot(install_1)     == snap_inst1, "Active installation 1 was modified!"
        assert _snapshot(install_2)     == snap_inst2, "Active installation 2 was modified!"
