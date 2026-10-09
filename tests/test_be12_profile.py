"""Read-only BE12 Pro / BE6500 checks; run with python -B tests/test_be12_profile.py.

These tests exercise CI assertions with synthetic .config values, not OpenWrt's
Kconfig resolver or a firmware build. Bash is required for the shell checks;
OWRT_TEST_BASH can select Git Bash on Windows.
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get("OWRT_TEST_BASH") or shutil.which("bash")
PROFILE = "TENDA-BE12-PRO"
MESH_ONLY_PROFILES = (PROFILE, "XIAOMI-BE6500")
TARGETS = {
    PROFILE: ("mediatek", "filogic"),
    "XIAOMI-BE6500": ("qualcommbe", "ipq53xx"),
    "SUPERGATEWAY-S20P": ("mediatek", "filogic"),
    "X86": ("x86", "64"),
    "IPQ53XX": ("qualcommbe", "ipq53xx"),
}
DEVICES = {
    PROFILE: "tenda_be12-pro",
    "XIAOMI-BE6500": "xiaomi_be6500",
}
BE6500_DRIVERS = (
    "kmod-qcom-ppe", "kmod-ath12k", "ath12k-firmware-ipq5332-ddwrt",
    "ath12k-firmware-qcn9274-ddwrt", "ipq-wifi-xiaomi_be6500",
)
DISABLED = (
    "luci-app-upnp", "miniupnpd", "miniupnpd-nftables", "miniupnpd-iptables",
    "luci-app-wolultra", "luci-app-passwall", "xray-core", "luci-app-daede",
    "daed", "dae", "upx-arm64-static", "owrt-core-update", "luci-app-bandix",
    "bandix", "luci-app-easytier", "easytier",
)
MESH = (
    "PACKAGE_luci-app-mesh", "PACKAGE_kmod-mac80211", "PACKAGE_MAC80211_MESH",
    "PACKAGE_wpad-openssl", "PACKAGE_kmod-batman-adv", "BATMAN_ADV_BLA",
    "PACKAGE_batctl-default", "PACKAGE_luci-proto-batman-adv", "PACKAGE_dawn",
    "PACKAGE_umdns",
)


def profile_config(profile):
    config = {}
    for name in ("GENERAL", profile):
        for line in (ROOT / "Config" / f"{name}.txt").read_text(encoding="utf-8").splitlines():
            if line.startswith("CONFIG_") and "=" in line:
                key, value = line.split("=", 1)
                config[key] = value
    return config


def workflow_blocks(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    name = ""
    for index, line in enumerate(lines):
        match = re.match(r"\s*- name: (.+)", line)
        if match:
            name = match.group(1)
        if not re.fullmatch(r"\s+run: \|", line):
            continue
        indent = len(line) - len(line.lstrip())
        block = []
        for following in lines[index + 1:]:
            if following.strip() and len(following) - len(following.lstrip()) <= indent:
                break
            block.append(following)
        yield name, textwrap.dedent("\n".join(block))


class ProfileConfigTests(unittest.TestCase):
    def test_mesh_enabled_and_extras_disabled(self):
        for profile in MESH_ONLY_PROFILES:
            config = profile_config(profile)
            for option in MESH:
                with self.subTest(profile=profile, option=option):
                    self.assertEqual(config[f"CONFIG_{option}"], "y")
            for package in DISABLED:
                with self.subTest(profile=profile, package=package):
                    self.assertEqual(config[f"CONFIG_PACKAGE_{package}"], "n")
            with self.subTest(profile=profile):
                self.assertEqual(config["CONFIG_PACKAGE_wpad-mesh-openssl"], "n")
                self.assertEqual(config["CONFIG_PACKAGE_luci-app-passwall_INCLUDE_Xray"], "n")
                self.assertEqual(config["CONFIG_PACKAGE_luci-app-autoreboot"], "y")

    def test_single_build_profile(self):
        workflows = {}
        for profile in MESH_ONLY_PROFILES:
            workflow = (ROOT / ".github/workflows" / f"{profile}.yml").read_text(encoding="utf-8")
            with self.subTest(profile=profile):
                self.assertRegex(workflow, rf"(?m)^name: {profile}$")
                self.assertRegex(workflow, rf"(?m)^\s+WRT_CONFIG: {profile}$")
                self.assertIn("uses: ./.github/workflows/WRT-CORE.yml", workflow)
                self.assertIn("workflow_run:", workflow)
                self.assertIn('workflows: ["Auto-Clean"]', workflow)
                self.assertIn("workflow_dispatch:", workflow)
                self.assertIn("PACKAGE:", workflow)
                self.assertNotIn("PROFILE:", workflow)
                self.assertNotIn("matrix", workflow)
                for suffix in ("PASSWALL", "DAED"):
                    self.assertFalse((ROOT / "Config" / f"{profile}-{suffix}.txt").exists())
            workflows[profile] = dict(re.findall(r"(?m)^      (WRT_\w+): (.+)$", workflow))
            workflows[profile].pop("WRT_CONFIG")
        self.assertEqual(workflows[PROFILE], workflows["XIAOMI-BE6500"])

    def test_be6500_preserves_be12_trimming(self):
        reference = profile_config(PROFILE)
        config = profile_config("XIAOMI-BE6500")
        for option, value in reference.items():
            if value == "n":
                with self.subTest(option=option):
                    self.assertEqual(config.get(option), value)

    def test_be6500_platform_and_drivers(self):
        config = profile_config("XIAOMI-BE6500")
        self.assertEqual(config["CONFIG_TARGET_qualcommbe"], "y")
        self.assertEqual(config["CONFIG_TARGET_qualcommbe_ipq53xx"], "y")
        devices = [key for key, value in config.items()
                   if key.startswith("CONFIG_TARGET_DEVICE_") and value == "y"]
        self.assertEqual(devices, ["CONFIG_TARGET_DEVICE_qualcommbe_ipq53xx_DEVICE_xiaomi_be6500"])
        self.assertFalse(any(key.startswith("CONFIG_TARGET_mediatek") for key in config))
        for package in BE6500_DRIVERS:
            with self.subTest(package=package):
                self.assertEqual(config[f"CONFIG_PACKAGE_{package}"], "y")
        for package in ("kmod-usb-dwc3-qcom", "kmod-usb-serial", "kmod-usb-serial-qualcomm"):
            with self.subTest(package=package):
                self.assertEqual(config[f"CONFIG_PACKAGE_{package}"], "n")

    def test_other_devices_keep_default_plugins(self):
        for profile in ("X86", "SUPERGATEWAY-S20P"):
            config = profile_config(profile)
            for package in ("luci-app-upnp", "luci-app-wolultra", "luci-app-passwall", "luci-app-daede", "xray-core"):
                with self.subTest(profile=profile, package=package):
                    self.assertEqual(config[f"CONFIG_PACKAGE_{package}"], "y")


@unittest.skipUnless(BASH, "Bash is required for read-only CI checks")
class ShellChecks(unittest.TestCase):
    def run_bash(self, script, profile=PROFILE, config=None, overrides="", syntax_only=False):
        config = profile_config(profile) if config is None else config
        target, subtarget = TARGETS[profile]
        env = dict(os.environ, GITHUB_WORKSPACE=ROOT.as_posix(), WRT_CONFIG=profile,
                   WRT_TARGET=target, WRT_SUBTARGET=subtarget,
                   WRT_SOURCE="VIKINGYFY/immortalwrt", WRT_BRANCH="owrt",
                   WRT_PACKAGE=overrides,
                   OWRT_TEST_CONFIG="\n".join(f"{key}={value}" for key, value in config.items()))
        args = [BASH, "--noprofile", "--norc", "-n" if syntax_only else "-s"]
        return subprocess.run(args, input=script, text=True, encoding="utf-8",
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=ROOT, env=env, timeout=20)

    def run_guards(self, profile=PROFILE, updates=None, overrides=""):
        config = profile_config(profile)
        config.update(updates or {})
        custom = dict(workflow_blocks(ROOT / ".github/workflows/WRT-CORE.yml"))["Custom Settings"]
        guards = custom.split("make defconfig -j$(nproc)", 1)[1].rsplit("make clean -j$(nproc)", 1)[0]
        # Route only reads of .config to an in-memory fixture. No package setup,
        # make, downloads, file writes, or firmware operations are performed.
        mock_grep = r'''
set -e
grep() {
    local args=("$@")
    local last=$((${#args[@]} - 1))
    if [[ "${args[$last]}" == .config ]]; then
        unset 'args[last]'
        command grep "${args[@]}" <<< "$OWRT_TEST_CONFIG"
    else
        command grep "$@"
    fi
}
'''
        return self.run_bash(mock_grep + guards, profile, config, overrides)

    def test_script_and_workflow_shell_syntax(self):
        scripts = list((ROOT / "Scripts").glob("*.sh"))
        scripts += list((ROOT / "Scripts/uci-defaults").iterdir())
        scripts += [ROOT / "Scripts/Files/core-update/owrt-core-update"]
        for path in scripts:
            with self.subTest(path=path.name):
                result = self.run_bash(path.read_text(encoding="utf-8"), syntax_only=True)
                self.assertEqual(result.returncode, 0, result.stderr)
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            for name, block in workflow_blocks(path):
                with self.subTest(workflow=path.name, step=name):
                    block = re.sub(r"\$\{\{.*?\}\}", "VALUE", block)
                    result = self.run_bash(block, syntax_only=True)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_default_profiles_pass_ci_guards(self):
        for profile in (*MESH_ONLY_PROFILES, "X86", "SUPERGATEWAY-S20P"):
            with self.subTest(profile=profile):
                result = self.run_guards(profile)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_removed_packages_rejected_as_builtin_or_module(self):
        for profile in MESH_ONLY_PROFILES:
            for package in DISABLED:
                for value in ("y", "m"):
                    with self.subTest(profile=profile, package=package, value=value):
                        result = self.run_guards(profile, updates={f"CONFIG_PACKAGE_{package}": value})
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(f"unexpectedly includes {package}", result.stdout)

    def test_mesh_dependencies_and_device_are_required(self):
        for profile in MESH_ONLY_PROFILES:
            target, subtarget = TARGETS[profile]
            device = DEVICES[profile]
            requirements = (*MESH, f"TARGET_{target}", f"TARGET_{target}_{subtarget}",
                            f"TARGET_DEVICE_{target}_{subtarget}_DEVICE_{device}")
            if profile == "XIAOMI-BE6500":
                requirements += tuple(f"PACKAGE_{package}" for package in BE6500_DRIVERS)
            for option in requirements:
                with self.subTest(profile=profile, option=option):
                    result = self.run_guards(profile, updates={f"CONFIG_{option}": "n"})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("missing after defconfig", result.stdout)
            for value in ("y", "m"):
                with self.subTest(profile=profile, conflicting_wpad=value):
                    result = self.run_guards(profile, updates={"CONFIG_PACKAGE_wpad-mesh-openssl": value})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("must not mix", result.stdout)

    def test_manual_overrides_and_independent_choice(self):
        for profile in MESH_ONLY_PROFILES:
            with self.subTest(profile=profile):
                result = self.run_guards(profile, updates={"CONFIG_PACKAGE_luci-app-upnp": "y"},
                                         overrides="CONFIG_PACKAGE_luci-app-upnp=y")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = self.run_guards(profile, updates={"CONFIG_PACKAGE_luci-app-daede_daed": "y"})
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = self.run_guards(profile, updates={"CONFIG_PACKAGE_adguardhome": "y"},
                                         overrides="CONFIG_PACKAGE_adguardhome=y")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("must not include AdGuard Home", result.stdout)

    def test_device_config_overrides_general(self):
        custom = dict(workflow_blocks(ROOT / ".github/workflows/WRT-CORE.yml"))["Custom Settings"]
        merge = custom.split("$GITHUB_WORKSPACE/Scripts/Settings.sh", 1)[0]
        # Exercise the real profile condition and cat order, but send the result
        # to stdout instead of creating a .config or running package setup.
        merge = merge[merge.index("if [["):].replace(">> .config", "")
        for profile in (*MESH_ONLY_PROFILES, "X86", "SUPERGATEWAY-S20P"):
            with self.subTest(profile=profile):
                result = self.run_bash("set -e\n" + merge, profile)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = "".join((ROOT / "Config" / f"{name}.txt").read_text(encoding="utf-8")
                                   for name in ("GENERAL", profile))
                self.assertEqual(result.stdout, expected)

    def test_target_and_cache_initialization(self):
        initialize = dict(workflow_blocks(ROOT / ".github/workflows/WRT-CORE.yml"))["Initialization Values"]
        # Stop before the environment/output-file writes; inspect only values.
        initialize = initialize.split("\n{\n", 1)[0]
        initialize += '\nprintf "%s|%s|%s" "$WRT_TARGET" "$WRT_SUBTARGET" "$WRT_CACHE_PREFIX"\n'
        for profile in TARGETS:
            with self.subTest(profile=profile):
                target, subtarget = TARGETS[profile]
                prefix = f"wrt-VIKINGYFY-immortalwrt-owrt-{target}-{subtarget}"
                if profile in (*MESH_ONLY_PROFILES, "SUPERGATEWAY-S20P"):
                    prefix += f"-{profile}"
                result = self.run_bash("set -e\n" + initialize, profile)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f"{target}|{subtarget}|{prefix}")

    def test_mesh_and_xray_target_gates(self):
        for name, selected in (("Mesh", {*MESH_ONLY_PROFILES, "SUPERGATEWAY-S20P"}),
                               ("Xray", {"X86", "SUPERGATEWAY-S20P"})):
            source = (ROOT / "Scripts" / f"{name}.sh").read_text(encoding="utf-8")
            gate = source[:source.index("\nesac") + len("\nesac")]
            for profile in TARGETS:
                with self.subTest(script=name, profile=profile):
                    result = self.run_bash(gate + "\nprintf selected\n", profile)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, "selected" if profile in selected else "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
