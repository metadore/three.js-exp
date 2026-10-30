"""
Central Registry of Canonical Knowledge Files and Multi-IDE Adapters
"""

from pathlib import Path

# Canonical knowledge file manifests
EXPECTED_CORE = [
    'api-version-compatibility.md',
    'engineering-principles.md',
    'framework-detection.md',
    'implementation-patterns.md'
]

EXPECTED_REFERENCES = [
    'accessibility.md',
    'decision-guide.md',
    'disposal-guide.md',
    'framework-nextjs.md',
    'framework-r3f.md',
    'framework-vanilla.md',
    'framework-vite.md',
    'troubleshooting-matrix.md',
    'troubleshooting.md',
    'webgpu-tsl.md'
]

EXPECTED_EXAMPLES = [
    'animation-cleanup.js',
    'basic-vanilla-scene.js',
    'gltf-loader-safe.js',
    'nextjs-client-canvas.tsx',
    'pointer-raycasting.js',
    'postprocessing-webgl.js',
    'production-scene.js',
    'r3f-standard-component.jsx',
    'scroll-animation.js',
    'vite-responsive-scene.js'
]

# Supported Multi-IDE Adapters Registry
# Maps adapter key to:
# - build_files: (src_rel, target_rel) for isolated adapter staging
# - deploy_files: (src_rel, target_rel) for real project-root deployment
ADAPTER_REGISTRY = {
    'antigravity': {
        'name': 'Google Antigravity',
        'description': 'Google Antigravity agent skill (SKILL.md) & knowledge bundle',
        'build_files': [('adapters/antigravity/SKILL.md', 'SKILL.md')],
        'deploy_files': [
            ('adapters/antigravity/SKILL.md', '.agents/skills/threejs-expert/SKILL.md'),
            *[(f'core/{f}', f'.agents/skills/threejs-expert/core/{f}') for f in EXPECTED_CORE],
            *[(f'references/{f}', f'.agents/skills/threejs-expert/references/{f}') for f in EXPECTED_REFERENCES],
            *[(f'examples/{f}', f'.agents/skills/threejs-expert/examples/{f}') for f in EXPECTED_EXAMPLES],
        ]
    },
    'claude-code': {
        'name': 'Claude Code',
        'description': 'Claude Code project instructions (CLAUDE.md) & slash command',
        'build_files': [
            ('adapters/claude-code/CLAUDE.md', 'CLAUDE.md'),
            ('adapters/claude-code/skills/threejs-expert/SKILL.md', '.claude/skills/threejs-expert/SKILL.md')
        ],
        'deploy_files': [
            ('adapters/claude-code/CLAUDE.md', 'CLAUDE.md'),
            ('adapters/claude-code/skills/threejs-expert/SKILL.md', '.claude/skills/threejs-expert/SKILL.md')
        ]
    },
    'cursor': {
        'name': 'Cursor',
        'description': 'Cursor IDE rule (.cursor/rules/threejs-expert.mdc)',
        'build_files': [('adapters/cursor/threejs-expert.mdc', '.cursor/rules/threejs-expert.mdc')],
        'deploy_files': [('adapters/cursor/threejs-expert.mdc', '.cursor/rules/threejs-expert.mdc')]
    },
    'copilot': {
        'name': 'GitHub Copilot',
        'description': 'GitHub Copilot repository instructions (.github/copilot-instructions.md)',
        'build_files': [('adapters/copilot/copilot-instructions.md', '.github/copilot-instructions.md')],
        'deploy_files': [('adapters/copilot/copilot-instructions.md', '.github/copilot-instructions.md')]
    },
    'windsurf': {
        'name': 'Windsurf',
        'description': 'Windsurf Cascade rule (.windsurf/rules/threejs-expert.md)',
        'build_files': [('adapters/windsurf/threejs-expert.md', '.windsurf/rules/threejs-expert.md')],
        'deploy_files': [('adapters/windsurf/threejs-expert.md', '.windsurf/rules/threejs-expert.md')]
    }
}
