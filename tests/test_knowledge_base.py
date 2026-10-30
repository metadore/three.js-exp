"""
Automated Validation Test Suite for Portable Three.js Expert Knowledge Base
"""

import os
import re
import tempfile
import unittest
from pathlib import Path

# Import from scripts/build.py
import sys
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

from build import (
    get_project_root,
    validate_canonical_sources,
    is_safe_destination,
    execute_build,
    EXPECTED_CORE,
    EXPECTED_REFERENCES,
    EXPECTED_EXAMPLES
)

class TestCanonicalManifest(unittest.TestCase):
    """Validates the canonical files inventory and integrity."""
    
    def setUp(self):
        self.project_root = get_project_root()
        
    def test_canonical_root_exists(self):
        self.assertTrue(self.project_root.is_dir(), f"Project root {self.project_root} does not exist.")
        
    def test_expected_files_exist(self):
        """1. All expected canonical knowledge files exist."""
        sources = validate_canonical_sources(self.project_root)
        self.assertEqual(len(sources['core']), 4)
        self.assertEqual(len(sources['references']), 10)
        self.assertEqual(len(sources['examples']), 10)
        
    def test_exact_category_counts(self):
        """2. Exactly 4 core, 10 reference, and 10 example files."""
        core_files = [f.name for f in (self.project_root / 'core').iterdir() if f.is_file()]
        ref_files = [f.name for f in (self.project_root / 'references').iterdir() if f.is_file()]
        ex_files = [f.name for f in (self.project_root / 'examples').iterdir() if f.is_file()]
        
        self.assertEqual(len(core_files), 4, f"Core files count mismatch: {core_files}")
        self.assertEqual(len(ref_files), 10, f"References count mismatch: {ref_files}")
        self.assertEqual(len(ex_files), 10, f"Examples count mismatch: {ex_files}")
        
    def test_no_reappeared_gltf_loader_pattern(self):
        """3. No deleted gltf-loader-pattern.js example has reappeared."""
        pattern_file = self.project_root / 'examples' / 'gltf-loader-pattern.js'
        self.assertFalse(pattern_file.exists(), "BUG-02 Regression: gltf-loader-pattern.js has reappeared!")
        
        # Also ensure no references in any canonical files
        for folder in ['core', 'references', 'examples']:
            for fp in (self.project_root / folder).iterdir():
                if fp.is_file():
                    content = fp.read_text(encoding='utf-8')
                    self.assertNotIn('gltf-loader-pattern.js', content, f"Residual reference in {fp}")

class TestFileFormattingAndLinks(unittest.TestCase):
    """Validates file formatting, line endings, and internal links."""
    
    def setUp(self):
        self.project_root = get_project_root()
        
    def test_lf_line_endings(self):
        """5. Canonical text files use LF line endings (no CRLF)."""
        crlf_found = []
        for folder in ['core', 'references', 'examples']:
            for fp in (self.project_root / folder).iterdir():
                if fp.is_file():
                    raw = fp.read_bytes()
                    if b'\r\n' in raw:
                        crlf_found.append(str(fp.relative_to(self.project_root)))
                        
        readme = self.project_root / 'README.md'
        if readme.exists() and b'\r\n' in readme.read_bytes():
            crlf_found.append('README.md')
            
        self.assertEqual(len(crlf_found), 0, f"CRLF line endings detected in: {crlf_found}")
        
    def test_internal_relative_markdown_links_resolve(self):
        """4. Internal relative Markdown links resolve to real files."""
        link_regex = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        broken_links = []
        
        for folder in ['core', 'references']:
            for fp in (self.project_root / folder).iterdir():
                if fp.suffix == '.md':
                    text = fp.read_text(encoding='utf-8')
                    for m in link_regex.finditer(text):
                        target = m.group(2).strip()
                        if target.startswith(('http:', 'https:', '#', 'mailto:')):
                            continue
                        clean_target = target.split('#')[0]
                        if not clean_target:
                            continue
                        target_path = (fp.parent / clean_target).resolve()
                        if not target_path.exists():
                            broken_links.append((str(fp.relative_to(self.project_root)), target, str(target_path)))
                            
        self.assertEqual(len(broken_links), 0, f"Broken internal links found: {broken_links}")

class TestBuildSafetyAndExecution(unittest.TestCase):
    """Validates destination validation, dry run, and output containment."""
    
    def setUp(self):
        self.project_root = get_project_root()
        
    def test_reject_unsafe_destinations(self):
        """6. Build configuration rejects unsafe or unintended destinations."""
        # Test filesystem root
        safe, msg = is_safe_destination(Path("C:\\"), self.project_root)
        self.assertFalse(safe)
        
        # Test targeting Three.js original library source
        source_repo_path = Path(os.environ.get("THREEJS_SOURCE_DIR", self.project_root.parent / "three.js-dev"))
        safe, msg = is_safe_destination(source_repo_path, self.project_root)
        self.assertFalse(safe)
        self.assertIn("FORBIDDEN", msg)
        
    def test_dry_run_does_not_modify_filesystem(self):
        """7. A dry run does not modify the filesystem."""
        with tempfile.TemporaryDirectory() as tmp_parent:
            non_existent_dest = Path(tmp_parent) / 'dry_run_target'
            self.assertFalse(non_existent_dest.exists())
            
            results = execute_build(non_existent_dest, dry_run=True)
            self.assertTrue(results['dry_run'])
            self.assertFalse(non_existent_dest.exists(), "Dry run modified disk and created destination!")
            self.assertEqual(len(results['created']), 25) # 24 canonical + 1 SKILL.md
            
    def test_generator_output_contained_in_destination(self):
        """8. Generator output cannot escape the explicitly selected destination."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir) / 'test_build_output'
            results = execute_build(dest, dry_run=False)
            
            self.assertTrue(dest.is_dir())
            built_files = list(dest.rglob('*'))
            
            resolved_dest = dest.resolve()
            for bf in built_files:
                if bf.is_file():
                    # Check boundary containment
                    self.assertTrue(str(bf.resolve()).startswith(str(resolved_dest)),
                                    f"File escaped destination boundary: {bf}")
                    
            # Confirm 24 canonical files + 1 SKILL.md = 25 files
            actual_files = [f for f in built_files if f.is_file()]
            self.assertEqual(len(actual_files), 25)

if __name__ == '__main__':
    unittest.main()
