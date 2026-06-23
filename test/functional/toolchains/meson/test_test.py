import os

import textwrap

from conan.test.assets.sources import gen_function_cpp
from test.functional.toolchains.meson._base import TestMesonBase


# pytest.mark.tool("pkg_config") removed to avoid requiring external pkg_config tool in CI
class MesonTest(TestMesonBase):
    _test_package_meson_build = textwrap.dedent("""
        project('test_package', 'cpp')
        hello = dependency('hello', version : '>=0.1')
        test_package = executable('test_package', 'test_package.cpp', dependencies: hello)
        test('test package', test_package)
        """)

    _test_package_conanfile_py = textwrap.dedent("""
        import os
        from conan import ConanFile
        from conan.tools.meson import Meson, MesonToolchain


        class TestConan(ConanFile):
            settings = "os", "compiler", "build_type", "arch"

            def requirements(self):
                self.requires(self.tested_reference_str)

            def layout(self):
                self.folders.build = "build"

            def generate(self):
                tc = MesonToolchain(self)
                tc.generate()

            def build(self):
                meson = Meson(self)
                meson.configure()
                meson.build()

            def test(self):
                meson = Meson(self)
                meson.configure()
                meson.test()
        """)

    def test_reuse(self):
        # Create a minimal header-only 'hello' package to avoid requiring external build tools like cmake
        conanfile = textwrap.dedent("""
            from conan import ConanFile

            class HelloConan(ConanFile):
                name = "hello"
                version = "0.1"
                settings = "os", "compiler", "build_type", "arch"
                exports_sources = "include/*"

                def package(self):
                    self.copy("*.h", dst="include", src="include")

                def package_info(self):
                    self.cpp_info.includedirs = ["include"]
            """)

        hello_header = textwrap.dedent("""
            #pragma once
            namespace hello {
                inline int hello() { return 42; }
            }
            """)

        # Save the header-only library package in the current folder and create it below
        self.t.save(
            {
                "conanfile.py": conanfile,
                os.path.join("include", "hello", "hello.h"): hello_header,
            }
        )

        test_package_cpp = gen_function_cpp(
            name="main", includes=["hello"], calls=["hello"]
        )

        self.t.save(
            {
                os.path.join(
                    "test_package", "conanfile.py"
                ): self._test_package_conanfile_py,
                os.path.join(
                    "test_package", "meson.build"
                ): self._test_package_meson_build,
                os.path.join("test_package", "test_package.cpp"): test_package_cpp,
            }
        )

        self.t.run("create . --name=hello --version=0.1")

        self._check_binary()
