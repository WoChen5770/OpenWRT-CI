#!/usr/bin/env python3
"""Offline updater smoke tests: release selection, digest guard, staged replacement."""
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import tarfile
import tempfile
import zipfile

SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'Scripts/Files/core-update/owrt-core-update'


def write_exe(path, text):
    path.write_text(text)
    path.chmod(0o755)


def run_case(kind, mismatch=False):
    with tempfile.TemporaryDirectory(prefix='core-updater-test-') as td:
        root = pathlib.Path(td)
        bindir = root / 'bin'
        bindir.mkdir()
        target = root / ('xray' if kind == 'xray' else 'AdGuardHome')
        service = root / 'service'
        write_exe(service, '#!/bin/sh\nexit 0\n')
        write_exe(target, '#!/bin/sh\necho old-version\n')
        old_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        new_bin = b'#!/bin/sh\necho new-version\n'
        if kind == 'xray':
            archive = root / 'archive.zip'
            with zipfile.ZipFile(archive, 'w') as zf:
                zf.writestr('xray', new_bin)
            asset = 'Xray-linux-arm64-v8a.zip'
            repo = 'XTLS/Xray-core'
        else:
            archive = root / 'archive.tar.gz'
            with tarfile.open(archive, 'w:gz') as tf:
                info = tarfile.TarInfo('AdGuardHome/AdGuardHome')
                info.mode = 0o755
                info.size = len(new_bin)
                tf.addfile(info, io.BytesIO(new_bin))
            asset = 'AdGuardHome_linux_arm64.tar.gz'
            repo = 'AdguardTeam/AdGuardHome'
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if mismatch:
            digest = '0' * 64
        release = dict(tag_name='v9.0.0', published_at='2026-09-27T00:00:00Z',
                       draft=False, assets=[dict(name=asset, digest='sha256:' + digest,
                       browser_download_url=f'https://github.com/{repo}/releases/download/v9.0.0/{asset}')])
        releases = [dict(tag_name='v8.0.0', published_at='2026-09-26T00:00:00Z', draft=False,
                         assets=[]), release] if kind == 'xray' else release
        (root / 'meta.json').write_text(json.dumps(releases))
        updater = root / 'updater'
        script = SOURCE.read_text().replace('/usr/bin/xray', str(target)).replace(
            '/etc/AdGuardHome/AdGuardHome', str(target)).replace(
            '/etc/init.d/passwall', str(service)).replace('/etc/init.d/AdGuardHome', str(service))
        write_exe(updater, script)
        write_exe(bindir / 'curl', '''#!/bin/sh
for arg do
    case "$arg" in
        https://api.github.com/*) src="$TEST_META" ;;
        https://github.com/*) src="$TEST_ARCHIVE" ;;
    esac
done
while [ "$1" != "-o" ]; do shift; done
cp "$src" "$2"
''')
        write_exe(bindir / 'jsonfilter', '''#!/usr/bin/env python3
import json, re, sys
f = sys.argv[sys.argv.index('-i') + 1]
e = sys.argv[sys.argv.index('-e') + 1]
val = json.load(open(f))
for bit in re.findall(r'\\[(\\d+)\\]|\\.([a-zA-Z_]+)', e):
    val = val[int(bit[0])] if bit[0] else val[bit[1]]
if val is not None: print(str(val).lower() if isinstance(val, bool) else val)
''')
        write_exe(bindir / 'upx', '''#!/bin/sh
if [ "$1" = -t ]; then exit 0; fi
while [ "$1" != "-o" ]; do shift; done
cp "$3" "$2"
''')
        write_exe(bindir / 'uname', '#!/bin/sh\necho aarch64\n')
        write_exe(bindir / 'pidof', '#!/bin/sh\nexit 1\n')
        env = dict(os.environ, PATH=f'{bindir}:{os.environ["PATH"]}',
                   TEST_META=str(root / 'meta.json'), TEST_ARCHIVE=str(archive))
        result = subprocess.run(['/bin/sh', str(updater), kind], env=env,
                                text=True, capture_output=True)
        if mismatch:
            assert result.returncode != 0, result.stdout
            assert 'SHA256 mismatch' in result.stderr, result.stderr
            assert hashlib.sha256(target.read_bytes()).hexdigest() == old_hash
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            assert target.read_bytes() == new_bin
            assert 'v9.0.0' in result.stdout
        assert not pathlib.Path(str(target) + '.core-update-new').exists()


if __name__ == '__main__':
    for name in ('xray', 'adguardhome'):
        run_case(name)
        run_case(name, mismatch=True)
    print('Manual core updater offline smoke tests: OK')
