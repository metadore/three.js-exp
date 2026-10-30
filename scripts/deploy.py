"""
Controlled, Reversible Deployment Tool for Three.js Expert Knowledge Base Adapters

Features:
- Validates explicit project roots against safety boundaries (blocks root, Three.js source repo, and escapes).
- Supports dry-run planning with explicit action categorization:
    CREATE, REPLACE, SKIP_IDENTICAL, CONFLICT.
- Non-destructive conflict policy: differing files are preserved as CONFLICT unless --force is specified.
- Pre-replacement backups: exact original bytes preserved in versioned, immutable backup folders.
- Atomic manifest generation with SHA-256 integrity hashes.
- Verification mode (--verify) validating live files against manifest hashes.
- Rollback mode (--rollback) with safety protections (refuses to delete subsequently modified files).
"""

import os
import sys
import json
import uuid
import shutil
import hashlib
import argparse
import datetime
from pathlib import Path

# Import central definitions from registry
try:
    from registry import ADAPTER_REGISTRY
except ImportError:
    from scripts.registry import ADAPTER_REGISTRY

def get_canonical_root() -> Path:
    """Returns canonical project root."""
    return Path(__file__).resolve().parent.parent

def file_sha256(path: Path) -> str:
    """Calculates SHA-256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()

def is_safe_project_root(project_root: Path) -> tuple[bool, str]:
    """Safety guard: validates destination project root."""
    resolved = project_root.resolve()
    
    # Reject filesystem root
    if len(resolved.parts) <= 1:
        return False, "Destination project root cannot be filesystem root."
        
    # Reject Three.js source library
    resolved_str = str(resolved).lower().replace('/', '\\')
    if '\\three.js-dev\\three.js-dev' in resolved_str:
        return False, "FORBIDDEN: Cannot deploy into original Three.js source repository."
        
    if not resolved.exists() or not resolved.is_dir():
        return False, f"Project root does not exist or is not a directory: {project_root}"
        
    return True, "Project root is safe."

def check_path_traversal(project_root: Path, rel_path: str) -> Path:
    """Ensures relative path resolves strictly inside project_root without escaping."""
    resolved_root = project_root.resolve()
    target_path = (resolved_root / rel_path).resolve()
    
    try:
        target_path.relative_to(resolved_root)
    except ValueError:
        raise PermissionError(f"Security violation: path traversal detected for '{rel_path}'")
        
    # Check for symlink escapes
    curr = target_path
    while curr != resolved_root and curr != curr.parent:
        if curr.is_symlink():
            sym_target = curr.resolve()
            try:
                sym_target.relative_to(resolved_root)
            except ValueError:
                raise PermissionError(f"Security violation: symlink escape detected at '{curr}' -> '{sym_target}'")
        curr = curr.parent
        
    return target_path

def plan_deployment(project_root: Path, adapter_key: str, force: bool = False) -> tuple[list[dict], list[str]]:
    """Plans deployment operations, checks file existence and hashes without modifying disk."""
    canonical_root = get_canonical_root()
    if adapter_key not in ADAPTER_REGISTRY and adapter_key != 'all':
        raise ValueError(f"Unknown adapter '{adapter_key}'. Supported: {', '.join(ADAPTER_REGISTRY.keys())}, all")
        
    targets = list(ADAPTER_REGISTRY.keys()) if adapter_key == 'all' else [adapter_key]
    plans = []
    conflicts = []
    
    for t in targets:
        for src_rel, dest_rel in ADAPTER_REGISTRY[t]['deploy_files']:
            src_path = canonical_root / src_rel
            if not src_path.is_file():
                raise FileNotFoundError(f"Missing canonical adapter file for {t}: {src_rel}")
                
            dest_path = check_path_traversal(project_root, dest_rel)
            src_bytes = src_path.read_bytes()
            # Normalize LF on canonical adapter bytes
            src_content = src_path.read_text(encoding='utf-8').strip() + '\n'
            src_hash = hashlib.sha256(src_content.encode('utf-8')).hexdigest()
            
            if not dest_path.exists():
                plans.append({
                    'action': 'CREATE',
                    'adapter': t,
                    'src_path': src_path,
                    'dest_path': dest_path,
                    'dest_rel': dest_rel,
                    'src_hash': src_hash,
                    'content': src_content,
                    'existed_before': False,
                    'pre_hash': None
                })
            elif dest_path.is_dir():
                conflicts.append(f"Destination is a directory: {dest_rel}")
            else:
                dest_hash = file_sha256(dest_path)
                if dest_hash == src_hash:
                    plans.append({
                        'action': 'SKIP_IDENTICAL',
                        'adapter': t,
                        'src_path': src_path,
                        'dest_path': dest_path,
                        'dest_rel': dest_rel,
                        'src_hash': src_hash,
                        'existed_before': True,
                        'pre_hash': dest_hash
                    })
                else:
                    if force:
                        plans.append({
                            'action': 'REPLACE',
                            'adapter': t,
                            'src_path': src_path,
                            'dest_path': dest_path,
                            'dest_rel': dest_rel,
                            'src_hash': src_hash,
                            'content': src_content,
                            'existed_before': True,
                            'pre_hash': dest_hash
                        })
                    else:
                        conflicts.append(f"Differing file exists at {dest_rel} (use --force to backup and replace)")
                        
    return plans, conflicts

def execute_deployment(project_root: Path, adapter_key: str, force: bool = False, dry_run: bool = False) -> dict:
    """Executes safe deployment with pre-replacement backups and atomic manifest creation."""
    safe, msg = is_safe_project_root(project_root)
    if not safe:
        raise ValueError(f"Project root rejected: {msg}")
        
    resolved_root = project_root.resolve()
    plans, conflicts = plan_deployment(resolved_root, adapter_key, force=force)
    
    if conflicts:
        raise RuntimeError(f"Deployment halted due to conflicts:\n  " + "\n  ".join(conflicts))
        
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = f"deploy_{timestamp_str}_{uuid.uuid4().hex[:8]}"
    backup_base = resolved_root / '.threejs-expert-backups' / unique_id
    
    manifest = {
        'manifest_version': '1.0',
        'deployment_id': unique_id,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'adapter': adapter_key,
        'project_root': str(resolved_root),
        'backup_dir': str(backup_base) if any(p['action'] == 'REPLACE' for p in plans) else None,
        'files': [],
        'status': 'DRY_RUN' if dry_run else 'PENDING'
    }
    
    results = {
        'dry_run': dry_run,
        'deployment_id': unique_id,
        'created': [],
        'replaced': [],
        'skipped': [],
        'manifest_path': None
    }
    
    if dry_run:
        for p in plans:
            act = p['action']
            rel = p['dest_rel']
            if act == 'CREATE':
                results['created'].append(rel)
            elif act == 'REPLACE':
                results['replaced'].append(rel)
            elif act == 'SKIP_IDENTICAL':
                results['skipped'].append(rel)
        return results
        
    # Real execution:
    try:
        # Step 1: Process Backups for REPLACED files
        for p in plans:
            if p['action'] == 'REPLACE':
                backup_base.mkdir(parents=True, exist_ok=True)
                backup_path = backup_base / p['dest_rel']
                if backup_path.exists():
                    raise RuntimeError(f"Backup conflict: {backup_path} already exists")
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                # Copy exact original bytes
                shutil.copy2(p['dest_path'], backup_path)
                # Verify backup
                if file_sha256(backup_path) != p['pre_hash']:
                    raise RuntimeError(f"Backup verification failed for {p['dest_rel']}")
                p['backup_rel'] = str(backup_path.relative_to(backup_base))
            else:
                p['backup_rel'] = None
                
        # Step 2: Write Files
        for p in plans:
            act = p['action']
            dest = p['dest_path']
            rel = p['dest_rel']
            
            if act in ('CREATE', 'REPLACE'):
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(p['content'])
                # Verify written file
                post_hash = file_sha256(dest)
                if post_hash != p['src_hash']:
                    raise RuntimeError(f"Post-write hash mismatch on {rel}")
                if act == 'CREATE':
                    results['created'].append(rel)
                else:
                    results['replaced'].append(rel)
            else:
                results['skipped'].append(rel)
                
            manifest['files'].append({
                'dest_rel': rel,
                'action': act,
                'existed_before': p['existed_before'],
                'pre_hash': p['pre_hash'],
                'deployed_hash': p['src_hash'],
                'backup_rel': p.get('backup_rel')
            })
            
        manifest['status'] = 'SUCCESS'
        
        # Step 3: Write Manifest Atomically
        manifest_dir = backup_base if backup_base.exists() else (resolved_root / '.threejs-expert-backups' / unique_id)
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = manifest_dir / 'manifest.json'
        tmp_manifest = manifest_dir / 'manifest.json.tmp'
        
        with open(tmp_manifest, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(manifest, f, indent=2)
        tmp_manifest.replace(manifest_file)
        
        results['manifest_path'] = str(manifest_file)
        return results
        
    except Exception as e:
        manifest['status'] = f'FAILED: {str(e)}'
        raise RuntimeError(f"Deployment failed during execution: {e}")

def verify_deployment(project_root: Path, manifest_path: Path) -> dict:
    """Verifies a live project against a deployment manifest."""
    safe, msg = is_safe_project_root(project_root)
    if not safe:
        raise ValueError(f"Project root rejected: {msg}")
        
    resolved_root = project_root.resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    verified = []
    discrepancies = []
    
    for item in data.get('files', []):
        rel = item['dest_rel']
        target = resolved_root / rel
        expected_hash = item['deployed_hash']
        
        if not target.exists():
            discrepancies.append(f"Missing file: {rel}")
        elif target.is_dir():
            discrepancies.append(f"Expected file but found directory: {rel}")
        else:
            curr_hash = file_sha256(target)
            if curr_hash == expected_hash:
                verified.append(rel)
            else:
                discrepancies.append(f"Hash discrepancy in {rel} (expected {expected_hash[:10]}, got {curr_hash[:10]})")
                
    return {
        'deployment_id': data.get('deployment_id'),
        'verified_count': len(verified),
        'discrepancies_count': len(discrepancies),
        'verified': verified,
        'discrepancies': discrepancies,
        'success': len(discrepancies) == 0
    }

def rollback_deployment(manifest_path: Path) -> dict:
    """Safely rolls back a deployment using its manifest."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    if data.get('status') == 'ROLLED_BACK':
        raise RuntimeError(f"Deployment {data.get('deployment_id')} has already been rolled back.")
        
    project_root = Path(data['project_root'])
    safe, msg = is_safe_project_root(project_root)
    if not safe:
        raise ValueError(f"Project root in manifest rejected: {msg}")
        
    resolved_root = project_root.resolve()
    backup_base = Path(data['backup_dir']) if data.get('backup_dir') else None
    
    restored = []
    deleted = []
    skipped = []
    conflicts = []
    
    # Pre-flight rollback validation
    for item in data.get('files', []):
        rel = item['dest_rel']
        act = item['action']
        target = resolved_root / rel
        
        if act == 'REPLACE':
            backup_rel = item.get('backup_rel')
            if not backup_rel or not backup_base:
                conflicts.append(f"Missing backup metadata for replaced file: {rel}")
                continue
            backup_file = backup_base / backup_rel
            if not backup_file.is_file():
                conflicts.append(f"Backup file missing on disk: {backup_file}")
            elif file_sha256(backup_file) != item['pre_hash']:
                conflicts.append(f"Backup file corrupted (hash mismatch): {backup_file}")
                
        elif act == 'CREATE':
            if target.exists():
                curr_hash = file_sha256(target)
                if curr_hash != item['deployed_hash']:
                    conflicts.append(f"Cannot rollback created file {rel}: modified after deployment")
                    
    if conflicts:
        raise RuntimeError(f"Rollback aborted due to safety conflicts:\n  " + "\n  ".join(conflicts))
        
    # Execute rollback
    for item in data.get('files', []):
        rel = item['dest_rel']
        act = item['action']
        target = resolved_root / rel
        
        if act == 'REPLACE':
            backup_file = backup_base / item['backup_rel']
            shutil.copy2(backup_file, target)
            restored.append(rel)
        elif act == 'CREATE':
            if target.exists():
                target.unlink()
                deleted.append(rel)
                # Clean up empty parent directory if empty
                parent = target.parent
                try:
                    if parent != resolved_root and not any(parent.iterdir()):
                        parent.rmdir()
                except Exception:
                    pass
        elif act == 'SKIP_IDENTICAL':
            skipped.append(rel)
            
    # Update manifest
    data['status'] = 'ROLLED_BACK'
    data['rolled_back_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(manifest_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=2)
        
    return {
        'deployment_id': data.get('deployment_id'),
        'restored': restored,
        'deleted': deleted,
        'skipped': skipped,
        'status': 'ROLLED_BACK'
    }

def main():
    parser = argparse.ArgumentParser(description="Multi-IDE Adapter Deployment Tool")
    parser.add_argument("--list", action="store_true", help="List all supported IDE adapters and destination paths")
    parser.add_argument("--adapter", type=str, choices=list(ADAPTER_REGISTRY.keys()) + ['all'], help="Target adapter to deploy")
    parser.add_argument("--project-root", type=str, help="Target project root directory")
    parser.add_argument("--dry-run", action="store_true", help="Calculate actions without modifying disk")
    parser.add_argument("--force", action="store_true", help="Permit backup and replacement of differing files")
    parser.add_argument("--verify", action="store_true", help="Verify deployment against a manifest")
    parser.add_argument("--rollback", action="store_true", help="Rollback deployment using a manifest")
    parser.add_argument("--manifest", type=str, help="Path to deployment manifest (required for --verify and --rollback)")
    
    args = parser.parse_args()
    
    if args.list:
        print("Supported Multi-IDE Adapters:")
        for k, v in ADAPTER_REGISTRY.items():
            print(f"\n[{k}] {v['name']}: {v['description']}")
            print("  Deployed Files:")
            for src, dest in v['deploy_files']:
                print(f"    {src} -> {dest}")
        sys.exit(0)
        
    if args.verify:
        if not args.manifest or not args.project_root:
            print("Error: --verify requires both --manifest and --project-root", file=sys.stderr)
            sys.exit(1)
        try:
            res = verify_deployment(Path(args.project_root), Path(args.manifest))
            print(f"Verification Result for {res['deployment_id']}:")
            print(f"  Verified:      {res['verified_count']} files")
            print(f"  Discrepancies: {res['discrepancies_count']} files")
            if res['discrepancies']:
                for d in res['discrepancies']:
                    print(f"    ! {d}")
                sys.exit(1)
            else:
                print("  Status: ALL DEPLOYED FILES VERIFIED.")
                sys.exit(0)
        except Exception as e:
            print(f"Verification error: {e}", file=sys.stderr)
            sys.exit(1)
            
    if args.rollback:
        if not args.manifest:
            print("Error: --rollback requires --manifest", file=sys.stderr)
            sys.exit(1)
        try:
            res = rollback_deployment(Path(args.manifest))
            print(f"Rollback Complete for {res['deployment_id']}:")
            print(f"  Restored from backup: {len(res['restored'])} files")
            for r in res['restored']:
                print(f"    <- {r}")
            print(f"  Deleted new files:    {len(res['deleted'])} files")
            for d in res['deleted']:
                print(f"    x {d}")
            sys.exit(0)
        except Exception as e:
            print(f"Rollback error: {e}", file=sys.stderr)
            sys.exit(1)
            
    if args.adapter:
        if not args.project_root:
            print("Error: --adapter deployment requires --project-root", file=sys.stderr)
            sys.exit(1)
        try:
            res = execute_deployment(
                project_root=Path(args.project_root),
                adapter_key=args.adapter,
                force=args.force,
                dry_run=args.dry_run
            )
            mode_str = "[DRY-RUN] " if res['dry_run'] else ""
            print(f"{mode_str}Deployment ID: {res['deployment_id']}")
            print(f"  Created:  {len(res['created'])} files")
            for f in res['created']:
                print(f"    + {f}")
            print(f"  Replaced: {len(res['replaced'])} files (backed up)")
            for f in res['replaced']:
                print(f"    * {f}")
            print(f"  Skipped:  {len(res['skipped'])} files (identical)")
            if res.get('manifest_path'):
                print(f"  Manifest: {res['manifest_path']}")
            sys.exit(0)
        except Exception as e:
            print(f"Deployment error: {e}", file=sys.stderr)
            sys.exit(1)
            
    parser.print_help()

if __name__ == '__main__':
    main()
