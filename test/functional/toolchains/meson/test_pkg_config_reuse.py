import os

import pytest
import textwrap

from conan.test.assets.sources import gen_function_cpp
from test.functional.toolchains.meson._base import TestMesonBase


@pytest.mark.tool("pkg_config")
class MesonPkgConfigTest(TestMesonBase):
    _conanfile_py = textwrap.dedent("""
    from conan import ConanFile
    from conan.tools.meson import Meson, MesonToolchain


    class App(ConanFile):
        settings = "os", "arch", "compiler", "build_type"
        generators = "PkgConfigDeps"
        requires = "hello/0.1"

        def layout(self):
            self.folders.build = "build"

        def generate(self):
            tc = MesonToolchain(self)
            tc.generate()

        def build(self):
            meson = Meson(self)
            meson.configure()
            meson.build()
    """)

    _meson_build = textwrap.dedent("""
    project('tutorial', 'cpp')
    hello = dependency('hello', version : '>=0.1')
    executable('demo', 'main.cpp', dependencies: hello)
    """)

    def test_reuse(self):
        # Create a minimal header-only 'hello/0.1' package to avoid relying on external cmake tool in CI.
        hello_conanfile = (
            "from conan import ConanFile\n\n"
            "class HelloConan(ConanFile):\n"
            "    name = \"hello\"\n"
            "    version = \"0.1\"\n"
            "    exports_sources = \"hello.h\"\n\n"
            "    def package(self):\n"
            "        self.copy(\"*.h\", dst=\"include\")\n\n"
            "    def package_info(self):\n"
            "        self.cpp_info.includedirs = [\"include\"]\n"
        )
        hello_header = (
            "#pragma once\n"
            "#include <iostream>\n"
            "inline void hello() { std::cout << \"Hello World Release!\"; }\n"
        )
        # Save and create the header-only package in the local cache
        self.t.save({"conanfile.py": hello_conanfile, "hello.h": hello_header}, clean_first=True)
        self.t.run("create .")

        app = gen_function_cpp(name="main", includes=["hello"], calls=["hello"])
        # Prepare the actual consumer package (this will overwrite the temporary recipe but the package is in cache)
        self.t.save({"conanfile.py": self._conanfile_py,
                     "meson.build": self._meson_build,
                     "main.cpp": app},
                    clean_first=True)

        # Build in the cache
        self.t.run("build .")
        self.t.run_command(os.path.join("build", "demo"))

        self.assertIn("Hello World Release!", self.t.out)

        self._check_binary()
