"""Test target scoping, duplicate cleanup, and the actual prebuilt package recipe."""
import os
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'Scripts/Makefiles/xray-core-prebuilt.mk'

SPEC = importlib.util.spec_from_file_location('resolve_xray', ROOT / 'Scripts/resolve_xray.py')
RESOLVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESOLVER)


def release(version='99.1.2', published='2026-09-10T00:00:00Z', prerelease=True):
    return {'tag_name': 'v' + version, 'published_at': published,
            'draft': False, 'prerelease': prerelease,
            'assets': [{'name': 'Xray-linux-64.zip', 'state': 'uploaded',
                        'digest': 'sha256:' + 'a' * 64,
                        'browser_download_url': 'https://github.com/XTLS/Xray-core/releases/download/v' +
                        version + '/Xray-linux-64.zip'}]}


class XrayPrebuiltTests(unittest.TestCase):
    def test_x86_replacement_is_repeatable_and_preserves_other_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / 'package'
            work.mkdir()
            (root / 'feeds/luci').mkdir(parents=True)
            old = root / 'feeds/packages/net/xray-core'
            old.mkdir(parents=True)
            (old / 'Makefile').write_text('old')
            link = work / 'feeds/packages/xray-core'
            link.parent.mkdir(parents=True)
            link.symlink_to(old, target_is_directory=True)
            other = work / 'xray-plugin'
            other.mkdir()
            (other / 'Makefile').write_text('keep')
            metadata = root / 'releases.json'
            bindir = root / 'bin'
            bindir.mkdir()
            curl = bindir / 'curl'
            curl.write_text('#!/bin/sh\ncat "$MOCK_RELEASES"\n')
            curl.chmod(0o755)
            env = dict(os.environ, GITHUB_WORKSPACE=str(ROOT), WRT_TARGET='x86', WRT_SUBTARGET='64',
                       PATH=str(bindir) + ':' + os.environ['PATH'], MOCK_RELEASES=str(metadata))
            for version in ['99.1.2', '99.1.3']:
                data = [release(version)]
                metadata.write_text(json.dumps(data))
                subprocess.run(['bash', str(ROOT / 'Scripts/Xray.sh')], cwd=work,
                               env=env, check=True, capture_output=True, text=True)
                self.assertEqual((work / 'xray-core/Makefile').read_text(),
                                 RESOLVER.render(data, TEMPLATE.read_text())[0])
                self.assertFalse(old.exists())
                self.assertFalse(link.is_symlink())
                self.assertEqual((other / 'Makefile').read_text(), 'keep')
            # A bad response on the next build must not delete the last valid recipe.
            saved = (work / 'xray-core/Makefile').read_text()
            metadata.write_text('{"message":"API rate limit exceeded"}')
            result = subprocess.run(['bash', str(ROOT / 'Scripts/Xray.sh')], cwd=work,
                                    env=env, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((work / 'xray-core/Makefile').read_text(), saved)

    def test_other_targets_are_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'xray-core'
            p.mkdir()
            (p / 'Makefile').write_text('original')
            for target, subtarget in [('x86', 'generic'), ('mediatek', 'filogic'), ('', '')]:
                subprocess.run(['bash', str(ROOT / 'Scripts/Xray.sh')], cwd=tmp, check=True,
                               env=dict(os.environ, WRT_TARGET=target, WRT_SUBTARGET=subtarget))
            self.assertEqual((p / 'Makefile').read_text(), 'original')

    def test_wrong_working_directory_fails_before_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(['bash', str(ROOT / 'Scripts/Xray.sh')], cwd=tmp,
                               env=dict(os.environ, GITHUB_WORKSPACE=str(ROOT),
                                        WRT_TARGET='x86', WRT_SUBTARGET='64'), capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_prepare_and_install_keep_binary_path_without_overwriting_geodata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'rules.mk').touch()
            (root / 'package.mk').touch()
            dl = root / 'dl'
            dl.mkdir()
            with zipfile.ZipFile(dl / 'Xray-linux-64-99.1.2.zip', 'w') as z:
                z.writestr('xray', b'fixture binary')
                z.writestr('LICENSE', b'fixture license')
                z.writestr('geoip.dat', b'not installed')
                z.writestr('geosite.dat', b'not installed')
            resolved = root / 'resolved.mk'
            resolved.write_text(RESOLVER.render([release()], TEMPLATE.read_text())[0])
            makefile = root / 'test.mk'
            makefile.write_text(f'''TOPDIR:={root}
INCLUDE_DIR:={root}
DL_DIR:={dl}
PKG_BUILD_DIR:={root}/build
INSTALL_DIR:=mkdir -p
INSTALL_BIN:=install -m 0755
include {resolved}
prepare:
\t$(Build/Prepare)
install: prepare
\t$(call Package/xray-core/install,{root}/stage)
''')
            subprocess.run(['make', '-f', str(makefile), 'install'], check=True,
                           capture_output=True, text=True)
            binary = root / 'stage/usr/bin/xray'
            self.assertEqual(binary.read_bytes(), b'fixture binary')
            self.assertTrue(os.access(binary, os.X_OK))
            self.assertFalse((root / 'build/geoip.dat').exists())
            self.assertEqual([p for p in (root / 'stage').rglob('*') if p.is_file()], [binary])
            self.assertIn('DEPENDS:=@x86_64 +ca-bundle', TEMPLATE.read_text())
            self.assertIn('PKG_SOURCE_URL_FILE:=Xray-linux-64.zip', TEMPLATE.read_text())


class XrayReleaseResolutionTests(unittest.TestCase):
    def test_latest_published_includes_prereleases_and_ignores_drafts(self):
        stable = release('98.1.1', '2026-08-01T00:00:00Z', False)
        newest = release()
        draft = release('100.0.0', '2026-09-12T00:00:00Z')
        draft['draft'] = True
        rendered, chosen = RESOLVER.render([stable, draft, newest], TEMPLATE.read_text())
        self.assertEqual(chosen['tag_name'], 'v99.1.2')
        self.assertIn('PKG_VERSION:=99.1.2', rendered)
        self.assertIn('PKG_HASH:=' + 'a' * 64, rendered)
        self.assertNotIn('@XRAY_', rendered)

    def test_missing_latest_asset_does_not_fall_back_to_older_release(self):
        newest = release()
        newest['assets'] = []
        with self.assertRaisesRegex(ValueError, 'missing or not ready'):
            RESOLVER.render([newest, release('98.1.1', '2026-08-01T00:00:00Z')], TEMPLATE.read_text())

    def test_missing_or_invalid_digest_is_rejected(self):
        for digest in [None, '', 'sha256:skip', 'md5:' + 'a' * 32]:
            data = release()
            data['assets'][0]['digest'] = digest
            with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, 'SHA256'):
                RESOLVER.render([data], TEMPLATE.read_text())

    def test_unexpected_url_or_tag_is_rejected(self):
        data = release()
        data['assets'][0]['browser_download_url'] = 'https://example.com/xray.zip'
        with self.assertRaisesRegex(ValueError, 'download URL'):
            RESOLVER.render([data], TEMPLATE.read_text())
        data = release()
        data['tag_name'] = 'v99.1.2; shell-injection'
        with self.assertRaisesRegex(ValueError, 'release tag'):
            RESOLVER.render([data], TEMPLATE.read_text())

    def test_empty_list_and_api_error_are_rejected(self):
        for data in [[], {'message': 'rate limited'}, [{'draft': True}]]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                RESOLVER.render(data, TEMPLATE.read_text())

    def test_template_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            RESOLVER.render([release()], TEMPLATE.read_text().replace('@XRAY_SHA256@', 'skip'))


if __name__ == '__main__':
    unittest.main()
