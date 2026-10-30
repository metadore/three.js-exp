"""
Three.js Expert Knowledge Base Maintenance & Version Audit System

Features:
- Version manifest validation & cross-declaration synchronization check.
- Read-only AST & pattern scanner distinguishing code examples from explanatory prose.
- Local Three.js repository symbol auditor (STRICTLY READ-ONLY).
- Static example validator checking syntax, imports, and known deprecated APIs.
- Deterministic finding generation with stable hashes.
- Comprehensive Markdown & JSON maintenance reporting.
- Review-first patch proposal engine with human-approval gate, stale detection,
  and metadata-only approval (patches are NEVER applied automatically).
"""

import os
import re
import sys
import json
import uuid
import shutil
import hashlib
import difflib
import argparse
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Import canonical file manifests from central registry
try:
    from registry import EXPECTED_CORE, EXPECTED_REFERENCES, EXPECTED_EXAMPLES, ADAPTER_REGISTRY
except ImportError:
    from scripts.registry import EXPECTED_CORE, EXPECTED_REFERENCES, EXPECTED_EXAMPLES, ADAPTER_REGISTRY

# Valid Evidence Statuses
EVIDENCE_STATUSES = {
    'CONFIRMED_LOCAL_SOURCE': 'Confirmed by inspection of local read-only source repository',
    'CONFIRMED_OFFICIAL_ONLINE': 'Confirmed by official online Three.js release notes or documentation',
    'CANDIDATE_FINDING': 'Candidate finding identified by scanner requiring human review',
    'UNVERIFIED': 'Claim or range recorded without primary source verification',
    'INCONCLUSIVE': 'Verification check could not complete (e.g., offline or ambiguous)'
}

# Known Deprecated/Removed API Signatures with Qualified and Token Patterns
KNOWN_DEPRECATED_APIS = {
    'THREE.PCFSoftShadowMap': {
        'status': 'REMOVED_IN_RENDERERS_DEPRECATED_IN_CONSTANTS',
        'target_version': '0.186.0',
        'replacement': 'THREE.PCFShadowMap',
        'severity': 'WARNING',
        'explanation': 'PCFSoftShadowMap is deprecated in constants.js:73 and actively removed in WebGL/WebGPU renderers with a console warning.',
        'patterns': [r'\bTHREE\.PCFSoftShadowMap\b']
    },
    'PCFSoftShadowMap': {
        'status': 'REMOVED_IN_RENDERERS_DEPRECATED_IN_CONSTANTS',
        'target_version': '0.186.0',
        'replacement': 'PCFShadowMap',
        'severity': 'WARNING',
        'explanation': 'PCFSoftShadowMap constant is deprecated; renderers coerce it to PCFShadowMap.',
        'patterns': [r'(?<![A-Za-z0-9_$.])PCFSoftShadowMap\b']
    },
    'RGBELoader': {
        'status': 'DEPRECATED',
        'target_version': '0.180.0',
        'replacement': 'HDRLoader',
        'severity': 'WARNING',
        'explanation': 'RGBELoader was superseded by HDRLoader in r180 and logs a deprecation warning.',
        'patterns': [r'(?<![A-Za-z0-9_$.])RGBELoader\b']
    },
    'THREE.PostProcessing': {
        'status': 'DEPRECATED',
        'target_version': '0.183.0',
        'replacement': 'RenderPipeline',
        'severity': 'WARNING',
        'explanation': 'PostProcessing in WebGPU was renamed to RenderPipeline in r183.',
        'patterns': [r'\bTHREE\.PostProcessing\b']
    },
    'PostProcessing': {
        'status': 'DEPRECATED',
        'target_version': '0.183.0',
        'replacement': 'RenderPipeline',
        'severity': 'WARNING',
        'explanation': 'PostProcessing in WebGPU was renamed to RenderPipeline in r183.',
        'patterns': [r'(?<![A-Za-z0-9_$.])PostProcessing\b']
    },
    'THREE.Geometry': {
        'status': 'REMOVED',
        'target_version': '0.125.0',
        'replacement': 'THREE.BufferGeometry',
        'severity': 'ERROR',
        'explanation': 'THREE.Geometry was completely removed in r125. All geometry must use BufferGeometry.',
        'patterns': [r'\bTHREE\.Geometry\b']
    },
    'THREE.sRGBEncoding': {
        'status': 'REMOVED',
        'target_version': '0.152.0',
        'replacement': 'THREE.SRGBColorSpace',
        'severity': 'ERROR',
        'explanation': 'Encodings were replaced with ColorSpace constants in r152.',
        'patterns': [r'\bTHREE\.sRGBEncoding\b']
    },
    'sRGBEncoding': {
        'status': 'REMOVED',
        'target_version': '0.152.0',
        'replacement': 'THREE.SRGBColorSpace',
        'severity': 'ERROR',
        'explanation': 'Encodings were replaced with ColorSpace constants in r152.',
        'patterns': [r'(?<![A-Za-z0-9_$.])sRGBEncoding\b']
    },
    'outputEncoding': {
        'status': 'REMOVED',
        'target_version': '0.152.0',
        'replacement': 'outputColorSpace',
        'severity': 'ERROR',
        'explanation': 'renderer.outputEncoding was replaced by renderer.outputColorSpace in r152.',
        'patterns': [r'(?<![A-Za-z0-9_$.])outputEncoding\b']
    }
}

IMPORT_RE = re.compile(
    r"""(?:^|\n)\s*(?:"""
    r"""import\s+(?:(?:[\w*\s{},$]+)\s+from\s+)?['"](?P<import_mod>[^'"]+)['"]"""
    r"""|(?:(?:const|let|var)\s+[\w\s{},$]+=\s*)?(?:await\s+)?import\s*\(\s*['"](?P<dyn_mod>[^'"]+)['"]\s*\)"""
    r"""|(?:const|let|var)\s+(?:[\w\s{},$]+)\s*=\s*require\s*\(\s*['"](?P<req_mod>[^'"]+)['"]\s*\)"""
    r""")""",
    re.MULTILINE
)

def parse_imports(text: str) -> Dict[str, Any]:
    """Extracts and categorizes imported modules from code, distinguishing Three, R3F, and Drei."""
    direct_three = []
    r3f = []
    drei = []
    all_mods = []
    
    for m in IMPORT_RE.finditer(text):
        mod = m.group('import_mod') or m.group('dyn_mod') or m.group('req_mod')
        if not mod:
            continue
        all_mods.append(mod)
        if mod == 'three' or mod.startswith('three/'):
            direct_three.append(mod)
        elif mod == '@react-three/fiber':
            r3f.append(mod)
        elif mod == '@react-three/drei':
            drei.append(mod)
            
    return {
        'all_imports': all_mods,
        'direct_three': direct_three,
        'r3f': r3f,
        'drei': drei,
        'has_three': len(direct_three) > 0,
        'has_r3f': len(r3f) > 0,
        'has_drei': len(drei) > 0
    }

def get_project_root() -> Path:
    """Returns canonical project root."""
    return Path(__file__).resolve().parent.parent

