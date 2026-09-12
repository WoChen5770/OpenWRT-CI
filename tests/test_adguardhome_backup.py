"""Execute the real package install recipe in a temporary staging directory."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AdGuardHomeBackupTests(unittest.TestCase):
    def test_packaged_keep_list_and_recursive_backup_selection(self):
        text = (ROOT / 'Scripts/Makefiles/luci-app-adguardhome-dashboard.mk').read_text()
        recipe = re.search(
            r'define Package/luci-app-adguardhome-dashboard/install\n(.*?)\nendef',
            text, re.S).group(0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage = root / 'stage'
            for source in re.findall(r'\./([^\s]+)', recipe):
                p = root / source
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('fixture')
            makefile = root / 'Makefile'
            makefile.write_text('INSTALL_DIR:=mkdir -p\nINSTALL_DATA:=cp -f\n' + recipe +
                                '\nall:\n\t$(call Package/luci-app-adguardhome-dashboard/install,' +
                                str(stage) + ')\n')
            subprocess.run(['make', '-f', str(makefile)], cwd=root, check=True,
                           capture_output=True, text=True)
            keep = stage / 'lib/upgrade/keep.d/adguardhome-dashboard'
            self.assertEqual(keep.read_text().splitlines(), [
                '/etc/AdGuardHome/', '/etc/init.d/AdGuardHome',
                '/etc/rc.d/*AdGuardHome', '/etc/adguardhome-dashboard.proxy'])
            self.assertFalse((stage / 'etc/sysupgrade.conf').exists())
            self.assertFalse((stage / 'etc/AdGuardHome').exists())
            # Emulate sysupgrade's static-list find traversal on a fake root.
            paths = ['etc/AdGuardHome/AdGuardHome', 'etc/AdGuardHome/AdGuardHome.yaml',
                     'etc/AdGuardHome/data/filters/1.txt', 'etc/init.d/AdGuardHome',
                     'etc/adguardhome-dashboard.proxy', 'etc/unrelated.conf']
            for rel in paths:
                p = stage / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('data')
            link = stage / 'etc/rc.d/S99AdGuardHome'
            link.parent.mkdir(parents=True)
            link.symlink_to('../init.d/AdGuardHome')
            patterns = [str(stage) + line for line in keep.read_text().splitlines()]
            # Paths originate solely from our fixed package keep-list, not user input.
            result = subprocess.run(['sh', '-c', 'find ' + ' '.join(patterns) +
                                     ' \\( -type f -o -type l \\)'],
                                    check=True, text=True, capture_output=True)
            selected = set(result.stdout.splitlines())
            for rel in paths[:-1]:
                self.assertIn(str(stage / rel), selected)
            self.assertIn(str(link), selected)
            self.assertNotIn(str(stage / 'etc/unrelated.conf'), selected)


if __name__ == '__main__':
    unittest.main()
