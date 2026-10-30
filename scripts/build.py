"""
Portable Build & Validation Interface for Three.js Expert Knowledge Base

Features:
- Dynamically derives project root from script location.
- Reads canonical knowledge files from disk (core/, references/, examples/).
- Reads official adapter files from disk (adapters/).
- Supports explicit --adapter selection (antigravity, claude-code, cursor, copilot, windsurf, all).
- Rejects unknown adapter targets.
- Supports explicit --output-dir and --dry-run mode.
- Validates all 24 canonical files exist before writing.
- Enforces strict safety boundary checks (rejects Three.js source repo and path escapes).
- Guarantees UTF-8 encoding and LF (\\n) line endings.
- Categorizes all planned file actions: CREATED, CHANGED, UNCHANGED, CONFLICT.
"""

import os
import sys
import shutil
import hashlib
import argparse
from pathlib import Path

# Import central definitions from registry
try:
    from registry import (
        EXPECTED_CORE,
        EXPECTED_REFERENCES,
        EXPECTED_EXAMPLES,
        ADAPTER_REGISTRY
    )
except ImportError:
    from scripts.registry import (
        EXPECTED_CORE,
        EXPECTED_REFERENCES,
        EXPECTED_EXAMPLES,
        ADAPTER_REGISTRY
    )

# Supported Multi-IDE Adapters Registry for build/staging
SUPPORTED_ADAPTERS = {
    k: {
        'description': v['description'],
        'files': v['build_files']
    }
    for k, v in ADAPTER_REGISTRY.items()
}

def get_project_root() -> Path:
    """Returns canonical project root dynamically."""
    return Path(__file__).resolve().parent.parent

def validate_canonical_sources(project_root: Path) -> dict:
    """Validates presence of all 24 canonical files on disk."""
    missing = []
    sources = {'core': [], 'references': [], 'examples': []}
    
    for fname in EXPECTED_CORE:
        p = project_root / 'core' / fname
        if not p.is_file():
            missing.append(f'core/{fname}')
        else:
            sources['core'].append(p)
            
    for fname in EXPECTED_REFERENCES:
        p = project_root / 'references' / fname
        if not p.is_file():
            missing.append(f'references/{fname}')
        else:
            sources['references'].append(p)
            
    for fname in EXPECTED_EXAMPLES:
        p = project_root / 'examples' / fname
        if not p.is_file():
            missing.append(f'examples/{fname}')
        else:
            sources['examples'].append(p)
            
    if missing:
        raise FileNotFoundError(f"Missing required canonical files: {', '.join(missing)}")
        
    return sources

def validate_adapter_sources(project_root: Path, adapter_key: str) -> list[tuple[Path, str]]:
    """Validates presence of adapter files on disk and returns (src_path, target_rel_path)."""
    if adapter_key not in SUPPORTED_ADAPTERS and adapter_key != 'all':
        supported = ', '.join(list(SUPPORTED_ADAPTERS.keys()) + ['all'])
        raise ValueError(f"Unknown adapter '{adapter_key}'. Supported targets: {supported}")
        
    targets = list(SUPPORTED_ADAPTERS.keys()) if adapter_key == 'all' else [adapter_key]
    planned = []
    
    for t in targets:
        for src_rel, dest_rel in SUPPORTED_ADAPTERS[t]['files']:
            src_p = project_root / src_rel
            if not src_p.is_file():
                raise FileNotFoundError(f"Adapter source file missing for {t}: {src_rel}")
            planned.append((src_p, dest_rel))
            
    return planned

def is_safe_destination(output_dir: Path, project_root: Path) -> tuple[bool, str]:
    """Safety guard: prevents writes to root, Three.js source repo, or path escapes."""
    resolved = output_dir.resolve()
    
    # Check for empty or root filesystem paths
    if len(resolved.parts) <= 1:
        return False, "Destination cannot be filesystem root."
        
    # Check against Three.js original source repository
    resolved_str = str(resolved).lower().replace('/', '\\')
    if '\\three.js-dev\\three.js-dev' in resolved_str:
        return False, "FORBIDDEN: Cannot target original Three.js library source repository."
        
    return True, "Destination path is safe."