def file_sha256(path: Path) -> str:
    """Computes SHA-256 hash of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()

def normalize_text_sha256(text: str) -> str:
    """Computes SHA-256 hash of normalized LF text."""
    normalized = text.strip() + '\n'
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def generate_stable_finding_id(file_rel: str, line_no: int, api_name: str) -> str:
    """Generates a deterministic finding identifier stable across runs."""
    token = f"{file_rel}:{line_no}:{api_name}"
    short_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()[:8]
    clean_api = re.sub(r'[^A-Z0-9]', '', api_name.upper())[:10]
    return f"FINDING-{clean_api}-{short_hash}"

# ==============================================================================
# 1. Manifest Validation & Cross-Declaration Checker
# ==============================================================================

def load_version_manifest(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Loads and validates version.json schema and mandatory constraints."""
    if project_root is None:
        project_root = get_project_root()
    manifest_path = project_root / 'version.json'
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing version manifest: {manifest_path}")
        
    try:
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed version.json: {e}")
        
    # Required top-level fields
    required_keys = ['manifest_version', 'declared_target', 'verification', 'compatibility_claims']
    for k in required_keys:
        if k not in data:
            raise ValueError(f"version.json missing required field: '{k}'")
            
    declared = data.get('declared_target', {})
    if not isinstance(declared, dict):
        raise ValueError("declared_target must be an object")
    if 'version' not in declared or not declared['version']:
        raise ValueError("version.json missing declared_target.version")
    if 'revision' not in declared:
        raise ValueError("version.json missing declared_target.revision")
    if declared.get('is_latest_claimed', False) is True:
        raise ValueError("declared_target.is_latest_claimed cannot be True without confirmed release verification")
    if declared.get('supported_range') is not None and declared.get('range_evidence_status') == 'UNVERIFIED':
        raise ValueError("supported_range cannot be declared with UNVERIFIED range_evidence_status")

    verification = data.get('verification', {})
    if not isinstance(verification, dict):
        raise ValueError("verification must be an object")
    overall_status = verification.get('overall_status')
    if overall_status not in EVIDENCE_STATUSES:
        raise ValueError(f"Invalid overall_status: '{overall_status}'. Valid: {list(EVIDENCE_STATUSES.keys())}")
    sources = verification.get('verification_sources', [])
    if not isinstance(sources, list) or len(sources) == 0:
        raise ValueError("verification.verification_sources must be a non-empty list")
    for s in sources:
        if not isinstance(s, dict) or 'source_id' not in s or 'evidence_status' not in s:
            raise ValueError("Each verification source must contain 'source_id' and 'evidence_status'")
        if s['evidence_status'] not in EVIDENCE_STATUSES:
            raise ValueError(f"Invalid verification source status: '{s['evidence_status']}'")

    claims = data.get('compatibility_claims', [])
    if not isinstance(claims, list):
        raise ValueError("compatibility_claims must be a list")
    for c in claims:
        if not isinstance(c, dict):
            raise ValueError("Each claim must be an object")
        for req in ['claim_id', 'affected_api', 'recommended_api', 'target_version', 'evidence_status']:
            if req not in c or not c[req]:
                raise ValueError(f"Claim missing required field '{req}': {c}")
        if c['evidence_status'] not in EVIDENCE_STATUSES:
            raise ValueError(f"Claim {c.get('claim_id')} has invalid evidence_status '{c['evidence_status']}'")
        if c['evidence_status'] == 'CONFIRMED_LOCAL_SOURCE' and not c.get('source_reference'):
            raise ValueError(f"Claim {c.get('claim_id')} has status CONFIRMED_LOCAL_SOURCE but lacks source_reference")
            
    return data

