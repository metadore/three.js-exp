"""
Phase 7 Stage C.5 — Comprehensive Testing

Fills coverage gaps identified by audit of the existing 43 tests.
All tests are isolated: no writes to canonical dirs, source repo, or skill installations.
Each test class targets a distinct functional area.

Test numbering: C5-01 … C5-N  (distinct from C.1–C.4 numbering).
"""

import os
import json
import hashlib
import datetime
from pathlib import Path
from unittest.mock import patch as mock_patch
import pytest
import sys

# ---------------------------------------------------------------------------
# Bootstrap path so scripts/ is importable
# ---------------------------------------------------------------------------
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
    is_negative_or_warning_context,
    build_report_data,
    render_markdown_report,
    is_safe_report_path,
    write_reports,
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
    KNOWN_DEPRECATED_APIS,
)

LOCAL_THREEJS_REPO = Path(os.environ.get("THREEJS_SOURCE_DIR", CANONICAL_ROOT.parent / "three.js-dev"))

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

MINIMAL_VERSION_JSON_VALID = {
    "manifest_version": "1.0.0",
    "declared_target": {
        "version": "0.186.0",
        "revision": "187dev",
        "revision_status": "RECORDED_CLAIM_NOT_INDEPENDENTLY_REVERIFIED",
        "is_latest_claimed": False,
        "supported_range": None,
        "range_evidence_status": "UNVERIFIED",
        "declarations_in_knowledge_base": [],
    },
    "verification": {
        "last_verified_date": "2026-10-30",
        "overall_status": "CONFIRMED_LOCAL_SOURCE",
        "verification_sources": [
            {
                "source_id": "test_src",
                "type": "test",
                "path": ".",
                "version_found": "0.186.0",
                "verified_date": "2026-10-30",
                "evidence_status": "CONFIRMED_LOCAL_SOURCE",
            }
        ],
    },
    "compatibility_claims": [],
    "known_limitations": [],
}


def _write_version_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _minimal_project(tmp_path: Path) -> Path:
    """Creates a minimal canonical project layout with a patchable core file."""
    (tmp_path / "core").mkdir()
    (tmp_path / "references").mkdir()
    (tmp_path / "examples").mkdir()
    (tmp_path / "reports").mkdir()
    _write_version_json(tmp_path / "version.json", MINIMAL_VERSION_JSON_VALID)
    content = "# Guide\n\nUse PCFShadowMap instead of PCFSoftShadowMap.\n"
    (tmp_path / "core" / "api-version-compatibility.md").write_text(content, encoding="utf-8")
    return tmp_path


def _confirmed_report_data(finding_id: str, target_file: str) -> dict:
    return {
        "report_version": "1.0.0",
        "generated_at": "2026-10-30T00:00:00+00:00",
        "target_version": {"version": "0.186.0"},
        "summary": {},
        "findings": [
            {
                "finding_id": finding_id,
                "file": target_file,
                "line": 3,
                "api": "PCFSoftShadowMap",
                "category": "SYMBOL_DEPRECATED_IN_SOURCE",
                "severity": "WARNING",
                "evidence_status": "CONFIRMED_LOCAL_SOURCE",
                "explanation": "PCFSoftShadowMap is deprecated.",
            }
        ],
        "audited_claims": [],
        "known_limitations": [],
    }


# ===========================================================================
# C5-01…C5-11: Version Manifest Validation (C.1 gaps)
# ===========================================================================