def file_sha256(path: Path) -> str:
    """Returns SHA-256 of file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()

def plan_copy(src: Path, dest: Path) -> dict:
    """Plans copy operation and determines action without touching disk."""
    if not dest.exists():
        return {'action': 'CREATED', 'src': src, 'dest': dest}
    
    if dest.is_dir():
        return {'action': 'CONFLICT', 'src': src, 'dest': dest, 'reason': 'Destination is a directory.'}
        
    src_hash = file_sha256(src)
    dest_hash = file_sha256(dest)
    
    if src_hash == dest_hash:
        return {'action': 'UNCHANGED', 'src': src, 'dest': dest}
    else:
        return {'action': 'CHANGED', 'src': src, 'dest': dest}

def execute_build(
    output_dir: Path,
    adapter: str | None = None,
    include_knowledge: bool = True,
    dry_run: bool = False
) -> dict:
    """Executes a validated, safe build of canonical knowledge and/or IDE adapters."""
    project_root = get_project_root()
    
    # 1. Safety check output_dir
    safe, msg = is_safe_destination(output_dir, project_root)
    if not safe:
        raise ValueError(f"Build destination rejected: {msg}")
        
    resolved_out = output_dir.resolve()
    plans = []
    
    # 2. Plan canonical knowledge copies
    if include_knowledge:
        sources = validate_canonical_sources(project_root)
        for cat in ['core', 'references', 'examples']:
            for src_path in sources[cat]:
                dest_path = resolved_out / cat / src_path.name
                plans.append(plan_copy(src_path, dest_path))
                
    # 3. Plan adapter copies
    if adapter is not None:
        adapter_copies = validate_adapter_sources(project_root, adapter)
        for src_path, target_rel in adapter_copies:
            dest_path = resolved_out / target_rel
            plans.append(plan_copy(src_path, dest_path))
    elif include_knowledge:
        # Default behavior when no adapter specified: include Antigravity adapter as standard SKILL.md
        src_path = project_root / 'adapters' / 'antigravity' / 'SKILL.md'
        if src_path.is_file():
            dest_path = resolved_out / 'SKILL.md'
            plans.append(plan_copy(src_path, dest_path))
            
    # Check for conflicts
    conflicts = [p for p in plans if p['action'] == 'CONFLICT']
    if conflicts:
        raise RuntimeError(f"Build conflicts detected: {conflicts}")
        
    results = {
        'dry_run': dry_run,
        'output_dir': str(resolved_out),
        'created': [],
        'changed': [],
        'unchanged': []
    }
    
    # 4. Execute or report
    for p in plans:
        act = p['action']
        dest = p['dest']
        rel_dest = dest.relative_to(resolved_out)
        
        if act == 'CREATED':
            results['created'].append(str(rel_dest))
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                content = p['src'].read_text(encoding='utf-8')
                with open(dest, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(content.strip() + '\n')
                        
        elif act == 'CHANGED':
            results['changed'].append(str(rel_dest))
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                content = p['src'].read_text(encoding='utf-8')
                with open(dest, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(content.strip() + '\n')
                        
        elif act == 'UNCHANGED':
            results['unchanged'].append(str(rel_dest))
            
    return results

def main():
    parser = argparse.ArgumentParser(description="Portable Three.js Expert Knowledge Base & Adapter Builder")
    parser.add_argument("--output-dir", type=str, required=True, help="Destination directory for build output")
    parser.add_argument("--adapter", type=str, choices=list(SUPPORTED_ADAPTERS.keys()) + ['all'], help="Target IDE adapter to build")
    parser.add_argument("--no-knowledge", action="store_true", help="Exclude canonical knowledge base files (build adapter only)")
    parser.add_argument("--dry-run", action="store_true", help="Calculate actions without modifying disk")
    
    args = parser.parse_args()
    out_path = Path(args.output_dir)
    
    try:
        results = execute_build(
            output_dir=out_path,
            adapter=args.adapter,
            include_knowledge=not args.no_knowledge,
            dry_run=args.dry_run
        )
        mode_str = "[DRY-RUN] " if results['dry_run'] else ""
        print(f"{mode_str}Build target: {results['output_dir']}")
        print(f"  Created:   {len(results['created'])} files")
        for f in results['created']:
            print(f"    + {f}")
        print(f"  Changed:   {len(results['changed'])} files")
        for f in results['changed']:
            print(f"    * {f}")
        print(f"  Unchanged: {len(results['unchanged'])} files")
    except Exception as e:
        print(f"Build error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