def check_version_declarations(project_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Cross-checks version.json against declarations in README, core, references, and adapters."""
    if project_root is None:
        project_root = get_project_root()
    manifest = load_version_manifest(project_root)
    declared_version = manifest['declared_target']['version']
    declared_revision = manifest['declared_target'].get('revision', '')
    
    findings = []
    
    # Files to check
    files_to_check = [
        project_root / 'README.md',
        project_root / 'core' / 'api-version-compatibility.md',
        project_root / 'references' / 'framework-vanilla.md',
        project_root / 'adapters' / 'antigravity' / 'SKILL.md',
        project_root / 'adapters' / 'claude-code' / 'CLAUDE.md',
        project_root / 'adapters' / 'copilot' / 'copilot-instructions.md',
        project_root / 'adapters' / 'windsurf' / 'threejs-expert.md'
    ]
    
    version_regex = re.compile(r'0\.\d{3}\.\d|r\d{3}|rev\s*\d{3}dev', re.IGNORECASE)
    
    for fp in files_to_check:
        if not fp.is_file():
            continue
        rel_path = str(fp.relative_to(project_root)).replace('\\', '/')
        lines = fp.read_text(encoding='utf-8').splitlines()
        
        has_declared_version = False
        for i, line in enumerate(lines, 1):
            if declared_version in line:
                has_declared_version = True
            # Check for version pattern mentions
            for match in version_regex.finditer(line):
                v_str = match.group(0)
                # If a full semver is mentioned and differs from declared version
                if re.match(r'0\.\d{3}\.\d', v_str) and v_str != declared_version:
                    # In api-version-compatibility.md, historical shifts are expected
                    if 'api-version-compatibility.md' not in rel_path:
                        finding_id = generate_stable_finding_id(rel_path, i, v_str)
                        findings.append({
                            'finding_id': finding_id,
                            'file': rel_path,
                            'line': i,
                            'api': v_str,
                            'category': 'VERSION_DISCREPANCY',
                            'severity': 'INFO',
                            'evidence_status': 'CANDIDATE_FINDING',
                            'snippet': line.strip(),
                            'explanation': f"File mentions Three.js version '{v_str}' while declared target is '{declared_version}'.",
                            'suggested_action': 'Verify if this is an intentional historical reference or an outdated target declaration.'
                        })
                        
        if not has_declared_version and 'api-version-compatibility.md' not in rel_path:
            findings.append({
                'finding_id': generate_stable_finding_id(rel_path, 1, 'TARGET_VERSION_MISSING'),
                'file': rel_path,
                'line': 1,
                'api': declared_version,
                'category': 'VERSION_DISCREPANCY',
                'severity': 'WARNING',
                'evidence_status': 'CANDIDATE_FINDING',
                'snippet': f"{rel_path}: Line 1",
                'explanation': f"File does not declare target version '{declared_version}'.",
                'suggested_action': f"Add explicit target version reference to '{declared_version}'."
            })
            
    return findings

# ==============================================================================
# 2. Read-Only Knowledge & Code Scanner
# ==============================================================================

def is_negative_or_warning_context(line: str, surrounding_lines: List[str]) -> bool:
    """Checks whether an API mention occurs in a deprecation warning, anti-pattern, or historical context."""
    negative_keywords = [
        'deprecated', 'deprecat', 'removed', 'obsolete', 'do not use', 'never use',
        'anti-pattern', 'superseded', 'replaced by', 'instead of', 'warning',
        'historical', 'evolution', 'deleted', 'dropped', 'legacy'
    ]
    combined_context = (line + ' ' + ' '.join(surrounding_lines)).lower()
    return any(kw in combined_context for kw in negative_keywords)

def scan_file_for_apis(project_root: Path, file_path: Path) -> List[Dict[str, Any]]:
    """Scans a single canonical file for deprecated/removed APIs, separating code from prose and avoiding substring false positives."""
    rel_path = str(file_path.relative_to(project_root)).replace('\\', '/')
    try:
        lines = file_path.read_text(encoding='utf-8').splitlines()
    except Exception as e:
        return [{
            'finding_id': generate_stable_finding_id(rel_path, 0, 'UNREADABLE_FILE'),
            'file': rel_path,
            'line': 0,
            'api': 'N/A',
            'category': 'UNREADABLE_FILE',
            'severity': 'ERROR',
            'evidence_status': 'INCONCLUSIVE',
            'is_code': False,
            'has_warning_context': False,
            'snippet': '',
            'replacement': None,
            'explanation': f"Could not read file: {e}",
            'suggested_action': "Verify file encoding and permissions."
        }]

    findings = []
    is_markdown = file_path.suffix.lower() == '.md'
    in_code_block = False

    # Pre-compile patterns: qualified patterns first, then longest symbol name first
    compiled_patterns = []
    for api, meta in KNOWN_DEPRECATED_APIS.items():
        for pat in meta.get('patterns', [re.escape(api)]):
            compiled_patterns.append({
                'api': api,
                'meta': meta,
                'regex': re.compile(pat),
                'is_qualified': '.' in api
            })
    compiled_patterns.sort(key=lambda x: (not x['is_qualified'], -len(x['api'])))

    for i, line in enumerate(lines, 1):
        if is_markdown:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue

        # Context window (3 lines before and 2 after)
        surrounding = lines[max(0, i-4):i-1] + lines[i:min(len(lines), i+3)]
        matched_spans = []

        for p in compiled_patterns:
            api = p['api']
            meta = p['meta']
            regex = p['regex']

            for m in regex.finditer(line):
                span = m.span()
                # Skip if this span overlaps an already matched higher-priority span
                if any(s[0] <= span[0] < s[1] or s[0] < span[1] <= s[1] for s in matched_spans):
                    continue

                matched_spans.append(span)
                is_neg_context = is_negative_or_warning_context(line, surrounding)
                is_actual_code = (not is_markdown) or in_code_block

                if is_actual_code:
                    if is_neg_context:
                        sev = 'INFO'
                        cat = 'DEPRECATED_API_IN_WARNING_CONTEXT'
                    else:
                        sev = meta['severity']
                        cat = 'DEPRECATED_API_IN_CODE'
                else:
                    sev = 'INFO'
                    cat = 'API_DOCUMENTATION_MENTION'

                finding_id = generate_stable_finding_id(rel_path, i, api)
                findings.append({
                    'finding_id': finding_id,
                    'file': rel_path,
                    'line': i,
                    'api': api,
                    'category': cat,
                    'severity': sev,
                    'is_code': is_actual_code,
                    'has_warning_context': is_neg_context,
                    'evidence_status': 'CANDIDATE_FINDING',
                    'snippet': line.strip(),
                    'replacement': meta.get('replacement'),
                    'explanation': meta['explanation'],
                    'suggested_action': f"Verify usage. Recommended replacement: {meta.get('replacement')}."
                })

    return findings

def get_scannable_files(project_root: Optional[Path] = None) -> List[Path]:
    """Returns canonical knowledge files and adapter documentation files, strictly excluding reports, backups, and caches."""
    if project_root is None:
        project_root = get_project_root()
    files = []
    for fname in sorted(EXPECTED_CORE):
        p = project_root / 'core' / fname
        if p.is_file():
            files.append(p)
    for fname in sorted(EXPECTED_REFERENCES):
        p = project_root / 'references' / fname
        if p.is_file():
            files.append(p)
    for fname in sorted(EXPECTED_EXAMPLES):
        p = project_root / 'examples' / fname
        if p.is_file():
            files.append(p)
    readme = project_root / 'README.md'
    if readme.is_file():
        files.append(readme)
    adapter_paths = [
        project_root / 'adapters' / 'COMPATIBILITY.md',
        project_root / 'adapters' / 'antigravity' / 'SKILL.md',
        project_root / 'adapters' / 'claude-code' / 'CLAUDE.md',
        project_root / 'adapters' / 'claude-code' / 'skills' / 'threejs-expert' / 'SKILL.md',
        project_root / 'adapters' / 'copilot' / 'copilot-instructions.md',
        project_root / 'adapters' / 'cursor' / 'threejs-expert.mdc',
        project_root / 'adapters' / 'windsurf' / 'threejs-expert.md'
    ]
    for ap in adapter_paths:
        if ap.is_file():
            files.append(ap)
    return files

def scan_knowledge_base(
    project_root: Optional[Path] = None,
    files_to_scan: Optional[List[Path]] = None
) -> List[Dict[str, Any]]:
    """Scans canonical knowledge files and examples (strictly read-only) with deterministic ordering."""
    if project_root is None:
        project_root = get_project_root()

    all_findings = []
    if files_to_scan is None:
        # Default: scan canonical 4 core + 10 references + 10 examples
        targets = []
        for fname in sorted(EXPECTED_CORE):
            fp = project_root / 'core' / fname
            if fp.is_file():
                targets.append(fp)
        for fname in sorted(EXPECTED_REFERENCES):
            fp = project_root / 'references' / fname
            if fp.is_file():
                targets.append(fp)
        for fname in sorted(EXPECTED_EXAMPLES):
            fp = project_root / 'examples' / fname
            if fp.is_file():
                targets.append(fp)
    else:
        targets = files_to_scan

    for fp in targets:
        all_findings.extend(scan_file_for_apis(project_root, fp))

    # Deterministic sort by file path, line number, API name, and category
    all_findings.sort(key=lambda x: (x['file'], x.get('line', 0), x['api'], x.get('category', '')))
    return all_findings

# ==============================================================================
# 3. Local-Source Auditor (Read-Only)
# ==============================================================================

def is_symbol_deprecated_at_occurrence(clean_symbol: str, line_no: int, lines: List[str]) -> Tuple[bool, str]:
    """
    Determines if an occurrence of clean_symbol at line_no represents a deprecation
    of clean_symbol itself, rather than a mention as a replacement.
    """
    current_line = lines[line_no - 1]

    # 1. Check if the line itself is inside an active removal/deprecation warning about this symbol
    warn_match = re.search(r'(?:warn|console\.warn)\s*\(\s*[\'"].*?[\'"]', current_line, re.IGNORECASE)
    if warn_match:
        warn_text = warn_match.group(0)
        if re.search(rf'\b{clean_symbol}\b.*?(?:deprecated|removed|superseded)', warn_text, re.IGNORECASE):
            return True, f"Removal/deprecation warning on symbol: {current_line.strip()}"

    # 2. Check if this line is a declaration/definition of clean_symbol
    is_decl = bool(re.search(
        rf'(?:export\s+)?(?:const|class|function|let|var|get|set)\s+\b{clean_symbol}\b'
        rf'|^\s*class\s+\b{clean_symbol}\b'
        rf'|\bexport\s*\{{[^}}]*\b{clean_symbol}\b[^}}]*\}}',
        current_line
    ))

    if is_decl:
        # Check comment block immediately preceding declaration (up to 12 lines back)
        preceding_lines = []
        for k in range(line_no - 2, max(-1, line_no - 14), -1):
            l = lines[k].strip()
            if not l:
                if preceding_lines:
                    break
                continue
            if l.startswith('*') or l.startswith('/*') or l.startswith('//') or l.endswith('*/'):
                preceding_lines.append(l)
            else:
                break

        comment_block = '\n'.join(reversed(preceding_lines))
        if '@deprecated' in comment_block:
            return True, f"Preceding @deprecated docstring on declaration of {clean_symbol}"

        # 3. Check for immediate subsequent warning in constructor/method body
        body_window = '\n'.join(lines[line_no:min(len(lines), line_no + 10)])
        if re.search(rf'(?:warn|console\.warn)\(.*?\b{clean_symbol}\b.*?(?:deprecated|removed)', body_window, re.IGNORECASE):
            return True, f"Constructor warning in body for {clean_symbol}"

    # 4. Check if the block is an interception branch deprecating the symbol
    surrounding_window = '\n'.join(lines[max(0, line_no - 2):min(len(lines), line_no + 6)])
    if re.search(rf'if\s*\([^)]*\b{clean_symbol}\b[^)]*\)\s*\{{[^}}]*?(?:warn|console\.warn)\(.*?\b{clean_symbol}\b.*?(?:deprecated|removed)', surrounding_window, re.IGNORECASE):
        return True, f"Interception block deprecating {clean_symbol}: {current_line.strip()}"

    return False, ""

def audit_symbol_in_source_file(
    source_dir: Path,
    rel_path: str,
    symbol: str,
    expected_line: Optional[int] = None
) -> Dict[str, Any]:
    """Audits a single symbol in a specific source file strictly read-only."""
    clean_symbol = symbol.replace('THREE.', '').strip()
    target_file = source_dir / rel_path

    result = {
        'symbol': symbol,
        'clean_symbol': clean_symbol,
        'source_file': rel_path,
        'line': expected_line,
        'expected_line': expected_line,
        'file_exists': False,
        'exists_in_file': False,
        'is_deprecated': False,
        'line_numbers': [],
        'evidence_status': 'INCONCLUSIVE',
        'category': 'UNKNOWN',
        'snippets': [],
        'explanation': '',
        'source_reference': f"{rel_path}" + (f":{expected_line}" if expected_line else "")
    }

    if not target_file.is_file():
        result['category'] = 'SOURCE_FILE_MISSING'
        result['explanation'] = f"Referenced source file missing: {rel_path}"
        result['evidence_status'] = 'INCONCLUSIVE'
        return result

    result['file_exists'] = True

    try:
        content = target_file.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        result['category'] = 'SOURCE_FILE_UNREADABLE'
        result['explanation'] = f"Could not read source file {rel_path}: {e}"
        result['evidence_status'] = 'INCONCLUSIVE'
        return result

    lines = content.splitlines()
    pattern = re.compile(r'(?<![A-Za-z0-9_$])' + re.escape(clean_symbol) + r'(?![A-Za-z0-9_$])')

    occurrences = []
    for idx, l in enumerate(lines, 1):
        if pattern.search(l):
            occurrences.append((idx, l))

    if not occurrences:
        result['exists_in_file'] = False
        result['category'] = 'SYMBOL_ABSENT_FROM_FILE'
        result['evidence_status'] = 'INCONCLUSIVE'
        result['explanation'] = (
            f"Symbol '{clean_symbol}' not found in {rel_path}. "
            f"Absence from this single file does not establish removal across the entire Three.js library."
        )
        return result

    result['exists_in_file'] = True
    result['line_numbers'] = [occ[0] for occ in occurrences]

    deprecations_found = []
    for line_no, l in occurrences:
        is_dep, reason = is_symbol_deprecated_at_occurrence(clean_symbol, line_no, lines)
        if is_dep:
            deprecations_found.append((line_no, l.strip(), reason))

    if deprecations_found:
        result['is_deprecated'] = True
        result['category'] = 'SYMBOL_DEPRECATED_IN_SOURCE'
        result['evidence_status'] = 'CONFIRMED_LOCAL_SOURCE'
        first_line = deprecations_found[0][0]
        result['line'] = first_line
        result['snippets'] = [f"Line {ln}: {snip} ({rsn})" for ln, snip, rsn in deprecations_found[:3]]
        result['explanation'] = (
            f"Symbol '{clean_symbol}' found at line {first_line} in {rel_path} with confirmed deprecation evidence."
        )
        result['source_reference'] = f"{rel_path}:{first_line}"
    else:
        result['is_deprecated'] = False
        result['category'] = 'SYMBOL_ACTIVE_IN_SOURCE'
        result['evidence_status'] = 'CONFIRMED_LOCAL_SOURCE'
        first_line = occurrences[0][0]
        result['line'] = first_line
        result['snippets'] = [f"Line {ln}: {snip}" for ln, snip in occurrences[:3]]
        result['explanation'] = (
            f"Symbol '{clean_symbol}' is actively present in {rel_path}:{first_line} without deprecation markers."
        )
        result['source_reference'] = f"{rel_path}:{first_line}"

    return result

def audit_local_threejs_source(
    project_root: Optional[Path] = None,
    source_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Audits compatibility claims against local read-only Three.js source repository with multi-symbol independent verification."""
    if project_root is None:
        project_root = get_project_root()
    manifest = load_version_manifest(project_root)

    if source_dir is None:
        candidate_paths = []
        env_src = os.environ.get('THREEJS_SOURCE_DIR')
        if env_src:
            candidate_paths.append(Path(env_src))
        candidate_paths.append(project_root.parent / 'three.js-dev')
        source_dir = next((p for p in candidate_paths if p.is_dir()), None)

    audit_results = {
        'source_available': False,
        'source_path': str(source_dir) if source_dir else None,
        'source_version': None,
        'audited_claims': [],
        'errors': []
    }

    if not source_dir or not source_dir.is_dir():
        audit_results['errors'].append("Local Three.js source repository not found or not a directory.")
        return audit_results

    audit_results['source_available'] = True

    # Read package.json strictly read-only
    pkg_json = source_dir / 'package.json'
    if pkg_json.is_file():
        try:
            pkg_data = json.loads(pkg_json.read_text(encoding='utf-8'))
            audit_results['source_version'] = pkg_data.get('version')
        except Exception as e:
            audit_results['errors'].append(f"Could not parse source package.json: {e}")

    # Audit each claim against source files
    for claim in manifest.get('compatibility_claims', []):
        claim_id = claim['claim_id']
        affected_api = claim['affected_api']
        recommended_api = claim.get('recommended_api', '')
        sources_ref = claim.get('source_reference', '')

        claim_audit = {
            'claim_id': claim_id,
            'affected_api': affected_api,
            'recommended_api': recommended_api,
            'source_reference': sources_ref,
            'verified_in_source': False,
            'evidence_status': 'UNVERIFIED',
            'symbol_audits': [],
            'details': []
        }

        ref_tokens = [t.strip() for t in sources_ref.split(';') if t.strip()]
        has_deprecated_evidence = False
        has_replacement_evidence = False

        for ref in ref_tokens:
            clean_rel = ref.split(':')[0].replace('three.js-dev/', '').strip()
            exp_line = int(ref.split(':')[1]) if ':' in ref else None

            # Audit affected API
            aff_audit = audit_symbol_in_source_file(source_dir, clean_rel, affected_api, exp_line)
            claim_audit['symbol_audits'].append(aff_audit)

            # Audit recommended API independently
            rec_audit = audit_symbol_in_source_file(source_dir, clean_rel, recommended_api, exp_line)
            claim_audit['symbol_audits'].append(rec_audit)

            if aff_audit['is_deprecated']:
                has_deprecated_evidence = True
                claim_audit['details'].append(
                    f"Affected symbol '{affected_api}' is deprecated in {clean_rel} (evidence: {aff_audit['snippets']})"
                )
            elif aff_audit['category'] == 'SYMBOL_ABSENT_FROM_FILE':
                claim_audit['details'].append(
                    f"Affected symbol '{affected_api}' is absent from {clean_rel}"
                )

            if rec_audit['exists_in_file'] and not rec_audit['is_deprecated']:
                has_replacement_evidence = True
                claim_audit['details'].append(
                    f"Recommended replacement '{recommended_api}' is actively present in {clean_rel}"
                )

        # Classify overall claim evidence status based on explicit evidence
        if has_deprecated_evidence:
            claim_audit['verified_in_source'] = True
            claim_audit['evidence_status'] = 'CONFIRMED_LOCAL_SOURCE'
        elif has_replacement_evidence and any(a['category'] == 'SYMBOL_ABSENT_FROM_FILE' for a in claim_audit['symbol_audits'] if a['symbol'] == affected_api):
            claim_audit['verified_in_source'] = True
            claim_audit['evidence_status'] = 'CONFIRMED_LOCAL_SOURCE'
        elif any(a['evidence_status'] == 'INCONCLUSIVE' for a in claim_audit['symbol_audits']):
            claim_audit['verified_in_source'] = False
            claim_audit['evidence_status'] = 'INCONCLUSIVE'
        else:
            claim_audit['verified_in_source'] = False
            claim_audit['evidence_status'] = 'UNVERIFIED'

        audit_results['audited_claims'].append(claim_audit)

    return audit_results

# ==============================================================================
# 4. Static Example Validator
# ==============================================================================

def validate_examples(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Validates example files for syntax, import standards, and active deprecated APIs."""
    if project_root is None:
        project_root = get_project_root()

    results = {
        'total_examples': len(EXPECTED_EXAMPLES),
        'passed': 0,
        'failed': 0,
        'details': []
    }

    for fname in EXPECTED_EXAMPLES:
        fp = project_root / 'examples' / fname
        rel_path = f"examples/{fname}"
        ex_res = {
            'file': rel_path,
            'exists': fp.is_file(),
            'valid_encoding': False,
            'no_deprecated_code': True,
            'import_standard_valid': False,
            'issues': []
        }

        if not fp.is_file():
            ex_res['issues'].append("File missing on disk.")
            results['failed'] += 1
            results['details'].append(ex_res)
            continue

        # Encoding check
        try:
            raw = fp.read_bytes()
            if b'\r\n' in raw:
                ex_res['issues'].append("CRLF line endings detected.")
            text = raw.decode('utf-8')
            ex_res['valid_encoding'] = True
        except UnicodeDecodeError:
            ex_res['issues'].append("Invalid UTF-8 encoding.")
            text = ""

        # Import standard check
        imp = parse_imports(text)
        if 'r3f' in fname.lower():
            if imp['has_r3f']:
                ex_res['import_standard_valid'] = True
            else:
                ex_res['issues'].append("R3F example does not import from '@react-three/fiber'.")
        else:
            if imp['has_three']:
                ex_res['import_standard_valid'] = True
            elif fname.endswith(('.js', '.jsx', '.tsx')) and not text.strip().startswith('//'):
                ex_res['issues'].append("Example does not import from 'three'.")

        # Check for active deprecated API calls using token patterns
        lines = text.splitlines()
        for line_no, line in enumerate(lines, 1):
            for api, meta in KNOWN_DEPRECATED_APIS.items():
                for pat in meta.get('patterns', []):
                    if re.search(pat, line):
                        surrounding = lines[max(0, line_no-3):line_no-1] + lines[line_no:min(len(lines), line_no+2)]
                        if not is_negative_or_warning_context(line, surrounding):
                            ex_res['no_deprecated_code'] = False
                            ex_res['issues'].append(f"Line {line_no}: Active usage of deprecated/removed API '{api}'.")

        if not ex_res['issues']:
            results['passed'] += 1
        else:
            results['failed'] += 1

        results['details'].append(ex_res)

    return results

# ==============================================================================
# 5. Deterministic Findings & Report Generation
# ==============================================================================

def is_safe_report_path(target_path: Path, project_root: Path) -> Tuple[bool, str]:
    """Safety guard: prevents writing reports inside canonical knowledge or adapter folders."""
    resolved_root = project_root.resolve()
    resolved_target = target_path.resolve()

    # Reject filesystem root
    if len(resolved_target.parts) <= 1:
        return False, "Destination cannot be filesystem root."

    # Check Three.js original source repository
    target_str = str(resolved_target).lower().replace('/', '\\')
    if "\\three.js-dev\\three.js-dev" in target_str or target_str.endswith("\\three.js-dev\\three.js-dev"):
        return False, "FORBIDDEN: Cannot target original Three.js library source repository."

    # Forbidden subdirectories inside canonical project
    forbidden_subdirs = ['core', 'references', 'examples', 'adapters']
    for sub in forbidden_subdirs:
        forbidden_path = (resolved_root / sub).resolve()
        try:
            resolved_target.relative_to(forbidden_path)
            return False, f"FORBIDDEN: Report output cannot be placed inside canonical directory '{sub}/'."
        except ValueError:
            pass

    return True, "Report path is safe."

def build_report_data(
    project_root: Optional[Path] = None,
    source_dir: Optional[Path] = None,
    generated_at: Optional[str] = None
) -> Dict[str, Any]:
    """Collects and normalizes findings from manifest, scanner, validator, and auditor into a deterministic structure."""
    if project_root is None:
        project_root = get_project_root()
    if generated_at is None:
        generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    manifest = load_version_manifest(project_root)
    declared_target = manifest.get('declared_target', {})

    # 1. Run checks
    version_disc = check_version_declarations(project_root)
    scan_findings = scan_knowledge_base(project_root)
    example_results = validate_examples(project_root)
    source_audit = audit_local_threejs_source(project_root, source_dir)

    all_findings = []

    # Candidate scanner findings
    for f in scan_findings:
        all_findings.append({
            'finding_id': f['finding_id'],
            'file': f['file'],
            'line': f.get('line'),
            'api': f['api'],
            'category': f['category'],
            'severity': f['severity'],
            'evidence_status': f['evidence_status'],
            'explanation': f['explanation'],
            'source_reference': f.get('file', ''),
            'suggested_action': f.get('suggested_action', '')
        })

    # Version declaration discrepancies
    for d in version_disc:
        all_findings.append({
            'finding_id': d['finding_id'],
            'file': d['file'],
            'line': d.get('line'),
            'api': d['api'],
            'category': d['category'],
            'severity': d['severity'],
            'evidence_status': d['evidence_status'],
            'explanation': d['explanation'],
            'source_reference': d.get('file', ''),
            'suggested_action': d.get('suggested_action', '')
        })

    # Example validation failures (if any)
    for ex in example_results.get('details', []):
        if ex.get('issues'):
            fid = generate_stable_finding_id(ex['file'], 0, 'EXAMPLE_FAIL')
            all_findings.append({
                'finding_id': fid,
                'file': ex['file'],
                'line': None,
                'api': 'EXAMPLE_VALIDATION',
                'category': 'EXAMPLE_VALIDATION_FAILURE',
                'severity': 'ERROR',
                'evidence_status': 'CONFIRMED_LOCAL_SOURCE',
                'explanation': f"Example validation failed: {'; '.join(ex['issues'])}",
                'source_reference': ex['file'],
                'suggested_action': 'Fix example syntax, imports, or remove deprecated API usages.'
            })

    # Source audit findings
    for claim in source_audit.get('audited_claims', []):
        for sym_audit in claim.get('symbol_audits', []):
            if sym_audit['category'] in ('SYMBOL_DEPRECATED_IN_SOURCE', 'SYMBOL_ABSENT_FROM_FILE', 'SOURCE_FILE_MISSING'):
                fid = generate_stable_finding_id(sym_audit['source_file'], sym_audit.get('line') or 0, sym_audit['symbol'])
                sev = 'WARNING' if sym_audit['category'] == 'SYMBOL_DEPRECATED_IN_SOURCE' else 'INFO'
                all_findings.append({
                    'finding_id': fid,
                    'file': sym_audit['source_file'],
                    'line': sym_audit.get('line'),
                    'api': sym_audit['symbol'],
                    'category': sym_audit['category'],
                    'severity': sev,
                    'evidence_status': sym_audit['evidence_status'],
                    'explanation': sym_audit['explanation'],
                    'source_reference': sym_audit.get('source_reference', ''),
                    'suggested_action': 'Review local source definition.'
                })

    # Deterministic deduplication and sorting by file, line (or 0), api, category
    seen = set()
    unique_findings = []
    for f in all_findings:
        key = (f['file'], f.get('line') or 0, f['api'], f['category'])
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    unique_findings.sort(key=lambda x: (x['file'], x.get('line') or 0, x['api'], x['category']))

    # Aggregations
    by_severity = {'ERROR': 0, 'WARNING': 0, 'INFO': 0}
    by_evidence = {
        'CONFIRMED_LOCAL_SOURCE': 0,
        'CONFIRMED_OFFICIAL_ONLINE': 0,
        'CANDIDATE_FINDING': 0,
        'INCONCLUSIVE': 0,
        'UNVERIFIED': 0
    }
    by_category = {}

    for f in unique_findings:
        sev = f['severity']
        by_severity[sev] = by_severity.get(sev, 0) + 1
        ev = f['evidence_status']
        by_evidence[ev] = by_evidence.get(ev, 0) + 1
        cat = f['category']
        by_category[cat] = by_category.get(cat, 0) + 1

    report = {
        'report_version': '1.0.0',
        'generated_at': generated_at,
        'target_version': {
            'version': declared_target.get('version'),
            'revision': declared_target.get('revision'),
            'revision_status': declared_target.get('revision_status'),
            'is_latest_claimed': declared_target.get('is_latest_claimed', False),
            'supported_range': declared_target.get('supported_range'),
            'range_evidence_status': declared_target.get('range_evidence_status')
        },
        'summary': {
            'total_findings': len(unique_findings),
            'by_severity': by_severity,
            'by_evidence_status': by_evidence,
            'by_category': by_category,
            'examples_validated': {
                'total': example_results['total_examples'],
                'passed': example_results['passed'],
                'failed': example_results['failed']
            },
            'claims_audited': {
                'total': len(source_audit.get('audited_claims', [])),
                'confirmed': sum(1 for c in source_audit.get('audited_claims', []) if c['evidence_status'] == 'CONFIRMED_LOCAL_SOURCE'),
                'inconclusive': sum(1 for c in source_audit.get('audited_claims', []) if c['evidence_status'] == 'INCONCLUSIVE'),
                'unverified': sum(1 for c in source_audit.get('audited_claims', []) if c['evidence_status'] == 'UNVERIFIED')
            }
        },
        'findings': unique_findings,
        'audited_claims': source_audit.get('audited_claims', []),
        'known_limitations': manifest.get('known_limitations', [])
    }
    return report

def render_markdown_report(data: Dict[str, Any]) -> str:
    """Renders structured report data into clean GitHub-flavored Markdown."""
    lines = []
    target = data.get('target_version', {})
    summary = data.get('summary', {})
    by_sev = summary.get('by_severity', {})
    by_ev = summary.get('by_evidence_status', {})

    lines.append("# Three.js Expert Knowledge Base - Maintenance & Version Audit Report\n")
    lines.append(f"**Generated at**: `{data.get('generated_at')}`  ")
    lines.append(f"**Declared Three.js Target**: `{target.get('version')}`  ")
    lines.append(f"**Recorded Revision**: `{target.get('revision')}` (Status: `{target.get('revision_status')}`)  ")
    lines.append(f"**Claimed Latest**: `{target.get('is_latest_claimed')}`  ")
    range_str = target.get('supported_range') or 'None'
    lines.append(f"**Supported Range**: `{range_str}` (Status: `{target.get('range_evidence_status')}`)  \n")
    lines.append("---\n")

    # Section 1: Executive Summary
    lines.append("## 1. Executive Summary\n")
    lines.append("| Metric | Count |")
    lines.append("| :--- | :--- |")
    lines.append(f"| **Total Findings** | **{summary.get('total_findings', 0)}** |")
    lines.append(f"| High Severity (Errors) | {by_sev.get('ERROR', 0)} |")
    lines.append(f"| Medium Severity (Warnings) | {by_sev.get('WARNING', 0)} |")
    lines.append(f"| Informational (Info) | {by_sev.get('INFO', 0)} |")
    lines.append(f"| Confirmed Local Source Findings | {by_ev.get('CONFIRMED_LOCAL_SOURCE', 0)} |")
    lines.append(f"| Candidate Findings (Unreviewed) | {by_ev.get('CANDIDATE_FINDING', 0)} |")
    lines.append(f"| Inconclusive / Absent Findings | {by_ev.get('INCONCLUSIVE', 0)} |")
    lines.append(f"| Unverified Claims | {by_ev.get('UNVERIFIED', 0)} |\n")

    ex_val = summary.get('examples_validated', {})
    lines.append(f"**Canonical Examples Validation**: {ex_val.get('passed', 0)} passed, {ex_val.get('failed', 0)} failed (out of {ex_val.get('total', 0)} total).\n")

    lines.append("---\n")

    # Section 2: Confirmed Local Source Findings
    confirmed = [f for f in data.get('findings', []) if f['evidence_status'] == 'CONFIRMED_LOCAL_SOURCE']
    lines.append(f"## 2. Confirmed Local Source Findings ({len(confirmed)})\n")
    if confirmed:
        lines.append("| Finding ID | Source File | Line | Symbol | Category | Evidence / Explanation |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for f in confirmed:
            ln = f.get('line') if f.get('line') is not None else 'N/A'
            lines.append(f"| `{f['finding_id']}` | `{f['file']}` | {ln} | `{f['api']}` | `{f['category']}` | {f['explanation']} |")
        lines.append("")
    else:
        lines.append("No confirmed local source findings.\n")

    lines.append("---\n")

    # Section 3: Candidate Findings (Requires Human Review)
    candidates = [f for f in data.get('findings', []) if f['evidence_status'] == 'CANDIDATE_FINDING']
    lines.append(f"## 3. Candidate Findings ({len(candidates)})\n")
    lines.append("> [!NOTE]\n> Candidate findings are potential references identified by automated static analysis in documentation or examples. They require human verification and must not be treated as confirmed errors.\n")
    if candidates:
        lines.append("| Finding ID | File | Line | Symbol | Category | Explanation |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for f in candidates:
            ln = f.get('line') if f.get('line') is not None else 'N/A'
            lines.append(f"| `{f['finding_id']}` | `{f['file']}` | {ln} | `{f['api']}` | `{f['category']}` | {f['explanation']} |")
        lines.append("")
    else:
        lines.append("No candidate findings.\n")

    lines.append("---\n")

    # Section 4: Inconclusive & Absent Symbols
    inconclusive = [f for f in data.get('findings', []) if f['evidence_status'] == 'INCONCLUSIVE']
    lines.append(f"## 4. Inconclusive & Absent Symbols ({len(inconclusive)})\n")
    lines.append("> [!WARNING]\n> A symbol's absence from a specific single file does not establish its global removal from the Three.js library. These items are strictly classified as inconclusive.\n")
    if inconclusive:
        lines.append("| Finding ID | File | Symbol | Category | Detail |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for f in inconclusive:
            lines.append(f"| `{f['finding_id']}` | `{f['file']}` | `{f['api']}` | `{f['category']}` | {f['explanation']} |")
        lines.append("")
    else:
        lines.append("No inconclusive findings.\n")

    lines.append("---\n")

    # Section 5: Local Source Compatibility Claims Audit
    claims = data.get('audited_claims', [])
    lines.append(f"## 5. Local Source Compatibility Claims Audit ({len(claims)})\n")
    if claims:
        lines.append("| Claim ID | Status | Affected Symbol | Recommended Symbol | Audit Details |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for c in claims:
            details_str = '<br>'.join(c.get('details', []))
            lines.append(f"| `{c['claim_id']}` | `{c['evidence_status']}` | `{c['affected_api']}` | `{c.get('recommended_api', '')}` | {details_str} |")
        lines.append("")
    else:
        lines.append("No compatibility claims audited.\n")

    lines.append("---\n")

    # Section 6: Known Limitations
    lines.append("## 6. Known Limitations\n")
    limitations = data.get('known_limitations', [])
    if limitations:
        for lim in limitations:
            lines.append(f"- {lim}")
        lines.append("")
    else:
        lines.append("No limitations recorded.\n")

    return '\n'.join(lines)

def write_reports(
    report_data: Dict[str, Any],
    project_root: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """Writes JSON and Markdown reports to a safe output directory."""
    if project_root is None:
        project_root = get_project_root()
    if output_dir is None:
        output_dir = project_root / 'reports'

    safe, msg = is_safe_report_path(output_dir, project_root)
    if not safe:
        raise PermissionError(f"Unsafe report destination: {msg}")

    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / 'latest.json'
    md_path = output_dir / 'latest.md'

    json_text = json.dumps(report_data, indent=2) + '\n'
    with open(json_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json_text)

    md_text = render_markdown_report(report_data) + '\n'
    with open(md_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(md_text)

    return {
        'json_path': json_path,
        'md_path': md_path
    }

# ==============================================================================
# 6. Human-Reviewed Patch Proposals (C.4)
# Proposals are stored under reports/proposals/<proposal_id>/.
# Approval is a METADATA-ONLY decision.  The target file is NEVER modified.
# ==============================================================================

PROPOSAL_STATUS_PENDING  = 'PENDING_REVIEW'
PROPOSAL_STATUS_APPROVED = 'APPROVED'
PROPOSAL_STATUS_REJECTED = 'REJECTED'
PROPOSAL_STATUS_STALE    = 'STALE'

# Only findings with these statuses may generate a proposal.
ELIGIBLE_EVIDENCE_STATUSES   = {'CONFIRMED_LOCAL_SOURCE', 'CONFIRMED_OFFICIAL_ONLINE'}
INELIGIBLE_EVIDENCE_STATUSES = {'CANDIDATE_FINDING', 'INCONCLUSIVE', 'UNVERIFIED'}

# Canonical subdirectories that may be patched.
PATCHABLE_CANONICAL_DIRS = ('core', 'references', 'examples')


def is_safe_proposal_path(target_path: Path, project_root: Path) -> Tuple[bool, str]:
    """Safety guard: proposal storage must be inside reports/proposals/, no traversal, no symlinks."""
    # Reject literal '..' components anywhere in the provided path
    try:
        parts = Path(target_path).parts
    except Exception as e:
        return False, f"Cannot parse path: {e}"
    if '..' in parts:
        return False, f"Path traversal (..) detected in proposal path: {target_path}"

    # Reject symlinks in any already-existing ancestor component
    check = target_path
    while True:
        parent = check.parent
        if parent == check:          # reached filesystem root
            break
        if check.exists() and check.is_symlink():
            return False, f"Symlink detected in proposal path: {check}"
        check = parent

    # Resolve (strict=False — non-existent leaf is OK)
    try:
        resolved        = target_path.resolve()
        proposals_root  = (project_root / 'reports' / 'proposals').resolve()
    except Exception as e:
        return False, f"Cannot resolve path: {e}"

    try:
        resolved.relative_to(proposals_root)
    except ValueError:
        return False, (
            f"Proposal path must be inside 'reports/proposals/'. "
            f"Got: {resolved}"
        )

    return True, "Proposal path is safe."


def is_safe_patch_target(target_path: Path, project_root: Path) -> Tuple[bool, str]:
    """Safety guard: target files must be canonical knowledge files, not symlinks, not outside project."""
    resolved_root = project_root.resolve()

    # Reject symlink
    if target_path.exists() and target_path.is_symlink():
        return False, f"FORBIDDEN: Target file is a symlink: {target_path}"

    # Resolve target
    try:
        resolved_target = target_path.resolve()
    except Exception as e:
        return False, f"Cannot resolve target path: {e}"

    # Must be within project_root
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError:
        return False, f"FORBIDDEN: Target file is outside project root: {resolved_target}"

    # Must be inside one of the canonical patchable directories
    in_canonical = False
    for d in PATCHABLE_CANONICAL_DIRS:
        try:
            resolved_target.relative_to((resolved_root / d).resolve())
            in_canonical = True
            break
        except ValueError:
            pass

    if not in_canonical:
        return False, (
            f"FORBIDDEN: Target file must be inside a canonical directory "
            f"({', '.join(d + '/' for d in PATCHABLE_CANONICAL_DIRS)}). "
            f"Got: {resolved_target}"
        )

    # Must be a regular file
    if not target_path.is_file():
        return False, f"Target file does not exist: {target_path}"

    return True, "Patch target is safe."


def _render_proposal_markdown(proposal: Dict[str, Any]) -> str:
    """Renders a proposal as human-readable Markdown for reviewer inspection."""
    lines = []
    lines.append(f"# Patch Proposal: {proposal['proposal_id']}\n")
    lines.append(f"**Status**: `{proposal['status']}`  ")
    lines.append(f"**Created**: `{proposal['created_at']}`  ")
    lines.append(f"**Finding ID**: `{proposal['finding_id']}`  ")
    lines.append(f"**Evidence Status**: `{proposal['evidence_status']}`  ")
    lines.append(f"**Target File**: `{proposal['target_file']}`  ")
    lines.append(f"**SHA-256 at proposal time**: `{proposal['target_sha256_at_proposal']}`  \n")
    lines.append("---\n")

    lines.append("## Rationale\n")
    lines.append(proposal.get('rationale', ''))
    lines.append("\n---\n")

    lines.append("## Original Snippet\n")
    lines.append("```")
    lines.append(proposal.get('original_snippet', ''))
    lines.append("```\n")

    lines.append("## Proposed Replacement\n")
    lines.append("```")
    lines.append(proposal.get('proposed_snippet', ''))
    lines.append("```\n")

    lines.append("---\n")
    lines.append("## Unified Diff\n")
    lines.append("```diff")
    lines.append(proposal.get('unified_diff', ''))
    lines.append("```\n")

    lines.append("---\n")
    lines.append("## Review Decision\n")
    if proposal.get('reviewer_decision'):
        lines.append(f"**Decision**: `{proposal['reviewer_decision']}`  ")
        lines.append(f"**Reviewed at**: `{proposal.get('reviewed_at')}`  ")
        if proposal.get('review_notes'):
            lines.append(f"\n**Notes**: {proposal['review_notes']}\n")
    elif proposal.get('status') == PROPOSAL_STATUS_STALE:
        lines.append("> [!WARNING]")
        lines.append("> This proposal is **STALE** — the target file has changed since the proposal was created.")
        lines.append("> Generate a new proposal against the current file state.\n")
    else:
        lines.append("> [!IMPORTANT]")
        lines.append("> This proposal is **PENDING REVIEW**.")
        lines.append("> Approve or reject explicitly via `--approve-proposal` or `--reject-proposal`.")
        lines.append(">")
        lines.append("> **IMPORTANT**: Approval records a decision ONLY. The patch is NOT applied automatically.\n")

    lines.append("---\n")
    lines.append("## Safety Notes\n")
    lines.append("- This proposal was generated read-only; the target file has NOT been modified.")
    lines.append("- Approving this proposal does NOT apply any change to any file.")
    lines.append("- Human action is required to apply any change after explicit approval.")

    return '\n'.join(lines)


def _save_proposal(proposal: Dict[str, Any], project_root: Path) -> None:
    """Persists proposal.json and review.md for an existing proposal (idempotent overwrite)."""
    proposal_dir = project_root / 'reports' / 'proposals' / proposal['proposal_id']
    json_path = proposal_dir / 'proposal.json'
    md_path   = proposal_dir / 'review.md'

    json_text = json.dumps(proposal, indent=2) + '\n'
    with open(json_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json_text)

    md_text = _render_proposal_markdown(proposal) + '\n'
    with open(md_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(md_text)


def generate_proposal(
    finding_id: str,
    target_file: str,
    original_snippet: str,
    proposed_snippet: str,
    rationale: str,
    project_root: Optional[Path] = None,
    report_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates a human-review proposal from a confirmed finding.

    Parameters
    ----------
    finding_id       : ID of a CONFIRMED_LOCAL_SOURCE or CONFIRMED_OFFICIAL_ONLINE finding.
    target_file      : Relative path to the canonical knowledge file to patch
                       (must be inside core/, references/, or examples/).
    original_snippet : Exact verbatim text currently in the file to be replaced.
    proposed_snippet : Proposed replacement text.
    rationale        : Human-readable justification.
    project_root     : Canonical project root (defaults to auto-detected).
    report_data      : Optional pre-built report dict for testing (bypasses disk load).

    Returns the proposal dict and writes proposal.json + review.md under
    reports/proposals/<proposal_id>/.

    Raises
    ------
    FileNotFoundError : Finding not in report / target file missing.
    ValueError        : Ineligible evidence status / snippet absent / path violation.
    PermissionError   : Unsafe target or proposal path.
    """
    if project_root is None:
        project_root = get_project_root()

    # --- Load report data ---------------------------------------------------
    if report_data is None:
        report_path = project_root / 'reports' / 'latest.json'
        if not report_path.is_file():
            raise FileNotFoundError(
                f"No report at {report_path}. Run `--report` first."
            )
        report_data = json.loads(report_path.read_text(encoding='utf-8'))

    # Build lookup: finding_id → finding dict
    findings: Dict[str, Any] = {}
    for f in report_data.get('findings', []):
        findings[f['finding_id']] = f

    # Also expose audited_claims symbol audits (they carry CONFIRMED_LOCAL_SOURCE)
    for claim in report_data.get('audited_claims', []):
        for sym in claim.get('symbol_audits', []):
            fid = generate_stable_finding_id(
                sym['source_file'], sym.get('line') or 0, sym['symbol']
            )
            if fid not in findings:
                findings[fid] = {
                    'finding_id': fid,
                    'file': sym['source_file'],
                    'line': sym.get('line'),
                    'api': sym['symbol'],
                    'category': sym['category'],
                    'severity': 'WARNING',
                    'evidence_status': sym['evidence_status'],
                    'explanation': sym['explanation'],
                }

    if finding_id not in findings:
        raise ValueError(
            f"Finding '{finding_id}' not found in the current report. "
            "Run `--report` to regenerate and use a finding ID from the output."
        )

    finding = findings[finding_id]
    evidence_status: str = finding.get('evidence_status', 'UNVERIFIED')

    if evidence_status in INELIGIBLE_EVIDENCE_STATUSES:
        raise ValueError(
            f"Finding '{finding_id}' has evidence status '{evidence_status}', "
            f"which is NOT eligible for a proposal. "
            f"Only {sorted(ELIGIBLE_EVIDENCE_STATUSES)} findings may generate proposals. "
            "CANDIDATE_FINDING and INCONCLUSIVE are not confirmed evidence."
        )

    if evidence_status not in ELIGIBLE_EVIDENCE_STATUSES:
        raise ValueError(
            f"Unrecognised evidence status '{evidence_status}' "
            f"for finding '{finding_id}'."
        )

    # --- Validate target file -----------------------------------------------
    target_path = project_root / target_file
    safe, msg = is_safe_patch_target(target_path, project_root)
    if not safe:
        raise PermissionError(msg)

    # Read current content
    try:
        file_content = target_path.read_text(encoding='utf-8')
    except Exception as e:
        raise IOError(f"Cannot read target file '{target_file}': {e}")

    # Verify original_snippet is verbatim in the file
    if original_snippet not in file_content:
        raise ValueError(
            f"original_snippet not found verbatim in '{target_file}'. "
            "The file may have changed since the finding was recorded, "
            "or the snippet does not match the file content exactly."
        )

    # Capture SHA-256 BEFORE any change (this proposal records it; nothing is changed)
    target_sha256 = hashlib.sha256(target_path.read_bytes()).hexdigest()

    # --- Generate unified diff ----------------------------------------------
    orig_lines = original_snippet.splitlines(keepends=True)
    prop_lines = proposed_snippet.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        orig_lines,
        prop_lines,
        fromfile=f"a/{target_file}",
        tofile=f"b/{target_file}",
        lineterm='',
    ))
    unified_diff_str = '\n'.join(diff_lines)

    # --- Assemble proposal --------------------------------------------------
    proposal_id = f"PROP-{uuid.uuid4().hex[:12].upper()}"
    created_at  = datetime.datetime.now(datetime.timezone.utc).isoformat()

    proposal: Dict[str, Any] = {
        'proposal_id':              proposal_id,
        'schema_version':           '1.0.0',
        'created_at':               created_at,
        'status':                   PROPOSAL_STATUS_PENDING,
        'finding_id':               finding_id,
        'evidence_status':          evidence_status,
        'rationale':                rationale,
        'target_file':              target_file,
        'target_sha256_at_proposal': target_sha256,
        'original_snippet':         original_snippet,
        'proposed_snippet':         proposed_snippet,
        'unified_diff':             unified_diff_str,
        'reviewer_decision':        None,
        'reviewed_at':              None,
        'review_notes':             None,
    }

    # --- Write to disk ------------------------------------------------------
    proposals_dir = project_root / 'reports' / 'proposals' / proposal_id
    safe, msg = is_safe_proposal_path(proposals_dir, project_root)
    if not safe:
        raise PermissionError(f"Unsafe proposal path: {msg}")

    proposals_dir.mkdir(parents=True, exist_ok=True)
    _save_proposal(proposal, project_root)

    return proposal


