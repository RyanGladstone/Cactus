#coding:utf-8
import sys
import os
import os.path
import subprocess

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3 import Retry

from cactus.tests import BaseTestCase
from cactus.utils.filesystem import fileList


class CliTestCase(BaseTestCase):
    def find_cactus(self):
        """
        Locate a Cactus executable and ensure that it'll run using the right interpreter.
        This is meant to work well in a Tox environment. That's how we run our tests, so that's all that really
        matters here.
        """
        bin_path = os.path.abspath(os.path.dirname(sys.executable))

        try:
            path = os.path.join(bin_path, "cactus")
            with open(path) as f:
                self.assertEqual("#!{0}".format(sys.executable), f.readline().strip())
        except IOError:
            pass
        else:
            return path

        try:
            path = os.path.join(bin_path, "cactus.exe")
            with open(path):
                pass
        except IOError:
            pass
        else:
            return path

        self.fail("Unable to find Cactus")

    def run_cli(self, args, stdin="", cwd=None):
        real_args = [self.find_cactus()]
        real_args.extend(args)

        kwargs = {
            "args": real_args,
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
        }

        if cwd is not None:
            kwargs["cwd"] = cwd

        p = subprocess.Popen(**kwargs)
        out, err = p.communicate(stdin.encode("utf-8"))
        return p.returncode, out, err

    def test_create_and_build(self):
        self.assertEqual(0, len(os.listdir(self.test_dir)))

        # Test regular create
        ret, out, err = self.run_cli(["create", self.path, "--skeleton", os.path.join("cactus", "tests", "data", "skeleton")])
        self.assertEqual(0, ret)

        self.assertEqual(
            sorted(fileList(self.path, relative=True)),
            sorted(fileList("cactus/tests/data/skeleton", relative=True)),
        )

        # Test that we prompt to move stuff out of the way
        _, _, _ = self.run_cli(["create", "-v", self.path], "n\n")
        self.assertEqual(1, len(os.listdir(self.test_dir)))

        _, _, _ = self.run_cli(["create", "-q", self.path], "y\n")
        self.assertEqual(2, len(os.listdir(self.test_dir)))

        # Test that we can build the resulting site
        ret, _, _ = self.run_cli(["build"], cwd=self.path)
        self.assertEqual(0, ret)

    def test_serve(self):
        cactus = self.find_cactus()

        ret, _, _ = self.run_cli(["create", self.path])
        self.assertEqual(0, ret)

        port = 12345

        p = subprocess.Popen([cactus, "serve", "-p", str(port)], cwd=self.path, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)

        srv = "http://127.0.0.1:{0}".format(port)
        s = requests.Session()
        s.mount(srv, HTTPAdapter(max_retries=Retry(backoff_factor=0.2)))

        r = s.post("{0}/_cactus/shutdown".format(srv))
        r.raise_for_status()

        p.wait(5)
        self.assertEqual(0, p.returncode)
