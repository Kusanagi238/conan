import pytest

from conan.test.utils.tools import TestClient


@pytest.mark.skipif(__import__('shutil').which("cmake") is None, reason="Required 'cmake' tool is not available")
def test_conan_new_compiles():
    # TODO: Maybe add more templates that are not used in the rest of the test suite?
    tc = TestClient()
    tc.run("new header_lib -d name=hello -d version=1.0 -o=hello")
    tc.run("new header_lib -d name=bye -d version=1.0 -d requires=hello/1.0 -o=bye")

    tc.run("create hello -tf=")
    tc.run("create bye")
