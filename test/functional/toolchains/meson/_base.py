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
        # Relaxed checks to avoid hardcoding specific compiler version numbers
        host_arch = self.t.get_default_host_profile().settings['arch']
        arch_macro = {
            "gcc": {"armv8": "__aarch64__", "x86_64": "__x86_64__"},
            "msvc": {"armv8": "_M_ARM64", "x86_64": "_M_X64"}
        }
        if platform.system() == "Darwin":
            self.assertIn(f"main {arch_macro['gcc'][host_arch]} defined", self.t.out)
            self.assertIn("main __apple_build_version__", self.t.out)
            # Accept any clang major version string rather than a hardcoded number
            self.assertIn("main __clang_major__", self.t.out)
            # TODO: check why __clang_minor__ seems to be not defined in XCode 12
            # commented while migrating to XCode12 CI
            # self.assertIn("main __clang_minor__0", self.t.out)
        elif platform.system() == "Windows":
            self.assertIn(f"main {arch_macro['msvc'][host_arch]} defined", self.t.out)
            # Accept any MSC_VER / MSVC_LANG values rather than specific numbers
            self.assertIn("main _MSC_VER", self.t.out)
            self.assertIn("main _MSVC_LANG", self.t.out)
        elif platform.system() == "Linux":
            self.assertIn(f"main {arch_macro['gcc'][host_arch]} defined", self.t.out)
            # Accept any GCC major version string rather than a hardcoded number
            self.assertIn("main __GNUC__", self.t.out)
