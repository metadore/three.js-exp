"""
Automated Test Suite for Multi-IDE Adapters and Adapter Build Interface
"""

import os
import re
import tempfile
import unittest
from pathlib import Path

import sys
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

from build import (
    get_project_root,
    is_safe_destination,
    execute_build,
    SUPPORTED_ADAPTERS
)

class TestAdapterDefinitions(unittest.TestCase):
    """Validates presence and schema of all declared adapters."""
    
    def setUp(self):
        self.project_root = get_project_root()
        self.adapters_dir = self.project_root / 'adapters'
        
    def test_all_declared_adapters_in_registry(self):
        """Every declared adapter has an entry in registry and on disk."""
        expected_adapters = {'antigravity', 'claude-code', 'cursor', 'copilot', 'windsurf'}
        self.assertEqual(set(SUPPORTED_ADAPTERS.keys()), expected_adapters)
        
        for name, config in SUPPORTED_ADAPTERS.items():
            for src_rel, _ in config['files']:
                src_path = self.project_root / src_rel
                self.assertTrue(src_path.is_file(), f"Missing adapter file for {name}: {src_rel}")
                
    def test_compatibility_matrix_exists_and_verified(self):
        """adapters/COMPATIBILITY.md exists and documents all 5 platforms."""
        compat_path = self.adapters_dir / 'COMPATIBILITY.md'
        self.assertTrue(compat_path.is_file(), "adapters/COMPATIBILITY.md is missing")
        content = compat_path.read_text(encoding='utf-8')
        for platform in ['Antigravity', 'Claude Code', 'Cursor', 'Copilot', 'Windsurf']:
            self.assertIn(platform, content, f"Missing platform in COMPATIBILITY.md: {platform}")
        self.assertIn("VERIFIED", content)

    def test_antigravity_frontmatter(self):
        """Antigravity SKILL.md has valid YAML frontmatter."""
        skill_path = self.adapters_dir / 'antigravity' / 'SKILL.md'
        text = skill_path.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---'))
        self.assertIn('name: threejs-expert', text)
        self.assertIn('description:', text)

    def test_cursor_mdc_frontmatter(self):
        """Cursor rule uses .mdc extension and has globs and description."""
        mdc_path = self.adapters_dir / 'cursor' / 'threejs-expert.mdc'
        self.assertTrue(mdc_path.is_file())
        text = mdc_path.read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---'))
        self.assertIn('globs:', text)
        self.assertIn('description:', text)
        self.assertIn('alwaysApply:', text)

    def test_copilot_instructions_pure_markdown(self):
        """GitHub Copilot instructions must be pure Markdown without YAML frontmatter."""
        copilot_path = self.adapters_dir / 'copilot' / 'copilot-instructions.md'
        self.assertTrue(copilot_path.is_file())
        text = copilot_path.read_text(encoding='utf-8')
        self.assertFalse(text.startswith('---'), "Copilot instructions must not use YAML frontmatter")
        self.assertTrue(text.startswith('# '), "Copilot instructions should start with markdown header")

    def test_claude_code_skills(self):
        """Claude Code has CLAUDE.md and skills/threejs-expert/SKILL.md."""
        claude_md = self.adapters_dir / 'claude-code' / 'CLAUDE.md'
        skill_md = self.adapters_dir / 'claude-code' / 'skills' / 'threejs-expert' / 'SKILL.md'
        self.assertTrue(claude_md.is_file())
        self.assertTrue(skill_md.is_file())
        self.assertIn('name: threejs-expert', skill_md.read_text(encoding='utf-8'))

    def test_canonical_file_references_in_adapters(self):
        """All adapter file references to canonical files point to valid files."""
        expected_canonical = {
            'core/framework-detection.md',
            'core/implementation-patterns.md',
            'references/decision-guide.md',
            'references/disposal-guide.md',
            'references/troubleshooting-matrix.md',
            'references/troubleshooting.md',
            'examples/gltf-loader-safe.js'
        }
        for name, config in SUPPORTED_ADAPTERS.items():
            for src_rel, _ in config['files']:
                text = (self.project_root / src_rel).read_text(encoding='utf-8')
                for canonical_ref in expected_canonical:
                    # Clean filename
                    filename = Path(canonical_ref).name
                    # If filename is mentioned, ensure it matches an existing canonical file
                    if filename in text:
                        found_path = list(self.project_root.rglob(filename))
                        self.assertTrue(len(found_path) > 0, f"Referenced {filename} does not exist!")

class TestAdapterBuildInterface(unittest.TestCase):
    """Validates adapter building, rejection of invalid targets, and dry-run safety."""
    
    def setUp(self):
        self.project_root = get_project_root()
        
    def test_unknown_adapter_rejected(self):
        """Rejects unknown adapter targets with clear error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir) / 'out'
            with self.assertRaises(ValueError) as ctx:
                execute_build(dest, adapter='unknown_ide')
            self.assertIn("Unknown adapter 'unknown_ide'", str(ctx.exception))

    def test_dry_run_creates_no_adapter_files(self):
        """Dry-run mode does not modify disk when building an adapter."""
        with tempfile.TemporaryDirectory() as tmp_parent:
            dest = Path(tmp_parent) / 'dry_run_adapter'
            self.assertFalse(dest.exists())
            results = execute_build(dest, adapter='cursor', dry_run=True)
            self.assertTrue(results['dry_run'])
            self.assertFalse(dest.exists(), "Dry run created directory!")
            self.assertTrue(any('threejs-expert.mdc' in f for f in results['created']))

    def test_adapter_output_contained_within_destination(self):
        """Generated adapter outputs cannot escape destination boundary."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir) / 'adapter_test_output'
            results = execute_build(dest, adapter='all', include_knowledge=False, dry_run=False)
            
            self.assertTrue(dest.is_dir())
            resolved_dest = dest.resolve()
            
            built_files = [f for f in dest.rglob('*') if f.is_file()]
            self.assertTrue(len(built_files) >= 5, "Expected at least 5 adapter files for 'all'")
            
            for bf in built_files:
                self.assertTrue(
                    str(bf.resolve()).startswith(str(resolved_dest)),
                    f"File escaped destination boundary: {bf}"
                )
                
            # Check individual expected outputs
            self.assertTrue((dest / 'SKILL.md').is_file())
            self.assertTrue((dest / 'CLAUDE.md').is_file())
            self.assertTrue((dest / '.claude' / 'skills' / 'threejs-expert' / 'SKILL.md').is_file())
            self.assertTrue((dest / '.cursor' / 'rules' / 'threejs-expert.mdc').is_file())
            self.assertTrue((dest / '.github' / 'copilot-instructions.md').is_file())
            self.assertTrue((dest / '.windsurf' / 'rules' / 'threejs-expert.md').is_file())

if __name__ == '__main__':
    unittest.main()
