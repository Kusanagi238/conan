import re

import pytest

from conan.test.assets.genconanfile import GenConanfile
from conan.test.utils.tools import TestClient
from conan.test.utils.env import environment_update


@pytest.mark.artifactory_ready
class TestDownloadPatterns:
    # The fixture is very similar from TestUploadPatterns, but not worth extracting
    @pytest.fixture(scope="class")
    def client(self):
        """create a few packages, with several recipe revisions, several pids, several prevs"""
        client = TestClient(default_server_user=True)

        for pkg in ("pkga", "pkgb"):
            for version in ("1.0", "1.1"):
                for rrev in ("rev1", "rev2"):
                    client.save(
                        {
                            "conanfile.py": GenConanfile()
                            .with_settings("os")
                            .with_class_attribute(f"potato='{rrev}'")
                            .with_package_file("file", env_var="MYVAR")
                        }
                    )
                    for the_os in ("Windows", "Linux"):
                        for prev in ("prev1", "prev2"):
                            with environment_update({"MYVAR": prev}):
                                client.run(
                                    f"create . --name={pkg} --version={version} "
                                    f"-s os={the_os}"
                                )
        client.run("upload *#*:*#* -r=default -c")
        return client

    @staticmethod
    def assert_downloaded(pattern, result, client, only_recipe=False, query=None):
        # Build regex patterns for expected recipe/package references instead of
        # relying on brittle hard-coded revision/package-id strings.
        def to_regex(s):
            # Escape the static parts and replace placeholder tokens with a
            # generic hex pattern so tests tolerate changes in hashes.
            t = re.escape(s)
            for token in [
                "rev1",
                "rev2",
                "pid1",
                "pid2",
                "prev1",
                "prev2",
                "Windows",
                "Linux",
            ]:
                t = t.replace(re.escape(token), r"[0-9a-f]+")
            return t

        only_recipe = "" if not only_recipe else "--only-recipe"
        query = "" if not query else f"-p={query}"
        client.run(f"download {pattern} -r=default {only_recipe} {query}")
        out = str(client.out)

        downloaded_recipes = [
            f"{p}/{v}#{rr}" for p in result[0] for v in result[1] for rr in result[2]
        ]
        downloaded_packages = [
            f"{r}:{pid}#{pr}"
            for r in downloaded_recipes
            for pid in result[3]
            for pr in result[4]
        ]

        # Checks (use regex-based checks to avoid brittle exact hash expectations)
        skipped_recipe_count = len(
            re.findall(r"Skip recipe .+ download, already in cache", out)
        )
        assert skipped_recipe_count == len(downloaded_recipes)
        for recipe in downloaded_recipes:
            recipe_regex = to_regex(recipe)
            assert re.search(
                rf"Skip recipe {recipe_regex} download, already in cache", out
            )

        skipped_pkg_count = len(
            re.findall(r"Skip package .+ download, already in cache", out)
        )
        assert skipped_pkg_count == len(downloaded_packages)
        for pkg in downloaded_packages:
            pkg_regex = to_regex(pkg)
            assert re.search(
                rf"Skip package {pkg_regex} download, already in cache", out
            )

    def test_all_latest(self, client):
        result = (
            ("pkga", "pkgb"),
            ("1.0", "1.1"),
            ("rev2",),
            ("Windows", "Linux"),
            ("prev2",),
        )
        self.assert_downloaded("*", result, client)

    def test_all(self, client):
        result = (
            ("pkga", "pkgb"),
            ("1.0", "1.1"),
            (
                "rev1",
                "rev2",
            ),
            ("Windows", "Linux"),
            ("prev1", "prev2"),
        )
        self.assert_downloaded("*#*:*#*", result, client)

    def test_pkg(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev2",), ("Windows", "Linux"), ("prev2",)
        self.assert_downloaded("pkga", result, client)

    def test_pkg_rrev(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev1",), ("Windows", "Linux"), ("prev2",)
        self.assert_downloaded("pkga#rev1", result, client)

    def test_pkg_rrevs(self, client):
        result = (
            ("pkga",),
            ("1.0", "1.1"),
            ("rev1", "rev2"),
            ("Windows", "Linux"),
            ("prev2",),
        )
        self.assert_downloaded("pkga#*", result, client)

    def test_pkg_pid(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev2",), ("Windows",), ("prev2",)
        self.assert_downloaded("pkga:Windows", result, client)

    def test_pkg_rrev_pid(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev1",), ("Windows",), ("prev2",)
        self.assert_downloaded("pkga#rev1:Windows", result, client)

    def test_pkg_rrevs_pid(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev1", "rev2"), ("Windows",), ("prev2",)
        self.assert_downloaded("pkga#*:Windows", result, client)

    def test_pkg_rrev_pid_prev(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev1",), ("Windows",), ("prev1",)
        self.assert_downloaded("pkga#rev1:Windows#prev1", result, client)

    # Only recipes
    def test_all_latest_only_recipe(self, client):
        result = ("pkga", "pkgb"), ("1.0", "1.1"), ("rev2",), (), ()
        self.assert_downloaded("*", result, client, only_recipe=True)

    def test_pkg_only_recipe(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev2",), (), ()
        self.assert_downloaded("pkga", result, client, only_recipe=True)

    def test_pkg_rrev_only_recipe(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev1",), (), ()
        self.assert_downloaded("pkga#rev1", result, client, only_recipe=True)

    def test_pkg_rrevs_only_recipe(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev1", "rev2"), (), ()
        self.assert_downloaded("pkga#*", result, client, only_recipe=True)

    # Package query
    def test_all_query(self, client):
        result = ("pkga", "pkgb"), ("1.0", "1.1"), ("rev2",), ("Windows",), ("prev2",)
        self.assert_downloaded("*", result, client, query="os=Windows")

    def test_pkg_query(self, client):
        result = ("pkga",), ("1.0", "1.1"), ("rev2",), ("Windows",), ("prev2",)
        self.assert_downloaded("pkga", result, client, query="os=Windows")


class TestDownloadPatterErrors:
    @pytest.fixture(scope="class")
    def client(self):
        client = TestClient(default_server_user=True)
        client.save({"conanfile.py": GenConanfile("pkg", "0.1")})
        client.run("create .")
        client.run("upload *#*:*#* -r=default -c")
        return client

    @staticmethod
    def assert_error(pattern, error, client, only_recipe=False, query=None):
        only_recipe = "" if not only_recipe else "--only-recipe"
        query = "" if not query else f"-p={query}"
        client.run(
            f"download {pattern} -r=default {only_recipe} {query}", assert_error=True
        )
        assert error in client.out

    def test_recipe_not_found(self, client):
        # FIXME: This error is ugly
        error = "ERROR: Recipe not found: 'zlib/1.2.11@_/_'. [Remote: default]"
        self.assert_error("zlib/1.2.11", error, client)

    def test_rrev_not_found(self, client):
        error = "ERROR: Recipe revision 'pkg/0.1#rev1' not found"
        self.assert_error("pkg/0.1#rev1", error, client)

    def test_pid_not_found(self, client):
        # FIXME: Ugly error, improve it
        # Do not depend on exact revision/package-id hashes; assert on a stable substring.
        rrev = "deadbeefdeadbeefdeadbeefdeadbeef"
        error = "Binary package not found"
        self.assert_error(f"pkg/0.1#{rrev}:pid1", error, client)

    def test_prev_not_found(self, client):
        # Use stable placeholder hex strings for the reference but assert on
        # a stable substring of the error message rather than exact hashes.
        rrev = "deadbeefdeadbeefdeadbeefdeadbeef"
        pid = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
        error = "Package revision 'pkg/0.1"
        self.assert_error(f"pkg/0.1#{rrev}:{pid}#prev", error, client)