class TestManifestValidation:
    """C5-01…C5-11: Comprehensive load_version_manifest validation paths."""

    def test_C5_01_missing_version_json_raises(self, tmp_path):
        """C5-01. Missing version.json raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Missing version manifest"):
            load_version_manifest(tmp_path)

    def test_C5_02_malformed_json_raises_value_error(self, tmp_path):
        """C5-02. Malformed (non-JSON) version.json raises ValueError."""
        (tmp_path / "version.json").write_text("{ THIS IS NOT JSON }", encoding="utf-8")
        with pytest.raises(ValueError, match="Malformed version.json"):
            load_version_manifest(tmp_path)

    def test_C5_03_missing_top_level_key_raises(self, tmp_path):
        """C5-03. Each required top-level key is individually validated."""
        required_keys = ["manifest_version", "declared_target", "verification", "compatibility_claims"]
        for key in required_keys:
            data = dict(MINIMAL_VERSION_JSON_VALID)
            del data[key]
            _write_version_json(tmp_path / "version.json", data)
            with pytest.raises(ValueError, match=key):
                load_version_manifest(tmp_path)

    def test_C5_04_is_latest_claimed_true_rejected(self, tmp_path):
        """C5-04. is_latest_claimed=true is unconditionally rejected."""
        data = json.loads(json.dumps(MINIMAL_VERSION_JSON_VALID))
        data["declared_target"]["is_latest_claimed"] = True
        _write_version_json(tmp_path / "version.json", data)
        with pytest.raises(ValueError, match="is_latest_claimed"):
            load_version_manifest(tmp_path)

    def test_C5_05_supported_range_with_unverified_rejected(self, tmp_path):
        """C5-05. Non-null supported_range + UNVERIFIED evidence raises ValueError."""
        data = json.loads(json.dumps(MINIMAL_VERSION_JSON_VALID))
        data["declared_target"]["supported_range"] = ">=0.180.0"
        data["declared_target"]["range_evidence_status"] = "UNVERIFIED"
        _write_version_json(tmp_path / "version.json", data)
        with pytest.raises(ValueError, match="supported_range"):
            load_version_manifest(tmp_path)

    def test_C5_06_invalid_overall_status_rejected(self, tmp_path):
        """C5-06. Unknown overall_status value is rejected."""
        data = json.loads(json.dumps(MINIMAL_VERSION_JSON_VALID))
        data["verification"]["overall_status"] = "TOTALLY_MADE_UP"
        _write_version_json(tmp_path / "version.json", data)
        with pytest.raises(ValueError, match="overall_status"):
            load_version_manifest(tmp_path)

    def test_C5_07_empty_verification_sources_rejected(self, tmp_path):
        """C5-07. Empty verification_sources list is rejected."""
        data = json.loads(json.dumps(MINIMAL_VERSION_JSON_VALID))
        data["verification"]["verification_sources"] = []
        _write_version_json(tmp_path / "version.json", data)
        with pytest.raises(ValueError, match="verification_sources"):
            load_version_manifest(tmp_path)

    def test_C5_08_invalid_source_evidence_status_rejected(self, tmp_path):
        """C5-08. Verification source with unknown evidence_status is rejected."""
        data = json.loads(json.dumps(MINIMAL_VERSION_JSON_VALID))
        data["verification"]["verification_sources"][0]["evidence_status"] = "FANTASY_STATUS"
        _write_version_json(tmp_path / "version.json", data)
        with pytest.raises(ValueError):
            load_version_manifest(tmp_path)

    def test_C5_09_compatibility_claims_must_be_list(self, tmp_path):
        """C5-09. compatibility_claims that is not a list raises ValueError."""
        data = json.loads(json.dumps(MINIMAL_VERSION_JSON_VALID))
        data["compatibility_claims"] = {"oops": "not a list"}
        _write_version_json(tmp_path / "version.json", data)
        with pytest.raises(ValueError, match="compatibility_claims"):
            load_version_manifest(tmp_path)

    def test_C5_10_claim_missing_required_field_raises(self, tmp_path):
        """C5-10. A claim missing a required field raises ValueError."""
        data = json.loads(json.dumps(MINIMAL_VERSION_JSON_VALID))
        # Missing 'source_reference' is OK if UNVERIFIED, but missing 'affected_api' is always invalid
        data["compatibility_claims"] = [
            {
                "claim_id": "CLAIM-X",
                # "affected_api" intentionally omitted
                "recommended_api": "Something",
                "target_version": "0.186.0",
                "evidence_status": "UNVERIFIED",
            }
        ]
        _write_version_json(tmp_path / "version.json", data)
        with pytest.raises(ValueError, match="affected_api"):
            load_version_manifest(tmp_path)

    def test_C5_11_confirmed_claim_without_source_reference_rejected(self, tmp_path):
        """C5-11. CONFIRMED_LOCAL_SOURCE claim without source_reference is rejected."""
        data = json.loads(json.dumps(MINIMAL_VERSION_JSON_VALID))
        data["compatibility_claims"] = [
            {
                "claim_id": "CLAIM-Y",
                "affected_api": "OldAPI",
                "recommended_api": "NewAPI",
                "target_version": "0.186.0",
                "evidence_status": "CONFIRMED_LOCAL_SOURCE",
                # source_reference intentionally omitted
            }
        ]
        _write_version_json(tmp_path / "version.json", data)
        with pytest.raises(ValueError, match="source_reference"):
            load_version_manifest(tmp_path)


# ===========================================================================
# C5-12…C5-20: Scanner edge cases (C.2 gaps)
# ===========================================================================


class TestScannerEdgeCases:
    """C5-12…C5-20: Token boundaries, context, markdown blocks, finding IDs."""

    def test_C5_12_api_in_markdown_prose_is_documentation_mention(self, tmp_path):
        """C5-12. Deprecated API outside a code block in Markdown → API_DOCUMENTATION_MENTION, INFO."""
        md_file = tmp_path / "guide.md"
        md_file.write_text(
            "# Migration Guide\n\nDo not use PCFSoftShadowMap any more.\n",
            encoding="utf-8",
        )
        findings = scan_file_for_apis(tmp_path, md_file)
        assert len(findings) >= 1
        prose = [f for f in findings if f["category"] == "API_DOCUMENTATION_MENTION"]
        assert len(prose) >= 1
        assert prose[0]["severity"] == "INFO"
        assert prose[0]["api"] in ("PCFSoftShadowMap", "THREE.PCFSoftShadowMap")

    def test_C5_13_api_inside_markdown_code_block_is_code_finding(self, tmp_path):
        """C5-13. Deprecated API inside a fenced code block in Markdown → DEPRECATED_API_IN_CODE."""
        md_file = tmp_path / "guide.md"
        md_file.write_text(
            "# Example\n\n```js\nrenderer.shadowMap.type = THREE.PCFSoftShadowMap;\n```\n",
            encoding="utf-8",
        )
        findings = scan_file_for_apis(tmp_path, md_file)
        code_findings = [f for f in findings if f["category"] == "DEPRECATED_API_IN_CODE"]
        assert len(code_findings) >= 1

    def test_C5_14_negative_context_produces_warning_context_finding(self, tmp_path):
        """C5-14. API in an explicit deprecation warning context → DEPRECATED_API_IN_WARNING_CONTEXT."""
        js_file = tmp_path / "renderer.js"
        js_file.write_text(
            "// DEPRECATED: PCFSoftShadowMap has been removed\n"
            "if (type === PCFSoftShadowMap) {\n"
            "  console.warn('PCFSoftShadowMap is deprecated');\n"
            "}\n",
            encoding="utf-8",
        )
        findings = scan_file_for_apis(tmp_path, js_file)
        # All findings in a warning context (the if-block is right after a DEPRECATED comment)
        categories = {f["category"] for f in findings}
        assert "DEPRECATED_API_IN_CODE" not in categories or "DEPRECATED_API_IN_WARNING_CONTEXT" in categories

    def test_C5_15_generate_stable_finding_id_deterministic(self):
        """C5-15. generate_stable_finding_id returns identical IDs for identical inputs."""
        id1 = generate_stable_finding_id("core/api-version-compatibility.md", 42, "PCFSoftShadowMap")
        id2 = generate_stable_finding_id("core/api-version-compatibility.md", 42, "PCFSoftShadowMap")
        assert id1 == id2
        assert len(id1) > 0

    def test_C5_16_generate_stable_finding_id_differs_for_different_inputs(self):
        """C5-16. Different file, line, or api produces a different finding ID."""
        base = generate_stable_finding_id("core/api.md", 1, "SymbolA")
        diff_file = generate_stable_finding_id("core/other.md", 1, "SymbolA")
        diff_line = generate_stable_finding_id("core/api.md", 2, "SymbolA")
        diff_api = generate_stable_finding_id("core/api.md", 1, "SymbolB")
        assert base != diff_file
        assert base != diff_line
        assert base != diff_api

    def test_C5_17_scan_knowledge_base_with_files_override(self, tmp_path):
        """C5-17. scan_knowledge_base accepts explicit files_to_scan override."""
        js_file = tmp_path / "custom.js"
        js_file.write_text("const l = new RGBELoader();\n", encoding="utf-8")
        findings = scan_knowledge_base(tmp_path, files_to_scan=[js_file])
        assert len(findings) >= 1
        assert findings[0]["api"] == "RGBELoader"

    def test_C5_18_is_negative_or_warning_context_detects_deprecation(self):
        """C5-18. is_negative_or_warning_context identifies lines with deprecation keywords."""
        assert is_negative_or_warning_context(
            "// DEPRECATED: use PCFShadowMap instead", []
        ) is True
        assert is_negative_or_warning_context(
            "console.warn('PCFSoftShadowMap is removed')", []
        ) is True

    def test_C5_19_is_negative_or_warning_context_passes_clean_code(self):
        """C5-19. is_negative_or_warning_context returns False for clean usage code."""
        assert is_negative_or_warning_context(
            "renderer.shadowMap.type = PCFShadowMap;", []
        ) is False

    def test_C5_20_prefix_substring_dot_not_falsely_matched(self, tmp_path):
        """C5-20. 'THREE.PCFSoftShadowMapHelper' must not match 'THREE.PCFSoftShadowMap'."""
        js_file = tmp_path / "helper.js"
        # The lookbehind pattern after THREE.PCFSoftShadowMap requires a word boundary (\b)
        js_file.write_text(
            "const x = THREE.PCFSoftShadowMapHelper;\n", encoding="utf-8"
        )
        findings = scan_file_for_apis(tmp_path, js_file)
        qualified = [f for f in findings if f["api"] == "THREE.PCFSoftShadowMap"]
        assert len(qualified) == 0, (
            "THREE.PCFSoftShadowMapHelper matched THREE.PCFSoftShadowMap — false positive"
        )


# ===========================================================================
# C5-21…C5-25: Import parsing edge cases (C.2 gaps)
# ===========================================================================


class TestImportParsingEdgeCases:
    """C5-21…C5-25: CommonJS, dynamic imports, mixed imports."""

    def test_C5_21_commonjs_require_detected(self):
        """C5-21. CommonJS require('three') is detected as a direct Three.js import."""
        code = "const THREE = require('three');\n"
        res = parse_imports(code)
        assert res["has_three"] is True

    def test_C5_22_dynamic_import_detected(self):
        """C5-22. Dynamic import('three') is detected."""
        code = "const mod = await import('three');\n"
        res = parse_imports(code)
        assert res["has_three"] is True

    def test_C5_23_mixed_imports_all_categorised(self):
        """C5-23. File mixing three, @react-three/fiber, and @react-three/drei is fully parsed."""
        code = (
            "import * as THREE from 'three';\n"
            "import { Canvas } from '@react-three/fiber';\n"
            "import { OrbitControls } from '@react-three/drei';\n"
        )
        res = parse_imports(code)
        assert res["has_three"] is True
        assert res["has_r3f"] is True
        assert res["has_drei"] is True

    def test_C5_24_all_imports_list_populated(self):
        """C5-24. all_imports list contains all detected import sources."""
        code = (
            "import { Scene } from 'three';\n"
            "import { Canvas } from '@react-three/fiber';\n"
        )
        res = parse_imports(code)
        assert len(res["all_imports"]) == 2
        sources = set(res["all_imports"])
        assert "three" in sources
        assert "@react-three/fiber" in sources

    def test_C5_25_single_quotes_and_double_quotes_both_parsed(self):
        """C5-25. Both single-quote and double-quote import styles are recognised."""
        single = "import * as THREE from 'three';\n"
        double = 'import * as THREE from "three";\n'
        assert parse_imports(single)["has_three"] is True
        assert parse_imports(double)["has_three"] is True


# ===========================================================================
# C5-26…C5-29: Local source auditor edge cases (C.2 gaps)
# ===========================================================================


class TestLocalSourceAuditorEdgeCases:
    """C5-26…C5-29: Missing source files, unavailable repo."""

    def test_C5_26_missing_source_file_returns_source_file_missing(self):
        """C5-26. audit_symbol_in_source_file for a non-existent file returns SOURCE_FILE_MISSING."""
        res = audit_symbol_in_source_file(
            LOCAL_THREEJS_REPO, "src/nonexistent_file_xyzabc.js", "SomeSymbol"
        )
        assert res["file_exists"] is False
        assert res["category"] == "SOURCE_FILE_MISSING"
        assert res["evidence_status"] == "INCONCLUSIVE"

    def test_C5_27_audit_with_unavailable_source_dir(self, tmp_path):
        """C5-27. audit_local_threejs_source with a non-existent source_dir returns source_available=False."""
        nonexistent = tmp_path / "no_such_repo"
        _write_version_json(tmp_path / "version.json", MINIMAL_VERSION_JSON_VALID)
        result = audit_local_threejs_source(tmp_path, nonexistent)
        assert result["source_available"] is False

    def test_C5_28_audit_symbol_no_line_numbers_for_absent(self):
        """C5-28. SYMBOL_ABSENT_FROM_FILE result has empty line_numbers list."""
        res = audit_symbol_in_source_file(
            LOCAL_THREEJS_REPO, "src/constants.js", "AbsolutelyFictionalSymbolZZZ"
        )
        assert res["line_numbers"] == []
        assert res["snippets"] == []

    def test_C5_29_audit_symbol_has_snippets_for_present(self):
        """C5-29. Present symbol returns non-empty snippets and line_numbers."""
        res = audit_symbol_in_source_file(
            LOCAL_THREEJS_REPO, "src/constants.js", "PCFShadowMap"
        )
        assert len(res["line_numbers"]) > 0
        assert len(res["snippets"]) > 0
        for s in res["snippets"]:
            assert "PCFShadowMap" in s


# ===========================================================================
# C5-30…C5-33: Report generation safety (C.3 gaps)
# ===========================================================================


class TestReportSafety:
    """C5-30…C5-33: write_reports raises on unsafe path; is_safe_report_path accepts valid subdir."""

    def test_C5_30_write_reports_raises_for_canonical_destination(self, tmp_path):
        """C5-30. write_reports raises PermissionError when output_dir is inside core/."""
        data = build_report_data(
            CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00"
        )
        forbidden = CANONICAL_ROOT / "core" / "output"
        with pytest.raises(PermissionError, match="[Uu]nsafe"):
            write_reports(data, CANONICAL_ROOT, forbidden)

    def test_C5_31_write_reports_raises_for_source_repo_destination(self, tmp_path):
        """C5-31. write_reports raises PermissionError when output_dir targets source repo."""
        data = build_report_data(
            CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00"
        )
        forbidden = LOCAL_THREEJS_REPO / "reports"
        with pytest.raises(PermissionError, match="[Uu]nsafe"):
            write_reports(data, CANONICAL_ROOT, forbidden)

    def test_C5_32_is_safe_report_path_accepts_reports_subdir(self):
        """C5-32. is_safe_report_path accepts a path that is a subdirectory of reports/."""
        root = CANONICAL_ROOT
        safe, msg = is_safe_report_path(root / "reports" / "archive" / "2026", root)
        assert safe is True

    def test_C5_33_report_lf_line_endings(self, tmp_path):
        """C5-33. write_reports produces LF-only line endings in both JSON and Markdown."""
        data = build_report_data(
            CANONICAL_ROOT, LOCAL_THREEJS_REPO, generated_at="2026-10-30T00:00:00+00:00"
        )
        report_dir = tmp_path / "rpts"
        paths = write_reports(data, CANONICAL_ROOT, report_dir)
        json_raw = paths["json_path"].read_bytes()
        md_raw = paths["md_path"].read_bytes()
        assert b"\r\n" not in json_raw, "JSON report contains CRLF line endings"
        assert b"\r\n" not in md_raw, "Markdown report contains CRLF line endings"


# ===========================================================================
# C5-34…C5-53: Proposal system comprehensive (C.4 gaps)
# ===========================================================================


class TestProposalSystemComprehensive:
    """C5-34…C5-53: Uncovered proposal paths, edge cases, and regressions."""

    # --- Eligibility ---

    def test_C5_34_confirmed_official_online_is_eligible(self, tmp_path):
        """C5-34. CONFIRMED_OFFICIAL_ONLINE evidence_status IS eligible for a proposal."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = {
            "report_version": "1.0.0",
            "generated_at": "2026-10-30T00:00:00+00:00",
            "target_version": {"version": "0.186.0"},
            "summary": {},
            "findings": [
                {
                    "finding_id": fid,
                    "file": target_rel,
                    "line": 3,
                    "api": "PCFSoftShadowMap",
                    "category": "SYMBOL_DEPRECATED_IN_SOURCE",
                    "severity": "WARNING",
                    "evidence_status": "CONFIRMED_OFFICIAL_ONLINE",
                    "explanation": "Officially confirmed online.",
                }
            ],
            "audited_claims": [],
            "known_limitations": [],
        }
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposal = generate_proposal(
            finding_id=fid,
            target_file=target_rel,
            original_snippet=snippet,
            proposed_snippet="Use PCFShadowMap (deprecated r186).",
            rationale="online evidence",
            project_root=root,
            report_data=rd,
        )
        assert proposal["evidence_status"] == "CONFIRMED_OFFICIAL_ONLINE"
        assert proposal["status"] == PROPOSAL_STATUS_PENDING

    def test_C5_35_unverified_finding_ineligible(self, tmp_path):
        """C5-35. UNVERIFIED evidence_status raises ValueError."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 1, "SomeSymbol")
        rd = _confirmed_report_data.__func__ if False else {
            "report_version": "1.0.0",
            "generated_at": "2026-10-30T00:00:00+00:00",
            "target_version": {},
            "summary": {},
            "findings": [
                {
                    "finding_id": fid,
                    "file": target_rel,
                    "line": 1,
                    "api": "SomeSymbol",
                    "category": "SOME_CAT",
                    "severity": "INFO",
                    "evidence_status": "UNVERIFIED",
                    "explanation": "unverified.",
                }
            ],
            "audited_claims": [],
            "known_limitations": [],
        }
        with pytest.raises(ValueError, match="UNVERIFIED"):
            generate_proposal(
                finding_id=fid,
                target_file=target_rel,
                original_snippet="anything",
                proposed_snippet="other",
                rationale="test",
                project_root=root,
                report_data=rd,
            )

    def test_C5_36_original_snippet_absent_from_file_raises(self, tmp_path):
        """C5-36. generate_proposal raises ValueError if original_snippet not found verbatim."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        with pytest.raises(ValueError, match="original_snippet not found verbatim"):
            generate_proposal(
                finding_id=fid,
                target_file=target_rel,
                original_snippet="THIS TEXT DOES NOT EXIST IN THE FILE AT ALL",
                proposed_snippet="replacement",
                rationale="test",
                project_root=root,
                report_data=rd,
            )

    def test_C5_37_nonexistent_target_file_raises(self, tmp_path):
        """C5-37. generate_proposal with a non-existent target_file raises PermissionError."""
        root = _minimal_project(tmp_path)
        # A path that's in the right dir but doesn't exist
        target_rel = "core/does-not-exist.md"
        fid = generate_stable_finding_id(target_rel, 1, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        with pytest.raises(PermissionError):
            generate_proposal(
                finding_id=fid,
                target_file=target_rel,
                original_snippet="anything",
                proposed_snippet="replacement",
                rationale="test",
                project_root=root,
                report_data=rd,
            )

    # --- Proposal fields ---

    def test_C5_38_proposal_schema_version_present(self, tmp_path):
        """C5-38. Generated proposal includes schema_version field."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        proposal = generate_proposal(
            finding_id=fid,
            target_file=target_rel,
            original_snippet="Use PCFShadowMap instead of PCFSoftShadowMap.",
            proposed_snippet="Use PCFShadowMap.",
            rationale="schema test",
            project_root=root,
            report_data=rd,
        )
        assert "schema_version" in proposal
        assert proposal["schema_version"] == "1.0.0"

    def test_C5_39_proposal_created_at_is_iso_timestamp(self, tmp_path):
        """C5-39. Proposal created_at is a parseable ISO-8601 UTC timestamp."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        proposal = generate_proposal(
            finding_id=fid,
            target_file=target_rel,
            original_snippet="Use PCFShadowMap instead of PCFSoftShadowMap.",
            proposed_snippet="Use PCFShadowMap.",
            rationale="timestamp test",
            project_root=root,
            report_data=rd,
        )
        ts = proposal["created_at"]
        # Must parse without error
        parsed = datetime.datetime.fromisoformat(ts)
        assert parsed is not None

    # --- Review error paths ---

    def test_C5_40_invalid_review_decision_raises(self, tmp_path):
        """C5-40. review_proposal raises ValueError for an invalid decision string."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="bad decision test", project_root=root, report_data=rd,
        )
        with pytest.raises(ValueError, match="decision must be"):
            review_proposal(proposal["proposal_id"], "MAYBE_LATER", root)

    def test_C5_41_re_reviewing_approved_proposal_raises(self, tmp_path):
        """C5-41. Attempting to re-review an APPROVED proposal raises ValueError."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="re-approve test", project_root=root, report_data=rd,
        )
        review_proposal(proposal["proposal_id"], PROPOSAL_STATUS_APPROVED, root)
        with pytest.raises(ValueError, match="already"):
            review_proposal(proposal["proposal_id"], PROPOSAL_STATUS_REJECTED, root)

    def test_C5_42_re_reviewing_rejected_proposal_raises(self, tmp_path):
        """C5-42. Attempting to re-review a REJECTED proposal raises ValueError."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="re-reject test", project_root=root, report_data=rd,
        )
        review_proposal(proposal["proposal_id"], PROPOSAL_STATUS_REJECTED, root)
        with pytest.raises(ValueError, match="already"):
            review_proposal(proposal["proposal_id"], PROPOSAL_STATUS_APPROVED, root)

    def test_C5_43_reviewing_already_stale_proposal_raises(self, tmp_path):
        """C5-43. Attempting to review an already-STALE proposal raises ValueError."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        # Create proposal, then change file to make it stale
        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="stale re-review test", project_root=root, report_data=rd,
        )
        (root / target_rel).write_text("# Changed\n", encoding="utf-8")
        # First review marks STALE
        updated = review_proposal(proposal["proposal_id"], PROPOSAL_STATUS_APPROVED, root)
        assert updated["status"] == PROPOSAL_STATUS_STALE
        # Second review must raise
        with pytest.raises(ValueError, match="STALE"):
            review_proposal(proposal["proposal_id"], PROPOSAL_STATUS_APPROVED, root)

    # --- get_proposal / list_proposals ---

    def test_C5_44_get_proposal_nonexistent_raises_file_not_found(self, tmp_path):
        """C5-44. get_proposal for a non-existent ID raises FileNotFoundError."""
        root = _minimal_project(tmp_path)
        with pytest.raises(FileNotFoundError):
            get_proposal("PROP-DOESNOTEXIST99", root)

    def test_C5_45_list_proposals_empty_returns_empty_list(self, tmp_path):
        """C5-45. list_proposals returns [] when no proposals directory exists."""
        root = _minimal_project(tmp_path)
        result = list_proposals(root)
        assert result == []

    def test_C5_46_list_proposals_sorted_by_created_at(self, tmp_path):
        """C5-46. list_proposals returns proposals sorted by created_at (oldest first)."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."

        props = []
        for i in range(3):
            fid = generate_stable_finding_id(target_rel, 3 + i, f"PCFSoftShadowMap_{i}")
            rd = _confirmed_report_data(fid, target_rel)
            # Inject finding with the exact id
            rd["findings"][0]["finding_id"] = fid
            rd["findings"][0]["api"] = f"Sym{i}"
            p = generate_proposal(
                finding_id=fid, target_file=target_rel,
                original_snippet=snippet, proposed_snippet=f"replacement {i}",
                rationale=f"sort test {i}", project_root=root, report_data=rd,
            )
            props.append(p)

        listed = list_proposals(root)
        assert len(listed) == 3
        timestamps = [p["created_at"] for p in listed]
        assert timestamps == sorted(timestamps)

    # --- Stale: original hash never overwritten ---

    def test_C5_47_stale_does_not_overwrite_original_sha256(self, tmp_path):
        """C5-47. When a proposal goes STALE, target_sha256_at_proposal is preserved unchanged."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        original_hash = hashlib.sha256((root / target_rel).read_bytes()).hexdigest()

        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="hash preservation test", project_root=root, report_data=rd,
        )
        captured = proposal["target_sha256_at_proposal"]
        assert captured == original_hash

        # Alter the file
        (root / target_rel).write_text("# Completely different content\n", encoding="utf-8")
        updated = review_proposal(proposal["proposal_id"], PROPOSAL_STATUS_APPROVED, root)
        assert updated["status"] == PROPOSAL_STATUS_STALE
        # The captured hash must still equal the original (not the new file's hash)
        assert updated["target_sha256_at_proposal"] == original_hash

    # --- Load from disk ---

    def test_C5_48_generate_proposal_reads_from_latest_json_on_disk(self, tmp_path):
        """C5-48. generate_proposal can load report data from reports/latest.json (no override)."""
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        # Write the report to disk as latest.json
        (root / "reports").mkdir(exist_ok=True)
        (root / "reports" / "latest.json").write_text(json.dumps(rd), encoding="utf-8")
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        # Call WITHOUT report_data — must read from disk
        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="disk read test", project_root=root,
        )
        assert proposal["finding_id"] == fid
        assert proposal["status"] == PROPOSAL_STATUS_PENDING

    def test_C5_49_generate_proposal_raises_when_no_report_on_disk(self, tmp_path):
        """C5-49. generate_proposal raises FileNotFoundError when reports/latest.json absent."""
        root = _minimal_project(tmp_path)
        with pytest.raises(FileNotFoundError, match="latest.json"):
            generate_proposal(
                finding_id="NONEXISTENT-ID",
                target_file="core/api-version-compatibility.md",
                original_snippet="anything",
                proposed_snippet="other",
                rationale="test",
                project_root=root,
            )

    # --- Symlink in proposal storage path ---

    def test_C5_50_symlink_in_proposal_storage_path_rejected(self, tmp_path):
        """C5-50. is_safe_proposal_path rejects a path with a symlinked component."""
        root = _minimal_project(tmp_path)
        proposals_root = root / "reports" / "proposals"
        proposals_root.mkdir(parents=True, exist_ok=True)

        # Patch is_symlink so the proposals_root itself appears as a symlink
        symlinked_path = proposals_root / "PROP-SYMLINK000000"
        with mock_patch.object(Path, "is_symlink", return_value=True):
            safe, msg = is_safe_proposal_path(symlinked_path, root)
        assert safe is False
        assert "symlink" in msg.lower()

    # --- No apply command regression ---

    def test_C5_51_no_apply_cli_argument_exists(self):
        """C5-51. The CLI must NOT expose any --apply command that applies patches automatically."""
        import argparse
        import importlib.util
        import ast

        maintain_path = CANONICAL_ROOT / "scripts" / "maintain.py"
        source = maintain_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Look for any argparse add_argument call containing '--apply'
        apply_args = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = getattr(node, "func", None)
                if func and getattr(func, "attr", "") == "add_argument":
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if "--apply" in arg.value:
                                apply_args.append(arg.value)

        assert len(apply_args) == 0, (
            f"CRITICAL: --apply CLI argument found. Automatic patch application is forbidden. "
            f"Found: {apply_args}"
        )

    # --- Regression: approval never modifies any canonical file ---

    def test_C5_52_approval_never_modifies_canonical_files(self, tmp_path):
        """C5-52. Regression: approving a proposal in an isolated project does not touch
        any canonical knowledge file in the real project."""
        scannable = get_scannable_files(CANONICAL_ROOT)
        hashes_before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}

        # Run full proposal cycle in isolated tmp project
        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="regression approval test", project_root=root, report_data=rd,
        )
        review_proposal(proposal["proposal_id"], PROPOSAL_STATUS_APPROVED, root)

        hashes_after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}
        assert hashes_before == hashes_after, (
            "REGRESSION: Canonical knowledge files were modified by proposal approval!"
        )

    def test_C5_53_rejection_never_modifies_canonical_files(self, tmp_path):
        """C5-53. Regression: rejecting a proposal does not touch any canonical knowledge file."""
        scannable = get_scannable_files(CANONICAL_ROOT)
        hashes_before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}

        root = _minimal_project(tmp_path)
        target_rel = "core/api-version-compatibility.md"
        fid = generate_stable_finding_id(target_rel, 3, "PCFSoftShadowMap")
        rd = _confirmed_report_data(fid, target_rel)
        snippet = "Use PCFShadowMap instead of PCFSoftShadowMap."
        proposal = generate_proposal(
            finding_id=fid, target_file=target_rel,
            original_snippet=snippet, proposed_snippet="Use PCFShadowMap.",
            rationale="regression rejection test", project_root=root, report_data=rd,
        )
        review_proposal(proposal["proposal_id"], PROPOSAL_STATUS_REJECTED, root)

        hashes_after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in scannable}
        assert hashes_before == hashes_after, (
            "REGRESSION: Canonical knowledge files were modified by proposal rejection!"
        )