def get_proposal(
    proposal_id: str,
    project_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Reads and returns a proposal dict by ID.

    Raises ValueError for path-traversal IDs; FileNotFoundError if not found.
    """
    if project_root is None:
        project_root = get_project_root()

    # Reject path traversal in the ID itself
    if '..' in proposal_id or '/' in proposal_id or '\\' in proposal_id:
        raise ValueError(
            f"Invalid proposal_id '{proposal_id}': "
            "must not contain path separators or '..'."
        )

    json_path = project_root / 'reports' / 'proposals' / proposal_id / 'proposal.json'
    if not json_path.is_file():
        raise FileNotFoundError(
            f"Proposal '{proposal_id}' not found at {json_path}"
        )

    return json.loads(json_path.read_text(encoding='utf-8'))


def list_proposals(
    project_root: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Returns all proposals sorted by creation timestamp (oldest first)."""
    if project_root is None:
        project_root = get_project_root()

    proposals_root = project_root / 'reports' / 'proposals'
    if not proposals_root.is_dir():
        return []

    results = []
    for d in sorted(proposals_root.iterdir()):
        if not d.is_dir():
            continue
        json_path = d / 'proposal.json'
        if json_path.is_file():
            try:
                p = json.loads(json_path.read_text(encoding='utf-8'))
                results.append(p)
            except Exception:
                pass  # skip corrupt entries silently

    results.sort(key=lambda x: x.get('created_at', ''))
    return results


def review_proposal(
    proposal_id: str,
    decision: str,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Records an approval or rejection decision for a proposal.

    * decision must be 'APPROVED' or 'REJECTED'.
    * Checks the target file SHA-256 first; marks STALE if changed.
    * NEVER modifies the target canonical file.
    * NEVER applies a patch.
    * Returns the updated proposal dict.
    """
    if project_root is None:
        project_root = get_project_root()

    if decision not in (PROPOSAL_STATUS_APPROVED, PROPOSAL_STATUS_REJECTED):
        raise ValueError(
            f"decision must be '{PROPOSAL_STATUS_APPROVED}' or "
            f"'{PROPOSAL_STATUS_REJECTED}'. Got: '{decision}'"
        )

    proposal = get_proposal(proposal_id, project_root)

    # Refuse to re-review already decided proposals
    if proposal['status'] in (PROPOSAL_STATUS_APPROVED, PROPOSAL_STATUS_REJECTED):
        raise ValueError(
            f"Proposal '{proposal_id}' is already {proposal['status']}. "
            "Cannot change a finalised decision."
        )

    # Already stale
    if proposal['status'] == PROPOSAL_STATUS_STALE:
        raise ValueError(
            f"Proposal '{proposal_id}' is already STALE. "
            "Generate a new proposal against the current file state."
        )

    # --- Stale detection (primary safety gate) ------------------------------
    target_path = project_root / proposal['target_file']
    if not target_path.is_file():
        proposal['status']       = PROPOSAL_STATUS_STALE
        proposal['review_notes'] = (
            f"Target file '{proposal['target_file']}' no longer exists. "
            "Generate a new proposal."
        )
        _save_proposal(proposal, project_root)
        return proposal

    current_sha256 = hashlib.sha256(target_path.read_bytes()).hexdigest()
    captured_sha256 = proposal['target_sha256_at_proposal']

    if current_sha256 != captured_sha256:
        proposal['status']       = PROPOSAL_STATUS_STALE
        proposal['review_notes'] = (
            f"Target file SHA-256 has changed since the proposal was created. "
            f"Captured: {captured_sha256[:16]}... "
            f"Current:  {current_sha256[:16]}... "
            "The proposal is now STALE. Generate a new proposal against the "
            "current file state."
        )
        # NOTE: original captured hash is PRESERVED — never overwritten
        _save_proposal(proposal, project_root)
        return proposal

    # --- Record metadata-only decision (target file NOT touched) ------------
    proposal['status']            = decision
    proposal['reviewer_decision'] = decision
    proposal['reviewed_at']       = datetime.datetime.now(datetime.timezone.utc).isoformat()

    _save_proposal(proposal, project_root)
    return proposal


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Three.js Expert Knowledge Maintenance & Audit Tool")
    parser.add_argument('--check-manifest',    action='store_true', help="Check version manifest and declarations")
    parser.add_argument('--scan',              action='store_true', help="Scan knowledge base for deprecated APIs")
    parser.add_argument('--audit-local',       action='store_true', help="Audit compatibility claims against local Three.js repo")
    parser.add_argument('--validate-examples', action='store_true', help="Validate canonical examples")
    parser.add_argument('--report',            action='store_true', help="Generate deterministic JSON and Markdown reports")
    parser.add_argument('--report-dir',        type=str, default=None, help="Custom output directory for reports (default: reports/)")
    parser.add_argument('--source-dir',        type=str, default=None, help="Path to local Three.js source repository for claim auditing")
    # --- C.4 proposal commands ---
    parser.add_argument('--propose',           type=str, metavar='FINDING_ID',  default=None,
                        help="Generate a patch proposal from a confirmed finding ID")
    parser.add_argument('--target-file',       type=str, default=None,
                        help="Canonical file to patch (relative, e.g. core/api-version-compatibility.md)")
    parser.add_argument('--original',          type=str, default=None,
                        help="Exact verbatim original snippet to replace")
    parser.add_argument('--replacement',       type=str, default=None,
                        help="Proposed replacement snippet")
    parser.add_argument('--rationale',         type=str, default=None,
                        help="Human rationale for the proposal")
    parser.add_argument('--list-proposals',    action='store_true',
                        help="List all patch proposals and their status")
    parser.add_argument('--show-proposal',     type=str, metavar='PROPOSAL_ID', default=None,
                        help="Display a specific proposal")
    parser.add_argument('--approve-proposal',  type=str, metavar='PROPOSAL_ID', default=None,
                        help="Approve a proposal (metadata only — patch is NOT applied automatically)")
    parser.add_argument('--reject-proposal',   type=str, metavar='PROPOSAL_ID', default=None,
                        help="Reject a proposal")

    args = parser.parse_args()
    root = get_project_root()

    src_override = Path(args.source_dir) if args.source_dir else None

    if args.check_manifest:
        m = load_version_manifest(root)
        print(f"Manifest Version: {m['manifest_version']}, Target: {m['declared_target']['version']}")
        disc = check_version_declarations(root)
        print(f"Cross-Declaration Discrepancies: {len(disc)}")
        for d in disc:
            print(f"  [{d['severity']}] {d['file']}:{d['line']} - {d['explanation']}")

    if args.scan:
        f = scan_knowledge_base(root)
        print(f"Total Candidate Findings: {len(f)}")
        for item in f:
            print(f"  [{item['severity']}] {item['file']}:{item['line']} - {item['api']} ({item['category']})")

    if args.audit_local:
        res = audit_local_threejs_source(root, src_override)
        print(f"Source Available: {res['source_available']}, Version: {res['source_version']}")
        for c in res['audited_claims']:
            print(f"  [{c['evidence_status']}] {c['claim_id']}: {c['details']}")

    if args.validate_examples:
        res = validate_examples(root)
        print(f"Examples Validated: {res['passed']} passed, {res['failed']} failed")

    if args.report:
        rep_dir = Path(args.report_dir) if args.report_dir else root / 'reports'
        data = build_report_data(root, src_override)
        paths = write_reports(data, root, rep_dir)
        print(f"Report successfully generated:")
        print(f"  JSON:     {paths['json_path']}")
        print(f"  Markdown: {paths['md_path']}")
        print(f"\nSummary:")
        print(f"  Target Version:  {data['target_version']['version']} (rev: {data['target_version']['revision']})")
        print(f"  Total Findings:  {data['summary']['total_findings']}")
        print(f"  By Severity:     {data['summary']['by_severity']}")
        print(f"  By Evidence:     {data['summary']['by_evidence_status']}")
        print(f"  Examples Status: {data['summary']['examples_validated']['passed']}/{data['summary']['examples_validated']['total']} passed")

    if args.propose:
        for req, name in [(args.target_file, '--target-file'), (args.original, '--original'),
                          (args.replacement, '--replacement'), (args.rationale, '--rationale')]:
            if not req:
                parser.error(f"--propose requires {name}")
        proposal = generate_proposal(
            finding_id=args.propose,
            target_file=args.target_file,
            original_snippet=args.original,
            proposed_snippet=args.replacement,
            rationale=args.rationale,
            project_root=root,
        )
        print(f"Proposal created: {proposal['proposal_id']}")
        print(f"  Status:      {proposal['status']}")
        print(f"  Target file: {proposal['target_file']}")
        print(f"  SHA-256:     {proposal['target_sha256_at_proposal'][:32]}...")
        print(f"  Location:    reports/proposals/{proposal['proposal_id']}/")
        print("\nINFO: This proposal is PENDING REVIEW. No files have been modified.")
        print("      Use --approve-proposal or --reject-proposal to record a decision.")

    if args.list_proposals:
        proposals = list_proposals(root)
        if not proposals:
            print("No proposals found.")
        else:
            print(f"{'Proposal ID':<22} {'Status':<16} {'Finding ID':<48} {'Target File'}")
            print("-" * 110)
            for p in proposals:
                print(f"{p['proposal_id']:<22} {p['status']:<16} {p['finding_id']:<48} {p['target_file']}")

    if args.show_proposal:
        p = get_proposal(args.show_proposal, root)
        print(json.dumps(p, indent=2))

    if args.approve_proposal:
        updated = review_proposal(args.approve_proposal, PROPOSAL_STATUS_APPROVED, root)
        print(f"Proposal {updated['proposal_id']}: {updated['status']}")
        if updated['status'] == PROPOSAL_STATUS_STALE:
            print(f"  STALE: {updated.get('review_notes', '')}")
        else:
            print(f"  Reviewed at: {updated['reviewed_at']}")
        print("  NOTE: No files have been modified. Approval is a metadata-only decision.")

    if args.reject_proposal:
        updated = review_proposal(args.reject_proposal, PROPOSAL_STATUS_REJECTED, root)
        print(f"Proposal {updated['proposal_id']}: {updated['status']}")
        if updated['status'] == PROPOSAL_STATUS_STALE:
            print(f"  STALE: {updated.get('review_notes', '')}")
        else:
            print(f"  Reviewed at: {updated['reviewed_at']}")
