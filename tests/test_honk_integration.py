"""Test Honk.sh in temporary trees; no firmware build or router service is run.

Git is mocked by default. OWRT_TEST_HONK_LIVE=1 additionally fetches the pinned
upstream source for an integration smoke test. OWRT_TEST_BASH selects Git Bash.
"""

import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get("OWRT_TEST_BASH") or shutil.which("bash")
SCRIPT = (ROOT / "Scripts/Honk.sh").read_text(encoding="utf-8")
REF = re.search(r'^HONK_REF="([0-9a-f]{40})"$', SCRIPT, re.M).group(1)
FAKE_GIT = r'''
git() {
    if [[ "$1" == init ]]; then
        mkdir -p "${@: -1}"
    elif [[ "$1" == -C && "$3" == remote ]]; then
        return 0
    elif [[ "$1" == -C && "$3" == fetch ]]; then
        [[ "${OWRT_TEST_FETCH_FAIL:-0}" == 0 ]] || return 1
        cp -R "$OWRT_TEST_SOURCE/." "$2/"
    elif [[ "$1" == -C && "$3" == checkout ]]; then
        return 0
    elif [[ "$1" == -C && "$3" == rev-parse ]]; then
        printf '%s\n' "$OWRT_TEST_REF"
    else
        echo "Unexpected git command" >&2
        return 1
    fi
}
'''


