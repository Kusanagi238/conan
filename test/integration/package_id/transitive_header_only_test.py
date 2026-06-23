from conan.test.utils.tools import TestClient, GenConanfile
from conan.internal.util.files import save


class TestTransitiveIds:

    def test_transitive_library(self):
        # https://github.com/conan-io/conan/issues/6450
        client = TestClient(light=True)
        save(client.paths.new_config_path, "core.package_id:default_unknown_mode=full_version_mode")
        client.save({"conanfile.py": GenConanfile()})
        client.run("create . --name=liba --version=1.0")
        client.run("create . --name=liba --version=1.1")
        client.save({"conanfile.py": GenConanfile().with_require("liba/1.0")})
        client.run("create . --name=libb --version=1.0")
        client.save({"conanfile.py": GenConanfile().with_require("libb/1.0")})
        client.run("create . --name=libc --version=1.0")
        client.save({"conanfile.py": GenConanfile().with_require("libc/1.0")
                                                   .with_require("liba/1.0")})
        client.run("create . --name=libd --version=1.0")
        # The consumer forces to depend on liba/2, instead of liba/1
        client.save({"conanfile.py": GenConanfile().with_require("libc/1.0")
                                                   .with_requirement("liba/1.1", force=True)})
        client.run("create . --name=libd --version=1.0", assert_error=True)
        # both B and C require a new binary
        client.assert_listed_binary(
            {"liba/1.1": "Cache",
             "libb/1.0": "Missing",
             "libc/1.0": "Missing",
             "libd/1.0": "Build"
             })

    def test_transitive_major_mode(self):
        # https://github.com/conan-io/conan/issues/6450
        # Test LibE->LibD->LibC->LibB->LibA
        # LibC declares that it only depends on major version changes of its upstream
        # So LibC package ID doesn't change, even if LibA changes
        # But LibD package ID changes, even if its direct dependency LibC doesn't
        client = TestClient(light=True)
        save(client.paths.new_config_path, "core.package_id:default_unknown_mode=full_version_mode")
        # LibA
        client.save({"conanfile.py": GenConanfile()})
        client.run("create . --name=liba --version=1.0")
        client.run("create . --name=liba --version=1.1")
        # libB -> LibA
        client.save({"conanfile.py": GenConanfile().with_require("liba/1.0")})
        client.run("create . --name=libb --version=1.0")
        # libC -> libB
        major_mode = "self.info.requires.major_mode()"
        client.save({"conanfile.py": GenConanfile().with_require("libb/1.0")
                                                   .with_package_id(major_mode)})
        client.run("create . --name=libc --version=1.0")
        # Check the LibC ref with RREV keeps the same
        client.assert_listed_binary({"libc/1.0": "Build"})
        # LibD -> LibC
        client.save({"conanfile.py": GenConanfile().with_require("libc/1.0")})
        client.run("create . --name=libd --version=1.0")
        # LibE -> LibD, LibA/2.0
        client.save({"conanfile.py": GenConanfile().with_require("libd/1.0")
                                                   .with_requirement("liba/1.1", force=True)})
        client.run("create . --name=libe --version=1.0", assert_error=True)
        # Check the LibC ref with RREV keeps the same, it is in cache, not missing
        # But LibD package ID changes and is missing, because it depends transitively on LibA
        client.assert_listed_binary(
            {"liba/1.1": "Cache",
             "libb/1.0": "Missing",
             "libc/1.0": "Cache",
             "libd/1.0": "Missing",
             "libe/1.0": "Build"
             })

    def test_transitive_unrelated(self):
        # https://github.com/conan-io/conan/issues/6450
        client = TestClient(light=True)
        # LibA
        client.save({"conanfile.py": GenConanfile()})
        client.run("create . --name=liba --version=1.0")
        client.run("create . --name=liba --version=2.0")
        # libB -> LibA
        client.save({"conanfile.py": GenConanfile().with_require("liba/1.0")})
        client.run("create . --name=libb --version=1.0")
        # libC -> libB
        unrelated = "self.info.requires['libb'].unrelated_mode()"
        client.save({"conanfile.py": GenConanfile().with_require("libb/1.0")
                    .with_package_id(unrelated)})
        client.run("create . --name=libc --version=1.0")
        # LibD -> LibC
        client.save({"conanfile.py": GenConanfile().with_require("libc/1.0")})
        client.run("create . --name=libd --version=1.0")
        # LibE -> LibD, LibA/2.0
        client.save({"conanfile.py": GenConanfile().with_require("libd/1.0")
                    .with_requirement("liba/2.0", force=True)})
        client.run("create . --name=libe --version=1.0", assert_error=True)
        client.assert_listed_binary({"liba/2.0": "Cache",
                                     "libb/1.0": "Missing",
                                     "libc/1.0": "Missing",
                                     "libd/1.0": "Missing"})

    def test_transitive_second_level_header_only(self):
        # https://github.com/conan-io/conan/issues/6450
        client = TestClient(light=True)
        # LibA
        client.save({"conanfile.py": GenConanfile()})
        client.run("create . --name=liba --version=1.0")
        client.run("create . --name=liba --version=2.0")
        # libB -> LibA
        client.save({"conanfile.py": GenConanfile().with_require("liba/1.0")})
        client.run("create . --name=libb --version=1.0")
        # libC -> libB

        unrelated = "self.info.clear()"
        client.save({"conanfile.py": GenConanfile().with_require("libb/1.0")
                                                   .with_package_id(unrelated)})
        client.run("create . --name=libc --version=1.0")
        # LibD -> LibC
        client.save({"conanfile.py": GenConanfile().with_require("libc/1.0")})
        client.run("create . --name=libd --version=1.0")
        client.assert_listed_binary({"libc/1.0": "Cache"})

        # LibE -> LibD, LibA/2.0
        client.save({"conanfile.py": GenConanfile().with_require("libd/1.0")
                                                   .with_requirement("liba/2.0", force=True)})
        client.run("create . --name=libe --version=1.0", assert_error=True)  # LibD is NOT missing!

        client.assert_listed_binary(
            {"liba/2.0": "Cache",
             "libb/1.0": "Missing",
             "libc/1.0": "Cache",
             "libd/1.0": "Missing"})

    def test_transitive_header_only(self):
        # https://github.com/conan-io/conan/issues/6450
        client = TestClient(light=True)
        save(client.paths.new_config_path, "core.package_id:default_unknown_mode=full_version_mode")
        client.save({"conanfile.py": GenConanfile()})
        client.run("create . --name=liba --version=1.0")
        client.run("create . --name=liba --version=2.0")
        client.save({"conanfile.py": GenConanfile().with_require("liba/1.0")
                                                   .with_package_id("self.info.clear()")})
        client.run("create . --name=libb --version=1.0")
        client.save({"conanfile.py": GenConanfile().with_require("libb/1.0")})
        client.run("create . --name=libc --version=1.0")
        client.save({"conanfile.py": GenConanfile().with_require("libc/1.0")
                                                   .with_require("liba/1.0")})
        client.run("create . --name=libd --version=1.0")
        client.save({"conanfile.py": GenConanfile().with_require("libc/1.0")
                                                   .with_requirement("liba/2.0", force=True)})
        # USE THE NEW FIXED PACKAGE_ID
        client.run("create . --name=libd --version=1.0", assert_error=True)
        client.assert_listed_binary({"liba/2.0": "Cache",
                                     "libb/1.0": "Cache",
                                     "libc/1.0": "Missing",
                                     })
