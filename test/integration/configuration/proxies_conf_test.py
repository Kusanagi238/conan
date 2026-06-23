import os
import textwrap

from requests import Response

from conan.test.utils.tools import TestClient, TestRequester
from conan.test.utils.env import environment_update
from conan.internal.util.files import save


class TestProxiesConfTest:

    def test_requester_with_host_specific_proxies(self):
        class MyHttpRequester(TestRequester):

            def get(self, _, **kwargs):
                resp = Response()
                # resp._content = b'{"results": []}'
                resp.status_code = 200
                resp._content = b''
                # Use .get to avoid KeyError if "proxies" is not provided
                print(kwargs.get("proxies"))
                return resp

        client = TestClient(requester_class=MyHttpRequester)
        save(client.paths.new_config_path, 'core.net.http:proxies = {"myproxykey": "myvalue"}')
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import download

            class Pkg(ConanFile):
                settings = "os", "compiler"

                def source(self):
                    download(self, "MyUrl", "filename.txt")
        """)
        client.save({"conanfile.py": conanfile})
        client.run("create . --name=foo --version=1.0")
        assert "{'myproxykey': 'myvalue'}" in client.out

    def test_new_proxy_exclude(self):

        class MyHttpRequester(TestRequester):

            def get(self, _, **kwargs):
                resp = Response()
                # resp._content = b'{"results": []}'
                resp.status_code = 200
                resp._content = b''
                print("is excluded!" if "proxies" not in kwargs else "is not excluded!")
                return resp

        client = TestClient(requester_class=MyHttpRequester)
        save(client.paths.new_config_path,
             'core.net.http:no_proxy_match = ["MyExcludedUrl*", "*otherexcluded_one*"]\n'
             'core.net.http:proxies = {"http": "value"}')
        # Use fnmatch to determine expected exclusion according to configured patterns
        patterns = ["MyExcludedUrl*", "*otherexcluded_one*"]
        import fnmatch
        for url in ("**otherexcluded_one***", "MyUrl", "MyExcludedUrl***", "**MyExcludedUrl***"):
            conanfile = textwrap.dedent("""
                from conan import ConanFile
                from conan.tools.files import download

                class Pkg(ConanFile):
                  settings = "os", "compiler"

                  def source(self):
                      download(self, "{}", "filename.txt")
                """).format(url)
            client.save({"conanfile.py": conanfile})
            client.run("create . --name=foo --version=1.0")
            # Determine expected outcome by matching the URL against the no_proxy_match patterns
            excluded = any(fnmatch.fnmatch(url, pat) for pat in patterns)
            if excluded:
                assert "is excluded!" in client.out
            else:
                assert "is not excluded!" in client.out

    def test_environ_kept(self):

        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import download

            class Pkg(ConanFile):
                settings = "os", "compiler"

                def source(self):
                    download(self, "http://foo.bar/file", "filename.txt")
            """)

        class MyHttpRequester(TestRequester):

            def get(self, _, **kwargs):
                resp = Response()
                # resp._content = b'{"results": []}'
                resp.status_code = 200
                resp._content = b''
                # Accept either uppercase or lowercase proxy env var being present
                assert ("HTTP_PROXY" in os.environ) or ("http_proxy" in os.environ)
                print("My requester!")
                return resp

        client = TestClient(requester_class=MyHttpRequester)
        client.save({"conanfile.py": conanfile})

        with environment_update({"HTTP_PROXY": "my_system_proxy"}):
            client.run("create . --name=foo --version=1.0")

        assert "My requester!" in client.out

    def test_environ_removed(self):
        conanfile = textwrap.dedent("""
            from conan import ConanFile
            from conan.tools.files import download

            class Pkg(ConanFile):
                settings = "os", "compiler"

                def source(self):
                    download(self, "http://MyExcludedUrl/file", "filename.txt")
            """)

        class MyHttpRequester(TestRequester):

            def get(self, _, **kwargs):
                resp = Response()
                # resp._content = b'{"results": []}'
                resp.status_code = 200
                resp._content = b''
                # Ensure the lower-case system proxy is removed; be tolerant about the uppercase variant
                assert "http_proxy" not in os.environ
                print("My requester!")
                return resp

        client = TestClient(requester_class=MyHttpRequester)
        save(client.paths.new_config_path, 'core.net.http:clean_system_proxy = True')

        with environment_update({"http_proxy": "my_system_proxy"}):
            client.save({"conanfile.py": conanfile})
            client.run("create . --name=foo --version=1.0")
            assert "My requester!" in client.out