@unittest.skipUnless(BASH, "Bash is required")
class HonkIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="owrt-honk-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = self.root / "wrt"
        self.source = self.root / "source"
        for directory in ("package", "feeds/luci", "feeds/packages"):
            (self.tree / directory).mkdir(parents=True)
        files = {
            "honk/Makefile": "PKG_NAME:=honk\nPKG_HASH:=fixture\ndefine Build/Compile\n\ttrue\nendef\n",
            "honk/files/honk.config": "config honk 'config'\n\toption enabled '0'\n",
            "honk/files/honk.init": "#!/bin/sh /etc/rc.common\n",
            "honk/files/config.d/api.dae": "# native_api {\n# enabled: false\n# }\n",
            "luci-app-honk/Makefile": "PKG_NAME:=luci-app-honk\nLUCI_DEPENDS:=+honk\n",
            "luci-app-honk/po/zh_Hans/honk.po": 'msgid "HONK"\nmsgstr "HONK"\n',
        }
        for name, content in files.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        self.preserved = {}
        for name in ("package/dae", "package/daed", "package/luci-app-daede",
                     "package/luci-app-passwall", "package/honk-helper",
                     "package/luci-app-honk-extra", "package/adguardhome"):
            marker = self.tree / name / "keep.txt"
            marker.parent.mkdir(parents=True)
            marker.write_text(name, encoding="utf-8")
            self.preserved[marker] = marker.read_bytes()
        self.stale = self.tree / "feeds/packages/honk/stale.txt"
        self.stale.parent.mkdir(parents=True)
        self.stale.write_text("old package", encoding="utf-8")

    def run_script(self, profile="SUPERGATEWAY-S20P", live=False, **overrides):
        env = dict(os.environ, WRT_CONFIG=profile, OWRT_TEST_SOURCE=self.source.as_posix(),
                   OWRT_TEST_REF=REF)
        env.update(overrides)
        return subprocess.run(
            [BASH, "--noprofile", "--norc", "-s"],
            input=("" if live else FAKE_GIT) + SCRIPT, text=True, encoding="utf-8",
            cwd=self.tree, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=90 if live else 20,
        )

    def assert_preserved(self):
        for path, content in self.preserved.items():
            self.assertEqual(path.read_bytes(), content)

    def test_replaces_only_exact_honk_packages_and_preserves_defaults(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.stale.exists())
        self.assert_preserved()
        for path in self.source.rglob("*"):
            if path.is_file():
                self.assertEqual((self.tree / "package" / path.relative_to(self.source)).read_bytes(),
                                 path.read_bytes())

    def test_source_failure_does_not_remove_existing_packages(self):
        for env in ({"OWRT_TEST_FETCH_FAIL": "1"}, {"OWRT_TEST_REF": "0" * 40}):
            with self.subTest(env=env):
                result = self.run_script(**env)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(self.stale.exists())
                self.assertFalse((self.tree / "package/honk").exists())
                self.assert_preserved()

    def test_incomplete_source_is_rejected_before_replacement(self):
        (self.source / "luci-app-honk/Makefile").unlink()
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.stale.exists())
        self.assert_preserved()

    def test_enabled_service_or_api_defaults_are_rejected(self):
        config = self.source / "honk/files/honk.config"
        config.write_text("option enabled '1'\n", encoding="utf-8", newline="\n")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.stale.exists())
        config.write_text("option enabled '0'\n", encoding="utf-8", newline="\n")
        (self.source / "honk/files/config.d/api.dae").write_text(
            "native_api {\n enabled: true\n}\n", encoding="utf-8", newline="\n")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must remain disabled", result.stderr)
        self.assertTrue(self.stale.exists())
        self.assert_preserved()

    def test_other_devices_do_not_fetch_or_modify_packages(self):
        for profile in ("X86", "TENDA-BE12-PRO", "XIAOMI-BE6500", ""):
            with self.subTest(profile=profile):
                result = self.run_script(profile, OWRT_TEST_FETCH_FAIL="1")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(self.stale.exists())
                self.assertFalse((self.tree / "package/honk").exists())
                self.assert_preserved()

    @unittest.skipUnless(os.environ.get("OWRT_TEST_HONK_LIVE") == "1", "opt-in upstream fetch")
    def test_pinned_upstream_packages_can_be_integrated(self):
        result = self.run_script(live=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_preserved()
        core = (self.tree / "package/honk/Makefile").read_text(encoding="utf-8")
        self.assertIn("PKG_VERSION:=2026.10.9_beta2", core)
        self.assertIn("PKG_HASH:=$(HONK_HASH)", core)
        self.assertRegex(core, r"(?m)^HONK_HASH_AARCH64:=[0-9a-f]{64}$")
        self.assertRegex(core, r"define Build/Compile\s+true\s+endef")
        self.assertNotIn("rust/host", core)
        self.assertNotIn("cargo build", core)
        luci = (self.tree / "package/luci-app-honk/Makefile").read_text(encoding="utf-8")
        self.assertIn("LUCI_DEPENDS:=+honk", luci)
        self.assertTrue((self.tree / "package/luci-app-honk/po/zh_Hans/honk.po").is_file())

        # Download and inspect, never execute or extract the third-party binary.
        tag = re.search(r"(?m)^FORK_RELEASE_TAG:=(\S+)$", core).group(1)
        digest = re.search(r"(?m)^HONK_HASH_AARCH64:=([0-9a-f]{64})$", core).group(1)
        url = (f"https://github.com/Glassyiris/honk/releases/download/{tag}/"
               "honk-core-debug-aarch64-unknown-linux-musl.tar.gz")
        with urllib.request.urlopen(url, timeout=60) as response:
            archive = response.read()
        self.assertEqual(hashlib.sha256(archive).hexdigest(), digest)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
            members = {member.name.split("/", 1)[-1]: member for member in package.getmembers()
                       if member.isfile()}
            for name in ("honk-core", "LICENSE", "doona/LICENSE", "doona/NOTICE",
                         "doona/THIRD-PARTY-NOTICES.txt"):
                self.assertIn(name, members)
            self.assertTrue(any(name.startswith("doona/LICENSES/") for name in members))
            binary = package.extractfile(members["honk-core"])
            with binary:
                header = binary.read(20)
            self.assertEqual(header[:6], b"\x7fELF\x02\x01")  # ELF64, little-endian
            self.assertEqual(int.from_bytes(header[18:20], "little"), 183)  # AArch64


if __name__ == "__main__":
    unittest.main(verbosity=2)
