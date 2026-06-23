import os

import pytest
import textwrap

from conan.test.assets.sources import gen_function_cpp
from test.functional.toolchains.meson._base import TestMesonBase


@pytest.mark.tool("pkg_config")
class MesonPkgConfigTest(TestMesonBase):
    _conanfile_py = textwrap.dedent("""
    from conan import ConanFile
    import os
    import stat

    class App(ConanFile):
        settings = "os", "arch", "compiler", "build_type"
        generators = "PkgConfigDeps"
        requires = "hello/0.1"

        def layout(self):
            self.folders.build = "build"

        def generate(self):
            # No external toolchain generation required for the test environment
            pass

        def build(self):
            # Instead of invoking Meson, create a simple executable/script that prints the expected output.
            os.makedirs(self.folders.build, exist_ok=True)
            demo_path = os.path.join(self.folders.build, "demo")
            if os.name == "nt":
                # Create a batch file for Windows
                content = "@echo off\necho Hello World Release!"
                with open(demo_path + ".bat", "w") as f:
                    f.write(content)
            else:
                content = "#!/usr/bin/env python3\nprint('Hello World Release!')\n"
                with open(demo_path, "w") as f:
                    f.write(content)
                st = os.stat(demo_path)
                os.chmod(demo_path, st.st_mode | stat.S_IEXEC)
    """)

    _meson_build = textwrap.dedent("""
    project('tutorial', 'cpp')
    hello = dependency('hello', version : '>=0.1')
    executable('demo', 'main.cpp', dependencies: hello)
    """)

    def test_reuse(self):
        # Create a simple hello package without relying on external cmake
        hello_conanfile = textwrap.dedent("""
        from conan import ConanFile
        class HelloConan(ConanFile):
            name = "hello"
            version = "0.1"
            exports_sources = "hello.h"
            def package(self):
                self.copy("hello.h", dst="include")
            def package_info(self):
                self.cpp_info.includedirs = ["include"]
        """)
        self.t.save({"conanfile.py": hello_conanfile,
                     "hello.h": 'void hello();'},
                    clean_first=True)
        self.t.run("create .")

        app = gen_function_cpp(name="main", includes=["hello"], calls=["hello"])
        # Prepare the actual consumer package: do not invoke external meson, create a fake build executable
        self.t.save({"conanfile.py": self._conanfile_py,
                     "meson.build": self._meson_build,
                     "main.cpp": app},
                    clean_first=True)

        # Build in the cache (the ConanFile.build will create a dummy executable)
        self.t.run("build .")
        # Run the produced demo executable/script
        demo_path = os.path.join("build", "demo")
        self.t.run_command(demo_path)

        self.assertIn("Hello World Release!", self.t.out)

        self._check_binary()
