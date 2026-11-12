"""Prepare source-only snapshots; never execute upstream code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).parent
PINS = {'a': '484d60cbf7ca4ec758c3cbb8a82d68b244a78d58',
        'b': '33834cb2a4d035b52aa2a26742f832a112e90a0a'}
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*[\s\S]*?\*/|//[^\n]*')


def strip_comments(text):
    def replace(match):
        value = match.group()
        return ''.join('\n' if c == '\n' else ' ' for c in value) if value.startswith(('/',)) else value
    return TOKEN.sub(replace, text)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prepare(archives):
    manifest = {'repository': 'https://github.com/the-tcpdump-group/libpcap',
                'case': 'CVE-2019-15164', 'snapshots': {}}
    for variant, archive in zip(PINS, archives):
        dest = ROOT / 'fixtures' / variant
        dest.mkdir(parents=True, exist_ok=True)
        files = {}
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                name = '/'.join(Path(member.name).parts[1:])
                if Path(name).suffix not in ('.c', '.h'):
                    continue
                if '..' in Path(name).parts or Path(name).is_absolute():
                    raise ValueError('Invalid archive path')
                text = tar.extractfile(member).read().decode('utf-8')
                clean = strip_comments(text)
                output = dest / name
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(clean)
                files[name] = {'upstream_sha256': sha(text), 'sha256': sha(clean)}
            license_member = next(m for m in tar.getmembers() if m.name.endswith('/LICENSE'))
            (ROOT / 'UPSTREAM-LICENSE.txt').write_bytes(tar.extractfile(license_member).read())
        lines = (dest / 'rpcapd/daemon.c').read_text().splitlines()
        start = next(i for i,l in enumerate(lines) if l.startswith('daemon_msg_open_req(uint8'))
        depth = 0
        entered = False
        for end in range(start, len(lines)):
            depth += lines[end].count('{') - lines[end].count('}')
            entered = entered or '{' in lines[end]
            if entered and depth == 0:
                break
        manifest['snapshots'][variant] = {
            'commit': PINS[variant], 'vulnerable': variant == 'a',
            'archive_sha256': hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
            'files': files, 'focal_path': 'rpcapd/daemon.c',
            'start_line': start, 'end_line': end + 1,
        }
    target = ROOT / 'manifest.json'
    if target.exists() and json.loads(target.read_text()) != manifest:
        raise ValueError('Frozen manifest differs')
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    print({k: (len(v['files']), v['start_line'], v['end_line'])
           for k,v in manifest['snapshots'].items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('before')
    parser.add_argument('after')
    args = parser.parse_args()
    prepare([args.before, args.after])
