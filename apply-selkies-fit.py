"""Apply/restore the recorded fixed-desktop fit patch without restarting Selkies.

Run with Selkies' Python on the Pod. --web-root targets only an explicit root;
otherwise update packaged assets and existing Selkies temporary web roots.
"""
import argparse
import re
from importlib import resources
from pathlib import Path


def update(root: Path, script: str, restore: bool) -> None:
    index = root / 'index.html'
    original = index.read_text(encoding='utf-8')
    if 'Selkies</title>' not in original:
        raise ValueError(f'Not a Selkies web root: {root}')
    backup = root / 'index.before-fit.html'
    asset = root / 'desktop-fit.js'
    if restore:
        if not backup.exists():
            raise FileNotFoundError(f'No original HTML backup: {backup}')
        index.write_text(backup.read_text(encoding='utf-8'), encoding='utf-8')
        asset.unlink(missing_ok=True)
        print(f'Restored {root}; reload the browser')
        return
    if not backup.exists():
        clean = original
        if 'desktop-fit.js' in clean:
            # The first live patch saved its original here rather than in the package.
            clean = Path('/workspace/config/selkies-index.before-fit.html').read_text(encoding='utf-8')
        if 'desktop-fit.js' in clean:
            raise ValueError(f'Original HTML already contains the patch: {root}')
        backup.write_text(clean, encoding='utf-8')
    if '</body>' not in original:
        raise ValueError(f'No closing body in {index}')
    asset.write_text(script, encoding='utf-8')
    if 'desktop-fit.js' not in original:
        original = original.replace('</body>', '<script src="desktop-fit.js?v=2"></script></body>')
    else:
        original = re.sub(r'desktop-fit\.js(?:\?v=\d+)?', 'desktop-fit.js?v=2', original)
    index.write_text(original, encoding='utf-8')
    print(f'Patched {root}; reload the browser')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web-root', type=Path)
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    script = Path(__file__).with_name('selkies-fit.js').read_text(encoding='utf-8')
    if args.web_root:
        roots = [args.web_root]
    else:
        roots = [Path(str(resources.files('selkies.selkies_web')))]
        roots.extend(p for p in Path('/tmp').glob('selkies_web*')
                     if (p / 'index.html').is_file())
    for root in roots:
        update(root, script, args.restore)


if __name__ == '__main__':
    main()
