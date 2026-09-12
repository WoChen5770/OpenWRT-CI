"""Test nested package extraction without contacting GitHub or touching real feeds."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NestedPackageTests(unittest.TestCase):
    def exercise(self, name='luci-app-bandix', alias='', failure='', missing=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / 'package'
            work.mkdir()
            for rel in ['feeds/luci/applications', 'feeds/packages/net']:
                (root / rel).mkdir(parents=True)
            old = root / 'feeds/luci/applications' / name
            old.mkdir()
            (old / 'Makefile').write_text('old')
            link = work / 'feeds/luci' / name
            link.parent.mkdir(parents=True)
            link.symlink_to(old, target_is_directory=True)
            unrelated = work / (name + '-plus')
            unrelated.mkdir()
            (unrelated / 'Makefile').write_text('keep')
            if alias:
                (work / alias).mkdir()
                (work / alias / 'Makefile').write_text('old backend')
            fixture = root / 'fixture'
            (fixture / name).mkdir(parents=True)
            if not missing:
                (fixture / name / 'Makefile').write_text('new package')
            (fixture / 'README.md').write_text('not a package file')
            bindir = root / 'bin'
            bindir.mkdir()
            git = bindir / 'git'
            git.write_text('''#!/bin/bash
[ -z "$MOCK_FAILURE" ] || exit 1
dest="${!#}"
mkdir -p "$dest"
cp -R "$MOCK_SOURCE/." "$dest/"
''')
            git.chmod(0o755)
            functions = (ROOT / 'Scripts/Packages.sh').read_text().split('# 调用示例')[0]
            command = functions + '\nUPDATE_NESTED_PACKAGE "$1" "timsaya/$1" main "$2"\n'
            result = subprocess.run(['bash', '-c', command, 'test', name, alias],
                                    cwd=work, text=True, capture_output=True,
                                    env=dict(os.environ, PATH=f'{bindir}:' + os.environ['PATH'],
                                             MOCK_SOURCE=str(fixture), MOCK_FAILURE=failure))
            self.assertEqual((unrelated / 'Makefile').read_text(), 'keep')
            if failure or missing:
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((old / 'Makefile').read_text(), 'old')
                self.assertTrue(link.is_symlink())
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((work / name / 'Makefile').read_text(), 'new package')
                self.assertFalse((work / name / name).exists())
                self.assertFalse(old.exists())
                self.assertFalse(link.is_symlink())
                if alias:
                    self.assertFalse((work / alias).exists())

    def test_frontend_same_repo_and_directory_name(self):
        self.exercise()

    def test_backend_alias_removed(self):
        self.exercise('openwrt-bandix', 'bandix')

    def test_failed_clone_preserves_old_package(self):
        self.exercise(failure='yes')

    def test_missing_makefile_preserves_old_package(self):
        self.exercise(missing=True)

    def test_default_selection_and_theme_sources(self):
        settings = (ROOT / 'Scripts/Settings.sh').read_text()
        packages = (ROOT / 'Scripts/Packages.sh').read_text()
        for theme in ['aurora', 'fluent', 'noobwrt']:
            self.assertIn(f'CONFIG_PACKAGE_luci-theme-{theme}=n', settings)
            self.assertNotIn(f'CONFIG_PACKAGE_luci-theme-{theme}=y', settings)
            self.assertIn(f'luci-theme-{theme}', packages)
        general = (ROOT / 'Config/GENERAL.txt').read_text()
        for package in ['luci-app-bandix', 'bandix', 'kmod-sched-core', 'kmod-sched-bpf']:
            self.assertIn(f'CONFIG_PACKAGE_{package}=y', general)


if __name__ == '__main__':
    unittest.main()
