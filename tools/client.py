"""Build a clean client game directory; never starts a launcher or game UI."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import shutil
import sys
import urllib.request
import zipfile

if sys.version_info < (3, 10):
    sys.exit('Python 3.10+ required; on Windows use py -3.12.')
ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'game'
CACHE = ROOT / '.runtime'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def safe(base, name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError('Unsafe path: ' + name)
    result = base.joinpath(*path.parts)
    if not result.resolve().is_relative_to(base.resolve()):
        raise ValueError('Path escapes destination: ' + name)
    return result


def validate_text_manifest(lock):
    pack_root = ROOT / 'pack'
    actual = {
        path.relative_to(pack_root).as_posix()
        for path in pack_root.rglob('*')
        if path.is_file()
    }
    listed = set(lock['textFiles'])
    unlisted = sorted(actual - listed)
    missing = sorted(listed - actual)
    if unlisted or missing:
        details = []
        if unlisted:
            details.append('Pack files missing from runtime-lock textFiles:\n' + '\n'.join(unlisted[:30]))
        if missing:
            details.append('runtime-lock textFiles missing from pack/:\n' + '\n'.join(missing[:30]))
        raise RuntimeError('\n'.join(details))


def download(record, target):
    if target.exists() and sha(target) == record['sha256']:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.partial')
    print('Downloading ' + record['url'], flush=True)
    req = urllib.request.Request(record['url'], headers={'User-Agent': 'muxigame-bmc5-client/1'})
    with urllib.request.urlopen(req, timeout=120) as response, partial.open('wb') as stream:
        shutil.copyfileobj(response, stream, 1024 * 1024)
    if sha(partial) != record['sha256']:
        raise RuntimeError('Checksum mismatch: ' + target.name)
    partial.replace(target)
    return target


def overlays(created):
    # Apply existing pack policy to newly seeded files only. Preserve local edits on rerun.
    policy = json.loads((ROOT / 'pack-policy.json').read_text(encoding='utf-8'))
    for rule in policy['overlays']:
        path = safe(GAME, rule['path'])
        if rule['path'] not in created:
            if not path.exists() and rule.get('createIfMissing'):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{}' if rule['format'] == 'Json' else '', encoding='utf-8')
            else:
                continue
        settings = {**rule.get('seedKeys', {}), **rule.get('enforce', {})}
        if rule['format'] == 'Json':
            obj = json.loads(path.read_text(encoding='utf-8-sig'))
            for key, value in settings.items():
                parts = key.split('/')
                current = obj
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = value
            path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        elif rule['format'] == 'Properties':
            sep = ':' if rule['path'] == 'options.txt' else '='
            lines = path.read_text(encoding='utf-8-sig').splitlines()
            for key, value in settings.items():
                rendered = str(value).lower() if isinstance(value, bool) else str(value)
                lines = [line for line in lines if not line.startswith(key + sep)]
                lines.append(key + sep + rendered)
            for key, values in rule.get('removeFromList', {}).items():
                for index, line in enumerate(lines):
                    if line.startswith(key + sep):
                        items = json.loads(line.split(sep, 1)[1])
                        lines[index] = key + sep + json.dumps([v for v in items if v not in values])
            path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        elif rule['format'] == 'Toml':
            lines = path.read_text(encoding='utf-8-sig').splitlines()
            for key, value in settings.items():
                parts = key.split('/')
                section = '.'.join(parts[:-1])
                keyname = parts[-1]
                current = ''; start = 0; end = len(lines); found_section = not section; found = False
                for i, line in enumerate(lines):
                    match = re.match(r'^\s*\[([^\[\]]+)\]\s*$', line)
                    if match:
                        if current == section:
                            end = i
                        current = match[1].replace('"', '')
                        if current == section:
                            start = i + 1; end = len(lines); found_section = True
                    if current == section and re.match(r'^\s*[\"\x27]?' + re.escape(keyname) + r'[\"\x27]?\s*=', line):
                        lines[i] = json.dumps(keyname) + ' = ' + json.dumps(value, ensure_ascii=False)
                        found = True
                        break
                if not found:
                    rendered = json.dumps(keyname) + ' = ' + json.dumps(value, ensure_ascii=False)
                    if found_section:
                        lines.insert(end, rendered)
                    else:
                        lines.extend(['', '[' + section + ']', rendered])
            path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def verify(lock):
    issues = []
    for record in lock['files'] + lock['external']:
        p = safe(GAME, record['path'])
        if not p.is_file() or p.stat().st_size != record['size'] or sha(p) != record['sha256']:
            issues.append(record['path'])
    for name in lock['textFiles']:
        if not safe(GAME, name).is_file():
            issues.append(name)
    if issues:
        raise RuntimeError('Missing/modified assets:\n' + '\n'.join(issues[:30]))
    print('Verified %d binary assets and %d text files.' % (len(lock['files']) + len(lock['external']), len(lock['textFiles'])), flush=True)


def setup(args, lock):
    bundle = Path(args.bundle).resolve() if args.bundle else CACHE / 'client-assets.zip'
    if args.bundle:
        if sha(bundle) != lock['bundle']['sha256']:
            raise RuntimeError('Local bundle checksum mismatch')
    else:
        download(lock['bundle'], bundle)
    expected = {r['path']: r for r in lock['files']}
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise RuntimeError('Bundle entries differ from manifest')
        for name in names:
            dest = safe(GAME, name)
            if dest.exists():
                if sha(dest) != expected[name]['sha256']:
                    raise RuntimeError('Refusing to overwrite modified binary: ' + name)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, dest.open('xb') as target:
                shutil.copyfileobj(source, target)
    for record in lock['external']:
        dest = safe(GAME, record['path'])
        if dest.exists() and sha(dest) != record['sha256']:
            raise RuntimeError('Refusing to overwrite modified binary: ' + record['path'])
        download(record, dest)
    created = set()
    for name in lock['textFiles']:
        dest = safe(GAME, name)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(safe(ROOT / 'pack', name), dest)
            created.add(name)
    if not (GAME / 'options.txt').exists():
        shutil.copyfile(ROOT / 'defaults/options.txt', GAME / 'options.txt')
        created.add('options.txt')
    overlays(created)
    verify(lock)
    print('Ready: ' + str(GAME), flush=True)
    print('Use a launcher with Minecraft 1.21.1 + NeoForge 21.1.250 + Java 21+, pointing at this game directory.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'verify'])
    parser.add_argument('--bundle', help='Optional checksum-matching local client-assets.zip')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'runtime-lock.json').read_text(encoding='utf-8'))
    validate_text_manifest(lock)
    setup(args, lock) if args.action == 'setup' else verify(lock)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
