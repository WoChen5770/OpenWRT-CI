"""Host-side shell regression tests; no host sysctl/firewall changes are made."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'Scripts/uci-defaults/40-net-tune'


class NetTuneTests(unittest.TestCase):
    def run_script(self, config=None, arch='x86_64', bbr=True, fq=True):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bindir = base / 'bin'
            bindir.mkdir()
            confdir = base / 'sysctl.d'
            confdir.mkdir()
            conf = confdir / '99-openwrt-tune.conf'
            if config is not None:
                conf.write_text(config)
            log = base / 'calls'
            log.touch()
            commands = {
                'uname': 'echo "$TEST_ARCH"',
                # Exercise builtin support too: failed modprobe is not fatal.
                'modprobe': 'exit 1',
                'logger': 'exit 0',
                'uci': 'echo "uci $*" >> "$TEST_LOG"',
                'sysctl': '''echo "sysctl $*" >> "$TEST_LOG"
if [ "$1" = '-n' ]; then
    echo "$TEST_CC"
    exit 0
fi
case "$2" in
    net.core.default_qdisc=fq) [ "$TEST_FQ" = 1 ] || exit 1 ;;
    obsolete.setting=*) exit 1 ;;
esac
exit 0''',
            }
            for name, body in commands.items():
                path = bindir / name
                path.write_text('#!/bin/sh\n' + body + '\n')
                path.chmod(0o755)
            script = base / 'net-tune'
            script.write_text(SCRIPT.read_text().replace('/etc/sysctl.d', str(confdir)))
            env = dict(os.environ, PATH=f'{bindir}:/usr/bin:/bin',
                       TEST_ARCH=arch, TEST_LOG=str(log),
                       TEST_CC='reno cubic bbr' if bbr else 'reno cubic',
                       TEST_FQ='1' if fq else '0')
            result = subprocess.run(['/bin/sh', str(script)], env=env,
                                    text=True, capture_output=True)
            return result, conf.read_text() if conf.exists() else None, log.read_text()

    def test_clean_install_and_builtin_modules(self):
        result, config, calls = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('net.core.default_qdisc=fq', config)
        self.assertIn('sysctl -w net.ipv4.tcp_fastopen=3', calls)
        self.assertIn('uci set firewall.@defaults[0].flow_offloading=1', calls)

    def test_preserved_config_and_repeat_run(self):
        config = '# custom\nnet.ipv4.tcp_congestion_control=bbr\nnet.core.default_qdisc=fq\nnet.ipv4.tcp_fastopen=1'
        for _ in range(2):
            result, saved, calls = self.run_script(config)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(saved, config)
            self.assertIn('sysctl -w net.ipv4.tcp_fastopen=1', calls)

    def test_invalid_old_key_does_not_skip_later_keys(self):
        config = '  # comment\n\nobsolete.setting=1\nnet.ipv4.tcp_fastopen=3\n'
        result, saved, calls = self.run_script(config)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(saved, config)
        self.assertIn('sysctl -w net.ipv4.tcp_fastopen=3', calls)
        self.assertNotIn('sysctl -w # comment', calls)

    def test_missing_fq_is_failure_not_silent_success(self):
        result, config, calls = self.run_script(fq=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('fq unavailable', result.stderr)
        self.assertIsNone(config)
        self.assertNotIn('uci ', calls)

    def test_missing_bbr_is_failure(self):
        result, _, calls = self.run_script(bbr=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('BBR unavailable', result.stderr)
        self.assertNotIn('uci ', calls)

    def test_other_architecture_is_untouched(self):
        result, config, calls = self.run_script(arch='aarch64')
        self.assertEqual(result.returncode, 0)
        self.assertIsNone(config)
        self.assertEqual(calls, '')


if __name__ == '__main__':
    unittest.main()
