import platform
import unittest

import pytest

from conan.test.utils.tools import TestClient


@pytest.mark.skipif(platform.system() not in ("Darwin", "Windows", "Linux"),
                    reason="Not tested for not mainstream boring operating systems")
class TestMesonBase(unittest.TestCase):
    def setUp(self):
        self.t = TestClient()

    def _check_binary(self):
        # Use non-version-specific checks to be robust across CI environments
        host_arch = self.t.get_default_host_profile().settings['arch']
        arch_macro = {
            "gcc": {"armv8": "__aarch64__", "x86_64": "__x86_64__"},
            "msvc": {"armv8": "_M_ARM64", "x86_64": "_M_X64"}
        }
        if platform.system() == "Darwin":
            self.assertIn(f"main {arch_macro['gcc'][host_arch]} defined", self.t.out)
            # check for clang/apple build markers without requiring exact version numbers
            self.assertIn("main __apple_build_version__", self.t.out)
            self.assertIn("main __clang_major__", self.t.out)
        elif platform.system() == "Windows":
            self.assertIn(f"main {arch_macro['msvc'][host_arch]} defined", self.t.out)
            # check presence of MSVC version and language standard macros without exact values
            self.assertIn("main _MSC_VER", self.t.out)
            self.assertIn("main _MSVC_LANG", self.t.out)
        elif platform.system() == "Linux":
            self.assertIn(f"main {arch_macro['gcc'][host_arch]} defined", self.t.out)
            # check for GCC macro without asserting a specific major version
            self.assertIn("main __GNUC__", self.t.out)
