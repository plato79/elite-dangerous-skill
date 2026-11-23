"""Smoke-test copying the complete skill into common local layouts."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills' / 'elite-dangerous'
REQUIRED = ('SKILL.md', 'LICENSE', 'references/inara-coriolis.md',
            'scripts/inara_profile.py', 'scripts/coriolis_api.py',
            'scripts/coriolis_link.py', 'scripts/test_helpers.py')

with tempfile.TemporaryDirectory() as temp:
    for home in ('.agents', '.claude'):
        target = Path(temp) / home / 'skills' / 'elite-dangerous'
        target.parent.mkdir(parents=True)
        shutil.copytree(SOURCE, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for relative in REQUIRED:
            assert (target / relative).is_file(), f'Missing {relative} in {home}'
        subprocess.run([sys.executable, str(target / 'scripts' / 'test_helpers.py')], check=True)
        print(f'{home} skill directory copy: OK', flush=True)
print('Note: file-copy tests do not exercise discovery by the agent applications.')
