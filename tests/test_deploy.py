"""
Automated Test Suite for Deployment, Safety Boundaries, Manifests, and Rollback
"""

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

from deploy import (
    get_canonical_root,
    is_safe_project_root,
    check_path_traversal,
    plan_deployment,
    execute_deployment,
    verify_deployment,
    rollback_deployment,
    file_sha256
)
from registry import ADAPTER_REGISTRY

class TestDeploymentSafetyAndExecution(unittest.TestCase):
    """Covers all 18 safety, deployment, and rollback requirements."""

    def setUp(self):
        self.canonical_root = get_canonical_root()

    def test_01_dry_run_does_not_modify_filesystem(self):
        """1. Dry run does not modify the filesystem."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            res = execute_deployment(project_root, adapter_key='cursor', dry_run=True)
            self.assertTrue(res['dry_run'])
            self.assertEqual(len(res['created']), 1)
            # Confirm no files were written to disk
            rule_file = project_root / '.cursor' / 'rules' / 'threejs-expert.mdc'
            self.assertFalse(rule_file.exists())
            self.assertFalse((project_root / '.threejs-expert-backups').exists())

    def test_02_new_files_deploy_to_correct_relative_paths(self):
        """2. New files deploy to the correct relative paths."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            res = execute_deployment(project_root, adapter_key='all', dry_run=False)
            self.assertEqual(len(res['created']), 30) # Antigravity (25 bundle), Claude (2), Cursor (1), Copilot (1), Windsurf (1)
            
            self.assertTrue((project_root / '.agents' / 'skills' / 'threejs-expert' / 'SKILL.md').is_file())
            self.assertTrue((project_root / '.agents' / 'skills' / 'threejs-expert' / 'core' / 'framework-detection.md').is_file())
            self.assertTrue((project_root / '.agents' / 'skills' / 'threejs-expert' / 'references' / 'decision-guide.md').is_file())
            self.assertTrue((project_root / '.agents' / 'skills' / 'threejs-expert' / 'examples' / 'basic-vanilla-scene.js').is_file())
            self.assertTrue((project_root / 'CLAUDE.md').is_file())
            self.assertTrue((project_root / '.claude' / 'skills' / 'threejs-expert' / 'SKILL.md').is_file())
            self.assertTrue((project_root / '.cursor' / 'rules' / 'threejs-expert.mdc').is_file())
            self.assertTrue((project_root / '.github' / 'copilot-instructions.md').is_file())
            self.assertTrue((project_root / '.windsurf' / 'rules' / 'threejs-expert.md').is_file())

    def test_antigravity_bundle_deployment_and_link_integrity(self):
        """Dedicated test: Antigravity skill deploys all 25 files and internal links resolve."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            res = execute_deployment(project_root, adapter_key='antigravity', dry_run=False)
            self.assertEqual(len(res['created']), 25)
            
            verify_res = verify_deployment(project_root, Path(res['manifest_path']))
            self.assertTrue(verify_res['success'])
            self.assertEqual(verify_res['verified_count'], 25)
            self.assertEqual(verify_res['discrepancies_count'], 0)
            
            # Check internal links in deployed SKILL.md
            import re
            skill_path = project_root / '.agents' / 'skills' / 'threejs-expert' / 'SKILL.md'
            link_regex = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
            text = skill_path.read_text(encoding='utf-8')
            for m in link_regex.finditer(text):
                target = m.group(2).strip()
                if target.startswith(('http:', 'https:', '#')):
                    continue
                clean_target = target.split('#')[0]
                target_file = (skill_path.parent / clean_target).resolve()
                self.assertTrue(target_file.is_file(), f"Broken link in deployed Antigravity SKILL.md: {clean_target}")

    def test_03_byte_identical_existing_files_are_skipped(self):
        """3. Byte-identical existing files are skipped."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            # First deployment
            res1 = execute_deployment(project_root, adapter_key='cursor', dry_run=False)
            self.assertEqual(len(res1['created']), 1)
            
            # Second deployment without force
            res2 = execute_deployment(project_root, adapter_key='cursor', dry_run=False)
            self.assertEqual(len(res2['created']), 0)
            self.assertEqual(len(res2['skipped']), 1)
            self.assertEqual(len(res2['replaced']), 0)

    def test_04_conflicting_files_are_preserved_and_reported(self):
        """4. Conflicting files are preserved and reported."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            # Create a conflicting pre-existing user file
            target_path = project_root / '.cursor' / 'rules' / 'threejs-expert.mdc'
            target_path.parent.mkdir(parents=True)
            custom_content = "# Pre-existing custom user rules\n"
            target_path.write_text(custom_content, encoding='utf-8')
            
            # Deploy without force must fail and preserve file
            with self.assertRaises(RuntimeError) as ctx:
                execute_deployment(project_root, adapter_key='cursor', force=False, dry_run=False)
                
            self.assertIn("Differing file exists", str(ctx.exception))
            # Verify file was NOT modified
            self.assertEqual(target_path.read_text(encoding='utf-8'), custom_content)

    def test_05_backups_preserve_original_bytes(self):
        """5. Backups preserve exact original bytes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            target_path = project_root / '.cursor' / 'rules' / 'threejs-expert.mdc'
            target_path.parent.mkdir(parents=True)
            original_bytes = b"# User Custom Bytes with special chars \xff\xfe\r\n"
            target_path.write_bytes(original_bytes)
            orig_hash = file_sha256(target_path)
            
            # Deploy with force
            res = execute_deployment(project_root, adapter_key='cursor', force=True, dry_run=False)
            self.assertEqual(len(res['replaced']), 1)
            
            # Verify backup preserves exact bytes
            manifest_path = Path(res['manifest_path'])
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            backup_file = Path(manifest['backup_dir']) / manifest['files'][0]['backup_rel']
            
            self.assertTrue(backup_file.is_file())
            self.assertEqual(backup_file.read_bytes(), original_bytes)
            self.assertEqual(file_sha256(backup_file), orig_hash)

    def test_06_existing_backups_are_never_overwritten(self):
        """6. Existing backups are never overwritten (unique deployment IDs)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            target_path = project_root / '.github' / 'copilot-instructions.md'
            target_path.parent.mkdir(parents=True)
            target_path.write_text("# Initial user config", encoding='utf-8')
            
            res1 = execute_deployment(project_root, adapter_key='copilot', force=True, dry_run=False)
            
            # Modify target again
            target_path.write_text("# Modified user config", encoding='utf-8')
            res2 = execute_deployment(project_root, adapter_key='copilot', force=True, dry_run=False)
            
            self.assertNotEqual(res1['deployment_id'], res2['deployment_id'])
            self.assertTrue(Path(res1['manifest_path']).exists())
            self.assertTrue(Path(res2['manifest_path']).exists())

    def test_07_deployment_manifests_contain_correct_hashes(self):
        """7. Deployment manifests contain correct hashes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            res = execute_deployment(project_root, adapter_key='cursor', dry_run=False)
            manifest = json.loads(Path(res['manifest_path']).read_text(encoding='utf-8'))
            
            self.assertEqual(manifest['status'], 'SUCCESS')
            deployed_file = project_root / '.cursor' / 'rules' / 'threejs-expert.mdc'
            self.assertEqual(manifest['files'][0]['deployed_hash'], file_sha256(deployed_file))

    def test_08_successful_deployment_passes_verification(self):
        """8. Successful deployment passes verification."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            res = execute_deployment(project_root, adapter_key='claude-code', dry_run=False)
            verify_res = verify_deployment(project_root, Path(res['manifest_path']))
            
            self.assertTrue(verify_res['success'])
            self.assertEqual(verify_res['discrepancies_count'], 0)
            self.assertEqual(verify_res['verified_count'], 2)

    def test_09_rollback_restores_replaced_files_exactly(self):
        """9. Rollback restores replaced files exactly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            target_path = project_root / '.cursor' / 'rules' / 'threejs-expert.mdc'
            target_path.parent.mkdir(parents=True)
            original_content = "# Original User Rules\n"
            target_path.write_text(original_content, encoding='utf-8')
            
            res = execute_deployment(project_root, adapter_key='cursor', force=True, dry_run=False)
            self.assertNotEqual(target_path.read_text(encoding='utf-8'), original_content)
            
            # Rollback
            rb_res = rollback_deployment(Path(res['manifest_path']))
            self.assertEqual(len(rb_res['restored']), 1)
            self.assertEqual(target_path.read_text(encoding='utf-8'), original_content)

    def test_10_rollback_removes_deployment_created_files_only_when_unchanged(self):
        """10. Rollback removes deployment-created files only when unchanged."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            res = execute_deployment(project_root, adapter_key='cursor', dry_run=False)
            target_path = project_root / '.cursor' / 'rules' / 'threejs-expert.mdc'
            self.assertTrue(target_path.is_file())
            
            rb_res = rollback_deployment(Path(res['manifest_path']))
            self.assertEqual(len(rb_res['deleted']), 1)
            self.assertFalse(target_path.exists())

    def test_11_rollback_refuses_to_delete_subsequently_modified_files(self):
        """11. Rollback refuses to delete subsequently modified files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            res = execute_deployment(project_root, adapter_key='cursor', dry_run=False)
            target_path = project_root / '.cursor' / 'rules' / 'threejs-expert.mdc'
            
            # Simulate user modification after deployment
            target_path.write_text("# User made edits after deployment\n", encoding='utf-8')
            
            with self.assertRaises(RuntimeError) as ctx:
                rollback_deployment(Path(res['manifest_path']))
                
            self.assertIn("modified after deployment", str(ctx.exception))
            self.assertTrue(target_path.exists(), "Modified file was deleted during unsafe rollback!")

    def test_12_path_traversal_is_rejected(self):
        """12. Path traversal is rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            with self.assertRaises(PermissionError) as ctx:
                check_path_traversal(project_root, "../../escaped.txt")
            self.assertIn("path traversal detected", str(ctx.exception))

    def test_13_symlink_escape_attempts_are_rejected(self):
        """13. Symlink escape attempts are rejected where supported."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            outside_dir = Path(tmp_dir) / 'outside'
            outside_dir.mkdir()
            
            symlink_dir = project_root / 'evil_link'
            try:
                os.symlink(outside_dir, symlink_dir, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks not supported in current environment/permissions")
                
            with self.assertRaises(PermissionError) as ctx:
                check_path_traversal(project_root, "evil_link/file.txt")
            self.assertIn("symlink escape detected", str(ctx.exception))

    def test_14_unsafe_project_roots_are_rejected(self):
        """14. Unsafe project roots are rejected."""
        safe, msg = is_safe_project_root(Path("C:\\"))
        self.assertFalse(safe)
        
        # Test Three.js source repo rejection
        three_source = Path(os.environ.get("THREEJS_SOURCE_DIR", self.canonical_root.parent / "three.js-dev"))
        safe, msg = is_safe_project_root(three_source)
        self.assertFalse(safe)
        self.assertIn("FORBIDDEN", msg)

    def test_15_unknown_adapters_are_rejected(self):
        """15. Unknown adapters are rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            with self.assertRaises(ValueError) as ctx:
                plan_deployment(project_root, adapter_key='emacs')
            self.assertIn("Unknown adapter 'emacs'", str(ctx.exception))

    def test_16_missing_source_files_fail_safely(self):
        """16. Missing source files fail safely."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            # Temporarily inject a non-existent source
            ADAPTER_REGISTRY['fake'] = {
                'deploy_files': [('non/existent/file.md', 'fake.md')]
            }
            try:
                with self.assertRaises(FileNotFoundError) as ctx:
                    plan_deployment(project_root, adapter_key='fake')
                self.assertIn("Missing canonical adapter file", str(ctx.exception))
            finally:
                del ADAPTER_REGISTRY['fake']

    def test_17_failed_writes_do_not_produce_misleading_manifest(self):
        """17. Failed writes do not produce a misleading success manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            # Make .cursor a file so directory creation fails
            bad_dir = project_root / '.cursor'
            bad_dir.write_text("blocked", encoding='utf-8')
            
            with self.assertRaises(RuntimeError):
                execute_deployment(project_root, adapter_key='cursor', dry_run=False)
                
            # Ensure no successful manifest exists
            backups = list((project_root / '.threejs-expert-backups').glob('*/manifest.json'))
            self.assertEqual(len(backups), 0)

    def test_18_repeated_deployments_handled_predictably(self):
        """18. Repeated deployments are handled predictably."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir) / 'test_proj'
            project_root.mkdir()
            
            # Deploy once
            res1 = execute_deployment(project_root, adapter_key='copilot', dry_run=False)
            self.assertEqual(len(res1['created']), 1)
            
            # Deploy second time (skipped identical)
            res2 = execute_deployment(project_root, adapter_key='copilot', dry_run=False)
            self.assertEqual(len(res2['skipped']), 1)
            
            # Deploy third time with force (skipped identical because content is identical)
            res3 = execute_deployment(project_root, adapter_key='copilot', force=True, dry_run=False)
            self.assertEqual(len(res3['skipped']), 1)

if __name__ == '__main__':
    unittest.main()
