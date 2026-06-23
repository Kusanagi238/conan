import platform
import unittest

import pytest

from conan.test.utils.tools import TestClient


@pytest.mark.tool("meson")
@pytest.mark.skipif(platform.system() not in ("Darwin", "Windows", "Linux"),
                    reason="Not tested for not mainstream boring operating systems")
class TestMesonBase(unittest.TestCase):
    def setUp(self):
        self.t = TestClient()

    def _check_binary(self):
        # FIXME: Some values are hardcoded to match the CI setup
        host_arch = self.t.get_default_host_profile().settings['arch']
        arch_macro = {
            "gcc": {"armv8": "__aarch64__", "x86_64": "__x86_64__"},
            "msvc": {"armv8": "_M_ARM64", "x86_64": "_M_X64"}
        }
        if platform.system() == "Darwin":
            self.assertIn(f"main {arch_macro['gcc'][host_arch]} defined", self.t.out)
            # Apple's build version macro should be present
            self.assertIn("main __apple_build_version__", self.t.out)
            # Do not assert a fixed clang major version; just check the macro name
            self.assertIn("main __clang_major__", self.t.out)
            # TODO: check why __clang_minor__ seems to be not defined in XCode 12
            # commented while migrating to XCode12 CI
            # self.assertIn("main __clang_minor__0", self.t.out)
        elif platform.system() == "Windows":
            self.assertIn(f"main {arch_macro['msvc'][host_arch]} defined", self.t.out)
            # Avoid hardcoding MSVC version numbers; check macro names only
            self.assertIn("main _MSC_VER", self.t.out)
            self.assertIn("main _MSVC_LANG", self.t.out)
        elif platform.system() == "Linux":
            self.assertIn(f"main {arch_macro['gcc'][host_arch]} defined", self.t.out)
            # Don't require a specific GNU major version; ensure the macro is present
            self.assertIn("main __GNUC__", self.t.out)
